# Shortcut Reference

The table below summarizes the current DotExpress shortcuts and common interactions related to the editor areas and the document list.

| Area | Action | Shortcut / Mouse | Description |
| --- | --- | --- | --- |
| `Source Text Editor` | Convert | `Ctrl+Enter` | Runs conversion. This is equivalent to clicking the `Convert` button. |
| `Source Text Editor` / `Braille Result Editor` | Increase font size | `Ctrl + Mouse Wheel Up` | Increases the editor font size. |
| `Source Text Editor` / `Braille Result Editor` | Decrease font size | `Ctrl + Mouse Wheel Down` | Decreases the editor font size. |
| `Braille Result Editor` | Export `.brl` | `Ctrl+S` | Exports the braille content of the currently open document as a `.brl` file. |
| Document List | Open document | `Enter` | Opens the currently selected document and loads its content into the editor area on the right. This is equivalent to `Open` in the context menu. |
| Document List | Rename | `F2` | Renames the currently selected document. This is equivalent to `Rename` in the context menu. |
| Document List | Delete document | `Delete` | Deletes the currently selected document. A confirmation prompt is shown first. |
| Document List | Open context menu | Right mouse button | Opens the action menu for the document list. |
| Main window sections | Move to the next section | `F6` | Cycles focus through `Conversion`, `Document List`, `View`, `Source Text`, and `Braille Result`. |
| Main window sections | Move to the previous section | `Shift+F6` | Cycles focus backward through the same five sections. |

## Document List Context Menu

| Item | Description |
| --- | --- |
| `Open` | Opens the currently selected document. |
| `Delete` | Deletes the currently selected document after a confirmation prompt. |
| `Delete All` | Deletes all documents. After confirmation, the current workspace documents are cleared and the application immediately requires creation of a new first document. |
| `Add` | Creates a new document. |
| `Rename` | Renames the currently selected document. |
| `Import` | Imports one or more documents. Use the submenu to choose `DEP` or `TXT`. |
| `Export` | Exports a single document. |
| `Export All` | Exports all documents. |

## Notes

* Font size synchronization | When font size is adjusted with `Ctrl + Mouse Wheel`, the `Source Text Editor`, `Braille Result Editor`, and `View > Font Size` remain synchronized.
* Default wheel behavior | When `Ctrl` is not held, the mouse wheel keeps its normal scrolling behavior.
* Section navigation | `F6 / Shift+F6` always moves focus to the first focusable control in each section. For example, `Conversion` lands on `Translation Tables...`, and `View` lands on `Font Size`.
