# DotExpress

DotExpress is a text-to-braille translation tool that converts plain text into fixed-width braille, producing output that can be used directly for printed braille.

DotExpress is designed for braille transcribers and educators who require precise control over printed braille output.

---

## Why DotExpress?

DotExpress was created to address long-standing limitations in traditional braille transcription tools, especially when handling mixed-language content such as Chinese, English, and technical symbols. It aims to provide a modern, accessible workflow for braille transcribers working in real-world educational and professional environments.

---

## Features

### Multilingual Text Translation

DotExpress provides independent braille table settings for Chinese, English, and Japanese. Users can select appropriate braille tables for different languages and regions, ensuring translation results better match practical usage.

For example, Taiwan Bopomofo Braille can be used for Chinese, while UEB Grade 1 Braille can be applied to English.

---

### Fixed Line Width Settings

DotExpress translates plain text into braille with a fixed number of braille cells per line, supporting printed braille production.

Users can configure how many braille cells each line contains. Output is formatted according to the specified line width to accommodate different paper sizes and printing requirements.

---

### Custom Dictionary

To address translation issues caused by proper nouns, rare vocabulary, or specialized terms not included in standard translation tables, DotExpress provides a Custom Dictionary feature.

This allows users to adjust translation results in real time while maintaining flexible translation behavior.

Users can define custom mapping rules between source text and target braille to fine-tune translation output.

When the target braille encoding type is set to "General" or "Unicode Braille", the "@" symbol can be inserted between characters as a separator. This allows the system to handle line wrapping at the character level, preventing the entire braille sequence from being treated as a single unit. For the "Bopomofo" type, the "@" symbol is not required, as the system will automatically perform line wrapping based on Bopomofo rules.

---

## Editing Dictionaries

1. Click the **Dictionary** button to open the dictionary editor.
2. Click **Add** to create a new translation mapping rule.
3. Select the desired dictionary mode, then enter values for the **Source Text** and corresponding **Braille** fields.

---

## Dictionary Modes

The Custom Dictionary supports the following three modes:

---

### General

In this mode, the content of the **Braille** field replaces the **Source Text** field directly, with no validation applied.

This is suitable for simple text-to-braille replacement scenarios.

---

### Bopomofo (Zhuyin)

In this mode, the content of the **Braille** field replaces the **Source Text** field and is interpreted according to Bopomofo symbol rules.

Only valid Bopomofo symbols and tone marks are permitted. Basic validation is performed to prevent invalid Bopomofo sequences.

This mode is intended for workflows that use Taiwanese Bopomofo Braille as the translation source.

* A space represents the first tone (Tone 1).
* Input must follow valid Bopomofo symbol sequence rules.

For the special standalone symbols
`ㄓ, ㄔ, ㄕ, ㄖ, ㄗ, ㄘ, ㄙ`,
when used without a final, the system automatically appends the corresponding `⠱` Braille code according to Bopomofo Braille rules.

---

### Braille (Unicode)

In this mode, the **Braille** field is treated as pure braille input.

Only characters within the Unicode Braille block (`0x2800`–`0x28FF`) are allowed.

This mode is suitable for users who are familiar with braille and require full control over the final output.

---

Through multilingual translation, fixed line width configuration, and a customizable dictionary system, DotExpress provides a flexible yet precise text-to-braille workflow, helping users complete printed braille transcription and pre-print preparation more efficiently.

---

## Build & Development

This project is developed using Python 3.13 (64-bit).

To build the executable or generate translation files locally, ensure your Python version meets this requirement, then install the dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
git submodule update --init --recursive
```

---

### Build Executable

Run the following command in Windows CMD to generate the executable using PyInstaller:

```bat
scripts\build_dotexpress.bat
```

### liblouis Version Policy

DotExpress uses liblouis from one tracked source plus generated runtime assets:

- `include/liblouis/`: upstream liblouis source submodule
- `client/braille/liblouis.dll`: generated runtime DLL
- `client/braille/liblouis/tables/`: generated runtime table set

The source of truth is the `include/liblouis` submodule. The DLL and tables under `client/braille/` are generated from that source and are not version-controlled.

Use a released liblouis tag for this submodule. Do not point DotExpress at `master` or other development snapshots unless you are explicitly working on liblouis compatibility fixes.

Rules:

1. Do not manually edit or version-control `client/braille/liblouis.dll`.
2. Do not manually edit or version-control `client/braille/liblouis/tables/`.
3. Do not update `client/braille/liblouis/tables/` by copying individual table files from another liblouis release.
4. When upgrading liblouis, update the `include/liblouis` submodule to a released tag first, then rerun `scripts\build-liblouis.bat` to regenerate both the DLL and tables from the same upstream revision.
5. `scripts\build_dotexpress.bat` depends on `scripts\build-liblouis.bat` and will call it first.
6. Do not keep alternate runtime table directories such as `tables(error)` in the shipping tree. They make it easy to mix incompatible table syntax with the generated DLL.

Recommended upgrade workflow:

1. Update `include/liblouis` to the target upstream release tag.
2. Run `scripts\\build-liblouis.bat` to rebuild the DLL and refresh the runtime tables from the same source checkout. The script expects the tracked `build/liblouis-static.nmake` file to be present.
4. Verify the runtime bundle as a matched set by testing at least:
   - Chinese default table translation
   - English UEB grade 1 translation
   - English UEB grade 2 translation
   - Mixed-language text that switches between Chinese and English
5. Commit the submodule update together with any script or documentation changes. Do not commit the generated DLL or tables.

If English grade 1 works but grade 2 fails after a liblouis upgrade, assume the local runtime artifacts were generated from the wrong source revision or are stale until proven otherwise.

The current recommended stable target is `v3.31.0`.

Why `v3.31.0`:

- `v3.31.0` and earlier are the last confirmed releases in this repo's workflow that stay close to the upstream Windows `nmake` path without extra compatibility shims.
- `v3.32.0` through `v3.35.0` introduce a Windows build compatibility gap around `strings.h`.
- Current development snapshots beyond those releases introduce additional Windows build compatibility issues, including newer C constructs in the Windows `nmake` path.

If you choose a version newer than `v3.31.0`, expect extra Windows compatibility work before `scripts\build-liblouis.bat` will succeed.

To move the liblouis submodule to a new upstream version:

```bash
cd include/liblouis
git fetch --tags origin
git checkout <tag-or-commit>
cd ../..
git add include/liblouis
```

Example:

```bash
cd include/liblouis
git fetch --tags origin
git checkout v3.31.0
cd ../..
git add include/liblouis
```

The submodule URL is stored in `.gitmodules`. The exact liblouis version used by DotExpress is recorded by the main repository's tracked submodule pointer at `include/liblouis`.

---

### Generate Translation Template

To update the translation template file (`.pot`), run:

```bat
scripts\generate_pot.bat
```

---

## License

This project is licensed under the GNU General Public License v2.0 (GPL-2.0).
