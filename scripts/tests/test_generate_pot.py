import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "client"
GENERATE_POT = ROOT / "scripts" / "generate-pot.bat"
POT = CLIENT / "locales" / "dotexpress.pot"
ZH_TW_PO = CLIENT / "locales" / "zh_TW" / "LC_MESSAGES" / "dotexpress.po"
# Directories generate-pot.bat does not scan.
SKIPPED_DIRS = {".venv", "tests", "build", "dist", "__pycache__"}
REFERENCE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.py:[0-9]+")
PO_STRING = re.compile(r'(?:(msgctxt|msgid|msgid_plural|msgstr(?:\[[0-9]+\])?)\s+)?(".*")')


def read_catalog(path: Path) -> list[dict]:
    """Parse the subset of the PO format xgettext and msgmerge write here."""
    entries = []
    entry = None
    field = None
    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        obsolete = line.startswith("#~")
        if obsolete:
            line = line[2:].lstrip()
        if not line.strip():
            if entry is not None:
                entries.append(entry)
            entry = None
            continue
        if entry is None:
            entry = {"msgid": "", "msgstr": "", "references": [], "flags": set(), "obsolete": False}
        entry["obsolete"] = entry["obsolete"] or obsolete
        if line.startswith("#:"):
            entry["references"].extend(line[2:].split())
        elif line.startswith("#,"):
            entry["flags"].update(flag.strip() for flag in line[2:].split(","))
        elif not line.startswith("#"):
            match = PO_STRING.fullmatch(line)
            if match is None:
                raise ValueError(f"{path.name}: unexpected line {line!r}")
            if match.group(1):
                field = match.group(1)
                entry[field] = ""
            entry[field] += ast.literal_eval(match.group(2))
    return entries


def messages(entries: list[dict]) -> list[dict]:
    """Active entries without the header."""
    return [entry for entry in entries if entry["msgid"] and not entry["obsolete"]]


def marked_source_strings() -> set[str]:
    extracted = set()
    for dirpath, dirnames, filenames in os.walk(CLIENT):
        dirnames[:] = [name for name in dirnames if name not in SKIPPED_DIRS]
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
    return extracted


class CommittedPotTests(unittest.TestCase):
    def test_references_are_relative_to_client_with_forward_slashes(self):
        for entry in messages(read_catalog(POT)):
            for reference in entry["references"]:
                with self.subTest(msgid=entry["msgid"], reference=reference):
                    self.assertRegex(reference, REFERENCE.pattern + "$")
                    relative, line = reference.rsplit(":", 1)
                    source = CLIENT / relative
                    self.assertTrue(source.is_file(), source)
                    self.assertLessEqual(int(line), len(source.read_text(encoding="utf-8").splitlines()))

    def test_msgids_match_marked_source_strings(self):
        pot_msgids = {entry["msgid"] for entry in messages(read_catalog(POT))}
        source_msgids = marked_source_strings()

        self.assertEqual(sorted(pot_msgids - source_msgids), [], "orphan msgids in dotexpress.pot")
        self.assertEqual(sorted(source_msgids - pot_msgids), [], "msgids missing from dotexpress.pot")


class ZhTwCatalogTests(unittest.TestCase):
    def test_active_msgids_match_pot(self):
        pot = [entry["msgid"] for entry in messages(read_catalog(POT))]
        po = [entry["msgid"] for entry in messages(read_catalog(ZH_TW_PO))]

        self.assertEqual(po, pot)

    def test_every_active_entry_is_translated_and_not_fuzzy(self):
        for entry in messages(read_catalog(ZH_TW_PO)):
            with self.subTest(msgid=entry["msgid"]):
                self.assertNotIn("fuzzy", entry["flags"])
                self.assertNotEqual(entry["msgstr"], "")


@unittest.skipUnless(sys.platform == "win32", "generate-pot.bat is a Windows script")
@unittest.skipUnless(shutil.which("xgettext"), "xgettext is not on PATH")
class GeneratePotBatchTests(unittest.TestCase):
    def test_generated_pot_matches_committed_pot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "dotexpress.pot"
            result = subprocess.run(
                [str(GENERATE_POT), str(output)],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            generated = messages(read_catalog(output))

        committed = messages(read_catalog(POT))
        self.assertEqual(
            [(entry["msgid"], entry["references"], entry["flags"]) for entry in generated],
            [(entry["msgid"], entry["references"], entry["flags"]) for entry in committed],
        )


if __name__ == "__main__":
    unittest.main()
