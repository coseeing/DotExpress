# External Dual View and Unified Application Data Paths Design

## Goal

Change the “Dual View” command under the “Translation” menu from opening an embedded `wx.html2.WebView` to opening the HTML in an available system browser, while targeting a new window size equal to the main DotExpress window. The dual-view HTML will be written to `dual_view/` under the DotExpress application directory instead of the system temporary directory.

As part of the same change, unify the root-directory strategy for files managed by DotExpress so that configuration, dictionaries, the document workspace, logs, and dual-view HTML all reside under the application root.

## Scope

### Included

- Generate an HTML file from the “Dual View” command under the “Translation” menu and open it in an external browser.
- Try Chrome, Microsoft Edge, and Firefox in that order; only use `os.startfile()` to open the HTML file if none of them can be launched.
- Pass known browsers launch parameters for a separate window and the main window’s width and height.
- Preserve the existing `DualViewFrame`, `wx.html2.WebView`, `_show_dual_view()`, and related refresh code without calling it from this menu command.
- Establish a single application-root path source and use it for configuration, dictionaries, the workspace, logs, and dual-view HTML.
- Explicitly verify at startup that all application-managed directories are writable; display an error and stop startup if they are not.
- Keep user-visible startup and dual-view errors in the gettext catalogs and compiled Traditional Chinese catalog.

### Not Included

- Controlling the system default browser or forcibly resizing an external browser window through the Windows API.
- Moving files selected by the user through an export dialog into the application directory.
- Preserving, reading, or migrating the old `~/.DotExpress/config.json`.
- Deleting or refactoring the existing wx.html dual-view functionality.

## Application Data Locations

The application-root resolution rules are:

- Packaged build: `Path(sys.executable).resolve().parent`, the directory containing `DotExpress.exe`.
- Development mode: the `client/` directory.

All writable data managed by DotExpress uses this structure:

```text
<application-root>/
  config.json
  dictionary/
  workspace/
  log/
  dual_view/
```

Dictionary files and preprocessing scripts under `dictionary/`, DEP documents under `workspace/`, logs under `log/`, and temporary HTML under `dual_view/` are all resolved from this root. The previous log location relative to the current working directory is no longer used; in development mode, the workspace previously created under `client/documents/workspace/` is changed to `client/workspace/`.

The configuration file is fixed at `<application-root>/config.json`. The program no longer reads or migrates `~/.DotExpress/config.json`.

At startup, create the required directories and verify the application root and every managed subdirectory by creating and removing a probe file before initializing services that create files. If `config.json` already exists, also open that exact file for append without changing its content so a file-specific read-only permission is detected. File loggers must defer opening their files until after this validation; importing a module must not create `log/` or a log file. If the root, existing config file, or any required directory is not writable, display a localized error that identifies the failing path, stop startup before creating the translation runtime or main frame, and do not fall back to the user’s home directory or another hidden location.

## External Dual View Flow

When the user starts “Dual View”:

1. Continue using the existing `build_dual_view_model()` and `render_dual_view_html()` to produce the HTML string, including the existing empty-data message.
2. Create the content in `dual_view/` for the current run and write each opening to a unique UTF-8 `.html` file, preventing an existing tab from reading stale content or cached data.
3. Read the current pixel width and height of the main wx window.
4. Find and attempt to launch Chrome, Microsoft Edge, and Firefox in order. Discovery checks `PATH` and the browsers’ standard per-user and `Program Files` Windows installation locations. Try the next browser only when the executable cannot be found or process creation raises an `OSError`; an immediate browser-process exit is outside the launcher’s observable success criteria.
5. Launch Chrome and Edge with `--new-window` and `--window-size=<width>,<height>`. Launch Firefox with `-new-window`, `-width <width>`, and `-height <height>`. The requested width and height equal the current result of the main wx window’s `GetSize()`. Browsers may reuse an existing process or adjust the final dimensions because of browser policy, window chrome, or Windows DPI scaling, so exact external-window geometry is a target rather than a guarantee.
6. If all three specified browsers are unavailable or cannot be launched, call Windows `os.startfile()` as the final fallback. This follows the Windows HTML file association, may open a non-browser application, and cannot control the window size. Tests on non-Windows systems inject a fallback callable and never require `os.startfile` to exist.

Browser discovery, command-line construction, and fallback ordering are implemented in a wx-independent helper for unit testing. The GUI only supplies the HTML and main-window dimensions, calls the helper, and reports write or launch failures using the existing user-facing error style.

## Dual-View HTML Cleanup

- After startup path validation, remove files matching the DotExpress-owned `dual-view-*.html` naming pattern left over from the previous run in `dual_view/`.
- Remove files matching that same owned pattern when DotExpress exits normally.
- Files left behind by an abnormal exit are removed at the next startup.
- Cleanup is strictly limited to owned HTML files in `dual_view/` under the application root. It does not remove unrelated files and does not affect the workspace, dictionary, log, or user-selected export locations.

## Preserved Embedded Viewer

Keep the construction, HTML refresh, close, and focus-handling code for `DualViewFrame` and its `wx.html2.WebView` unchanged. Keep `_show_dual_view()` available as an entry point; only the “Dual View” menu event changes to call the external-browser flow. Existing viewer tests remain in place.

## Error Handling

- Root not writable: display an error during early GUI startup, stop the program, and do not use an alternative location.
- Previous-run dual-view cleanup fails at startup: report the failing `dual_view/` path with the same startup error and stop before constructing the runtime or main frame.
- Current-run dual-view cleanup fails during normal shutdown: log the failure and continue closing the translation runtime and application.
- Failure to generate or write dual-view HTML: log detailed error information, show an error using the existing style, and leave documents and translation data unchanged.
- Specified browser unavailable: continue in the fixed Chrome, Edge, Firefox order.
- `os.startfile()` also fails: log detailed error information and show an open-failure message.

## Verification

- Test application-root resolution in frozen and development modes.
- Test that configuration, dictionary, workspace, log, and dual-view paths all resolve under the common application root.
- Test required directory creation and initialization errors for an unwritable directory or existing read-only config file.
- Test that logger construction does not create a directory or open a file before startup validation and resolves its delayed file handler under `log/`.
- Test that dual-view HTML is written as UTF-8 with a unique filename under `dual_view/`.
- Test browser discovery, launch, and fallback order: Chrome → Edge → Firefox → `os.startfile()`.
- Test that each browser command line includes the file URI, new-window parameter, and main-window dimensions.
- Test that `dual_view/` cleanup only removes its own files at startup and normal shutdown.
- Test that the GUI menu event uses the external-browser flow and that existing `DualViewFrame` tests remain.
- Validate the gettext template, Traditional Chinese PO file, and regenerated MO file for the new user-visible errors.
