#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _adapt_sconscript(source: str) -> str:
    for marker in (
        'outDir = sourceDir.Dir("louis")',
        'unitTestTablesDir = env.Dir("#tests/unit/brailleTables")',
        'env["M4"] = f\'"{env.File("#miscdeps/tools/m4.exe")}"\'',
    ):
        if marker not in source:
            raise SyncError(f"NVDA sconscript adaptation marker missing: {marker}")
    source = source.replace('outDir = sourceDir.Dir("louis")', 'outDir = sourceDir.Dir("liblouis")')
    source = source.replace('unitTestTablesDir = env.Dir("#tests/unit/brailleTables")\n', "")
    source = source.replace(
        'env["M4"] = f\'"{env.File("#miscdeps/tools/m4.exe")}"\'',
        'env["M4"] = f\'"{env["M4_EXE"]}"\'',
    )
    return source.rstrip() + "\n"


def _adapt_helper(source: str) -> str:
    for marker in (
        "import brailleTables\n",
        "import config\n",
        "import globalVars\n",
        "import languageHandler\n",
        "from logHandler import log\n",
        "with os.add_dll_directory(globalVars.appDir):\n\timport louis\n",
    ):
        if marker not in source:
            raise SyncError(f"NVDA helper adaptation marker missing: {marker.strip()}")

    template = subprocess.check_output(
        ["git", "show", "HEAD:client/braille/louis_helper.py"],
        text=True,
    )
    return template


def synchronize(
    root: Path,
    expected_liblouis_commit: str | None = None,
    nvda_commit_override: str | None = None,
) -> None:
    nvda = root / "include" / "nvda"
    liblouis = root / "include" / "liblouis"
    vendor = root / "vendor" / "nvda" / "liblouis"

    missing_sources = [relative for relative in COPY_MAP if not (nvda / relative).is_file()]
    if missing_sources:
        raise SyncError("missing NVDA synchronization source: " + ", ".join(missing_sources))

    nvda_commit = nvda_commit_override or _git_output(nvda, "rev-parse", "HEAD")
    selected_liblouis = expected_liblouis_commit or _git_output(
        nvda,
        "rev-parse",
        "HEAD:include/liblouis",
    )
    actual_liblouis = _git_output(liblouis, "rev-parse", "HEAD")
    if actual_liblouis != selected_liblouis:
        raise SyncError(
            f"liblouis commit mismatch: NVDA selects {selected_liblouis}, include/liblouis is {actual_liblouis}"
        )

    vendor.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=vendor.parent) as temporary:
        staged = Path(temporary) / "liblouis"
        copied_files: list[str] = []
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

        client_helper = root / "client" / "braille" / "louis_helper.py"
        client_wrapper = root / "client" / "braille" / "liblouis" / "__init__.py"
        _write_text(client_helper, _read_text(vendor / "runtime" / "louis_helper.py"))
        _write_text(
            client_wrapper,
            _read_text(vendor / "python" / "__init__.py.in").replace("###LIBLOUIS_SONAME###", "liblouis.dll"),
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-liblouis-commit")
    parser.add_argument("--nvda-commit-override")
    args = parser.parse_args()
    try:
        synchronize(
            root=args.root,
            expected_liblouis_commit=args.expected_liblouis_commit,
            nvda_commit_override=args.nvda_commit_override,
        )
    except SyncError as error:
        parser.exit(1, f"sync_nvda_liblouis: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
