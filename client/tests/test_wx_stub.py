import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path

from tests import wx_stub

_FAKE_WX = "_wxstub_fake_wx"
_PREFIX = "_wxstub_"


class _TempModulesMixin:
    """Writes throwaway modules named ``_wxstub_*`` and removes every trace afterwards."""

    def setUp(self) -> None:
        super().setUp()
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        sys.path.insert(0, temp_dir.name)
        self.addCleanup(sys.path.remove, temp_dir.name)
        self.addCleanup(self._forget_temp_modules)

    @staticmethod
    def _forget_temp_modules() -> None:
        for name in [name for name in sys.modules if name.startswith(_PREFIX)]:
            del sys.modules[name]

    def write_module(self, relative_path: str, source: str) -> None:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        importlib.invalidate_caches()

    def write_consumer_package(self) -> None:
        self.write_module("_wxstub_pkg/__init__.py", "")
        self.write_module("_wxstub_pkg/consumer.py", f"import {_FAKE_WX} as wx\n")


class WidgetBaseTest(unittest.TestCase):
    def test_widget_masks_missing_attributes_and_ignores_bind(self) -> None:
        parent = object()
        widget = wx_stub.Widget(parent, label="Label", size=(1, 2))

        self.assertIs(widget.parent, parent)
        self.assertEqual(widget.label, "Label")
        self.assertEqual(widget.size, (1, 2))
        self.assertTrue(callable(widget.title))
        self.assertIsNone(widget.AnyMissingMethod(1, key=2))
        self.assertIsNone(widget.Bind("event", "handler"))
        self.assertFalse(hasattr(wx_stub.Widget, "bound_events"))

    def test_recording_widget_records_events_focus_and_visibility(self) -> None:
        widget = wx_stub.RecordingWidget(None, title="Title")

        widget.Bind("event", "handler")
        widget.Hide()
        widget.SetFocus()

        self.assertEqual(widget.title, "Title")
        self.assertEqual(widget.bound_events, {"event": "handler"})
        self.assertFalse(widget.visible)
        self.assertTrue(widget.HasFocus())
        self.assertIsNone(widget.AnyMissingMethod())


class AutoModuleTest(unittest.TestCase):
    def test_auto_class_module_caches_one_new_class_per_name(self) -> None:
        module = wx_stub.AutoClassModule(_FAKE_WX)

        first = module.Anything

        self.assertIsInstance(first, type)
        self.assertIs(module.Anything, first)
        with self.assertRaises(AttributeError):
            module.__missing_dunder__

    def test_auto_submodule_module_registers_submodules_and_absorbs_or(self) -> None:
        self.addCleanup(sys.modules.pop, f"{_FAKE_WX}.Flag", None)
        module = wx_stub.AutoSubmoduleModule(_FAKE_WX)

        flag = module.Flag

        self.assertIs(sys.modules[f"{_FAKE_WX}.Flag"], flag)
        self.assertIs(module.Flag, flag)
        self.assertIs(flag | 1, flag)
        self.assertIs(1 | flag, flag)


class StubScopeTest(_TempModulesMixin, unittest.TestCase):
    def test_loading_installs_stubs_then_leaves_no_trace(self) -> None:
        self.write_consumer_package()
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))

        with scope.loading():
            import _wxstub_pkg.consumer as consumer

        self.assertIs(consumer.wx, fake_wx)
        self.assertNotIn(_FAKE_WX, sys.modules)
        self.assertNotIn("_wxstub_pkg.consumer", sys.modules)
        self.assertIn("_wxstub_pkg", sys.modules)
        self.assertNotIn("consumer", vars(sys.modules["_wxstub_pkg"]))
        self.assertIs(scope.loaded["_wxstub_pkg.consumer"], consumer)
        self.assertIs(scope.loaded[_FAKE_WX], fake_wx)

    def test_loading_restores_previous_modules_and_parent_attribute(self) -> None:
        self.write_consumer_package()
        previous_wx = types.ModuleType(_FAKE_WX)
        sys.modules[_FAKE_WX] = previous_wx
        import _wxstub_pkg.consumer as previous_consumer
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))

        with scope.loading():
            import _wxstub_pkg.consumer as consumer

        self.assertIsNot(consumer, previous_consumer)
        self.assertIs(consumer.wx, fake_wx)
        self.assertIs(sys.modules[_FAKE_WX], previous_wx)
        self.assertIs(sys.modules["_wxstub_pkg.consumer"], previous_consumer)
        self.assertIs(sys.modules["_wxstub_pkg"].consumer, previous_consumer)

    def test_activate_reinstalls_loaded_modules_and_deactivate_restores(self) -> None:
        self.write_consumer_package()
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx}, isolate=("_wxstub_pkg.consumer",))
        with scope.loading():
            import _wxstub_pkg.consumer as consumer
        package = sys.modules["_wxstub_pkg"]

        scope.activate()
        try:
            self.assertIs(sys.modules[_FAKE_WX], fake_wx)
            self.assertIs(sys.modules["_wxstub_pkg.consumer"], consumer)
            self.assertIs(package.consumer, consumer)
            sys.modules[f"{_FAKE_WX}.CreatedAtRunTime"] = types.ModuleType("child")
        finally:
            scope.deactivate()

        self.assertNotIn(_FAKE_WX, sys.modules)
        self.assertNotIn(f"{_FAKE_WX}.CreatedAtRunTime", sys.modules)
        self.assertNotIn("_wxstub_pkg.consumer", sys.modules)
        self.assertNotIn("consumer", vars(package))

    def test_leak_guard_names_module_that_keeps_a_stub(self) -> None:
        self.write_module("_wxstub_leaky.py", f"import {_FAKE_WX} as wx\n")
        scope = wx_stub.StubScope({_FAKE_WX: types.ModuleType(_FAKE_WX)})

        with self.assertRaises(wx_stub.StubLeakError) as caught:
            with scope.loading():
                import _wxstub_leaky  # noqa: F401

        self.assertIn("_wxstub_leaky.wx", str(caught.exception))
        self.assertNotIn(_FAKE_WX, sys.modules)

    def test_eviction_policy_controls_other_new_modules(self) -> None:
        self.write_module("_wxstub_kept.py", "VALUE = 1\n")
        self.write_module("_wxstub_evicted.py", "VALUE = 2\n")

        with wx_stub.StubScope({}).loading():
            import _wxstub_kept  # noqa: F401
        with wx_stub.StubScope({}, evict=wx_stub.evict_everything).loading():
            import _wxstub_evicted  # noqa: F401

        self.assertIn("_wxstub_kept", sys.modules)
        self.assertNotIn("_wxstub_evicted", sys.modules)

    def test_eviction_removes_parent_attribute_of_evicted_submodule(self) -> None:
        self.write_module("_wxstub_pkg/__init__.py", "")
        self.write_module("_wxstub_pkg/child.py", "VALUE = 4\n")
        import _wxstub_pkg

        with wx_stub.StubScope({}, evict=wx_stub.evict_everything).loading():
            import _wxstub_pkg.child as evicted_child

        self.assertIn("_wxstub_pkg", sys.modules)
        self.assertNotIn("_wxstub_pkg.child", sys.modules)
        self.assertNotIn("child", vars(_wxstub_pkg))
        from _wxstub_pkg import child as fresh_child
        self.assertIsNot(fresh_child, evicted_child)
        self.assertIs(fresh_child, sys.modules["_wxstub_pkg.child"])

    def test_eviction_keeps_parent_attribute_that_is_not_the_evicted_module(self) -> None:
        self.write_module("_wxstub_pkg/__init__.py", "")
        self.write_module("_wxstub_pkg/child.py", "VALUE = 5\n")
        import _wxstub_pkg

        with wx_stub.StubScope({}, evict=wx_stub.evict_everything).loading():
            import _wxstub_pkg.child  # noqa: F401
            replacement = types.ModuleType("replacement")
            _wxstub_pkg.child = replacement

        self.assertNotIn("_wxstub_pkg.child", sys.modules)
        self.assertIs(vars(_wxstub_pkg)["child"], replacement)

    def test_scope_keeps_attributes_wiring_stub_modules_together(self) -> None:
        fake_wx = types.ModuleType(_FAKE_WX)
        fake_html2 = types.ModuleType(f"{_FAKE_WX}.html2")
        fake_wx.html2 = fake_html2
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx, f"{_FAKE_WX}.html2": fake_html2})

        with scope.loading():
            pass
        self.assertIs(fake_wx.html2, fake_html2)

        scope.activate()
        scope.deactivate()
        self.assertIs(fake_wx.html2, fake_html2)

    def test_deactivate_removes_parent_attribute_of_dropped_stub_child(self) -> None:
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx})
        with scope.loading():
            pass

        scope.activate()
        try:
            child = types.ModuleType(f"{_FAKE_WX}.CreatedAtRunTime")
            sys.modules[f"{_FAKE_WX}.CreatedAtRunTime"] = child
            fake_wx.CreatedAtRunTime = child
        finally:
            scope.deactivate()

        self.assertNotIn(f"{_FAKE_WX}.CreatedAtRunTime", sys.modules)
        self.assertNotIn("CreatedAtRunTime", vars(fake_wx))

    def test_load_file_runs_a_private_module_and_removes_it(self) -> None:
        self.write_module("_wxstub_source.py", f"import {_FAKE_WX} as wx\nVALUE = 3\n")
        fake_wx = types.ModuleType(_FAKE_WX)
        scope = wx_stub.StubScope({_FAKE_WX: fake_wx})

        with scope.loading():
            module = scope.load_file("_wxstub_private", self.root / "_wxstub_source.py")

        self.assertEqual(module.VALUE, 3)
        self.assertIs(module.wx, fake_wx)
        self.assertNotIn("_wxstub_private", sys.modules)
        self.assertNotIn("_wxstub_private", scope.loaded)


class StubFactoryTest(unittest.TestCase):
    def assert_fresh(self, factory, names: list[str]) -> dict:
        first = factory()
        second = factory()

        self.assertEqual(sorted(first), sorted(names))
        for name in names:
            self.assertIsInstance(first[name], types.ModuleType)
            self.assertIsNot(first[name], second[name])
        self.assertIsNot(first["wx"].Window, second["wx"].Window)
        return first

    def test_dialog_validation_stubs_are_fresh_plain_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.dialog_validation_stubs, ["wx"])["wx"]

        self.assertIs(type(wx), types.ModuleType)
        self.assertEqual(
            sorted(name for name in vars(wx) if not name.startswith("__")),
            ["CommandEvent", "Dialog", "ListCtrl", "Window"],
        )
        self.assertFalse(hasattr(wx, "OK"))

    def test_dual_view_stubs_are_fresh_with_recording_frame(self) -> None:
        stubs = self.assert_fresh(wx_stub.dual_view_stubs, ["wx", "wx.html2"])
        wx = stubs["wx"]
        calls = []

        frame = wx.Frame("parent", size=(1, 2))
        wx.CallAfter(lambda: calls.append("called"))

        self.assertEqual(frame.init_args, ("parent",))
        self.assertEqual(frame.init_kwargs, {"size": (1, 2)})
        self.assertEqual(calls, ["called"])
        self.assertFalse(hasattr(wx.Window, "FindFocus"))
        self.assertIs(wx.html2, stubs["wx.html2"])
        self.assertEqual((wx.VERTICAL, wx.EXPAND), (1, 2))
        self.assertIsNot(wx.AnyName, wx.AnyName)

    def test_gui_frame_stubs_are_fresh_with_ignoring_widgets(self) -> None:
        stubs = self.assert_fresh(
            wx_stub.gui_frame_stubs,
            ["braille.louis_helper", "dialog", "wx", "wx.html2", "wx.lib", "wx.lib.scrolledpanel"],
        )
        wx = stubs["wx"]

        self.assertTrue(issubclass(wx.Window, wx_stub.Widget))
        self.assertFalse(issubclass(wx.Window, wx_stub.RecordingWidget))
        self.assertEqual((wx.ID_OK, wx.OK, wx.VERTICAL), (2, 4, 4096))
        self.assertEqual(wx.MessageBox("text"), wx.OK)
        self.assertIs(wx.lib, stubs["wx.lib"])
        self.assertIs(stubs["wx.lib.scrolledpanel"].ScrolledPanel, wx.lib.ScrolledPanel)
        self.assertIsNot(wx.EVT_CLOSE, wx.EVT_CLOSE)
        self.assertEqual(stubs["dialog"].DictionaryNameDialog().ShowModal(), 0)
        self.assertIsNone(stubs["braille.louis_helper"].initialize())

    def test_settings_dialog_stubs_are_fresh_with_recording_widgets(self) -> None:
        names = ["braille", "braille.tables", "wx", "wx.lib", "wx.lib.scrolledpanel"]
        stubs = self.assert_fresh(wx_stub.settings_dialog_stubs, names)
        other = wx_stub.settings_dialog_stubs()
        wx = stubs["wx"]

        self.assertTrue(issubclass(wx.Window, wx_stub.RecordingWidget))
        self.assertEqual((wx.ID_OK, wx.OK, wx.VERTICAL), (5100, 4, 1))
        self.assertIsNot(wx.MessageBox, other["wx"].MessageBox)
        self.assertIs(wx.lib.scrolledpanel, stubs["wx.lib.scrolledpanel"])
        self.assertFalse(hasattr(stubs["braille"], "__path__"))
        self.assertEqual(stubs["braille.tables"].listTables(), [])

    def test_speech_dialog_stubs_are_fresh_submodule_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.speech_dialog_stubs, ["wx"])["wx"]

        self.assertIsInstance(wx, wx_stub.AutoSubmoduleModule)
        self.assertEqual((wx.NOT_FOUND, wx.OK, wx.ICON_ERROR), (-1, 1, 2))
        self.assertIsNone(wx.MessageBox("text"))

    def test_dialog_display_stubs_are_fresh_class_caching_modules(self) -> None:
        wx = self.assert_fresh(wx_stub.dialog_display_stubs, ["wx"])["wx"]

        self.assertIsInstance(wx, wx_stub.AutoClassModule)
        self.assertEqual((wx.ID_OK, wx.ID_CLOSE, wx.OK, wx.CLOSE), (1, 4, 4, 32))
        self.assertIs(wx.AnyName, wx.AnyName)


if __name__ == "__main__":
    unittest.main()
