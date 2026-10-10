import errno
import json
import os
import stat
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import documents.workspace as workspace
from documents.importers.base import source_name
from documents.workspace import (
    BatchIssue,
    Document,
    batch_import_documents,
    export_document_brl,
    load_document_package,
    load_text_document,
    load_workspace_documents,
    normalize_document_name,
    prepare_document_for_save,
    save_document_package,
)
from shared import name_validation
from tests.case_insensitive_package_files import CaseInsensitivePackageFiles
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import SHARE_MODES, hold_open, is_hidden, make_hidden, make_read_only


def setUpModule() -> None:
    # Recovery logs a failed rename to dotexpress.gui (F-8 D3): never to the real gui.log.
    unittest.addModuleCleanup(isolate_file_logs("dotexpress.gui"))


class DocumentWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self._tmpdir.name) / "workspace"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_normalize_document_name_accepts_unicode_trims_and_allows_default(self) -> None:
        self.assertEqual(normalize_document_name("  default中文12"), "default中文12")
        self.assertEqual(normalize_document_name(" default"), "default")
        self.assertEqual(normalize_document_name("1.1"), "1.1")
        self.assertEqual(normalize_document_name("name\u3000"), "name")

    def test_normalize_document_name_rejects_windows_invalid_names(self) -> None:
        invalid_values = [
            "",
            " ",
            ".",
            "..",
            " name ",
            "a.",
            "name ",
            "name\t",
            "a. ",
            "a<b",
            "a>b",
            "a:b",
            'a"b',
            "a/b",
            r"a\\b",
            "a|b",
            "a?b",
            "a*b",
            f"a{chr(1)}b",
            "CON",
            "prn",
            "AUX",
            "nul",
            "COM1",
            "com9",
            "LPT1",
            "lpt9",
            "a" * 33,
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_document_name(value)

    def test_normalize_document_name_accepts_32_characters(self) -> None:
        self.assertEqual(normalize_document_name("a" * 32), "a" * 32)

    def test_normalize_document_name_raises_typed_errors(self) -> None:
        cases = (("", "empty"), ("a?b", "invalid"), ("name ", "invalid"), ("a" * 33, "too_long"), ("a\ud800", "invalid"))
        for value, code in cases:
            with self.subTest(value=value):
                with self.assertRaises(name_validation.NameValidationError) as caught:
                    normalize_document_name(value)
                self.assertEqual(caught.exception.code, code)

    def test_importer_source_name_raises_typed_errors_with_the_english_message(self) -> None:
        cases = (
            ("CON.docx", "invalid", "Name contains invalid characters."),
            ("name..docx", "invalid", "Name cannot end with a period or space."),
            ("a" * 33 + ".docx", "too_long", "Name cannot exceed 32 characters."),
        )
        for file_name, code, message in cases:
            with self.subTest(file_name=file_name):
                with self.assertRaises(name_validation.NameValidationError) as caught:
                    source_name(Path(file_name))
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(str(caught.exception), message)

    def test_save_and_load_document_package_roundtrip(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_and_load_document_package_preserves_pending_braille_state(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)
        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_and_load_document_package_roundtrip_with_dotted_name(self) -> None:
        document = Document(name="1.1", text="source", braille="braille")
        package_path = self.workspace_dir / "1.1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document)

        import zipfile

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["1.1.brl", "1.1.txt"])

        loaded = load_document_package(package_path)
        self.assertEqual(loaded, document)

    def test_save_document_package_can_skip_pending_metadata_for_exports(self) -> None:
        document = Document(name="lesson1", text="source", braille=None)
        package_path = self.workspace_dir / "lesson1.dep"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(package_path, document, include_pending_metadata=False)

        import zipfile

        with zipfile.ZipFile(package_path, "r") as archive:
            self.assertEqual(sorted(archive.namelist()), ["lesson1.brl", "lesson1.txt"])

    def test_load_document_package_rejects_mismatched_internal_names(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        package_path = self.workspace_dir / "lesson1.dep"
        save_document_package(package_path, Document(name="math", text="source", braille="braille"))
        with self.assertRaises(ValueError):
            load_document_package(package_path)

    def test_load_text_document_uses_stem_and_sets_pending_braille(self) -> None:
        source_path = self.workspace_dir / "lesson1.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="lesson1", text="hello", braille=None))

    def test_load_text_document_handles_dotted_document_name(self) -> None:
        source_path = self.workspace_dir / "1.1.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="1.1", text="hello", braille=None))

    def test_load_text_document_accepts_32_character_stem(self) -> None:
        source_path = self.workspace_dir / f"{'a' * 32}.txt"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("hello", encoding="utf-8")

        loaded = load_text_document(source_path)

        self.assertEqual(loaded, Document(name="a" * 32, text="hello", braille=None))

    def test_export_document_brl_writes_plain_braille_text(self) -> None:
        document = Document(name="lesson1", text="source", braille="⠇⠑⠎⠎")
        output_path = self.workspace_dir / "lesson1.brl"
        export_document_brl(output_path, document)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "⠇⠑⠎⠎")

    def test_brl_export_failure_keeps_the_existing_file(self) -> None:
        # F-8 (D8): the in-place write emptied an existing export before it failed. Here
        # the encoder fails part way (a lone surrogate in the braille).
        self.workspace_dir.mkdir(parents=True)
        output_path = self.workspace_dir / "lesson1.brl"
        output_path.write_bytes(b"OLD GOOD EXPORT")
        document = Document(name="lesson1", text="source", braille="⠇⠑" + chr(0xD800) + "⠎")

        with self.assertRaises(UnicodeEncodeError):
            export_document_brl(output_path, document)

        self.assertEqual(output_path.read_bytes(), b"OLD GOOD EXPORT")
        self.assertEqual(sorted(path.name for path in self.workspace_dir.iterdir()), ["lesson1.brl"])

    def test_batch_import_documents_imports_txt_only_and_reports_duplicates(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "alpha.txt").write_text("A", encoding="utf-8")
        (source_dir / "beta.txt").write_text("B", encoding="utf-8")
        (source_dir / "alpha.dep").write_text("ignored", encoding="utf-8")

        documents, issues = batch_import_documents(
            [source_dir / "alpha.txt", source_dir / "beta.txt", source_dir / "alpha.dep"],
            format_key="txt",
            existing_names={"beta"},
        )

        self.assertEqual(documents, [Document(name="alpha", text="A", braille=None)])
        self.assertEqual(
            issues,
            [
                BatchIssue(path=source_dir / "alpha.dep", reason="Text document must use the .txt extension."),
                BatchIssue(path=source_dir / "beta.txt", reason='Document "beta" already exists.'),
            ],
        )

    def test_batch_import_documents_dispatches_semantic_importer(self) -> None:
        source = Path(self._tmpdir.name) / "lesson.docx"
        calls = []

        def loader(path: Path | str) -> Document:
            calls.append(Path(path))
            return Document("lesson", "# Heading\n", None)

        original_loaders = workspace.IMPORT_LOADERS.copy()
        workspace.IMPORT_LOADERS["docx"] = loader
        try:
            documents, issues = batch_import_documents([source], format_key="docx", existing_names=set())
        finally:
            workspace.IMPORT_LOADERS.clear()
            workspace.IMPORT_LOADERS.update(original_loaders)

        self.assertEqual(documents, [Document("lesson", "# Heading\n", None)])
        self.assertEqual(issues, [])
        self.assertEqual(calls, [source])

    def test_batch_import_documents_all_detects_each_supported_extension(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            source_dir / "alpha.txt",
            source_dir / "beta.dep",
            source_dir / "gamma.pdf",
            source_dir / "delta.docx",
            source_dir / "epsilon.epub",
        ]
        calls = []

        def make_loader(key: str, document: Document):
            def loader(path: Path | str) -> Document:
                calls.append((key, Path(path)))
                return document

            return loader

        loaders = {
            "txt": make_loader("txt", Document("alpha", "A", None)),
            "dep": make_loader("dep", Document("beta", "B", "⠃")),
            "pdf": make_loader("pdf", Document("gamma", "G", None)),
            "docx": make_loader("docx", Document("delta", "D", None)),
            "epub": make_loader("epub", Document("epsilon", "E", None)),
        }

        original_loaders = workspace.IMPORT_LOADERS.copy()
        workspace.IMPORT_LOADERS.update(loaders)
        try:
            documents, issues = batch_import_documents(paths, format_key="all", existing_names=set())
        finally:
            workspace.IMPORT_LOADERS.clear()
            workspace.IMPORT_LOADERS.update(original_loaders)

        self.assertEqual(
            documents,
            [
                Document("alpha", "A", None),
                Document("beta", "B", "⠃"),
                Document("delta", "D", None),
                Document("epsilon", "E", None),
                Document("gamma", "G", None),
            ],
        )
        self.assertEqual(issues, [])
        self.assertEqual(
            sorted(calls),
            sorted((path.suffix.lstrip("."), path) for path in paths),
        )

    def test_batch_import_documents_rejects_unknown_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported import format"):
            batch_import_documents([], format_key="rtf", existing_names=set())

    def test_batch_import_documents_reports_invalid_dep(self) -> None:
        source_dir = Path(self._tmpdir.name) / "incoming"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "bad.dep").write_text("not-a-zip", encoding="utf-8")

        documents, issues = batch_import_documents([source_dir / "bad.dep"], format_key="dep", existing_names=set())

        self.assertEqual(documents, [])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].path, source_dir / "bad.dep")

    def test_prepare_document_for_save_preserves_pending_braille(self) -> None:
        document = Document(name="lesson1", text="old", braille=None)

        prepared = prepare_document_for_save(
            document,
            text="new text",
            braille="⠞⠑⠎⠞",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille=None))

    def test_prepare_document_for_save_keeps_existing_braille(self) -> None:
        document = Document(name="lesson1", text="old", braille="⠃⠗⠇")

        prepared = prepare_document_for_save(
            document,
            text="new text",
            braille="⠃⠗⠇",
        )

        self.assertEqual(prepared, Document(name="lesson1", text="new text", braille="⠃⠗⠇"))

    def test_replace_lone_surrogates_replaces_each_unpaired_surrogate(self) -> None:
        # F-5 (D4): one U+FFFD per surrogate that is not half of a pair, so UTF-8 can encode it.
        cases = {
            "lone high": ("a\ud800b", "a�b"),
            "lone low": ("a\udc00b", "a�b"),
            "reversed pair": ("a\ude00\ud83db", "a��b"),
            "two highs": ("\ud800\ud800", "��"),
            "high at the end": ("ab\ud83d", "ab�"),
            "surrogate escape": ("x\udcff", "x�"),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(workspace.replace_lone_surrogates(text), expected)

    def test_replace_lone_surrogates_joins_split_pairs_and_keeps_other_text(self) -> None:
        self.assertEqual(workspace.replace_lone_surrogates("a\ud83d\ude00b"), "a\U0001f600b")
        for text in ("a\U0001f600b", "中文", "⠁⠃", "tab\tand\nnewline", ""):
            with self.subTest(text=text):
                self.assertIs(workspace.replace_lone_surrogates(text), text)

    def test_prepare_document_for_save_replaces_lone_surrogates(self) -> None:
        kept = prepare_document_for_save(Document("alpha", "old", "⠁"), text="x\ud800", braille="\udc00⠁")
        pending = prepare_document_for_save(Document("alpha", "old", None), text="x\ud800", braille="\udc00")

        self.assertEqual(kept, Document("alpha", "x�", "�⠁"))
        self.assertEqual(pending, Document("alpha", "x�", None))

    def test_load_workspace_documents_sorts_valid_documents_and_collects_invalid_paths(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        save_document_package(self.workspace_dir / "Beta.dep", Document(name="Beta", text="b", braille="1"))
        save_document_package(self.workspace_dir / "alpha.dep", Document(name="alpha", text="a", braille="2"))
        save_document_package(self.workspace_dir / "bad.dep", Document(name="other", text="x", braille="3"))
        documents, invalid_paths = load_workspace_documents(self.workspace_dir)
        self.assertEqual([document.name for document in documents], ["alpha", "Beta"])
        self.assertEqual(invalid_paths, [self.workspace_dir / "bad.dep"])


class AtomicSaveDocumentPackageTest(unittest.TestCase):
    """``save_document_package`` never leaves a broken package and keeps the format (F-3)."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace_dir = Path(temp_dir.name) / "workspace"
        self.path = self.workspace_dir / "alpha.dep"
        self.alpha = Document("alpha", "a", "1")

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace_dir.iterdir())

    def _write_alpha(self) -> bytes:
        save_document_package(self.path, self.alpha)
        return self.path.read_bytes()

    def test_save_writes_the_same_bytes_as_the_in_place_writer(self) -> None:
        # The format does not change: for the same timestamp the bytes equal those of the
        # in-place writer before F-3, rebuilt here (ZipFile on the path, three writestr calls).
        self.workspace_dir.mkdir(parents=True)
        reference = self.workspace_dir / "reference.dep"
        for document in (Document("alpha", "a\n中文", "⠁⠂"), Document("alpha", "pending", None)):
            with self.subTest(braille=document.braille):
                with patch("time.time", return_value=1_760_000_000.0):
                    save_document_package(self.path, document)
                    with zipfile.ZipFile(reference, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                        archive.writestr("alpha.txt", document.text)
                        archive.writestr("alpha.brl", document.braille or "")
                        if document.braille is None:
                            archive.writestr("alpha.meta.json", json.dumps({"braille_pending": True}, ensure_ascii=False))

                self.assertEqual(self.path.read_bytes(), reference.read_bytes())

    def test_load_workspace_documents_ignores_leftover_temporary_files(self) -> None:
        # A crash or a failed clean-up can leave the temporary file of a save
        # (.<name>.dep.<16 hex>.tmp) or of a rename (.<name>.dep.<8 characters>.tmp).
        # "*.dep" never matches them: startup neither loads nor offers to delete them.
        self._write_alpha()
        for name in (".alpha.dep.0123456789abcdef.tmp", ".alpha.dep.k2j1abcd.tmp", ".beta.dep.x.tmp"):
            (self.workspace_dir / name).write_bytes(b"not a zip")

        self.assertEqual(load_workspace_documents(self.workspace_dir), ([self.alpha], []))

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_save_keeps_the_permission_bits_of_the_package(self) -> None:
        self._write_alpha()
        os.chmod(self.path, 0o640)

        save_document_package(self.path, Document("alpha", "edited", "1"))

        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o640))
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "1"))

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_save_of_a_read_only_package_gives_the_old_message(self) -> None:
        # The in-place open("w+b") failed with exactly this text; F-3 keeps it (D3).
        before = self._write_alpha()
        make_read_only(self, self.path)

        with self.assertRaises(PermissionError) as raised:
            save_document_package(self.path, Document("alpha", "edited", "1"))

        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_failure_that_is_not_an_os_error_keeps_the_existing_package(self) -> None:
        # A bug in the writer (simulated: writestr raises ValueError) while the first or the
        # second member is written. The in-place save had already truncated the package and
        # left a zip without the failing member (invalid at the next start).
        before = self._write_alpha()
        real_writestr = zipfile.ZipFile.writestr
        for failing in (1, 2):
            with self.subTest(failing_member=failing):
                written = []

                def writestr_failing(archive, name, data, *args, **kwargs):
                    written.append(name)
                    if len(written) == failing:
                        raise ValueError("injected")
                    return real_writestr(archive, name, data, *args, **kwargs)

                with patch.object(zipfile.ZipFile, "writestr", writestr_failing):
                    with self.assertRaises(ValueError):
                        save_document_package(self.path, Document("alpha", "edited", "2"))

                self.assertEqual(written, ["alpha.txt", "alpha.brl"][:failing])
                self.assertEqual(self._listing(), ["alpha.dep"])
                self.assertEqual(load_document_package(self.path), self.alpha)
                self.assertEqual(self.path.read_bytes(), before)

    def test_save_replaces_lone_surrogates_with_the_replacement_character(self) -> None:
        # F-5 (D4): a lone surrogate (pasted text) used to make every save fail with
        # "surrogates not allowed"; it is written as U+FFFD (EF BF BD in UTF-8).
        cases = {
            "text": (Document("alpha", "a\ud800", "1"), Document("alpha", "a�", "1"), "alpha.txt", b"a\xef\xbf\xbd"),
            "braille": (
                Document("alpha", "a", "\udc00⠁"),
                Document("alpha", "a", "�⠁"),
                "alpha.brl",
                b"\xef\xbf\xbd\xe2\xa0\x81",
            ),
        }
        for field, (document, expected, member, data) in cases.items():
            with self.subTest(field=field):
                save_document_package(self.path, document)

                self.assertEqual(load_document_package(self.path), expected)
                with zipfile.ZipFile(self.path) as archive:
                    self.assertEqual(archive.read(member), data)
                self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_failure_while_writing_keeps_the_existing_package(self) -> None:
        # A full disk while the second member is written (simulated).
        before = self._write_alpha()
        real_writestr = zipfile.ZipFile.writestr
        written = []

        def writestr_until_the_disk_is_full(archive, name, data, *args, **kwargs):
            written.append(name)
            if len(written) == 2:
                raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
            return real_writestr(archive, name, data, *args, **kwargs)

        with patch.object(zipfile.ZipFile, "writestr", writestr_until_the_disk_is_full):
            with self.assertRaises(OSError) as raised:
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(written, ["alpha.txt", "alpha.brl"])
        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self.path), self.alpha)
        self.assertEqual(self.path.read_bytes(), before)

    def test_save_install_failure_keeps_the_existing_package(self) -> None:
        before = self._write_alpha()

        with patch("os.replace", side_effect=PermissionError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_installs_a_temporary_file_from_the_same_folder(self) -> None:
        self._write_alpha()

        with patch("os.replace", wraps=os.replace) as replace:
            save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(replace.call_count, 1)
        source, destination = replace.call_args.args
        self.assertEqual(Path(source).parent, self.workspace_dir)
        self.assertRegex(Path(source).name, r"^\.alpha\.dep\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(Path(destination), self.path)
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "2"))
        self.assertEqual(self._listing(), ["alpha.dep"])

    def test_save_refuses_a_package_without_write_access(self) -> None:
        before = self._write_alpha()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.path)!r}",
        )
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self._listing(), ["alpha.dep"])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_save_of_a_package_held_open_keeps_it(self) -> None:
        # Another program reading the package. The in-place save failed with [Errno 13]
        # or rewrote the file under that program (share read+write); now the replace is
        # refused in every share mode and the package keeps its bytes (spec D12, Q1).
        before = self._write_alpha()
        for label, share in SHARE_MODES:
            with self.subTest(share=label):
                release = hold_open(self, self.path, share)
                try:
                    with self.assertRaises(PermissionError) as raised:
                        save_document_package(self.path, Document("alpha", "edited", "2"))
                finally:
                    release()

                self.assertEqual(raised.exception.winerror, 5)
                self.assertEqual(self.path.read_bytes(), before)
                self.assertEqual(self._listing(), ["alpha.dep"])

    @unittest.skipUnless(os.name == "nt", "Windows hidden attribute")
    def test_save_of_a_hidden_package_replaces_it_and_drops_the_attribute(self) -> None:
        # The in-place open (CREATE_ALWAYS) refused a hidden file with [Errno 13]; the
        # replaced package is a new file with default attributes (spec D11).
        self._write_alpha()
        make_hidden(self.path)

        save_document_package(self.path, Document("alpha", "edited", "2"))

        self.assertFalse(is_hidden(self.path))
        self.assertEqual(load_document_package(self.path), Document("alpha", "edited", "2"))
        self.assertEqual(self._listing(), ["alpha.dep"])


class _FailingPackageFiles:
    """The real ``PackageFiles``, except that ``operation`` raises ``OSError`` when ``when(*paths)`` is true.

    Predicates compare ``path.name`` strings: ``Path`` equality ignores case on Windows.
    """

    def __init__(self, operation: str, when=lambda *paths: True) -> None:
        self._files = workspace.PackageFiles()
        self._operation = operation
        self._when = when

    def _check(self, operation: str, *paths) -> None:
        if operation == self._operation and self._when(*(Path(path) for path in paths)):
            raise OSError(f"injected {operation} failure")

    def ensure_writable(self, path) -> None:
        self._check("ensure_writable", path)
        self._files.ensure_writable(path)

    def exists(self, path) -> bool:
        return self._files.exists(path)

    def write(self, path, document) -> None:
        self._check("write", path)
        self._files.write(path, document)

    def replace(self, source, destination) -> None:
        self._check("replace", source, destination)
        self._files.replace(source, destination)

    def remove(self, path) -> None:
        self._check("remove", path)
        self._files.remove(path)

    def copy_permissions(self, source, destination) -> None:
        self._check("copy_permissions", source, destination)
        self._files.copy_permissions(source, destination)

    def temporary_path(self, directory, name) -> Path:
        return self._files.temporary_path(directory, name)


class MoveDocumentPackageTest(unittest.TestCase):
    """``move_document_package`` on the real file system (F-1, D4)."""

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace_dir = Path(temp_dir.name) / "workspace"

    def _path(self, name: str) -> Path:
        return self.workspace_dir / f"{name}.dep"

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace_dir.iterdir())

    def _members(self, name: str) -> list[str]:
        with zipfile.ZipFile(self._path(name)) as archive:
            return sorted(archive.namelist())

    def _write_alpha(self, braille: str | None = "1") -> bytes:
        save_document_package(self._path("Alpha"), Document("Alpha", "a", braille))
        return self._path("Alpha").read_bytes()

    def _move(self, old_name: str, document: Document, files=None) -> None:
        workspace.move_document_package(
            self._path(old_name),
            self._path(document.name),
            document,
            files=workspace.PackageFiles() if files is None else files,
        )

    def test_case_only_move_leaves_only_the_new_spelling(self) -> None:
        self._write_alpha()

        self._move("Alpha", Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.txt"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))

    def test_move_to_a_different_name(self) -> None:
        save_document_package(self._path("alpha"), Document("alpha", "a", "1"))

        self._move("alpha", Document("gamma", "a", "1"))

        self.assertEqual(self._listing(), ["gamma.dep"])
        self.assertEqual(load_document_package(self._path("gamma")), Document("gamma", "a", "1"))

    def test_move_onto_an_existing_third_file_puts_the_old_package_back(self) -> None:
        # F-8 (D1): a package that is not listed (kept invalid at startup) or one created
        # after the name was checked is never replaced; the old package stays.
        save_document_package(self._path("alpha"), Document("alpha", "a", "1"))
        before = self._path("alpha").read_bytes()
        self._path("bad").write_bytes(b"not a zip")

        with self.assertRaises(FileExistsError) as raised:
            self._move("alpha", Document("bad", "a", "1"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EEXIST}] {os.strerror(errno.EEXIST)}: {str(self._path('bad'))!r}",
        )
        self.assertEqual(self._listing(), ["alpha.dep", "bad.dep"])
        self.assertEqual(self._path("alpha").read_bytes(), before)
        self.assertEqual(self._path("bad").read_bytes(), b"not a zip")

    def test_case_only_move_on_the_case_insensitive_model_is_not_refused(self) -> None:
        # The check for a third file runs after the old package is moved aside: before
        # that, the new spelling names the old package itself on such a file system.
        self._write_alpha()

        self._move("Alpha", Document("alpha", "a", "1"), CaseInsensitivePackageFiles())

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))

    def test_missing_old_package_and_directory_writes_the_new_package(self) -> None:
        self._move("Alpha", Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))

    def test_pending_braille_keeps_its_metadata(self) -> None:
        self._write_alpha(braille=None)

        self._move("Alpha", Document("alpha", "a", None))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(self._members("alpha"), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", None))

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_case_only_move_keeps_the_permission_bits_of_the_old_package(self) -> None:
        self._write_alpha()
        os.chmod(self._path("Alpha"), 0o640)

        self._move("Alpha", Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(oct(stat.S_IMODE(os.stat(self._path("alpha")).st_mode)), oct(0o640))
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))

    def test_staging_write_failure_keeps_the_old_package(self) -> None:
        before = self._write_alpha()

        with self.assertRaises(OSError):
            self._move("Alpha", Document("alpha", "a", "1"), _FailingPackageFiles("write"))

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_staging_error_that_is_not_an_os_error_keeps_the_old_package(self) -> None:
        before = self._write_alpha()

        with patch.object(zipfile.ZipFile, "writestr", side_effect=ValueError("injected")):
            with self.assertRaises(ValueError):
                self._move("Alpha", Document("alpha", "a", "1"))

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_move_aside_failure_keeps_the_old_package(self) -> None:
        before = self._write_alpha()
        files = _FailingPackageFiles("replace", when=lambda source, destination: source.name == "Alpha.dep")

        with self.assertRaises(OSError):
            self._move("Alpha", Document("alpha", "a", "1"), files)

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_install_failure_puts_the_old_package_back(self) -> None:
        before = self._write_alpha()
        files = _FailingPackageFiles("replace", when=lambda source, destination: destination.name == "alpha.dep")

        with self.assertRaises(OSError):
            self._move("Alpha", Document("alpha", "a", "1"), files)

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_permission_copy_failure_puts_the_old_package_back(self) -> None:
        before = self._write_alpha()

        with self.assertRaises(OSError):
            self._move("Alpha", Document("alpha", "a", "1"), _FailingPackageFiles("copy_permissions"))

        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_clean_up_failure_is_ignored_and_leaves_a_tmp_file_the_workspace_ignores(self) -> None:
        self._write_alpha()

        self._move("Alpha", Document("alpha", "a", "1"), _FailingPackageFiles("remove"))

        listing = self._listing()
        self.assertEqual([name for name in listing if not name.endswith(".tmp")], ["alpha.dep"])
        leftovers = [name for name in listing if name.endswith(".tmp")]
        self.assertEqual(len(leftovers), 1)
        self.assertTrue(leftovers[0].startswith(".Alpha.dep."), leftovers)
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "a", "1"))
        self.assertEqual(load_workspace_documents(self.workspace_dir), ([Document("alpha", "a", "1")], []))

    def test_unwritable_old_package_is_refused_before_anything_changes(self) -> None:
        before = self._write_alpha()

        with patch("os.access", return_value=False):
            with self.assertRaises(PermissionError) as raised:
                self._move("Alpha", Document("gamma", "a", "1"))

        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self._path('Alpha'))!r}",
        )
        self.assertEqual(self._listing(), ["Alpha.dep"])
        self.assertEqual(self._path("Alpha").read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_read_only_old_package_is_refused_and_leaves_no_temporary_file(self) -> None:
        # Without the check, moving a read-only package aside succeeds (it needs only
        # delete access) and the aside file cannot be removed: a read-only .tmp stays
        # (F-1 note; spec D7, Q2). Case-only and regular renames are both refused.
        root = self.workspace_dir
        for new_name in ("alpha", "gamma"):
            with self.subTest(new_name=new_name):
                self.workspace_dir = root / new_name
                before = self._write_alpha()
                make_read_only(self, self._path("Alpha"))

                with self.assertRaises(PermissionError) as raised:
                    self._move("Alpha", Document(new_name, "a", "1"))

                self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self._path('Alpha'))!r}")
                self.assertEqual(self._listing(), ["Alpha.dep"])
                self.assertEqual(self._path("Alpha").read_bytes(), before)

    def test_temporary_path_creates_the_directory_and_is_not_a_package(self) -> None:
        path = workspace.PackageFiles().temporary_path(self.workspace_dir, "alpha.dep")

        self.assertEqual(path.parent, self.workspace_dir)
        self.assertTrue(path.is_file())
        self.assertTrue(path.name.startswith(".alpha.dep."), path.name)
        self.assertTrue(path.name.endswith(".tmp"), path.name)
        self.assertEqual(list(self.workspace_dir.glob("*.dep")), [])

    def test_staged_package_is_written_directly_and_flushed_to_disk(self) -> None:
        # The staged file is already private and new: it is written in place (no second
        # temporary file inside the first) and synced before the move installs it (D4).
        files = workspace.PackageFiles()
        staged = files.temporary_path(self.workspace_dir, "alpha.dep")
        real_fsync = os.fsync
        sizes_at_fsync = []

        def fsync_recording_the_size(descriptor: int) -> None:
            sizes_at_fsync.append(os.fstat(descriptor).st_size)
            real_fsync(descriptor)

        with patch("os.fsync", side_effect=fsync_recording_the_size), patch("os.replace", wraps=os.replace) as replace:
            files.write(staged, Document("alpha", "a", None))

        replace.assert_not_called()
        self.assertEqual(sizes_at_fsync, [staged.stat().st_size])
        self.assertGreater(sizes_at_fsync[0], 0)
        self.assertEqual(self._listing(), [staged.name])
        with zipfile.ZipFile(staged) as archive:
            self.assertEqual(sorted(archive.namelist()), ["alpha.brl", "alpha.meta.json", "alpha.txt"])
            self.assertEqual(archive.read("alpha.txt"), b"a")

    def test_staged_package_replaces_lone_surrogates(self) -> None:
        # F-5 (D4): the staged package of a rename goes through the same normalization.
        files = workspace.PackageFiles()
        staged = files.temporary_path(self.workspace_dir, "alpha.dep")
        files.write(staged, Document("alpha", "x\ud800", "1"))
        with zipfile.ZipFile(staged) as archive:
            self.assertEqual(archive.read("alpha.txt"), b"x\xef\xbf\xbd")
        staged.unlink()
        self._write_alpha()

        self._move("Alpha", Document("alpha", "y\udc00", "1"))

        self.assertEqual(self._listing(), ["alpha.dep"])
        self.assertEqual(load_document_package(self._path("alpha")), Document("alpha", "y�", "1"))


class RecoverInterruptedPackagesTest(unittest.TestCase):
    """Startup puts back a package that a crash left only in a temporary file (F-8 D3).

    The leftovers are written as the F-8 probe found them: a Save writes
    ``.<name>.dep.<16 hex>.tmp`` and a Rename uses ``.<name>.dep.<8 characters>.tmp`` for the
    staged new package and for the old package moved aside, which keeps its older
    modification time.
    """

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.workspace_dir = Path(temp_dir.name) / "workspace"
        self.workspace_dir.mkdir()

    def _leftover(self, file_name: str, document: Document, *, age_s: int = 0) -> Path:
        """``file_name`` holding ``document`` as a package, last modified ``age_s`` seconds ago."""
        path = self.workspace_dir / file_name
        workspace.PackageFiles().write(path, document)
        modified = time.time_ns() - age_s * 1_000_000_000
        os.utime(path, ns=(modified, modified))
        return path

    def _raw_leftover(self, file_name: str, member_stem: str) -> Path:
        """``file_name`` holding a package whose members are ``<member_stem>.txt`` and ``.brl``."""
        path = self.workspace_dir / file_name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(f"{member_stem}.txt", "text")
            archive.writestr(f"{member_stem}.brl", "1")
        return path

    def _recover(self, listed=()) -> list[Document]:
        # Nothing is logged: a skipped file never even reaches os.rename (which on Windows
        # would refuse a taken name and log it).
        with self.assertNoLogs("dotexpress.gui"):
            return workspace.recover_interrupted_packages(self.workspace_dir, list(listed))

    def _listing(self) -> list[str]:
        return sorted(path.name for path in self.workspace_dir.iterdir())

    def _snapshot(self) -> dict[str, bytes]:
        return {path.name: path.read_bytes() for path in self.workspace_dir.iterdir()}

    def test_interrupted_rename_is_recovered_under_the_old_name(self) -> None:
        # Rename alpha -> gamma crashed after the move aside, before the install: no .dep.
        aside = self._leftover(".alpha.dep._vw4x6f_.tmp", Document("alpha", "text", "1"), age_s=60)
        before = aside.read_bytes()
        staged = self._leftover(".gamma.dep.mlw4jang.tmp", Document("gamma", "text", "1"))
        staged_bytes = staged.read_bytes()

        recovered = self._recover()

        self.assertEqual(recovered, [Document("alpha", "text", "1")])
        self.assertEqual(self._listing(), [".gamma.dep.mlw4jang.tmp", "alpha.dep"])
        self.assertEqual((self.workspace_dir / "alpha.dep").read_bytes(), before)
        self.assertEqual(staged.read_bytes(), staged_bytes)
        self.assertEqual(load_document_package(self.workspace_dir / "alpha.dep"), Document("alpha", "text", "1"))

    def test_leftover_of_a_completed_rename_is_not_recovered(self) -> None:
        # The rename installed gamma.dep, then removing the moved-aside alpha failed.
        gamma = Document("gamma", "text", "1")
        save_document_package(self.workspace_dir / "gamma.dep", gamma)
        self._leftover(".alpha.dep.7gdjw2yi.tmp", Document("alpha", "text", "1"), age_s=60)
        before = self._snapshot()

        self.assertEqual(self._recover([gamma]), [])

        self.assertEqual(self._snapshot(), before)

    def test_leftover_save_next_to_its_package_is_not_recovered(self) -> None:
        # The save wrote and synced its temporary file, then crashed before os.replace:
        # from the user's point of view that save never completed.
        alpha = Document("alpha", "old text", "1")
        save_document_package(self.workspace_dir / "alpha.dep", alpha)
        self._leftover(".alpha.dep.97dc8315c5cf865f.tmp", Document("alpha", "new text", "1"))
        before = self._snapshot()

        self.assertEqual(self._recover([alpha]), [])

        self.assertEqual(self._snapshot(), before)

    def test_invalid_and_empty_temporary_files_are_ignored(self) -> None:
        complete = self._leftover(".delta.dep.0123456789abcdef.tmp", Document("delta", "text", "1"))
        (self.workspace_dir / ".gamma.dep.x2y3z4w5.tmp").write_bytes(complete.read_bytes()[:40])
        complete.unlink()
        (self.workspace_dir / ".alpha.dep.0123456789abcdef.tmp").write_bytes(b"not a zip")
        (self.workspace_dir / ".beta.dep.k2j1abcd.tmp").write_bytes(b"")
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_name_held_by_an_unlisted_package_is_not_recovered(self) -> None:
        # An invalid package kept at startup holds the name in another case.
        (self.workspace_dir / "ALPHA.dep").write_bytes(b"not a zip")
        self._leftover(".alpha.dep.k2j1abcd.tmp", Document("alpha", "text", "1"))
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_names_that_are_not_valid_document_names_are_ignored(self) -> None:
        # Names a Windows folder can hold but a document cannot have.
        too_long = "x" * 33
        for stem in (" alpha", "alpha ", "alpha.", too_long, "CON"):
            self._raw_leftover(f".{stem}.dep.k2j1abcd.tmp", stem)
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_member_names_must_match_the_temporary_file_name(self) -> None:
        self._raw_leftover(".alpha.dep.k2j1abcd.tmp", "beta")
        self._raw_leftover(".gamma.dep.k2j1abcd.tmp", "Gamma")
        before = self._snapshot()

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._snapshot(), before)

    def test_files_that_are_not_package_leftovers_are_ignored(self) -> None:
        self._leftover("alpha.tmp", Document("alpha", "text", "1"))
        self._leftover(".beta.txt.k2j1abcd.tmp", Document("beta", "text", "2"))
        self._leftover(".gamma.dep.k2j1abcd.bak", Document("gamma", "text", "3"))
        (self.workspace_dir / ".delta.dep.k2j1abcd.tmp").mkdir()
        before = sorted(self._listing())

        self.assertEqual(self._recover(), [])

        self.assertEqual(self._listing(), before)

    def test_recovery_never_deletes_or_replaces_a_file(self) -> None:
        self._leftover(".alpha.dep._vw4x6f_.tmp", Document("alpha", "text", "1"), age_s=60)
        self._leftover(".gamma.dep.mlw4jang.tmp", Document("gamma", "text", "1"))
        save_document_package(self.workspace_dir / "beta.dep", Document("beta", "b", "2"))
        self._leftover(".beta.dep.97dc8315c5cf865f.tmp", Document("beta", "newer", "2"))
        (self.workspace_dir / ".delta.dep.k2j1abcd.tmp").write_bytes(b"")
        recorders = [
            patch("os.unlink", wraps=os.unlink),
            patch("os.remove", wraps=os.remove),
            patch("os.replace", wraps=os.replace),
            patch("pathlib.Path.unlink", autospec=True, wraps=Path.unlink),
            patch("shutil.rmtree"),
        ]
        mocks = [recorder.start() for recorder in recorders]
        for recorder in recorders:
            self.addCleanup(recorder.stop)

        recovered = self._recover([Document("beta", "b", "2")])

        self.assertEqual(recovered, [Document("alpha", "text", "1")])
        self.assertEqual([mock.call_count for mock in mocks], [0, 0, 0, 0, 0])
        self.assertEqual(
            self._listing(),
            [".beta.dep.97dc8315c5cf865f.tmp", ".delta.dep.k2j1abcd.tmp", ".gamma.dep.mlw4jang.tmp", "alpha.dep", "beta.dep"],
        )

    def test_documents_are_recovered_oldest_first(self) -> None:
        # Two interrupted renames: each old package comes back under its own name; their
        # staged twins hold the same text and stay.
        self._leftover(".beta.dep.aaaaaaaa.tmp", Document("beta", "b", "2"), age_s=120)
        self._leftover(".alpha.dep.bbbbbbbb.tmp", Document("alpha", "a", "1"), age_s=60)
        self._leftover(".zeta.dep.cccccccc.tmp", Document("zeta", "a", "1"), age_s=30)
        self._leftover(".delta.dep.dddddddd.tmp", Document("delta", "b", "2"))

        recovered = self._recover()

        self.assertEqual(recovered, [Document("beta", "b", "2"), Document("alpha", "a", "1")])
        self.assertEqual(
            self._listing(),
            [".delta.dep.dddddddd.tmp", ".zeta.dep.cccccccc.tmp", "alpha.dep", "beta.dep"],
        )

    @unittest.skipUnless(os.name == "nt", "os.rename never replaces an existing file on Windows")
    def test_recovery_does_not_replace_a_file_created_meanwhile(self) -> None:
        # Another program creates alpha.dep between the disk check and the rename.
        leftover = self._leftover(".alpha.dep.k2j1abcd.tmp", Document("alpha", "text", "1"))
        before = leftover.read_bytes()
        target = self.workspace_dir / "alpha.dep"
        real_rename = os.rename

        def create_then_rename(source, destination):
            Path(destination).write_bytes(b"created meanwhile")
            real_rename(source, destination)

        with patch("os.rename", side_effect=create_then_rename), self.assertLogs("dotexpress.gui", "ERROR") as logs:
            recovered = workspace.recover_interrupted_packages(self.workspace_dir, [])

        self.assertEqual(recovered, [])
        self.assertEqual(target.read_bytes(), b"created meanwhile")
        self.assertEqual(leftover.read_bytes(), before)
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(
            logs.records[0].getMessage().startswith(
                f"Cannot recover interrupted document package {leftover}: [WinError 183] "
            ),
            logs.records[0].getMessage(),
        )
        self.assertIsNone(logs.records[0].exc_info)


class ReplaceNulCharactersTest(unittest.TestCase):
    """U+0000 becomes U+FFFD where documents enter the app (F-8 D12)."""

    def test_replace_nul_characters(self) -> None:
        clean = "clean text\r\n"
        self.assertIs(workspace.replace_nul_characters(clean)[0], clean)
        cases = {
            "clean": (clean, (clean, 0)),
            "empty": ("", ("", 0)),
            "inside": ("a\x00b", ("a\ufffdb", 1)),
            "leading and trailing": ("\x00ab\x00", ("\ufffdab\ufffd", 2)),
            "consecutive": ("a\x00\x00\x00b", ("a\ufffd\ufffd\ufffdb", 3)),
            "next to CRLF": ("line\r\n\x00\r\nend", ("line\r\n\ufffd\r\nend", 1)),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label):
                self.assertEqual(workspace.replace_nul_characters(text), expected)

    def test_displayable_counts_text_and_braille_and_keeps_pending_braille(self) -> None:
        cases = (
            ("text and braille", Document("alpha", "a\x00b", "⠁\x00"), Document("alpha", "a\ufffdb", "⠁\ufffd"), 2),
            ("braille only", Document("alpha", "ab", "\x00⠁\x00"), Document("alpha", "ab", "\ufffd⠁\ufffd"), 2),
            ("pending braille", Document("alpha", "\x00", None), Document("alpha", "\ufffd", None), 1),
        )
        for label, document, expected, count in cases:
            with self.subTest(label):
                self.assertEqual(workspace._displayable(document), (expected, count))
        clean = Document("alpha", "ab", "⠁")
        displayable, count = workspace._displayable(clean)
        self.assertIs(displayable, clean)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
