from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

import wx


@dataclass
class DictionaryEntry:
	text: str
	braille: str


class AddSymbolDialog(wx.Dialog):
	"""Simple dialog to capture original text for a new dictionary entry."""

	def __init__(self, parent: wx.Window | None):
		super().__init__(parent, title="新增字典條目")

		main_sizer = wx.BoxSizer(wx.VERTICAL)

		label = wx.StaticText(self, label="原始文字")
		main_sizer.Add(label, 0, wx.ALL, 8)

		self.identifier_ctrl = wx.TextCtrl(self)
		main_sizer.Add(self.identifier_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)

		self.SetSizerAndFit(main_sizer)
		self.identifier_ctrl.SetFocus()

	def get_identifier(self) -> str:
		return self.identifier_ctrl.GetValue().strip()

	def __enter__(self) -> "AddSymbolDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()


class SpeechSymbolsDialog(wx.Dialog):
	"""Dialog for editing custom dictionary mappings stored on disk."""

	def __init__(self, parent: wx.Window | None, dictionary_path: Path | None = None):
		super().__init__(parent, title="自訂字典管理", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.dictionary_path = Path(dictionary_path) if dictionary_path else (Path("data") / "dictionary.csv")
		self.entries: List[DictionaryEntry] = self._load_entries()
		self.selected_index: int | None = None

		self._build_ui()
		self._populate_list()
		self._set_selection(None)

	def __enter__(self) -> "SpeechSymbolsDialog":
		return self

	def __exit__(self, exc_type, exc, _tb) -> None:
		self.Destroy()

	def _build_ui(self) -> None:
		main_sizer = wx.BoxSizer(wx.VERTICAL)

		# List of existing entries
		self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
		self.list_ctrl.InsertColumn(0, "原始文字", width=200)
		self.list_ctrl.InsertColumn(1, "點字", width=250)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
		main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 8)

		# Buttons: add / remove
		button_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.add_button = wx.Button(self, label="新增")
		self.remove_button = wx.Button(self, label="刪除")
		self.remove_button.Disable()
		button_sizer.Add(self.add_button, 0, wx.RIGHT, 8)
		button_sizer.Add(self.remove_button, 0)
		main_sizer.Add(button_sizer, 0, wx.LEFT | wx.RIGHT, 8)

		self.add_button.Bind(wx.EVT_BUTTON, self._on_add_clicked)
		self.remove_button.Bind(wx.EVT_BUTTON, self._on_remove_clicked)

		# Editing area
		edit_box = wx.StaticBoxSizer(wx.VERTICAL, self, label="編輯選定條目")

		source_label = wx.StaticText(edit_box.GetStaticBox(), label="原始文字")
		self.source_text = wx.TextCtrl(edit_box.GetStaticBox(), style=wx.TE_READONLY)
		edit_box.Add(source_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		edit_box.Add(self.source_text, 0, wx.EXPAND | wx.ALL, 8)

		braille_label = wx.StaticText(edit_box.GetStaticBox(), label="自訂點字")
		self.braille_text = wx.TextCtrl(edit_box.GetStaticBox())
		self.braille_text.Bind(wx.EVT_TEXT, self._on_braille_changed)
		edit_box.Add(braille_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
		edit_box.Add(self.braille_text, 0, wx.EXPAND | wx.ALL, 8)

		main_sizer.Add(edit_box, 0, wx.EXPAND | wx.ALL, 8)

		# OK / Cancel buttons
		button_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
		if button_sizer:
			main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 8)
			ok_button = self.FindWindowById(wx.ID_OK)
			if ok_button:
				ok_button.Bind(wx.EVT_BUTTON, self._on_ok)

		self.SetSizer(main_sizer)
		self.SetMinSize((520, 420))
		self.Layout()

	def _load_entries(self) -> List[DictionaryEntry]:
		if not self.dictionary_path.exists():
			return []

		entries: List[DictionaryEntry] = []
		with self.dictionary_path.open("r", newline="", encoding="utf-8") as fp:
			reader = csv.DictReader(fp)
			for row in reader:
				text = (row.get("text") or "").strip()
				if not text:
					continue
				braille = (row.get("braille") or "").strip()
				entries.append(DictionaryEntry(text=text, braille=braille))
		return entries

	def _populate_list(self) -> None:
		self.list_ctrl.DeleteAllItems()
		for entry in self.entries:
			index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), entry.text)
			self.list_ctrl.SetItem(index, 1, entry.braille)

	def _set_selection(self, index: int | None) -> None:
		self.selected_index = index
		has_selection = index is not None
		self.remove_button.Enable(has_selection)
		self.braille_text.Enable(has_selection)

		if not has_selection:
			for item in range(self.list_ctrl.GetItemCount()):
				self.list_ctrl.SetItemState(item, 0, wx.LIST_STATE_SELECTED)
			self.source_text.SetValue("")
			self.braille_text.ChangeValue("")
			return

		self.list_ctrl.Select(index)
		self.list_ctrl.Focus(index)
		entry = self.entries[index]
		self.source_text.SetValue(entry.text)
		self.braille_text.ChangeValue(entry.braille)

	def _on_item_selected(self, event: wx.ListEvent) -> None:
		self._set_selection(event.GetIndex())
		event.Skip()

	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
		with AddSymbolDialog(self) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			identifier = dialog.get_identifier()
			if not identifier:
				wx.MessageBox("請輸入原始文字。", "提示", wx.OK | wx.ICON_INFORMATION, parent=self)
				return
			if any(entry.text == identifier for entry in self.entries):
				wx.MessageBox(f'原始文字 "{identifier}" 已存在。', "錯誤", wx.OK | wx.ICON_ERROR, parent=self)
				return

		self.entries.append(DictionaryEntry(text=identifier, braille=""))
		self._populate_list()
		self._set_selection(len(self.entries) - 1)

	def _on_remove_clicked(self, _event: wx.CommandEvent) -> None:
		if self.selected_index is None:
			return
		del self.entries[self.selected_index]
		self._populate_list()
		if self.entries:
			self._set_selection(min(self.selected_index, len(self.entries) - 1))
		else:
			self._set_selection(None)

	def _on_braille_changed(self, event: wx.CommandEvent) -> None:
		if self.selected_index is None:
			return
		value = self.braille_text.GetValue()
		entry = self.entries[self.selected_index]
		entry.braille = value
		self.list_ctrl.SetItem(self.selected_index, 1, value)
		event.Skip()

	def _on_ok(self, event: wx.CommandEvent) -> None:
		try:
			self._save_entries()
		except IOError as exc:
			wx.MessageBox(f"儲存失敗：{exc}", "錯誤", wx.OK | wx.ICON_ERROR, parent=self)
			return
		event.Skip()

	def _save_entries(self) -> None:
		self.dictionary_path.parent.mkdir(parents=True, exist_ok=True)
		with self.dictionary_path.open("w", newline="", encoding="utf-8") as fp:
			writer = csv.DictWriter(fp, fieldnames=["text", "braille"])
			writer.writeheader()
			for entry in self.entries:
				writer.writerow({"text": entry.text, "braille": entry.braille})
