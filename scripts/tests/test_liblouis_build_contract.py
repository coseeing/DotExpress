import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LiblouisBuildContractTests(unittest.TestCase):
    def test_sconstruct_exposes_nvda_contract_and_runtime_destination(self):
        text = (ROOT / "sconstruct").read_text(encoding="utf-8")
        for required in (
            'TARGET_ARCH="x86_64"',
            '"thirdPartyEnv"',
            '"sourceDir"',
            '"nvdaHelperDebugFlags"',
            '"certFile"',
            '"apiSigningToken"',
            "vendor/nvda/liblouis/build/sconscript",
            "client/braille",
            'tools=["default", "m4"]',
            'miscdeps/tools/m4.exe',
            '"UNICODE"',
            '"/MT"',
            '"_WIN32_WINNT"',
            "LINKFLAGS",
            "release",
            "signExec",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_vendor_sconscript_requires_generated_liblouis_header(self):
        text = (ROOT / "vendor" / "nvda" / "liblouis" / "build" / "sconscript").read_text(encoding="utf-8")
        self.assertIn("env.Requires(objs, liblouisH)", text)

    def test_batch_bootstrap_invokes_scons_without_nmake(self):
        text = (ROOT / "scripts" / "build-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn("scons", text.lower())
        self.assertNotIn("nmake", text.lower())
        self.assertNotIn("liblouis-static.nmake", text)
        self.assertNotIn("M4_EXE", text)

    def test_retired_makefile_is_absent(self):
        self.assertFalse((ROOT / "build" / "liblouis-static.nmake").exists())

    def test_sconstruct_cleans_runtime_tables_before_install(self):
        text = (ROOT / "sconstruct").read_text(encoding="utf-8")
        self.assertIn("liblouis/tables", text)
        self.assertIn("Delete", text)

    def test_repo_contains_m4_toolchain_files(self):
        self.assertTrue((ROOT / "miscdeps" / "tools" / "m4.exe").is_file())
        self.assertTrue((ROOT / "miscdeps" / "tools" / "regex2.dll").is_file())
