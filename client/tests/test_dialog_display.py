import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


class _AutoModule(types.ModuleType):
	def __getattr__(self, name):
		if name.startswith("__") and name.endswith("__"):
			raise AttributeError(name)
		value = type(name, (), {})
		setattr(self, name, value)
		return value


def _load_dialog_module():
	dialog_path = Path(__file__).resolve().parents[1] / "dialog.py"
	previous = dict(sys.modules)
	try:
		wx = _AutoModule("wx")
		wx.Dialog = type("Dialog", (), {})
		wx.ListCtrl = type("ListCtrl", (), {})
		wx.Window = type("Window", (), {})
		wx.NOT_FOUND = -1
		sys.modules["wx"] = wx
		for name in (
			"braille",
			"braille.tables",
			"Bopomofo",
			"dictionaries",
			"dictionaries.actions",
			"dictionaries.manager",
			"documents",
			"documents.workspace",
			"translation",
			"settings",
			"settings.translation",
		):
			sys.modules.setdefault(name, _AutoModule(name))
		spec = importlib.util.spec_from_file_location("_dialog_display_test", dialog_path)
		module = importlib.util.module_from_spec(spec)
		sys.modules[spec.name] = module
		spec.loader.exec_module(module)
		return module
	finally:
		for name in list(sys.modules):
			if name not in previous:
				del sys.modules[name]
		sys.modules.update(previous)


dialog_module = _load_dialog_module()


class FinalizeDialogLayoutTest(unittest.TestCase):
	def test_fits_and_centers_on_parent(self):
		owner = object()
		dialog = Mock()
		dialog.GetParent.return_value = owner
		sizer = object()

		dialog_module.finalize_dialog_layout(dialog, sizer)

		dialog.SetSizerAndFit.assert_called_once_with(sizer)
		dialog.CentreOnParent.assert_called_once_with()
		dialog.Centre.assert_not_called()

	def test_fits_and_centers_on_screen_without_parent(self):
		dialog = Mock()
		dialog.GetParent.return_value = None
		sizer = object()

		dialog_module.finalize_dialog_layout(dialog, sizer)

		dialog.SetSizerAndFit.assert_called_once_with(sizer)
		dialog.Centre.assert_called_once_with()
		dialog.CentreOnParent.assert_not_called()


if __name__ == "__main__":
	unittest.main()
