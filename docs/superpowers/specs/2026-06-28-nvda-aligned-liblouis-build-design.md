# DotExpress NVDA-Aligned liblouis Build Design

## Summary

DotExpress currently builds `liblouis` through an upstream Windows `nmake` path plus repository-local adjustments. That path has diverged from NVDA, even though DotExpress already reuses NVDA-derived Python `liblouis` integration code. The result is a fragile integration boundary: build settings, compatibility shims, Python ctypes bindings, and runtime table handling are no longer managed as one unit.

This design changes DotExpress to align its `liblouis` integration with NVDA. The build entrypoint will move to SCons, matching NVDA's `liblouis` build model. NVDA integration files and Python wrapper files will be synchronized from a pinned NVDA source submodule at `include/nvda`, then frozen into `vendor/nvda/liblouis/` for product use. DotExpress will keep `include/liblouis/` as the upstream `liblouis` source submodule and will continue to ship runtime artifacts under `client/braille/`.

The first version is intentionally narrow: Windows x64 only, no signing, no multi-architecture matrix, and no MathCAT work.

## Goals

- Align DotExpress `liblouis` build behavior with NVDA's `liblouis` build integration.
- Manage the build integration layer and Python wrapper layer as a single synchronized unit.
- Replace the current `nmake`-based build path with a minimal DotExpress SCons entrypoint that invokes NVDA-aligned `liblouis` build logic.
- Pin the NVDA source used for synchronization in a Git submodule at `include/nvda`.
- Preserve a clear separation between:
  - upstream `liblouis` source,
  - NVDA integration source,
  - DotExpress runtime output.
- Keep DotExpress runtime import paths stable by copying synchronized Python wrapper files into existing `client/braille/` locations.

## Non-Goals

- No MathCAT changes.
- No attempt to vendor or reuse NVDA's full build system.
- No support for x86, arm64, or arm64ec in the first version.
- No signing or packaging integration.
- No direct runtime imports from `vendor/nvda/liblouis/`.
- No automatic network fetch of NVDA during sync or build.
- No broad refactor of DotExpress braille behavior outside the `liblouis` integration boundary.

## Motivation

DotExpress is already coupled to NVDA's `liblouis` Python integration model. If the repository only syncs DLL build behavior while leaving the ctypes wrapper and helper code on an older fork, the project can still break when `liblouis` API shape, callback expectations, constants, or load behavior change. Therefore, the correct synchronization unit is not only the native build script. It is:

- the native build integration,
- the Python ctypes wrapper,
- the runtime copy/output contract.

That unit should be versioned and upgraded together.

## High-Level Architecture

The new architecture has three layers:

1. Upstream source layer
   - `include/liblouis/`
   - Tracks upstream `liblouis` source as a Git submodule.
   - This remains the actual C source and table source used for compilation.

2. NVDA integration layer
   - `include/nvda/`
   - Tracks a pinned NVDA commit/tag as a Git submodule.
   - Serves only as the synchronization source, never as a direct runtime or direct build dependency.
   - `vendor/nvda/liblouis/`
   - Stores the synchronized, frozen NVDA-derived integration files used by DotExpress.

3. DotExpress runtime layer
   - `client/braille/`
   - Receives generated DLLs, tables, and synchronized Python wrapper files.
   - Keeps the current runtime/import structure stable for the rest of DotExpress.

The build will read upstream `liblouis` from `include/liblouis/` and NVDA-derived build integration from `vendor/nvda/liblouis/`. Runtime code will continue to load from `client/braille/`.

## Directory Layout

### Upstream source

- `include/liblouis/`
  - Upstream `liblouis` Git submodule.

### NVDA source

- `include/nvda/`
  - Pinned NVDA Git submodule.
  - Used as the local source of truth for synchronization.

### Frozen vendor integration

- `vendor/nvda/liblouis/build/`
  - NVDA `liblouis` build integration files copied from `include/nvda/`.

- `vendor/nvda/liblouis/python/`
  - NVDA `liblouis` Python wrapper/helper files copied from `include/nvda/`.

- `vendor/nvda/liblouis/SOURCE.json`
  - Metadata recording the NVDA source reference and synchronized file list.

### DotExpress runtime output

- `client/braille/liblouis.dll`
- `client/braille/liblouis/tables/`
- `client/braille/louis_helper.py`
- `client/braille/liblouis/__init__.py`

These runtime files are outputs of the sync/build flow and should no longer be treated as manually maintained logic.

## Sync Contract

### Sync source

Synchronization will read from `include/nvda/`, which is pinned to a fixed commit/tag by Git submodule state.

### Sync target

Synchronization will copy only a fixed white-list of files into `vendor/nvda/liblouis/`.

### White-list: native build integration

Copy into `vendor/nvda/liblouis/build/`:

- `nvdaHelper/liblouis/sconscript`
- `nvdaHelper/liblouis/config.h`
- `nvdaHelper/liblouis/strings.h`

These files matter because:

- `sconscript` defines the NVDA build behavior and compiler/tool expectations.
- `config.h` and `strings.h` provide the Windows compatibility shims that NVDA uses to successfully build `liblouis`.

### White-list: Python wrapper integration

Copy into `vendor/nvda/liblouis/python/`:

- NVDA's `louisHelper.py`
- NVDA's Python ctypes binding source for `liblouis` (the source used to produce DotExpress's `client/braille/liblouis/__init__.py`)

The exact source path may vary by NVDA revision, but the synchronized unit must always include:

- the ctypes binding layer,
- the table resolver/helper layer.

This requirement is semantic, not merely path-based: if NVDA renames or reorganizes these files, the sync script must still extract the equivalent logical components.

### Sync metadata

`vendor/nvda/liblouis/SOURCE.json` will record:

- source repository,
- source submodule path,
- source ref or tag if known,
- exact source commit,
- synchronized file list,
- sync timestamp.

Example structure:

```json
{
  "source_repo": "nvaccess/nvda",
  "source_path": "include/nvda",
  "source_ref": "2025.2.0",
  "source_commit": "abc123...",
  "files": [
    "nvdaHelper/liblouis/sconscript",
    "nvdaHelper/liblouis/config.h",
    "nvdaHelper/liblouis/strings.h",
    "source/louisHelper.py",
    "source/louis.py"
  ]
}
```

## Build System Design

### Build system choice

DotExpress will use SCons for `liblouis` build orchestration. This is not just a wrapper change from `.bat` to SCons invocation; it is a deliberate alignment with NVDA's build contract.

### Why SCons

The NVDA `liblouis` integration expects:

- `clang-cl`,
- `m4`,
- Windows/MSVC link environment,
- specific CPP defines,
- specific include shims,
- specific table handling.

Trying to re-encode that behavior into a separate custom `nmake` path would preserve the same maintenance divergence that caused the current issue. Using SCons allows DotExpress to keep the NVDA build logic substantially intact.

### DotExpress root SCons environment

DotExpress will add a repository-level `sconstruct` that defines a minimal environment only for the `liblouis` build.

The first version will provide only the variables required by the synchronized NVDA `sconscript`, including:

- `TARGET_ARCH = x86_64`
- `sourceDir`
- `thirdPartyEnv`
- `certFile = ""`
- `apiSigningToken = ""`
- `signExec = no-op or unset-compatible placeholder`
- `nvdaHelperDebugFlags = []`

The root `sconstruct` is intentionally not a copy of NVDA's full root build script. It exists only to satisfy the synchronized `liblouis` integration layer.

### Build entrypoint

DotExpress will keep a thin `scripts/build-liblouis.bat` entrypoint, but its role changes:

1. Load Visual Studio 2022 build environment via `vcvarsall.bat x64`
2. Invoke `scons`

The batch script is only a Windows shell bootstrap. The actual build definition resides in SCons.

### Compiler and tools

The aligned build requires:

- Visual Studio 2022 C++ tools
- Clang tools for Windows
- Python
- SCons
- `m4.exe`

Purpose of these dependencies:

- Visual Studio 2022 C++ tools provide:
  - Windows SDK headers,
  - linker,
  - runtime libraries,
  - `vcvarsall.bat`
- Clang tools for Windows provide:
  - `clang-cl`
- SCons provides:
  - the orchestration model used by NVDA
- `m4.exe` provides:
  - expansion for `.in` translation table files

For the aligned NVDA-style build, Visual Studio and Clang are both required.

### `m4` handling

The first version should not import all of NVDA's `miscDeps` structure. Instead, DotExpress should provide `m4.exe` through either:

- a repository-local known path, or
- an explicit environment variable such as `M4_EXE`.

The SCons environment should map that tool into the synchronized NVDA `sconscript` contract without expanding the dependency surface unnecessarily.

## Runtime Output Contract

After build and sync:

- native output will be copied to:
  - `client/braille/liblouis.dll`
  - `client/braille/liblouis/tables/*`
- synchronized Python wrapper output will be copied to:
  - `client/braille/louis_helper.py`
  - `client/braille/liblouis/__init__.py`

This preserves the existing DotExpress runtime import locations while ensuring they are refreshed from a pinned NVDA source.

This is preferred over direct runtime imports from `vendor/nvda/liblouis/`, because:

- product code stays independent from vendor layout,
- runtime paths remain stable,
- vendor content remains clearly distinguished from runtime outputs.

## Build Flow

The first-version build flow is:

1. Ensure submodules are initialized:
   - `include/liblouis`
   - `include/nvda`

2. Synchronize NVDA integration into vendor:
   - run `scripts/sync_nvda_liblouis.py`

3. Build `liblouis`:
   - run `scripts/build-liblouis.bat`
   - which enters Visual Studio x64 environment and invokes SCons

4. SCons compiles from:
   - upstream source in `include/liblouis`
   - NVDA integration in `vendor/nvda/liblouis/build`

5. Post-build copy refreshes runtime outputs in `client/braille/`

## Manual Upgrade Flow

Because NVDA synchronization is intentionally pinned and manual, the upgrade flow is:

1. Update `include/nvda` submodule to the target commit/tag.
2. Run `scripts/sync_nvda_liblouis.py`.
3. Review changes under `vendor/nvda/liblouis/`.
4. Run `scripts/build-liblouis.bat`.
5. Run verification commands and manual checks.
6. Commit the submodule pointer update, vendor sync changes, and any related documentation/test changes.

This preserves auditability and prevents accidental product changes from a silent upstream move.

## Verification Strategy

Verification must cover both build correctness and runtime integration correctness.

### Build verification

- SCons build completes successfully.
- `client/braille/liblouis.dll` is regenerated.
- `client/braille/liblouis/tables/` is refreshed.

### Sync verification

- `client/braille/louis_helper.py` is refreshed from synchronized NVDA wrapper source.
- `client/braille/liblouis/__init__.py` is refreshed from synchronized NVDA ctypes binding source.
- `vendor/nvda/liblouis/SOURCE.json` reflects the pinned NVDA commit.

### Functional verification

At minimum:

- Chinese default table translation works.
- English UEB grade 1 translation works.
- English UEB grade 2 translation works.

### Automated verification

Run at least the existing braille/liblouis-relevant tests, plus any targeted tests added during implementation. Exact commands belong in the implementation plan, but the intended scope is:

- configuration tests affected by braille runtime selection,
- direct `liblouis` helper tests,
- any table resolution tests,
- any regression tests needed for the new sync/build flow.

## Error Handling and Failure Modes

Expected hard failures should be explicit and early:

- missing `include/liblouis` submodule,
- missing `include/nvda` submodule,
- missing synchronized white-list source file,
- missing `clang-cl`,
- missing Visual Studio build environment,
- missing `m4.exe`,
- failed SCons build,
- failed runtime artifact copy.

The build and sync scripts should fail fast with clear, specific diagnostics rather than continuing with partial outputs.

## Constraints and Tradeoffs

### Why not build directly from `include/nvda`

Directly consuming `include/nvda` during product build would blur the boundary between:

- a pinned third-party reference source,
- DotExpress's frozen integration source,
- product runtime outputs.

Keeping `vendor/nvda/liblouis/` as the formal build input preserves a reviewable and controllable handoff.

### Why not keep the current `nmake` path

The current path is already a divergence point. Continuing to encode NVDA behavior indirectly into a separate `nmake` flow would preserve the same maintenance risk. The point of this change is to align with NVDA's chosen `liblouis` integration mechanism.

### Why not synchronize only the native build files

Synchronizing only native build files leaves a high risk of ctypes/API drift between:

- the compiled DLL behavior,
- the Python wrapper behavior,
- DotExpress's runtime use.

The native build integration and Python wrapper integration must move together.

## Implementation Boundaries

The implementation should be kept narrow:

- Introduce SCons only for `liblouis` build alignment.
- Keep runtime import paths stable.
- Avoid broad code cleanup unrelated to the integration boundary.
- Add only the minimum DotExpress glue needed to host NVDA's synchronized `liblouis` build logic.

## Success Criteria

This design is successful when all of the following are true:

- DotExpress `liblouis` build runs through SCons, not the current custom `nmake` path.
- The synchronized NVDA `liblouis` build integration files live under `vendor/nvda/liblouis/`.
- `include/nvda` is the pinned, local synchronization source.
- Python wrapper files are synchronized alongside native build files.
- Runtime outputs remain under `client/braille/`.
- The x64 Windows build completes using Visual Studio 2022 C++ tools plus Clang tools for Windows.
- Basic braille translation scenarios and relevant tests pass after the migration.
