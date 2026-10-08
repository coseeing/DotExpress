"""Recording fakes for document-menu tests (no wx).

``MenuRecorder.new_menu`` creates menus named ``menu0``, ``menu1``, ... in
creation order. Every wx-style call lands in one shared ``log`` list:

* ``("new", "menu0")``
* ``("menu0", "Append", item_id, label)``
* ``("menu0", "AppendSubMenu", "menu1", label)``
* ``("menu0", "Bind", event, "menu1:<label>")``
* ``("Enable", "menu0:<label>", value)``
* ``("menu0", "Destroy")``

Items are named ``"<owning menu>:<label>"``. ``binds`` keeps
``(menu name, item name, handler)`` for every ``Bind`` so tests can call the
handlers.

``DOCUMENT_MENU_BUILD_LOG`` is today's File-menu build log (append pass, then
bind pass) with labels translated as ``T[...]``, ``wx.ID_ANY == -1`` and the
event recorded as the string ``"EVT_MENU"``.
"""

from __future__ import annotations


def fake_translate(value: str) -> str:
    return f"T[{value}]"


class RecordedItem:
    def __init__(self, log: list, name: str):
        self.log = log
        self.name = name

    def Enable(self, enabled: bool) -> None:
        self.log.append(("Enable", self.name, enabled))


class RecordedMenu:
    def __init__(self, recorder: "MenuRecorder", name: str):
        self.recorder = recorder
        self.name = name

    def Append(self, item_id, label):
        self.recorder.log.append((self.name, "Append", item_id, label))
        return RecordedItem(self.recorder.log, f"{self.name}:{label}")

    def AppendSubMenu(self, submenu, label):
        self.recorder.log.append((self.name, "AppendSubMenu", submenu.name, label))
        return RecordedItem(self.recorder.log, f"{self.name}:{label}")

    def Bind(self, event, handler, item):
        self.recorder.log.append((self.name, "Bind", event, item.name))
        self.recorder.binds.append((self.name, item.name, handler))

    def Destroy(self) -> None:
        self.recorder.log.append((self.name, "Destroy"))


class MenuRecorder:
    def __init__(self):
        self.log: list = []
        self.binds: list = []
        self.menus: list[RecordedMenu] = []

    def new_menu(self, *_args, **_kwargs) -> RecordedMenu:
        menu = RecordedMenu(self, f"menu{len(self.menus)}")
        self.menus.append(menu)
        self.log.append(("new", menu.name))
        return menu


DOCUMENT_MENU_BUILD_LOG = [
    ("new", "menu0"),
    ("menu0", "Append", -1, "T[Open]"),
    ("menu0", "Append", -1, "T[Delete]"),
    ("menu0", "Append", -1, "T[Delete All]"),
    ("menu0", "Append", -1, "T[Add]"),
    ("menu0", "Append", -1, "T[Rename]"),
    ("menu0", "Append", -1, "T[Import]"),
    ("new", "menu1"),
    ("menu0", "AppendSubMenu", "menu1", "T[Export]"),
    ("menu1", "Append", -1, "T[Package DEP]"),
    ("menu1", "Append", -1, "T[Braille BRL]"),
    ("menu1", "Append", -1, "T[Dual View HTML]"),
    ("new", "menu2"),
    ("menu0", "AppendSubMenu", "menu2", "T[Export All]"),
    ("menu2", "Append", -1, "T[Package DEP]"),
    ("menu2", "Append", -1, "T[Braille BRL]"),
    ("menu2", "Append", -1, "T[Dual View HTML]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Open]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Delete]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Delete All]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Add]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Rename]"),
    ("menu0", "Bind", "EVT_MENU", "menu0:T[Import]"),
    ("menu0", "Bind", "EVT_MENU", "menu1:T[Package DEP]"),
    ("menu0", "Bind", "EVT_MENU", "menu1:T[Braille BRL]"),
    ("menu0", "Bind", "EVT_MENU", "menu1:T[Dual View HTML]"),
    ("menu0", "Bind", "EVT_MENU", "menu2:T[Package DEP]"),
    ("menu0", "Bind", "EVT_MENU", "menu2:T[Braille BRL]"),
    ("menu0", "Bind", "EVT_MENU", "menu2:T[Dual View HTML]"),
]

# Top-level items of the default document menu, in Enable order.
DOCUMENT_MENU_TOP_ITEMS = (
    "menu0:T[Open]",
    "menu0:T[Delete]",
    "menu0:T[Delete All]",
    "menu0:T[Add]",
    "menu0:T[Rename]",
    "menu0:T[Import]",
    "menu0:T[Export]",
    "menu0:T[Export All]",
)


def enable_log(*values: bool, items=DOCUMENT_MENU_TOP_ITEMS) -> list:
    """The expected ``Enable`` entries for the top-level items, in order."""
    assert len(values) == len(items)
    return [("Enable", item, value) for item, value in zip(items, values)]
