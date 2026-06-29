import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LiblouisBuildContractTests(unittest.TestCase):
    def test_root_gitignore_excludes_python_caches(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("__pycache__/", text)
        self.assertIn("*.pyc", text)

    def test_client_gitignore_owns_client_specific_ignore_rules(self):
        root_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        client_text = (ROOT / "client" / ".gitignore").read_text(encoding="utf-8")
        for required in (
            "build/",
            "dist/",
            "dictionary/",
            "log/",
            ".venv/",
            "workspace/",
            "DotExpress.spec",
            "braille/liblouis.dll",
            "braille/liblouis.lib",
            "braille/liblouis.exp",
            "braille/louis_helper.py",
            "braille/liblouis/__init__.py",
            "braille/liblouis/tables/",
        ):
            with self.subTest(required=required):
                self.assertIn(required, client_text)
        self.assertNotIn("client/build/", root_text)

    def test_sconstruct_exposes_nvda_contract_and_runtime_destination(self):
        text = (ROOT / "sconstruct").read_text(encoding="utf-8")
        for required in (
            'TARGET_ARCH="x86_64"',
            '"thirdPartyEnv"',
            '"nvdaHelperDebugFlags"',
            '"certFile"',
            '"apiSigningToken"',
            "vendor/nvda/liblouis/build/sconscript",
            "vendor/nvda/liblouis/dist",
            'tools=["default", "m4"]',
            'miscdeps/tools/m4.exe',
            '"UNICODE"',
            '"/MT"',
            '"_WIN32_WINNT"',
            "LINKFLAGS",
            "release",
            "signExec",
            'Alias("build"',
            'Alias("install"',
            'Alias("clean-liblouis"',
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_vendor_sconscript_requires_generated_liblouis_header(self):
        text = (ROOT / "vendor" / "nvda" / "liblouis" / "build" / "sconscript").read_text(encoding="utf-8")
        self.assertIn("env.Requires(objs, liblouisH)", text)

    def test_batch_bootstrap_invokes_scons_without_nmake(self):
        text = (ROOT / "scripts" / "build-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn("scons build", text.lower())
        self.assertNotIn("nmake", text.lower())
        self.assertNotIn("liblouis-static.nmake", text)
        self.assertNotIn("M4_EXE", text)

    def test_install_batch_invokes_scons_install(self):
        text = (ROOT / "scripts" / "install-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn("scons install", text.lower())

    def test_clean_batch_invokes_scons_clean(self):
        text = (ROOT / "scripts" / "clean-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn("scons clean-liblouis", text.lower())
        for required in (
            "dist",
            "client_braille",
            r'liblouis\tables',
            'liblouis.dll',
            r'include\liblouis\liblouis\liblouis.h',
        ):
            with self.subTest(required=required):
                self.assertIn(required, text.lower())

    def test_batch_bootstrap_removes_shadowing_source_header(self):
        text = (ROOT / "scripts" / "build-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn(r"include\liblouis\liblouis\liblouis.h", text)
        self.assertIn("del /q", text.lower())

    def test_retired_makefile_is_absent(self):
        self.assertFalse((ROOT / "build" / "liblouis-static.nmake").exists())

    def test_sconstruct_cleans_runtime_tables_before_install(self):
        text = (ROOT / "sconstruct").read_text(encoding="utf-8")
        self.assertIn("liblouis/tables", text)
        self.assertIn("Delete", text)

    def test_clean_rebuild_dotexpress_stages_clean_build_install_before_packaging(self):
        text = (ROOT / "scripts" / "clean-rebuild-dotexpress.bat").read_text(encoding="utf-8")
        for required in (
            r"call scripts\clean-liblouis.bat",
            r"call scripts\build-liblouis.bat",
            r"call scripts\install-liblouis.bat",
            r"call scripts\build-dotexpress.bat",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_repo_contains_m4_toolchain_files(self):
        self.assertTrue((ROOT / "miscdeps" / "tools" / "m4.exe").is_file())
        self.assertTrue((ROOT / "miscdeps" / "tools" / "regex2.dll").is_file())

    def test_windows_clean_script_stays_within_submodule_outputs(self):
        text = (ROOT / "include" / "liblouis" / "windows" / "clean.bat").read_text(encoding="utf-8")
        for required in ("erase *.obj", "erase liblouis*.dll", "erase liblouis*.exp", "erase liblouis*.lib"):
            with self.subTest(required=required):
                self.assertIn(required, text)
        for forbidden in (
            "client\\braille",
            "BRAILLE_RUNTIME",
            "BRAILLE_TABLES",
            "louis_helper.py",
            "__pycache__",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
