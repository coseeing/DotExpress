"""Build, bind and enable the document menu from its descriptors.

This module does not import wx. The caller passes the wx pieces in
(``new_menu=wx.Menu``, ``menu_event=wx.EVT_MENU``, ``item_id=wx.ID_ANY``),
so tests can use recording fakes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from ui.action_menu import DocumentMenuItem, get_document_menu_descriptors


def build_document_menu(
    menu,
    handlers: Mapping[str, Callable[..., None]],
    *,
    translate: Callable[[str], str],
    new_menu: Callable[[], object],
    menu_event: object,
    item_id: int,
    descriptors: Sequence[DocumentMenuItem] | None = None,
) -> dict[str, object]:
    """Append every descriptor to ``menu``, then bind every item on ``menu``.

    Commands call ``handlers[action](event)``. Submenu format items call
    ``handlers[action](format_key)`` with the casefolded format key. Returns the
    top-level items (commands and submenus) keyed by action.
    """
    items = tuple(get_document_menu_descriptors() if descriptors is None else descriptors)
    actions = [item.action for item in items]
    missing = [action for action in actions if action not in handlers]
    extra = sorted(set(handlers) - set(actions))
    if missing or extra:
        raise ValueError(f"Document menu handlers do not match the menu actions: missing {missing}, extra {extra}.")

    top_items: dict[str, object] = {}
    format_items: dict[str, list[tuple[str, object]]] = {}
    for item in items:
        if item.kind == "command":
            top_items[item.action] = menu.Append(item_id, translate(item.label))
            continue
        submenu = new_menu()
        top_items[item.action] = menu.AppendSubMenu(submenu, translate(item.label))
        format_items[item.action] = [
            (format_key.casefold(), submenu.Append(item_id, translate(format_label)))
            for format_key, format_label in item.formats
        ]

    for item in items:
        handler = handlers[item.action]
        if item.kind == "command":
            menu.Bind(menu_event, handler, top_items[item.action])
            continue
        for format_key, format_item in format_items[item.action]:
            menu.Bind(menu_event, lambda _event, key=format_key, handler=handler: handler(key), format_item)
    return top_items


def apply_document_menu_state(
    items_by_action: Mapping[str, object],
    enabled_by_action: Mapping[str, bool],
) -> None:
    """Enable or disable each item, in the order of ``enabled_by_action``."""
    for action, enabled in enabled_by_action.items():
        items_by_action[action].Enable(enabled)
