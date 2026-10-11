from __future__ import annotations

import itertools
import unittest
from collections.abc import Callable
from contextlib import contextmanager
from unittest.mock import Mock, patch

from tests import wx_stub

_SCOPE = wx_stub.StubScope(wx_stub.dialog_validation_stubs(), isolate=("dialog", "ui.message_box"))
with _SCOPE.loading():
    import dialog as dialog_module
    from dialog import (
        AddSymbolDialog,
        DictionaryEntriesDialog,
        DictionaryManagementDialog,
        DictionaryNameDialog,
        DocumentNameDialog,
        FileIssuesDialog,
        InvalidWorkspaceFilesDialog,
    )

setUpModule = _SCOPE.activate
tearDownModule = _SCOPE.deactivate

from dictionaries.entries import DictionaryEntry
from dictionaries.manager import DEFAULT_DICTIONARY_NAME, MAX_DICTIONARY_NAME_LENGTH, normalize_dictionary_name
from documents.workspace import normalize_document_name
from i18n import _

DICTIONARY_EMPTY = "請輸入字典名稱。"
DICTIONARY_TOO_LONG = "字典名稱長度需為 1 到 32 個字元。"
DICTIONARY_INVALID = "字典名稱不是有效的 Windows 檔名。"
DICTIONARY_RESERVED = "字典名稱「default」為保留名稱。"
DOCUMENT_EMPTY = "請輸入文件名稱。"
DOCUMENT_TOO_LONG = "文件名稱長度需為 1 到 32 個字元。"
DOCUMENT_INVALID = "文件名稱不是有效的 Windows 檔名。"
INFO_TITLE = "資訊"
CONTEXT_MANAGED_DIALOGS = (
    AddSymbolDialog,
    DictionaryNameDialog,
    DocumentNameDialog,
    InvalidWorkspaceFilesDialog,
    FileIssuesDialog,
    DictionaryEntriesDialog,
    DictionaryManagementDialog,
)


# Pre-P2-1 reference: a verbatim copy of dialog._normalize_dialog_name as it was
# before P2-1 removed it (renamed). Do not edit; it is the oracle for the name dialogs.
def _pre_p2_1_normalize_dialog_name(
    candidate: str,
    normalizer: Callable[[str], str],
    empty_message: str,
    length_message: str,
    invalid_message: str,
    reserved_message: str | None = None,
) -> tuple[str | None, str | None]:
    if not candidate or not candidate.strip():
        return None, empty_message
    if any(ord(char) < 32 for char in candidate):
        return None, invalid_message
    if candidate.endswith((" ", ".")):
        return None, invalid_message
    normalized_candidate = candidate.strip()
    if len(normalized_candidate) > MAX_DICTIONARY_NAME_LENGTH:
        return None, length_message
    try:
        return normalizer(normalized_candidate), None
    except ValueError as exc:
        if reserved_message and normalized_candidate.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
            return None, reserved_message
        if "exceed" in str(exc):
            return None, length_message
        return None, invalid_message


def _pre_p2_1_dictionary_result(candidate: str) -> tuple[str | None, str | None]:
    return _pre_p2_1_normalize_dialog_name(
        candidate,
        normalize_dictionary_name,
        _("Please enter the dictionary name."),
        _("Dictionary name must be 1 to 32 characters."),
        _("Dictionary name is not a valid Windows file name."),
        _('Dictionary name "{name}" is reserved.').format(name=DEFAULT_DICTIONARY_NAME),
    )


def _pre_p2_1_document_result(candidate: str) -> tuple[str | None, str | None]:
    return _pre_p2_1_normalize_dialog_name(
        candidate,
        normalize_document_name,
        _("Please enter the document name."),
        _("Document name must be 1 to 32 characters."),
        _("Document name is not a valid Windows file name."),
    )


def _name_corpus() -> list[str]:
    """Every string of up to 3 pieces from ALPHABET, plus WORDS with one piece added at either end."""
    alphabet = ["", " ", ".", "\t", "\u3000", "\xa0", "\x85", "a", "?", "C", "O", "N", "d", "\x7f", "x."]
    words = [
        "default",
        "Default",
        "DEFAULT",
        "default.",
        " default",
        "default\u3000",
        "CON",
        "con.txt",
        "COM1",
        "LPT9.a",
        "..",
        ".",
        "a" * 32,
        "a" * 33,
        " " + "a" * 32,
        "a" * 32 + "\u3000",
        "a" * 31 + ".",
        "\u3000" * 40,
        "a" * 33 + " ",
    ]
    corpus = set(words)
    for length in range(4):
        for pieces in itertools.product(alphabet, repeat=length):
            corpus.add("".join(pieces))
    for word in words:
        for piece in alphabet:
            corpus.add(piece + word)
            corpus.add(word + piece)
    return sorted(corpus)


NAME_CORPUS = _name_corpus()


class _TextCtrl:
    def __init__(self) -> None:
        self.value = None
        self.focused = False
        self.selected_all = False

    def SetValue(self, value: str) -> None:
        self.value = value

    def GetValue(self) -> str:
        return self.value or ""

    def SetFocus(self) -> None:
        self.focused = True

    def SelectAll(self) -> None:
        self.selected_all = True


class DialogValidationTextTest(unittest.TestCase):
    def test_dictionary_name_validation_mentions_32_characters(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertEqual(
            DictionaryNameDialog._validate_name(dialog, "a" * 33),
            "字典名稱長度需為 1 到 32 個字元。",
        )

    def test_document_name_validation_mentions_32_characters(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        self.assertEqual(
            DocumentNameDialog._validate_name(dialog, "a" * 33),
            "文件名稱長度需為 1 到 32 個字元。",
        )

    def test_dictionary_name_dialog_applies_initial_name(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)
        dialog.name_ctrl = _TextCtrl()

        DictionaryNameDialog._apply_initial_name(dialog, "1.1")

        self.assertEqual(dialog.name_ctrl.value, "1.1")
        self.assertTrue(dialog.name_ctrl.focused)
        self.assertTrue(dialog.name_ctrl.selected_all)

    def test_dictionary_name_validation_accepts_windows_valid_names(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertIsNone(DictionaryNameDialog._validate_name(dialog, "1.1"))
        self.assertIsNone(DictionaryNameDialog._validate_name(dialog, "name\u3000"))

    def test_dictionary_name_validation_rejects_windows_invalid_names(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        for name in ("name.", "name ", "name\t", " name ", "CON", "a?b"):
            with self.subTest(name=name):
                self.assertEqual(
                    DictionaryNameDialog._validate_name(dialog, name),
                    "字典名稱不是有效的 Windows 檔名。",
                )

    def test_dictionary_name_validation_keeps_reserved_default_message(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)

        self.assertEqual(
            DictionaryNameDialog._validate_name(dialog, "default"),
            "字典名稱「default」為保留名稱。",
        )

    def test_document_name_validation_accepts_windows_valid_names(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        self.assertIsNone(DocumentNameDialog._validate_name(dialog, "1.1"))
        self.assertIsNone(DocumentNameDialog._validate_name(dialog, "name\u3000"))

    def test_document_name_validation_rejects_windows_invalid_names(self) -> None:
        dialog = object.__new__(DocumentNameDialog)

        for name in ("name.", "name ", "name\t", " name ", "CON", "a?b"):
            with self.subTest(name=name):
                self.assertEqual(
                    DocumentNameDialog._validate_name(dialog, name),
                    "文件名稱不是有效的 Windows 檔名。",
                )

    def test_name_with_a_lone_surrogate_shows_the_existing_invalid_name_message(self) -> None:
        # F-5 review M-1: no new string; the name dialogs reuse their invalid-name message.
        for dialog_class, message in ((DocumentNameDialog, DOCUMENT_INVALID), (DictionaryNameDialog, DICTIONARY_INVALID)):
            dialog = object.__new__(dialog_class)
            for name in ("a\ud800", "\udc00b"):
                with self.subTest(dialog=dialog_class.__name__, name=ascii(name)):
                    self.assertEqual(dialog_class._validate_name(dialog, name), message)


class _RecordingNameCtrl:
    def __init__(self, value: str, events: list[tuple]) -> None:
        self.value = value
        self.events = events

    def GetValue(self) -> str:
        return self.value

    def SetValue(self, value: str) -> None:
        self.events.append(("SetValue", value))

    def SetFocus(self) -> None:
        self.events.append(("SetFocus",))


class _RecordingEvent:
    def __init__(self, events: list[tuple]) -> None:
        self.events = events

    def Skip(self) -> None:
        self.events.append(("Skip",))


class _NameDialogHarness:
    """Runs a name dialog's real ``_on_ok`` with a recording text box, event and message box."""

    @contextmanager
    def recording_message_box(self):
        events: list[tuple] = []

        def message_box(*args, **kwargs):
            events.append(("MessageBox", args, kwargs))

        with (
            patch.object(dialog_module, "message_box", message_box),
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
        ):
            yield events

    def run_on_ok(self, dialog_class, text: str, events: list[tuple]) -> object:
        events.clear()
        dialog = object.__new__(dialog_class)
        dialog.name_ctrl = _RecordingNameCtrl(text, events)
        dialog_class._on_ok(dialog, _RecordingEvent(events))
        return dialog

    def on_ok_outcome(self, dialog_class, text: str, events: list[tuple]) -> tuple[str, str]:
        """("message", text) for box-then-focus, ("accepted", name) for set-then-skip, else ("unexpected", events)."""
        dialog = self.run_on_ok(dialog_class, text, events)
        if (
            len(events) == 2
            and events[0][0] == "MessageBox"
            and events[0][1][1:] == (INFO_TITLE, 132)
            and events[0][2] == {"parent": dialog}
            and events[1] == ("SetFocus",)
        ):
            return "message", events[0][1][0]
        if len(events) == 2 and events[0][0] == "SetValue" and events[1] == ("Skip",):
            return "accepted", events[0][1]
        return "unexpected", repr(events)


class NameDialogOracleTest(_NameDialogHarness, unittest.TestCase):
    def assert_matches_oracle(self, dialog_class, oracle) -> None:
        self.assertEqual(len(NAME_CORPUS), 3431)
        mismatches = []
        with self.recording_message_box() as events:
            for name in NAME_CORPUS:
                normalized, message = oracle(name)
                expected = ("message", message) if message else ("accepted", normalized)
                validated = dialog_class._validate_name(object.__new__(dialog_class), name)
                outcome = self.on_ok_outcome(dialog_class, name, events)
                if validated != message or outcome != expected:
                    mismatches.append((name, expected, validated, outcome))
        self.assertEqual(mismatches, [])

    def test_dictionary_name_dialog_matches_the_pre_p2_1_validation(self) -> None:
        self.assert_matches_oracle(DictionaryNameDialog, _pre_p2_1_dictionary_result)

    def test_document_name_dialog_matches_the_pre_p2_1_validation(self) -> None:
        self.assert_matches_oracle(DocumentNameDialog, _pre_p2_1_document_result)


NAME_MESSAGE_TABLE = (
    ("", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
    ("   ", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
    ("\u3000", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
    ("\t", DICTIONARY_EMPTY, DOCUMENT_EMPTY),
    ("a\x01b", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("name ", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("name.", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("name\u3000", None, None),
    (" name", None, None),
    ("a" * 32, None, None),
    ("a" * 33, DICTIONARY_TOO_LONG, DOCUMENT_TOO_LONG),
    (" " + "a" * 32, None, None),
    (" " + "a" * 33, DICTIONARY_TOO_LONG, DOCUMENT_TOO_LONG),
    ("a?b", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("CON", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("con.txt", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("..", DICTIONARY_INVALID, DOCUMENT_INVALID),
    ("default", DICTIONARY_RESERVED, None),
    ("Default", DICTIONARY_RESERVED, None),
    ("DEFAULT", DICTIONARY_RESERVED, None),
)


class NameDialogMessageTableTest(unittest.TestCase):
    def test_dictionary_name_dialog_messages(self) -> None:
        dialog = object.__new__(DictionaryNameDialog)
        for name, expected, _document_expected in NAME_MESSAGE_TABLE:
            with self.subTest(name=name):
                self.assertEqual(DictionaryNameDialog._validate_name(dialog, name), expected)

    def test_document_name_dialog_messages(self) -> None:
        dialog = object.__new__(DocumentNameDialog)
        for name, _dictionary_expected, expected in NAME_MESSAGE_TABLE:
            with self.subTest(name=name):
                self.assertEqual(DocumentNameDialog._validate_name(dialog, name), expected)


class NameDialogOkTest(_NameDialogHarness, unittest.TestCase):
    def assert_rejects(self, dialog_class, cases) -> None:
        with self.recording_message_box() as events:
            for name, message in cases:
                with self.subTest(name=name):
                    dialog = self.run_on_ok(dialog_class, name, events)
                    self.assertEqual(
                        events,
                        [("MessageBox", (message, INFO_TITLE, 132), {"parent": dialog}), ("SetFocus",)],
                    )

    def assert_accepts(self, dialog_class, cases) -> None:
        with self.recording_message_box() as events:
            for name, normalized in cases:
                with self.subTest(name=name):
                    self.run_on_ok(dialog_class, name, events)
                    self.assertEqual(events, [("SetValue", normalized), ("Skip",)])

    def test_dictionary_on_ok_shows_the_message_then_focuses_and_stays_open(self) -> None:
        self.assert_rejects(
            DictionaryNameDialog,
            (("", DICTIONARY_EMPTY), ("a" * 33, DICTIONARY_TOO_LONG), ("CON", DICTIONARY_INVALID), ("Default", DICTIONARY_RESERVED)),
        )

    def test_dictionary_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
        self.assert_accepts(DictionaryNameDialog, ((" name", "name"), ("name\u3000", "name"), ("1.1", "1.1")))

    def test_document_on_ok_shows_the_message_then_focuses_and_stays_open(self) -> None:
        self.assert_rejects(
            DocumentNameDialog,
            (("", DOCUMENT_EMPTY), ("a" * 33, DOCUMENT_TOO_LONG), ("CON", DOCUMENT_INVALID)),
        )

    def test_document_on_ok_writes_back_the_normalized_name_then_skips(self) -> None:
        self.assert_accepts(DocumentNameDialog, ((" name", "name"), ("name\u3000", "name"), ("Default", "Default")))


class AddSymbolDialogOkTest(unittest.TestCase):
    def test_invalid_entry_shows_the_message_on_the_dialog_and_focuses_the_source_text(self) -> None:
        # Message box call site 1 of F-7: the entry dialog's own validation message.
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: DictionaryEntry("", "x", "General")
        dialog._is_duplicate = None
        event = Mock()

        with (
            patch.object(dialog_module, "message_box") as message_box,
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
        ):
            AddSymbolDialog._on_ok(dialog, event)

        message_box.assert_called_once_with(_("Please enter the source text."), INFO_TITLE, 132, parent=dialog)
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()


class AddSymbolDialogDuplicateTest(unittest.TestCase):
    """The duplicate check runs in the entry dialog's OK, after the format checks (F-11 D8)."""

    ERROR_TITLE = "錯誤"

    def make_dialog(self, entry: DictionaryEntry, is_duplicate):
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.braille_ctrl = _TextCtrl()
        dialog.get_entry = lambda: entry
        dialog._is_duplicate = is_duplicate
        return dialog

    def press_ok(self, dialog):
        event = Mock()
        with (
            patch.object(dialog_module, "message_box") as message_box,
            patch.object(dialog_module.wx, "OK", 4, create=True),
            patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
            patch.object(dialog_module.wx, "ICON_ERROR", 512, create=True),
        ):
            AddSymbolDialog._on_ok(dialog, event)
        return message_box, event

    def test_duplicate_shows_the_message_on_the_entry_dialog_keeps_it_open_and_selects_the_source_text(self) -> None:
        # P2-2 Q6: the entry dialog closed first and the typed entry was lost.
        is_duplicate = Mock(return_value=True)
        dialog = self.make_dialog(DictionaryEntry("Alpha", "⠁", "General"), is_duplicate)

        message_box, event = self.press_ok(dialog)

        is_duplicate.assert_called_once_with("Alpha")
        message_box.assert_called_once_with('來源文字「Alpha」已存在。', self.ERROR_TITLE, 4 | 512, parent=dialog)
        self.assertTrue(dialog.identifier_ctrl.focused)
        self.assertTrue(dialog.identifier_ctrl.selected_all)
        self.assertFalse(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()

    def test_format_is_checked_before_the_duplicate(self) -> None:
        is_duplicate = Mock(return_value=True)
        dialog = self.make_dialog(DictionaryEntry("Alpha", "abc", "Braille"), is_duplicate)

        message_box, event = self.press_ok(dialog)

        is_duplicate.assert_not_called()
        message_box.assert_called_once_with(_("Please enter the a valid Unicode Braille sequence."), INFO_TITLE, 4 | 128, parent=dialog)
        self.assertTrue(dialog.braille_ctrl.focused)
        event.Skip.assert_not_called()

    def test_entry_that_is_not_a_duplicate_closes_the_dialog(self) -> None:
        for is_duplicate in (Mock(return_value=False), None):
            with self.subTest(check=is_duplicate is not None):
                dialog = self.make_dialog(DictionaryEntry("Alpha", "⠁", "General"), is_duplicate)

                message_box, event = self.press_ok(dialog)

                message_box.assert_not_called()
                event.Skip.assert_called_once_with()


class _Choice:
    def __init__(self, selection: int) -> None:
        self.selection = selection

    def GetSelection(self) -> int:
        return self.selection


class AddSymbolDialogEntryTest(unittest.TestCase):
    def make_dialog(self, text: str, braille: str, type_index: int):
        dialog = object.__new__(AddSymbolDialog)
        dialog.identifier_ctrl = _TextCtrl()
        dialog.identifier_ctrl.SetValue(text)
        dialog.braille_ctrl = _TextCtrl()
        dialog.braille_ctrl.SetValue(braille)
        dialog.type_choice = _Choice(type_index)
        return dialog

    def entry(self, text: str, braille: str, type_index: int) -> DictionaryEntry:
        with patch.object(dialog_module.wx, "NOT_FOUND", -1, create=True):
            return AddSymbolDialog.get_entry(self.make_dialog(text, braille, type_index))

    def test_a_bopomofo_sequence_loses_only_its_leading_whitespace(self) -> None:
        # F-11 (D14, decided by the user 2026-10-11): the trailing tone space is kept as
        # typed, and none is appended.
        self.assertEqual(self.entry(" 中心 ", " ㄓㄨㄥ ㄒㄧㄣ ", 1), DictionaryEntry("中心", "ㄓㄨㄥ ㄒㄧㄣ ", "Bopomofo"))
        self.assertEqual(self.entry("媽", "ㄇㄚ", 1), DictionaryEntry("媽", "ㄇㄚ", "Bopomofo"))
        self.assertEqual(self.entry("媽", "\tㄇㄚ  ", 1), DictionaryEntry("媽", "ㄇㄚ  ", "Bopomofo"))
        self.assertEqual(self.entry("肚子", "ㄉㄨˋㄗ˙ ", 1), DictionaryEntry("肚子", "ㄉㄨˋㄗ˙ ", "Bopomofo"))

    def test_other_types_are_stripped_on_both_sides(self) -> None:
        self.assertEqual(self.entry("媽", " ㄇㄚ ", 0), DictionaryEntry("媽", "ㄇㄚ", "General"))
        self.assertEqual(self.entry("點", " ⠁ ", 2), DictionaryEntry("點", "⠁", "Braille"))

    def test_ok_rejects_a_missing_tone_space_and_accepts_the_typed_one(self) -> None:
        for braille, accepted in (("ㄇㄚ", False), ("ㄇㄚ  ", False), ("ㄇㄚ ", True), (" ㄇㄚ ", True)):
            with self.subTest(braille=braille):
                dialog = self.make_dialog("媽", braille, 1)
                dialog._is_duplicate = None
                event = Mock()
                with (
                    patch.object(dialog_module, "message_box") as message_box,
                    patch.object(dialog_module.wx, "NOT_FOUND", -1, create=True),
                    patch.object(dialog_module.wx, "OK", 4, create=True),
                    patch.object(dialog_module.wx, "ICON_INFORMATION", 128, create=True),
                ):
                    AddSymbolDialog._on_ok(dialog, event)

                if accepted:
                    message_box.assert_not_called()
                    event.Skip.assert_called_once_with()
                else:
                    message_box.assert_called_once_with("請輸入有效的注音序列。", INFO_TITLE, 132, parent=dialog)
                    self.assertTrue(dialog.braille_ctrl.focused)
                    event.Skip.assert_not_called()


class DialogContextManagerTest(unittest.TestCase):
    def make_dialog(self, dialog_class):
        dialog = object.__new__(dialog_class)
        dialog.Destroy = Mock()
        return dialog

    def test_with_returns_the_dialog_and_destroys_it_once(self) -> None:
        for dialog_class in CONTEXT_MANAGED_DIALOGS:
            with self.subTest(dialog=dialog_class.__name__):
                dialog = self.make_dialog(dialog_class)
                with dialog as entered:
                    self.assertIs(entered, dialog)
                    dialog.Destroy.assert_not_called()
                dialog.Destroy.assert_called_once_with()

    def test_with_destroys_the_dialog_and_propagates_an_exception(self) -> None:
        for dialog_class in CONTEXT_MANAGED_DIALOGS:
            with self.subTest(dialog=dialog_class.__name__):
                dialog = self.make_dialog(dialog_class)
                error = RuntimeError("boom")
                with self.assertRaises(RuntimeError) as caught:
                    with dialog:
                        raise error
                self.assertIs(caught.exception, error)
                dialog.Destroy.assert_called_once_with()

    def test_exit_returns_none(self) -> None:
        for dialog_class in CONTEXT_MANAGED_DIALOGS:
            with self.subTest(dialog=dialog_class.__name__):
                dialog = self.make_dialog(dialog_class)
                self.assertIsNone(dialog.__exit__(None, None, None))
                self.assertIsNone(dialog.__exit__(ValueError, ValueError("x"), None))
                self.assertEqual(dialog.Destroy.call_count, 2)


if __name__ == "__main__":
    unittest.main()
