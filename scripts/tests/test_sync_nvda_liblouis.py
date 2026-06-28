import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.sync_nvda_liblouis import SyncError, synchronize


class SyncNvdaLiblouisTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.nvda = self.root / "include" / "nvda"
        self.liblouis = self.root / "include" / "liblouis"
        self.vendor = self.root / "vendor" / "nvda" / "liblouis"

        for path in (self.nvda, self.liblouis):
            path.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(path)], check=True)
            subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)

        fixture_root = Path(__file__).resolve().parents[2]
        files = {
            "nvdaHelper/liblouis/sconscript": fixture_root.joinpath("include/nvda/nvdaHelper/liblouis/sconscript").read_text(
                encoding="utf-8"
            ),
            "nvdaHelper/liblouis/config.h": fixture_root.joinpath("include/nvda/nvdaHelper/liblouis/config.h").read_text(
                encoding="utf-8"
            ),
            "nvdaHelper/liblouis/strings.h": fixture_root.joinpath("include/nvda/nvdaHelper/liblouis/strings.h").read_text(
                encoding="utf-8"
            ),
            "source/louisHelper.py": fixture_root.joinpath("include/nvda/source/louisHelper.py").read_text(
                encoding="utf-8"
            ),
            "include/liblouis/python/louis/__init__.py.in": fixture_root.joinpath(
                "include/nvda/include/liblouis/python/louis/__init__.py.in"
            ).read_text(encoding="utf-8"),
        }
        for relative, content in files.items():
            target = self.nvda / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        (self.liblouis / "configure.ac").write_text("AC_INIT\n", encoding="utf-8")

        subprocess.run(["git", "-C", str(self.liblouis), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.liblouis), "commit", "-qm", "fixture"], check=True)
        self.liblouis_commit = subprocess.check_output(
            ["git", "-C", str(self.liblouis), "rev-parse", "HEAD"],
            text=True,
        ).strip()

        subprocess.run(["git", "-C", str(self.nvda), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.nvda), "commit", "-qm", "fixture"], check=True)
        self.nvda_commit = subprocess.check_output(
            ["git", "-C", str(self.nvda), "rev-parse", "HEAD"],
            text=True,
        ).strip()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_records_commit_without_tag_or_ref(self):
        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )
        metadata = json.loads((self.vendor / "SOURCE.json").read_text(encoding="utf-8"))
        self.assertEqual("https://github.com/nvaccess/nvda.git", metadata["source_repo"])
        self.assertEqual("include/nvda", metadata["source_path"])
        self.assertEqual(self.nvda_commit, metadata["source_commit"])
        self.assertNotIn("source_tag", metadata)
        self.assertNotIn("source_ref", metadata)
        self.assertNotIn("synced_at", metadata)
        self.assertEqual(sorted(metadata["files"]), metadata["files"])

    def test_missing_allowlisted_source_fails_before_writing_vendor(self):
        (self.nvda / "source" / "louisHelper.py").unlink()
        with self.assertRaisesRegex(SyncError, "source/louisHelper.py"):
            synchronize(
                root=self.root,
                expected_liblouis_commit=self.liblouis_commit,
                nvda_commit_override=self.nvda_commit,
            )
        self.assertFalse(self.vendor.exists())

    def test_liblouis_revision_mismatch_fails(self):
        with self.assertRaisesRegex(SyncError, "liblouis commit mismatch"):
            synchronize(
                root=self.root,
                expected_liblouis_commit="0" * 40,
                nvda_commit_override=self.nvda_commit,
            )

    def test_sync_removes_stale_files_and_is_repeatable(self):
        stale = self.vendor / "build" / "removed-upstream.h"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale", encoding="utf-8")

        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )
        first = hashlib.sha256((self.vendor / "SOURCE.json").read_bytes()).hexdigest()

        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )
        second = hashlib.sha256((self.vendor / "SOURCE.json").read_bytes()).hexdigest()

        self.assertFalse(stale.exists())
        self.assertEqual(first, second)
        self.assertEqual(
            [
                "build/config.h",
                "build/sconscript",
                "build/strings.h",
                "python/__init__.py.in",
                "python/louisHelper.py",
                "runtime/louis_helper.py",
            ],
            json.loads((self.vendor / "SOURCE.json").read_text(encoding="utf-8"))["files"],
        )

    def test_synced_sources_compile(self):
        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )
        adapted_helper = (self.vendor / "runtime" / "louis_helper.py").read_text(encoding="utf-8")
        adapted_sconscript = (self.vendor / "build" / "sconscript").read_text(encoding="utf-8")
        compile(adapted_helper, "louis_helper.py", "exec")
        compile(adapted_sconscript, "sconscript", "exec")

    def test_sconscript_adaptation_removes_nvda_test_block_and_returns_outputs(self):
        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )
        adapted_sconscript = (self.vendor / "build" / "sconscript").read_text(encoding="utf-8")
        self.assertNotIn("unitTestTablesDir", adapted_sconscript)
        self.assertNotIn("testTable =", adapted_sconscript)
        self.assertIn('Return("louisLibInstall", "louisPython", "louisTables")', adapted_sconscript)

    def test_helper_adaptation_uses_nvda_source_not_repository_head(self):
        helper_source = (self.nvda / "source" / "louisHelper.py").read_text(encoding="utf-8")
        helper_source = helper_source.replace(
            "def _isDebug():\n\treturn config.conf[\"debugLog\"][\"louis\"]\n",
            "def _isDebug():\n\treturn config.conf[\"debugLog\"][\"louis\"]\n\n\ndef dotexpressFixtureMarker():\n\treturn True\n",
        )
        (self.nvda / "source" / "louisHelper.py").write_text(helper_source, encoding="utf-8")

        synchronize(
            root=self.root,
            expected_liblouis_commit=self.liblouis_commit,
            nvda_commit_override=self.nvda_commit,
        )

        adapted_helper = (self.vendor / "runtime" / "louis_helper.py").read_text(encoding="utf-8")
        self.assertIn("dotexpressFixtureMarker", adapted_helper)
        self.assertNotIn("git show", adapted_helper)

    def test_synchronize_isolated_from_current_working_directory(self):
        helper_source = (self.nvda / "source" / "louisHelper.py").read_text(encoding="utf-8")
        helper_source = helper_source.replace(
            "return languageHandler.normalizeLanguage(lang) if lang else None\n",
            "return languageHandler.normalizeLanguage(lang) if lang else None\n# temp-root-only marker\n",
        )
        (self.nvda / "source" / "louisHelper.py").write_text(helper_source, encoding="utf-8")

        previous_cwd = Path.cwd()
        other = Path(tempfile.mkdtemp())
        try:
            os.chdir(other)
            synchronize(
                root=self.root,
                expected_liblouis_commit=self.liblouis_commit,
                nvda_commit_override=self.nvda_commit,
            )
        finally:
            os.chdir(previous_cwd)

        adapted_helper = (self.vendor / "runtime" / "louis_helper.py").read_text(encoding="utf-8")
        self.assertIn("temp-root-only marker", adapted_helper)

    def test_sconscript_adaptation_fails_when_install_block_shape_changes(self):
        sconscript = (self.nvda / "nvdaHelper" / "liblouis" / "sconscript").read_text(encoding="utf-8")
        sconscript = sconscript.replace(
            'env.Install(sourceDir, louisLib)\n',
            'env.Install(\n\t sourceDir,\n\t louisLib,\n)\n',
        )
        (self.nvda / "nvdaHelper" / "liblouis" / "sconscript").write_text(sconscript, encoding="utf-8")

        with self.assertRaisesRegex(SyncError, "Expected exactly one match"):
            synchronize(
                root=self.root,
                expected_liblouis_commit=self.liblouis_commit,
                nvda_commit_override=self.nvda_commit,
            )
