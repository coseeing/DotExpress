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
git submodule update --init include/liblouis
git submodule update --init include/nvda
```

This initializes the top-level `include/liblouis` and `include/nvda` submodules without recursively fetching nested submodules declared inside NVDA. Use `git submodule update --init --recursive` only when you explicitly need nested submodules as well.

---

### Build Executable

Run the following command in Windows CMD to generate the executable using PyInstaller:

```bat
scripts\build-dotexpress.bat
```

### Building liblouis on Windows

DotExpress builds liblouis from two tracked source checkouts:

- `include/liblouis/`: upstream liblouis source submodule
- `include/nvda/`: pinned NVDA source submodule used for the liblouis integration layer
- `vendor/nvda/liblouis/`: synced NVDA-derived vendor snapshot
- `vendor/nvda/mathcat/`: synced NVDA MathCAT assets snapshot

The generated runtime outputs are:

- `client/braille/liblouis.dll`
- `client/braille/liblouis/tables/`
- `client/braille/louis_helper.py`
- `client/braille/liblouis/__init__.py`
- `client/mathcat/assets/`

The source of truth is the pair of submodule pointers, with `vendor/nvda/liblouis/` and `vendor/nvda/mathcat/` acting as frozen sync snapshots from `include/nvda/`. The runtime DLLs, helper, wrapper, and tables are generated from those sources and should not be hand-edited.

### Prerequisites

- Visual Studio 2022 C++ tools
- Clang tools for Windows
- Python 3 with SCons (`py -m pip install scons`)
- GNU `m4.exe` and `regex2.dll` in `miscDeps/tools/`

### Initial checkout and build

```bat
git submodule update --init include/liblouis
git submodule update --init include/nvda
py scripts\sync-nvda.py
scripts\clean-liblouis.bat
scripts\build-liblouis.bat
scripts\install.bat
```

### Manual NVDA upgrade

1. Check out the approved commit in `include/nvda`.
2. Set `include/liblouis` to the gitlink printed by `git -C include/nvda rev-parse HEAD:include/liblouis`.
3. Run `py scripts\sync-nvda.py`.
4. Review `vendor/nvda/liblouis/`, `vendor/nvda/mathcat/`, `SOURCE.json`, and the regenerated runtime files.
5. Clean-build and run the liblouis runtime tests.
6. Commit both submodule pointers, synchronized vendor files, and generated runtime files together.

---

### Generate Translation Template

To update the translation template file (`.pot`), run:

```bat
scripts\generate_pot.bat
```

---

## License

This project is licensed under the GNU General Public License v2.0 (GPL-2.0).
