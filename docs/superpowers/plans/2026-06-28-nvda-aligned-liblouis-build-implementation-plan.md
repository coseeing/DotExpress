# DotExpress NVDA-Aligned liblouis Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace DotExpress's custom `nmake` liblouis build with a Windows x64 SCons build synchronized from pinned NVDA source, including the Python ctypes wrapper and helper integration.

**Architecture:** `include/nvda/` is a pinned Git submodule used only as the synchronization source, while `include/liblouis/` is pinned to the same liblouis commit selected by that NVDA commit. A deterministic sync script copies an explicit NVDA file allowlist into `vendor/nvda/liblouis/`, records only the NVDA commit as the source revision, and materializes the DotExpress-compatible helper. A small root SCons entry point supplies NVDA's expected environment, invokes the synchronized `sconscript`, and installs the DLL, generated Python wrapper, and tables under `client/braille/`.

**Tech Stack:** Git submodules, Python 3, `unittest`, SCons, Visual Studio 2022 C++ Build Tools, Clang tools for Windows (`clang-cl`), Windows SDK linker/runtime, GNU `m4`

---

## File map

### Source pinning and synchronization

- Modify `.gitmodules`
  - Add the `include/nvda` submodule.
- Create `scripts/sync_nvda_liblouis.py`
  - Validate both submodules.
  - Enforce that `include/liblouis` matches NVDA's nested liblouis gitlink.
  - Copy the approved native-build and Python integration files.
  - Generate the DotExpress-compatible helper from the synchronized NVDA helper.
  - Write deterministic commit-only source metadata.
- Create `scripts/tests/test_sync_nvda_liblouis.py`
  - Test validation, synchronization, transformations, stale-file cleanup, and metadata.
- Create `scripts/tests/__init__.py`
  - Make script tests importable by `unittest`.
- Create `vendor/nvda/liblouis/SOURCE.json`
  - Record repository, source path, exact NVDA commit, and synchronized file list; do not record a tag or ref.
- Create `vendor/nvda/liblouis/build/{sconscript,config.h,strings.h}`
  - Frozen NVDA compatibility headers plus a deterministically path-adapted `sconscript`.
- Create `vendor/nvda/liblouis/python/{louisHelper.py,__init__.py.in}`
  - Frozen copies of NVDA's helper and the liblouis wrapper template selected by NVDA.
- Create `vendor/nvda/liblouis/runtime/louis_helper.py`
  - Deterministically adapted helper for DotExpress's package and logging environment.

### Build integration

- Create `sconstruct`
  - Validate the Windows x64 toolchain.
  - Supply the minimum environment expected by NVDA's synchronized `sconscript`.
  - Redirect NVDA's build outputs to `client/braille/`.
- Modify `scripts/build-liblouis.bat`
  - Keep only Visual Studio environment discovery/bootstrap and the SCons invocation.
- Delete `build/liblouis-static.nmake`
  - Remove the retired divergent `nmake` build.
- Create `scripts/tests/test_liblouis_build_contract.py`
  - Verify the SCons entry point, required variables, runtime destinations, and absence of the old build path without requiring Windows compilation.

### Runtime compatibility and documentation

- Modify `client/braille/louis_helper.py`
  - Replace it with the synchronized, adapted runtime helper.
- Modify `client/braille/liblouis/__init__.py`
  - Replace it with SCons-generated output from NVDA's selected upstream template.
- Create `client/tests/test_liblouis_runtime.py`
  - Verify DLL loading, table resolution, and representative Chinese/UEB translations on Windows.
- Modify `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md`
  - Remove tag/ref metadata and describe commit-only source tracking.
- Modify `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design_zh-TW.md`
  - Apply the same commit-only correction in Traditional Chinese.
- Modify `README.md`
  - Document prerequisites, initial checkout, build, verification, and manual NVDA commit upgrade.

## Task 1: Pin NVDA and liblouis to one coherent source graph

**Files:**

- Modify: `.gitmodules`
- Modify: `include/liblouis` (Git submodule pointer)
- Create: `include/nvda` (Git submodule pointer)

- [ ] **Step 1: Add NVDA as a submodule at the approved reference commit**

Run:

```bash
git submodule add https://github.com/nvaccess/nvda.git include/nvda
git -C include/nvda checkout b493fe7e1f361a8d549f17a3353d826f6fe32334
git submodule update --init include/nvda/include/liblouis
```

Expected: `.gitmodules` contains `include/nvda`, and `git -C include/nvda rev-parse HEAD` prints exactly `b493fe7e1f361a8d549f17a3353d826f6fe32334`.

- [ ] **Step 2: Read the liblouis commit selected by the pinned NVDA commit**

Run:

```bash
git -C include/nvda ls-tree HEAD include/liblouis
```

Expected: output contains gitlink commit `2aa5f84b14de17bcfe8317862d11f6bd7d640e55`.

- [ ] **Step 3: Align DotExpress's liblouis submodule to NVDA's gitlink**

Run:

```bash
git -C include/liblouis fetch origin 2aa5f84b14de17bcfe8317862d11f6bd7d640e55
git -C include/liblouis checkout 2aa5f84b14de17bcfe8317862d11f6bd7d640e55
test "$(git -C include/liblouis rev-parse HEAD)" = "$(git -C include/nvda rev-parse HEAD:include/liblouis)"
```

Expected: the final command exits with status 0. This prevents building NVDA's integration against a different liblouis API revision.

- [ ] **Step 4: Verify recursive checkout from repository metadata**

Run:

```bash
git submodule status include/nvda include/liblouis
git diff --submodule=short -- .gitmodules include/nvda include/liblouis
```

Expected: both top-level submodules have pinned commits; no branch-tracking setting such as `branch = master` is present.

- [ ] **Step 5: Commit the coherent source pins**

```bash
git add .gitmodules include/nvda include/liblouis
git commit -m "build: pin nvda liblouis sources"
```

## Task 2: Build a deterministic NVDA synchronization tool

**Files:**

- Create: `scripts/tests/__init__.py`
- Create: `scripts/tests/test_sync_nvda_liblouis.py`
- Create: `scripts/sync_nvda_liblouis.py`

- [ ] **Step 1: Write failing tests for source validation and commit-only metadata**

Create `scripts/tests/__init__.py` as an empty file.

Create `scripts/tests/test_sync_nvda_liblouis.py` with temporary repositories and these core assertions:

```python
import hashlib
import json
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

        files = {
            "nvdaHelper/liblouis/sconscript": (
                "Import(['thirdPartyEnv', 'sourceDir'])\n"
                'outDir = sourceDir.Dir("louis")\n'
                'unitTestTablesDir = env.Dir("#tests/unit/brailleTables")\n'
                'env["M4"] = f\'"{env.File("#miscdeps/tools/m4.exe")}"\'\n'
                "# Custom tables unit test\n"
                "testTable = env.Install('unused')\n"
            ),
            "nvdaHelper/liblouis/config.h": "#define PACKAGE_NAME \"liblouis\"\n",
            "nvdaHelper/liblouis/strings.h": "#pragma once\n",
            "source/louisHelper.py": (
                "import os\n"
                "from ctypes import (\n"
                "\tWINFUNCTYPE,\n"
                "\taddressof,\n"
                ")\n"
                "import brailleTables\n"
                "import config\n"
                "import globalVars\n"
                "import languageHandler\n"
                "from logHandler import log\n"
                "with os.add_dll_directory(globalVars.appDir):\n"
                "\timport louis\n"
                "def _isDebug():\n"
                '\treturn config.conf[\"debugLog\"][\"louis\"]\n'
                "def emit(level, message):\n"
                "\tNVDALevel = level\n"
                '\tcodepath = "liblouis"\n'
                "\tlog._log(NVDALevel, message, [], codepath=codepath)\n"
                "def getTableLanguage(table):\n"
                '\tlang = \"en_US\"\n'
                "\treturn languageHandler.normalizeLanguage(lang) if lang else None\n"
            ),
            "include/liblouis/python/louis/__init__.py.in": (
                'liblouis = _loader["###LIBLOUIS_SONAME###"]\n'
            ),
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
```

- [ ] **Step 2: Run the sync tests and confirm the module is missing**

Run:

```bash
python3 -m unittest scripts.tests.test_sync_nvda_liblouis -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.sync_nvda_liblouis'`.

- [ ] **Step 3: Implement explicit allowlists, validation, atomic replacement, and metadata**

Create `scripts/sync_nvda_liblouis.py` with these public constants and entry points:

```python
#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

SOURCE_REPO = "https://github.com/nvaccess/nvda.git"
COPY_MAP = {
    "nvdaHelper/liblouis/sconscript": "build/sconscript",
    "nvdaHelper/liblouis/config.h": "build/config.h",
    "nvdaHelper/liblouis/strings.h": "build/strings.h",
    "source/louisHelper.py": "python/louisHelper.py",
    "include/liblouis/python/louis/__init__.py.in": "python/__init__.py.in",
}


class SyncError(RuntimeError):
    pass


def _git_output(repository: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), *args],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as error:
        raise SyncError(error.output.strip()) from error


def _adapt_helper(source: str) -> str:
    replacements = {
        "from ctypes import (\n\tWINFUNCTYPE,": (
            "from ctypes import (\n\tCFUNCTYPE,"
        ),
        "import brailleTables\n": "from braille import tables as brailleTables\n",
        "import config\n": "",
        "import globalVars\n": "",
        "import languageHandler\n": "",
        "from logHandler import log\n": (
            "import logging\n\n"
            "log = logging.getLogger(__name__)\n"
            "WINFUNCTYPE = getattr(__import__(\"ctypes\"), \"WINFUNCTYPE\", CFUNCTYPE)\n"
            "BASE_DIR = os.path.dirname(os.path.abspath(__file__))\n"
        ),
        "with os.add_dll_directory(globalVars.appDir):\n\timport louis\n": (
            "from contextlib import nullcontext\n\n"
            "dll_directory = (\n"
            "\tos.add_dll_directory(BASE_DIR)\n"
            "\tif hasattr(os, \"add_dll_directory\")\n"
            "\telse nullcontext()\n"
            ")\n"
            "with dll_directory:\n"
            "\tfrom braille import liblouis as louis\n"
        ),
        '\treturn config.conf["debugLog"]["louis"]\n': (
            "\treturn log.isEnabledFor(logging.DEBUG)\n"
        ),
        "\tlog._log(NVDALevel, message, [], codepath=codepath)\n": (
            "\tlog.log(NVDALevel, \"%s: %s\", codepath, message)\n"
        ),
        "\treturn languageHandler.normalizeLanguage(lang) if lang else None\n": (
            '\treturn lang.replace("_", "-") if lang else None\n'
        ),
    }
    for old, new in replacements.items():
        if old not in source:
            raise SyncError(f"NVDA helper adaptation marker missing: {old.strip()}")
        source = source.replace(old, new, 1)
    return source


def _adapt_sconscript(source: str) -> str:
    replacements = {
        'outDir = sourceDir.Dir("louis")\n': (
            'outDir = sourceDir.Dir("liblouis")\n'
        ),
        'unitTestTablesDir = env.Dir("#tests/unit/brailleTables")\n': "",
        'env["M4"] = f\'"{env.File("#miscdeps/tools/m4.exe")}"\'\n': (
            'env["M4"] = f\'"{env["M4_EXE"]}"\'\n'
        ),
    }
    for old, new in replacements.items():
        if old not in source:
            raise SyncError(f"NVDA sconscript adaptation marker missing: {old.strip()}")
        source = source.replace(old, new, 1)
    test_tables_marker = "# Custom tables unit test\n"
    if source.count(test_tables_marker) != 1:
        raise SyncError("NVDA sconscript unit-test table marker missing or duplicated")
    source = source.partition(test_tables_marker)[0]
    return source + '\nReturn("louisLib", "louisPython")\n'


def synchronize(
    root: Path,
    expected_liblouis_commit: str | None = None,
    nvda_commit_override: str | None = None,
) -> None:
    nvda = root / "include" / "nvda"
    liblouis = root / "include" / "liblouis"
    vendor = root / "vendor" / "nvda" / "liblouis"
    missing = [relative for relative in COPY_MAP if not (nvda / relative).is_file()]
    if missing:
        raise SyncError("missing NVDA synchronization source: " + ", ".join(missing))

    nvda_commit = nvda_commit_override or _git_output(nvda, "rev-parse", "HEAD")
    selected_liblouis = expected_liblouis_commit or _git_output(
        nvda,
        "rev-parse",
        "HEAD:include/liblouis",
    )
    actual_liblouis = _git_output(liblouis, "rev-parse", "HEAD")
    if actual_liblouis != selected_liblouis:
        raise SyncError(
            f"liblouis commit mismatch: NVDA selects {selected_liblouis}, "
            f"include/liblouis is {actual_liblouis}"
        )

    vendor.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=vendor.parent) as temporary:
        staged = Path(temporary) / "liblouis"
        copied_files = []
        for source_name, destination_name in COPY_MAP.items():
            destination = staged / destination_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            content = (nvda / source_name).read_text(encoding="utf-8")
            if source_name == "nvdaHelper/liblouis/sconscript":
                content = _adapt_sconscript(content)
            destination.write_text(content, encoding="utf-8", newline="\n")
            copied_files.append(destination_name)

        runtime_helper = staged / "runtime" / "louis_helper.py"
        runtime_helper.parent.mkdir(parents=True)
        runtime_helper.write_text(
            _adapt_helper((nvda / "source/louisHelper.py").read_text(encoding="utf-8")),
            encoding="utf-8",
            newline="\n",
        )
        copied_files.append("runtime/louis_helper.py")

        metadata = {
            "source_repo": SOURCE_REPO,
            "source_path": "include/nvda",
            "source_commit": nvda_commit,
            "files": sorted(copied_files),
        }
        (staged / "SOURCE.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if vendor.exists():
            shutil.rmtree(vendor)
        shutil.copytree(staged, vendor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        synchronize(args.root)
    except SyncError as error:
        parser.exit(1, f"sync_nvda_liblouis: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The actual test fixture must preserve the multiline `ctypes` import and all SConscript markers used by pinned NVDA so every replacement above is exercised. Add tests that call `compile(adapted_source, "louis_helper.py", "exec")` and `compile(adapted_sconscript, "sconscript", "exec")` after synchronization. The implementation must not perform `git fetch`, `git checkout`, or any network operation. A missing source or adaptation marker is a hard failure.

- [ ] **Step 4: Run the synchronization tests**

Run:

```bash
python3 -m unittest scripts.tests.test_sync_nvda_liblouis -v
```

Expected: all sync tests PASS; the adapted helper compiles, and two consecutive synchronizations produce byte-identical metadata.

- [ ] **Step 5: Commit the synchronization tool**

```bash
git add scripts/sync_nvda_liblouis.py scripts/tests
git commit -m "build: add nvda liblouis sync tool"
```

## Task 3: Synchronize and review the frozen NVDA integration

**Files:**

- Create: `vendor/nvda/liblouis/SOURCE.json`
- Create: `vendor/nvda/liblouis/build/sconscript`
- Create: `vendor/nvda/liblouis/build/config.h`
- Create: `vendor/nvda/liblouis/build/strings.h`
- Create: `vendor/nvda/liblouis/python/louisHelper.py`
- Create: `vendor/nvda/liblouis/python/__init__.py.in`
- Create: `vendor/nvda/liblouis/runtime/louis_helper.py`

- [ ] **Step 1: Run synchronization from the pinned submodules**

Run:

```bash
python3 scripts/sync_nvda_liblouis.py
```

Expected: exit status 0 and all files listed above are created.

- [ ] **Step 2: Verify exact native/Python source copies**

Run:

```bash
cmp include/nvda/nvdaHelper/liblouis/config.h vendor/nvda/liblouis/build/config.h
cmp include/nvda/nvdaHelper/liblouis/strings.h vendor/nvda/liblouis/build/strings.h
cmp include/nvda/source/louisHelper.py vendor/nvda/liblouis/python/louisHelper.py
cmp include/nvda/include/liblouis/python/louis/__init__.py.in vendor/nvda/liblouis/python/__init__.py.in
```

Expected: every `cmp` exits with status 0.

- [ ] **Step 3: Verify metadata contains the commit and no tag/ref**

Run:

```bash
python3 -c "import json; from pathlib import Path; d=json.loads(Path('vendor/nvda/liblouis/SOURCE.json').read_text()); assert d['source_commit']=='b493fe7e1f361a8d549f17a3353d826f6fe32334'; assert 'source_tag' not in d and 'source_ref' not in d"
```

Expected: exit status 0.

- [ ] **Step 4: Review the helper adaptation as a small auditable delta**

Run:

```bash
diff -u include/nvda/nvdaHelper/liblouis/sconscript vendor/nvda/liblouis/build/sconscript
diff -u vendor/nvda/liblouis/python/louisHelper.py vendor/nvda/liblouis/runtime/louis_helper.py
```

Expected: SConscript differences are limited to output paths, `M4_EXE`, removal of NVDA-only unit-test tables, and `Return`; helper differences are limited to DotExpress-compatible imports, DLL path, logging, debug-state, and language normalization. Any additional upstream dependency change requires an explicit sync transformation and test.

- [ ] **Step 5: Commit the frozen integration**

```bash
git add vendor/nvda/liblouis
git commit -m "build: sync nvda liblouis integration"
```

## Task 4: Add a contract test for the SCons build boundary

**Files:**

- Create: `scripts/tests/test_liblouis_build_contract.py`

- [ ] **Step 1: Write a failing source-level build contract test**

Create `scripts/tests/test_liblouis_build_contract.py`:

```python
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
            'vendor/nvda/liblouis/build/sconscript',
            'client/braille',
            "M4_EXE",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_batch_bootstrap_invokes_scons_without_nmake(self):
        text = (ROOT / "scripts" / "build-liblouis.bat").read_text(encoding="utf-8")
        self.assertIn("scons", text.lower())
        self.assertNotIn("nmake", text.lower())
        self.assertNotIn("liblouis-static.nmake", text)

    def test_retired_makefile_is_absent(self):
        self.assertFalse((ROOT / "build" / "liblouis-static.nmake").exists())
```

- [ ] **Step 2: Run the test and confirm the old build fails the contract**

Run:

```bash
python3 -m unittest scripts.tests.test_liblouis_build_contract -v
```

Expected: FAIL because `sconstruct` is absent and the batch file still invokes `nmake`.

- [ ] **Step 3: Commit only the failing contract test**

```bash
git add scripts/tests/test_liblouis_build_contract.py
git commit -m "test: define nvda liblouis build contract"
```

## Task 5: Implement the minimal NVDA-compatible SCons environment

**Files:**

- Create: `sconstruct`

- [ ] **Step 1: Verify the synchronized sconscript has only the approved adaptations**

Run:

```bash
diff -u include/nvda/nvdaHelper/liblouis/sconscript vendor/nvda/liblouis/build/sconscript
```

Expected: the diff contains only `outDir = sourceDir.Dir("liblouis")`, external `M4_EXE`, removal of NVDA's `tests/unit/brailleTables` block, and `Return("louisLib", "louisPython")`. NVDA's compiler selection, source list, architecture flags, `CPPDEFINES`, generated header, wrapper generation, and table macro behavior remain unchanged.

- [ ] **Step 2: Create the minimal root `sconstruct`**

Create `sconstruct` with fail-fast validation and only the exports consumed by the synchronized script:

```python
import os
from pathlib import Path

from SCons.Script import ARGUMENTS, Default, Dir, Environment, Export, SConscript

if os.name != "nt":
    raise RuntimeError("The aligned liblouis build currently supports Windows x64 only")

root = Path(Dir("#").abspath)
m4_exe = ARGUMENTS.get("M4_EXE") or os.environ.get("M4_EXE")
if not m4_exe:
    raise RuntimeError("M4_EXE is required and must point to m4.exe")
if not Path(m4_exe).is_file():
    raise RuntimeError(f"M4_EXE does not exist: {m4_exe}")

thirdPartyEnv = Environment(
    ENV=os.environ,
    TARGET_ARCH="x86_64",
    tools=["default"],
)
if not thirdPartyEnv.WhereIs("clang-cl"):
    raise RuntimeError(
        "clang-cl was not found; install Visual Studio 2022 C++ tools "
        "and Clang tools for Windows"
    )
if not thirdPartyEnv.WhereIs("link"):
    raise RuntimeError("MSVC linker was not found; run from a VS 2022 x64 environment")

thirdPartyEnv["M4_EXE"] = str(Path(m4_exe).resolve())
thirdPartyEnv["nvdaHelperDebugFlags"] = []
thirdPartyEnv["certFile"] = ""
thirdPartyEnv["apiSigningToken"] = ""
sourceDir = thirdPartyEnv.Dir("#client/braille")

Export("thirdPartyEnv", "sourceDir")
outputs = SConscript("vendor/nvda/liblouis/build/sconscript")
Default(outputs)
```

The synchronized `sconscript` returns `louisLib` and `louisPython`; use those values as `outputs`.

- [ ] **Step 3: Parse the SCons graph on a Windows VS 2022 x64 shell**

Run:

```bat
set M4_EXE=C:\Tools\m4\m4.exe
scons --tree=prune --no-exec
```

Expected: SCons resolves `clang-cl`, enumerates liblouis C objects, generated `liblouis.h`, `client\braille\liblouis.dll`, `client\braille\__init__.py` staging output, and tables without invoking a compiler.

- [ ] **Step 4: Run the platform-independent build contract test**

Run:

```bash
python3 -m unittest scripts.tests.test_liblouis_build_contract -v
```

Expected: the SConstruct contract test now passes; batch/deletion assertions still fail until Task 6.

- [ ] **Step 5: Commit the SCons graph**

```bash
git add sconstruct
git commit -m "build: add nvda-aligned liblouis scons graph"
```

## Task 6: Replace the nmake launcher and install runtime artifacts

**Files:**

- Modify: `scripts/build-liblouis.bat`
- Delete: `build/liblouis-static.nmake`
- Modify: `sconstruct`

- [ ] **Step 1: Replace the batch file with a thin Visual Studio/SCons bootstrap**

Use `vswhere.exe` instead of a hard-coded Visual Studio edition path:

```bat
@echo off
setlocal

set "ROOT=%~dp0.."
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    echo Missing vswhere.exe. Install Visual Studio 2022 C++ Build Tools.
    exit /b 1
)

for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -version [17.0^,18.0^) -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSROOT=%%I"
if not defined VSROOT (
    echo Visual Studio 2022 C++ tools were not found.
    exit /b 1
)

call "%VSROOT%\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 exit /b 1

where clang-cl >nul 2>&1
if errorlevel 1 (
    echo clang-cl was not found. Install Clang tools for Windows.
    exit /b 1
)
where scons >nul 2>&1
if errorlevel 1 (
    echo scons was not found. Install it with: py -m pip install scons
    exit /b 1
)
if not defined M4_EXE (
    echo M4_EXE must point to m4.exe.
    exit /b 1
)

pushd "%ROOT%"
scons M4_EXE="%M4_EXE%" %*
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%
```

- [ ] **Step 2: Make runtime destinations explicit in SCons**

Ensure the synchronized `sconscript` produces:

```text
client/braille/liblouis.dll
client/braille/liblouis/__init__.py
client/braille/liblouis/tables/*
```

Use `sourceDir = #client/braille` and `outDir = sourceDir.Dir("liblouis")`. The generated wrapper's `###LIBLOUIS_SONAME###` substitution must be `liblouis.dll`, and tables must be installed under `outDir.Dir("tables")`.

Add an SCons `InstallAs` node for the synchronized adapted helper:

```python
helper = thirdPartyEnv.InstallAs(
    "#client/braille/louis_helper.py",
    "#vendor/nvda/liblouis/runtime/louis_helper.py",
)
Default(helper)
```

- [ ] **Step 3: Remove the retired custom makefile**

Run:

```bash
git rm build/liblouis-static.nmake
```

Expected: no tracked build script references `nmake` or `liblouis-static.nmake`.

- [ ] **Step 4: Run the build contract tests**

Run:

```bash
python3 -m unittest scripts.tests.test_liblouis_build_contract -v
rg -n "nmake|liblouis-static\\.nmake" scripts sconstruct vendor
```

Expected: all tests PASS and `rg` returns no matches.

- [ ] **Step 5: Perform the first clean Windows x64 build**

From a normal Windows command prompt:

```bat
set M4_EXE=C:\Tools\m4\m4.exe
scripts\build-liblouis.bat -c
scripts\build-liblouis.bat
```

Expected: both commands exit 0; the second command invokes `clang-cl` and produces the DLL, generated wrapper, adapted helper, and expanded `.in` tables under `client\braille`.

- [ ] **Step 6: Commit the launcher migration**

```bash
git add scripts/build-liblouis.bat sconstruct client/braille/louis_helper.py client/braille/liblouis/__init__.py client/braille/liblouis/tables
git add -u build/liblouis-static.nmake
git commit -m "build: replace liblouis nmake flow with scons"
```

## Task 7: Verify Python ABI/API compatibility and translations

**Files:**

- Create: `client/tests/test_liblouis_runtime.py`

- [ ] **Step 1: Add Windows-only runtime smoke tests**

Create `client/tests/test_liblouis_runtime.py`:

```python
import os
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(sys.platform == "win32", "requires the Windows liblouis runtime")
class LiblouisRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from braille import liblouis
        from braille import louis_helper
        from braille import tables

        cls.louis = liblouis
        cls.helper = louis_helper
        cls.tables = tables
        cls.helper.initialize()

    @classmethod
    def tearDownClass(cls):
        cls.helper.terminate()

    def test_built_wrapper_loads_bundled_dll(self):
        dll = Path(__file__).parents[1] / "braille" / "liblouis.dll"
        self.assertTrue(dll.is_file())
        self.assertGreater(self.louis.charSize(), 0)
        self.assertTrue(self.louis.version())

    def test_table_resolver_finds_bundled_table(self):
        resolved = list(self.helper._resolveTableInner(["en-ueb-g2.ctb"]))
        self.assertEqual(1, len(resolved))
        self.assertTrue(Path(resolved[0]).is_file())

    def test_chinese_default_table_translates(self):
        result = self.louis.translateString(["zh-tw.ctb"], "中文")
        self.assertTrue(result)

    def test_ueb_grade_1_translates(self):
        result = self.louis.translateString(["en-ueb-g1.ctb"], "hello")
        self.assertTrue(result)

    def test_ueb_grade_2_translates_and_contracts(self):
        grade_1 = self.louis.translateString(["en-ueb-g1.ctb"], "the")
        grade_2 = self.louis.translateString(["en-ueb-g2.ctb"], "the")
        self.assertTrue(grade_2)
        self.assertNotEqual(grade_1, grade_2)
```

Before committing, confirm the repository's actual Chinese default table filename in `client/braille/tables.py`. If it is not `zh-tw.ctb`, replace that literal with the registered default table filename; do not add a fallback that hides a missing expected table.

- [ ] **Step 2: Run the focused runtime tests from `client/`**

Run on Windows:

```bat
cd client
py -m unittest tests.test_liblouis_runtime -v
```

Expected: five tests PASS. A DLL load failure, missing symbol, callback type error, or missing table is a release-blocking wrapper/build mismatch.

- [ ] **Step 3: Run existing translation/configuration regression tests**

Run on Windows from `client/`:

```bat
py -m unittest tests.test_config tests.test_translation_result tests.test_translation_language_result tests.test_language_detection_translation -v
```

Expected: all non-environmental tests PASS with the synchronized DLL, wrapper, helper, and tables.

- [ ] **Step 4: Verify generated wrapper provenance**

Run from repository root:

```bash
python3 -c "from pathlib import Path; t=Path('vendor/nvda/liblouis/python/__init__.py.in').read_text(); r=Path('client/braille/liblouis/__init__.py').read_text(); assert r == t.replace('###LIBLOUIS_SONAME###', 'liblouis.dll')"
```

Expected: exit status 0. This proves the runtime ctypes wrapper comes from the same template selected by pinned NVDA.

- [ ] **Step 5: Commit runtime compatibility coverage**

```bash
git add client/tests/test_liblouis_runtime.py
git commit -m "test: cover aligned liblouis runtime"
```

## Task 8: Correct commit-only provenance documentation

**Files:**

- Modify: `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md`
- Modify: `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design_zh-TW.md`
- Modify: `README.md`

- [ ] **Step 1: Remove tag/ref fields from both design documents**

In both design files:

- Change every “commit / tag” statement to “commit”.
- Remove `source_ref` and tag examples from `SOURCE.json`.
- State that `SOURCE.json` records `source_repo`, `source_path`, `source_commit`, and the synchronized files.
- Keep upgrade policy manual: the operator checks out an explicit commit in `include/nvda`, synchronizes, reviews, builds, and tests.

The corrected JSON example must be:

```json
{
  "source_repo": "https://github.com/nvaccess/nvda.git",
  "source_path": "include/nvda",
  "source_commit": "b493fe7e1f361a8d549f17a3353d826f6fe32334",
  "files": [
    "build/config.h",
    "build/sconscript",
    "build/strings.h",
    "python/__init__.py.in",
    "python/louisHelper.py",
    "runtime/louis_helper.py"
  ]
}
```

- [ ] **Step 2: Add the operational workflow to `README.md`**

Add a “Building liblouis on Windows” section containing:

```markdown
### Prerequisites

- Visual Studio 2022 C++ tools
- Clang tools for Windows
- Python 3 with SCons (`py -m pip install scons`)
- GNU `m4.exe`, exposed through `M4_EXE`

### Initial checkout and build

```bat
git submodule update --init --recursive
py scripts\sync_nvda_liblouis.py
set M4_EXE=C:\Tools\m4\m4.exe
scripts\build-liblouis.bat
```

### Manual NVDA upgrade

1. Check out the approved commit in `include/nvda`.
2. Set `include/liblouis` to the gitlink printed by
   `git -C include/nvda rev-parse HEAD:include/liblouis`.
3. Run `py scripts\sync_nvda_liblouis.py`.
4. Review `vendor/nvda/liblouis/` and `SOURCE.json`.
5. Clean-build and run the liblouis runtime tests.
6. Commit both submodule pointers, synchronized vendor files, and generated runtime files together.
```

- [ ] **Step 3: Verify documentation contains no tag-based source policy**

Run:

```bash
rg -n "source_ref|source_tag|commit / tag|commit/tag|commit 或 tag|commit / tag" \
  docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md \
  docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design_zh-TW.md \
  README.md
```

Expected: no matches.

- [ ] **Step 4: Commit documentation**

Because `docs/` is ignored in this repository, force-add only the two already tracked design files if required:

```bash
git add README.md
git add -f docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md
git add -f docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design_zh-TW.md
git commit -m "docs: describe nvda-aligned liblouis workflow"
```

## Task 9: Run end-to-end reproducibility and regression verification

**Files:**

- Verify only; no planned file changes.

- [ ] **Step 1: Verify synchronization is clean and deterministic**

Run:

```bash
python3 scripts/sync_nvda_liblouis.py
git diff --exit-code -- vendor/nvda/liblouis client/braille/louis_helper.py
```

Expected: exit status 0 and no diff.

- [ ] **Step 2: Run all platform-independent synchronization/build tests**

Run:

```bash
python3 -m unittest scripts.tests.test_sync_nvda_liblouis scripts.tests.test_liblouis_build_contract -v
```

Expected: all tests PASS.

- [ ] **Step 3: Clean-build twice on Windows**

Run:

```bat
set M4_EXE=C:\Tools\m4\m4.exe
scripts\build-liblouis.bat -c
scripts\build-liblouis.bat
for /f "tokens=*" %%I in ('certutil -hashfile client\braille\liblouis.dll SHA256 ^| findstr /v hash') do set FIRST=%%I
scripts\build-liblouis.bat -c
scripts\build-liblouis.bat
```

Expected: both clean builds exit 0. Do not require byte-identical DLL hashes because PE toolchains can embed nondeterministic data; require identical source metadata and generated Python/table content.

- [ ] **Step 4: Run focused and full client regressions on Windows**

Run from `client/`:

```bat
py -m unittest tests.test_liblouis_runtime tests.test_config tests.test_translation_result tests.test_translation_language_result tests.test_language_detection_translation -v
py -m unittest discover -s tests -v
```

Expected: focused tests PASS. Full discovery has no new failures relative to the repository baseline; document any pre-existing environment-specific skips.

- [ ] **Step 5: Inspect final repository state**

Run:

```bash
git status --short
git diff --check
git log --oneline --max-count=12
```

Expected: `git diff --check` exits 0. Unrelated existing `chat.txt` and `ref/` remain untouched and uncommitted. The implementation consists of small scoped commits corresponding to the tasks above.
