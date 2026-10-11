import ast
import gettext
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import i18n


CLIENT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_SETUP_FUNCTIONS = {"resource_path", "_resource_path"}
LEGACY_SETUP_GLOBALS = {"LOCALE_DOMAIN", "LOCALE_LANGUAGES", "_translation", "_"}


def _module_tree(relative_path: str) -> ast.Module:
    path = CLIENT_ROOT / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class ResourcePathTest(unittest.TestCase):
    def test_resource_path_defaults_to_client_root(self) -> None:
        self.assertEqual(i18n.CLIENT_ROOT, CLIENT_ROOT)
        self.assertEqual(i18n.resource_path("data"), CLIENT_ROOT / "data")
        catalog = i18n.resource_path("locales") / "zh_TW" / "LC_MESSAGES" / "dotexpress.mo"
        self.assertTrue(catalog.is_file(), catalog)

    def test_resource_path_uses_meipass_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as bundle_dir:
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", bundle_dir, create=True):
                self.assertEqual(i18n.resource_path("locales"), Path(bundle_dir) / "locales")

    def test_resource_path_ignores_frozen_without_meipass(self) -> None:
        self.assertFalse(hasattr(sys, "_MEIPASS"))
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(i18n.resource_path("locales"), CLIENT_ROOT / "locales")


class TranslationTest(unittest.TestCase):
    def test_translates_known_msgids_to_zh_tw(self) -> None:
        self.assertEqual(i18n.LOCALE_DOMAIN, "dotexpress")
        self.assertEqual(i18n.LOCALE_LANGUAGES, ("zh_TW",))
        self.assertIsInstance(i18n.load_translation(), gettext.GNUTranslations)
        self.assertEqual(i18n._("General"), "一般")
        self.assertEqual(i18n._("Startup Error"), "啟動錯誤")

    def test_unreadable_dictionary_strings_are_translated(self) -> None:
        # F-6: the count column, the label of the reason field, the headline and the four reasons.
        expected = {
            "Unreadable": "無法讀取",
            "Why this dictionary cannot be read:": "無法讀取的原因：",
            'Dictionary "{name}" cannot be read.': "無法讀取字典「{name}」。",
            'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
            "for example with Save As in Excel.": "檔案不是以 UTF-8 儲存。請重新存成「CSV UTF-8 (逗號分隔)」格式，"
            "例如在 Excel 中使用「另存新檔」。",
            "The file cannot be opened. It may be in use by another program, or you may not have "
            "permission to read it. Close the other program and try again.": "無法開啟檔案。檔案可能正被其他程式使用，"
            "或你沒有讀取權限。請關閉其他程式後再試一次。",
            "The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}": (
                "檔案不是有效的 CSV 檔案。請檢查是否有未成對的引號。詳細資訊：{error}"
            ),
            "The file cannot be read: {error}": "無法讀取檔案：{error}",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_recovery_strings_are_translated(self) -> None:
        # F-8 (D4): the box that names the documents startup put back.
        message = (
            "DotExpress was interrupted while saving or renaming a document. These documents were "
            "recovered:\n\n{names}\n\nCheck that their content is what you expect."
        )
        expected = {
            "Documents Recovered": "已復原文件",
            message: "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)
        self.assertEqual(
            translation.gettext(message).format(names="alpha\nbeta"),
            "DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\nalpha\nbeta\n\n請確認內容是否正確。",
        )

    def test_replaced_character_strings_are_translated(self) -> None:
        # F-8 (D13): the box shown when a document whose U+0000 was replaced is first opened.
        message = (
            'Some characters in document "{name}" cannot be shown ({count} in all). Each one has been '
            "replaced with the replacement character {mark}, so the text after it is kept.\n\n"
            "Delete or change these {mark} characters before converting. Otherwise each one "
            "appears in the braille as an escape code."
        )
        expected = {
            "Characters Replaced": "已取代字元",
            message: "文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。"
            "\n\n轉換前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)
        self.assertEqual(
            translation.gettext(message).format(name="alpha", count=3, mark="\ufffd"),
            "文件「alpha」中有 3 個無法顯示的字元，已全部以替代字元 \ufffd 標示，後面的文字都保留下來了。"
            "\n\n轉換前請刪除或修改這些 \ufffd，否則每一個都會在點字中變成一段跳脫碼。",
        )

    def test_conversion_result_saved_string_is_translated(self) -> None:
        # F-9 (D2): a conversion result written to the document that started it while
        # another document is open.
        message = 'Conversion completed. The result was saved to document "{name}".'
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "轉換完成。結果已儲存到文件「{name}」。")
        self.assertEqual(translation.gettext(message).format(name="alpha"), "轉換完成。結果已儲存到文件「alpha」。")

    def test_dictionary_editor_failure_string_is_translated(self) -> None:
        # F-11 (D12): building the dictionary editor failed for a reason other than its file.
        message = "Failed to open the dictionary editor: {error}"
        translation = i18n.load_translation()

        self.assertEqual(translation.gettext(message), "無法開啟字典編輯器：{error}")

    def test_hidden_rows_box_strings_are_translated(self) -> None:
        # F-11 (D1): the box that lists the rows the editor cannot show before removing them.
        message = (
            'Some rows of dictionary "{name}" cannot be shown in the editor. Saving removes them from the file:'
            "\n\n{rows}\n\nDo you want to remove these rows and save the dictionary?"
        )
        expected = {
            "Remove Rows That Cannot Be Shown": "移除無法顯示的列",
            message: "字典「{name}」中有些列無法在編輯器中顯示，儲存時會從檔案中移除：\n\n{rows}\n\n要移除這些列並儲存字典嗎？",
            "Row {line}: no source text": "第 {line} 列：沒有來源文字",
            'Row {line}: "{text}", Bopomofo "{bopomofo}" is not valid': "第 {line} 列：「{text}」的注音「{bopomofo}」格式不正確",
            "Other rows not listed: {count}": "另有 {count} 列未列出",
            "Remove and &Save": "移除並儲存(&S)",
            "&Back to Editing": "返回編輯(&B)",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_discard_changes_box_strings_are_translated(self) -> None:
        # F-11 (D7): Cancel, Esc or the close box after a change in the dictionary editor.
        expected = {
            "Unsaved Changes": "尚未儲存的變更",
            'Do you want to discard the changes you made to dictionary "{name}"?': "要放棄對字典「{name}」所做的變更嗎？",
            "&Discard Changes": "放棄變更(&D)",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unrecognized_dictionary_header_string_is_translated(self) -> None:
        # F-11 review M-1: OK in the dictionary editor on a file whose header names no text column.
        message = (
            'Dictionary "{name}" cannot be saved: its header is not recognized. '
            "The first line of the file must contain the text, braille, and type headers."
        )
        translation = i18n.load_translation()

        self.assertEqual(
            translation.gettext(message),
            "無法儲存字典「{name}」：無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。",
        )

    def test_export_summary_and_conversion_fallback_strings_are_translated(self) -> None:
        # F-12 (D1, D2): the Export All summary (its three texts revived from obsolete catalog
        # entries) and the two public conversion fallback texts; all were English (P1-4 defect 4).
        expected = {
            "Export Complete with Errors": "匯出完成，但有錯誤",
            "All documents were exported successfully.": "所有文件皆已成功匯出。",
            "Exported documents: {success_count}\nFailed documents: {failure_count}\n\n{failures}": (
                "成功匯出的文件：{success_count}\n匯出失敗的文件：{failure_count}\n\n{failures}"
            ),
            "An unknown error occurred.": "發生不明的錯誤。",
            "The selected translation table could not translate this text.": "選取的轉譯表無法轉譯這段文字。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_import_problem_strings_are_translated(self) -> None:
        # F-12 (D3): the reasons of the Import Issues dialog; the DEP one is revived from an
        # obsolete catalog entry.
        expected = {
            "The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.": (
                "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"
            ),
            "This file type cannot be imported.": "無法匯入這種類型的檔案。",
            "The file name extension does not match the selected file type.": "副檔名與選取的檔案類型不符。",
            "Imported file must be a valid DotExpress DEP package.": "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。",
            "This PDF file is encrypted and cannot be imported.": "這個 PDF 檔已加密，無法匯入。",
            "The EPUB file is damaged or has no readable content.": "EPUB 檔已損壞，或沒有可讀取的內容。",
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unreadable_dictionary_conversion_strings_are_translated(self) -> None:
        # F-12 (D4): a conversion that cannot read the selected dictionary; the header reason
        # uses the words of F-11's message for the editor.
        expected = {
            'Dictionary "{name}" cannot be read. {reason}': "無法讀取字典「{name}」。{reason}",
            "Its header is not recognized. The first line of the file must contain the text, braille, and type headers.": (
                "無法辨識檔案的表頭。檔案的第一列必須包含 text、braille 與 type 表頭。"
            ),
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unlisted_entry_strings_are_translated(self) -> None:
        # F-12 (D5): a document name held by a file in the workspace folder that is not listed.
        expected = {
            'The name "{name}" is used by "{file}" in the workspace folder, but that file is not in the document list.': (
                "名稱「{name}」已被工作區資料夾中的「{file}」使用，但這個檔案不在文件清單中。"
            ),
            "Choose another name, or move or delete that file. Workspace folder:\n{folder}": (
                "請改用其他名稱，或將這個檔案移走或刪除。工作區資料夾：\n{folder}"
            ),
        }
        translation = i18n.load_translation()

        self.assertEqual({msgid: translation.gettext(msgid) for msgid in expected}, expected)

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

    def test_load_translation_falls_back_without_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as empty_dir:
            translation = i18n.load_translation(localedir=Path(empty_dir))

        self.assertIs(type(translation), gettext.NullTranslations)
        self.assertEqual(translation.gettext("General"), "General")

    def test_n_returns_message_unchanged(self) -> None:
        message = "General"

        self.assertIs(i18n.N_(message), message)
        self.assertEqual(i18n.N_("General"), "General")

    def test_language_does_not_follow_environment(self) -> None:
        env = dict(os.environ, LANGUAGE="en_US", LANG="C", LC_ALL="C", PYTHONIOENCODING="utf-8")
        env.pop("PYTHONSAFEPATH", None)

        result = subprocess.run(
            [sys.executable, "-c", "from i18n import _; print(_('General'))"],
            cwd=CLIENT_ROOT,
            env=env,
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "一般")


class SharedSetupConsumerTest(unittest.TestCase):
    def assert_uses_shared_i18n(self, relative_path: str, expected_names: set[str]) -> None:
        tree = _module_tree(relative_path)
        from_i18n = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "i18n" and node.level == 0
            for alias in node.names
        }
        plain_imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assigned = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        self.assertEqual(from_i18n, expected_names, f"{relative_path} must import {sorted(expected_names)} from i18n")
        self.assertNotIn("gettext", plain_imports, f"{relative_path} still imports gettext")
        self.assertEqual(functions & LEGACY_SETUP_FUNCTIONS, set(), f"{relative_path} still defines its own resource path")
        self.assertEqual(assigned & LEGACY_SETUP_GLOBALS, set(), f"{relative_path} still builds its own catalog")

    def test_dialog_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("dialog.py", {"N_", "_"})

    def test_settings_dialogs_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("settings/dialogs.py", {"_"})

    def test_settings_options_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("settings/options.py", {"N_"})

    def test_dictionary_entries_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("dictionaries/entries.py", {"_"})

    def test_about_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("about.py", {"_"})

    def test_gui_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("gui.py", {"_", "resource_path"})


class DuplicateSetupGuardTest(unittest.TestCase):
    SETUP_PATTERN = re.compile(
        r"gettext\.translation\(|^\s*import gettext|_MEIPASS|def _?resource_path|LOCALE_LANGUAGES",
        re.MULTILINE,
    )
    SKIPPED_DIRS = {"tests", ".venv", "__pycache__"}
    SKIPPED_FILES = {"i18n.py", "braille/tables/__tables.py"}

    def test_no_module_duplicates_translation_setup(self) -> None:
        offenders = []
        for dirpath, dirnames, filenames in os.walk(CLIENT_ROOT):
            dirnames[:] = sorted(name for name in dirnames if name not in self.SKIPPED_DIRS)
            for filename in sorted(filenames):
                path = Path(dirpath) / filename
                relative = path.relative_to(CLIENT_ROOT).as_posix()
                if not filename.endswith(".py") or relative in self.SKIPPED_FILES:
                    continue
                for match in self.SETUP_PATTERN.finditer(path.read_text(encoding="utf-8")):
                    offenders.append(f"{relative}: {match.group(0).strip()}")

        self.assertEqual(offenders, [])


class ExtractionMarkerTest(unittest.TestCase):
    # The strings that the marker tuple in gui.py kept extractable before P1-2
    # (its 48 entries minus the four import filters that nothing displays).
    # Each one is now marked with _() or N_() where it is defined.
    FORMER_MARKER_MSGIDS = (
        "Add",
        "Edit",
        "Delete",
        "Import",
        "Export",
        "Open",
        "Dual View",
        "Rename",
        "Default",
        "Braille Font",
        "SimBraille",
        "Export All",
        "DEP",
        "Package DEP",
        "TXT",
        "PDF",
        "DOCX",
        "EPUB",
        "BRL",
        "Braille BRL",
        "Dual View HTML",
        "Delete All",
        "Translation",
        "No conversion data is available for this document.",
        "Convert",
        "Settings",
        "Dictionary Management...",
        "Text Processing",
        "Text Processing Python Code",
        "Unable to open text processing script: {error}",
        "Unable to save text processing script: {error}",
        "Text processing failed: {error}",
        "The script must define exactly one top-level synchronous main function.",
        "main must define exactly one positional parameter and no other parameters.",
        "Confirm Delete Dictionary",
        "Do you want to delete dictionary \"{name}\"?",
        "Rename Dictionary",
        "Help",
        "Coseeing Website",
        "About DotExpress",
        "CSV files (*.csv)|*.csv",
        "DotExpress files (*.dep)|*.dep",
        "Braille files (*.brl)|*.brl",
        "All Supported Files",
    )

    def test_former_marker_strings_are_still_extracted(self) -> None:
        extracted = set()
        for dirpath, dirnames, filenames in os.walk(CLIENT_ROOT):
            dirnames[:] = [name for name in dirnames if name not in {"tests", ".venv", "__pycache__"}]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                path = Path(dirpath) / filename
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id in {"_", "N_"}
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        extracted.add(node.args[0].value)

        self.assertEqual(len(self.FORMER_MARKER_MSGIDS), 44)
        self.assertEqual(sorted(set(self.FORMER_MARKER_MSGIDS) - extracted), [])

    def test_export_summary_and_conversion_fallback_texts_are_marked_where_defined(self) -> None:
        # F-12 (D1, D2): these values are translated where they are shown, so each must be an
        # N_ call where it is defined, or it stays English.
        tree = _module_tree("documents/export_results.py")
        values = {
            target.id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        names = (
            "EXPORT_COMPLETE_TITLE",
            "EXPORT_COMPLETE_WITH_ERRORS_TITLE",
            "EXPORT_ALL_SUCCESS_MESSAGE",
            "EXPORT_ALL_PARTIAL_MESSAGE",
        )
        self.assertEqual(
            {name: ast.unparse(values[name].func) if isinstance(values[name], ast.Call) else None for name in names},
            dict.fromkeys(names, "N_"),
        )
        returns = [
            ast.unparse(node.value)
            for node in sorted(
                (node for node in ast.walk(_module_tree("conversion/plain_text.py")) if isinstance(node, ast.Return)),
                key=lambda node: node.lineno,
            )
        ]
        self.assertEqual(
            returns,
            [
                "N_('An unknown error occurred.')",
                "N_('The selected translation table could not translate this text.')",
                "message",
            ],
        )

    def test_generate_pot_extracts_n_keyword(self) -> None:
        script = (CLIENT_ROOT.parent / "scripts" / "generate-pot.bat").read_text(encoding="utf-8")

        self.assertIn("xgettext --language=Python --keyword=_ --keyword=N_ --files-from=", script)


if __name__ == "__main__":
    unittest.main()
