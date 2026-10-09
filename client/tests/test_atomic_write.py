import ast
import errno
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import shared.atomic_write as atomic_write


def _write_line(stream) -> None:
    stream.write("a,b\r\n")


def _write_then_fail(stream) -> None:
    stream.write("a,b\r\n")
    stream.write("\ud800")


class WriteTextAtomicallyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = self.directory / "d.csv"

    def listing(self) -> list[str]:
        return sorted(os.listdir(self.directory))

    def test_replaces_an_existing_file_with_the_written_text(self) -> None:
        self.path.write_bytes(b"old,bytes\n")

        atomic_write.write_text_atomically(self.path, _write_line)

        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_creates_a_file_that_does_not_exist(self) -> None:
        atomic_write.write_text_atomically(str(self.path), _write_line)

        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_write_error_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
        self.path.write_bytes(b"old,bytes\n")

        with self.assertRaises(UnicodeEncodeError):
            atomic_write.write_text_atomically(self.path, _write_then_fail)

        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_replace_error_keeps_the_original_bytes_and_leaves_no_temporary_file(self) -> None:
        self.path.write_bytes(b"old,bytes\n")

        with patch("os.replace", side_effect=PermissionError(13, "denied")) as replace:
            with self.assertRaises(PermissionError):
                atomic_write.write_text_atomically(self.path, _write_line)

        source, destination = replace.call_args.args
        self.assertEqual(Path(source).parent, self.directory)
        self.assertRegex(Path(source).name, r"^\.d\.csv\..+\.tmp$")
        self.assertEqual(Path(destination), self.path)
        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_interrupt_leaves_no_temporary_file_and_propagates(self) -> None:
        self.path.write_bytes(b"old,bytes\n")

        def interrupt(stream) -> None:
            stream.write("a,b\r\n")
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            atomic_write.write_text_atomically(self.path, interrupt)

        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_failure_without_an_existing_file_creates_nothing(self) -> None:
        with self.assertRaises(UnicodeEncodeError):
            atomic_write.write_text_atomically(self.path, _write_then_fail)

        self.assertEqual(self.listing(), [])

    def test_data_is_flushed_to_disk_before_the_replace(self) -> None:
        calls = Mock()

        with patch("os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            calls.attach_mock(fsync, "fsync")
            calls.attach_mock(replace, "replace")
            atomic_write.write_text_atomically(self.path, _write_line)

        self.assertEqual([name for name, _args, _kwargs in calls.mock_calls], ["fsync", "replace"])
        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_keeps_the_permission_bits_of_an_existing_file(self) -> None:
        self.path.write_bytes(b"old,bytes\n")
        os.chmod(self.path, 0o640)

        atomic_write.write_text_atomically(self.path, _write_line)

        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o640))
        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_a_new_file_gets_the_default_mode_for_the_umask(self) -> None:
        previous = os.umask(0o002)
        self.addCleanup(os.umask, previous)

        atomic_write.write_text_atomically(self.path, _write_line)

        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o664))
        self.assertEqual(self.listing(), ["d.csv"])

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_a_read_only_file_gets_the_same_verdict_as_writing_it_in_place(self) -> None:
        # The old save opened the dictionary with "w": a 0o444 file failed with
        # PermissionError and stayed as it was. The atomic save asks os.access first, so
        # it keeps that verdict (a privileged user, such as root, could write in place).
        self.path.write_bytes(b"old,bytes\n")
        os.chmod(self.path, 0o444)
        try:
            with open(self.path, "r+b"):
                writable_in_place = True
        except PermissionError:
            writable_in_place = False

        if writable_in_place:
            atomic_write.write_text_atomically(self.path, _write_line)
            self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
        else:
            with self.assertRaises(PermissionError) as raised:
                atomic_write.write_text_atomically(self.path, _write_line)
            self.assertEqual(raised.exception.errno, errno.EACCES)
            self.assertEqual(raised.exception.filename, str(self.path))
            self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(oct(stat.S_IMODE(os.stat(self.path).st_mode)), oct(0o444))
        self.assertEqual(self.listing(), ["d.csv"])

    def test_a_file_without_write_access_raises_permission_error_and_is_kept(self) -> None:
        self.path.write_bytes(b"old,bytes\n")

        with patch("os.access", return_value=False) as access:
            with self.assertRaises(PermissionError) as raised:
                atomic_write.write_text_atomically(self.path, _write_line)

        access.assert_called_with(self.path, os.W_OK)
        self.assertEqual(
            str(raised.exception),
            f"[Errno {errno.EACCES}] {os.strerror(errno.EACCES)}: {str(self.path)!r}",
        )
        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_an_unknown_encoding_raises_it_and_leaves_no_temporary_file(self) -> None:
        # The temporary file exists before the text stream is built; the stream's own
        # error must come out (not a second close of its descriptor) and the file goes.
        self.path.write_bytes(b"old,bytes\n")

        with self.assertRaises(LookupError):
            atomic_write.write_text_atomically(self.path, _write_line, encoding="no-such-codec")

        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(self.listing(), ["d.csv"])

    def test_a_taken_temporary_name_is_skipped_and_kept(self) -> None:
        self.path.write_bytes(b"old,bytes\n")
        taken = self.directory / ".d.csv.aaaa.tmp"
        taken.write_bytes(b"someone else's\n")

        with patch("secrets.token_hex", side_effect=["aaaa", "bbbb"]) as token_hex:
            atomic_write.write_text_atomically(self.path, _write_line)

        self.assertEqual(token_hex.call_count, 2)
        self.assertEqual(self.path.read_bytes(), b"a,b\r\n")
        self.assertEqual(taken.read_bytes(), b"someone else's\n")
        self.assertEqual(self.listing(), [".d.csv.aaaa.tmp", "d.csv"])

    def test_gives_up_when_every_temporary_name_is_taken(self) -> None:
        self.path.write_bytes(b"old,bytes\n")
        taken = self.directory / ".d.csv.aaaa.tmp"
        taken.write_bytes(b"someone else's\n")

        with patch("secrets.token_hex", return_value="aaaa") as token_hex:
            with self.assertRaises(FileExistsError):
                atomic_write.write_text_atomically(self.path, _write_line)

        self.assertGreater(token_hex.call_count, 1)
        self.assertEqual(self.path.read_bytes(), b"old,bytes\n")
        self.assertEqual(taken.read_bytes(), b"someone else's\n")
        self.assertEqual(self.listing(), [".d.csv.aaaa.tmp", "d.csv"])


class ProductionCodeDoesNotSetTheUmaskTest(unittest.TestCase):
    # The umask is process-wide: reading it with os.umask(0) round trips races with any
    # other thread creating a file. The atomic write lets the kernel apply it instead.
    def test_no_production_module_calls_os_umask(self) -> None:
        client = Path(__file__).resolve().parents[1]
        skipped = {".venv", "tests", "__pycache__"}
        scanned = []
        offenders = []
        for path in sorted(client.rglob("*.py")):
            relative = path.relative_to(client)
            if skipped & set(relative.parts[:-1]):
                continue
            scanned.append(relative.as_posix())
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                uses_umask = (isinstance(node, ast.Attribute) and node.attr == "umask") or (
                    isinstance(node, ast.ImportFrom) and any(alias.name == "umask" for alias in node.names)
                )
                if uses_umask:
                    offenders.append(f"{relative.as_posix()}:{node.lineno}")

        self.assertIn("shared/atomic_write.py", scanned)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
