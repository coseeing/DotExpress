import ast
import tempfile
import unittest
from pathlib import Path

from dictionaries.entries import DictionaryEntry, PreservedDictionaryRow
from dictionaries.entry_list_model import DictionaryEntryListModel, DuplicateEntryError, EntryListUpdate

MODULE_PATH = Path(__file__).resolve().parents[1] / "dictionaries" / "entry_list_model.py"
GENERAL = "\u4e00\u822c"
BOPOMOFO = "\u6ce8\u97f3"
DUZI = "\u809a\u5b50"
INVALID_DUZI = "\u3109\u3128\u02cb|\u3117\u02d9"  # "|" is not a Bopomofo symbol
VALID_DUZI = "\u3109\u3128\u02cb\u3117\u02d9"
# MIXED_CSV of test_dictionary_entries (F-4): two entries around every kind of row the
# editor does not show, and what saving it writes (the row with a missing field gets
# its empty third field).
MIXED_CSV = (
	"text,braille,type\r\n"
	"Alpha,\u2801,General\r\n"
	",\u2803,General\r\n"
	"  ,\u2803,General\r\n"
	"\u809a\u5b50, \u3109\u3128\u02cb|\u3117\u02d9 ,Bopomofo\r\n"
	"\u5abd,\u3107\u311a ,Bopomofo\r\n"
	",\u2803\r\n"
	'"q,""x""","a\r\nb",Bopomofo\r\n'
	"Beta,\u2803,General\r\n"
).encode("utf-8")
MIXED_CSV_SAVED = MIXED_CSV.replace(",\u2803\r\n".encode("utf-8"), ",\u2803,\r\n".encode("utf-8"))


def _entry(text: str, braille: str = "\u2801", entry_type: str = "General") -> DictionaryEntry:
	return DictionaryEntry(text, braille, entry_type)


class _ModelTestCase(unittest.TestCase):
	def assertUnchanged(self, model: DictionaryEntryListModel, entries, visible, filter_text: str) -> None:
		self.assertEqual(model.entries, tuple(entries))
		self.assertEqual(model.visible_entries, tuple(visible))
		self.assertEqual(model.filter_text, filter_text)

	def assertSameObjects(self, actual, expected) -> None:
		self.assertEqual([id(entry) for entry in actual], [id(entry) for entry in expected])


class DuplicateEntryErrorTest(unittest.TestCase):
	def test_is_a_value_error_that_keeps_the_identifier(self) -> None:
		error = DuplicateEntryError("Alpha")

		self.assertIsInstance(error, ValueError)
		self.assertEqual(error.identifier, "Alpha")
		self.assertEqual(error.args, ("Alpha",))


class EntryListUpdateTest(unittest.TestCase):
	def test_is_frozen_and_does_not_clear_the_filter_by_default(self) -> None:
		update = EntryListUpdate(2)

		self.assertEqual(update, EntryListUpdate(selection=2, filter_cleared=False))
		with self.assertRaises(AttributeError):
			update.selection = 0


class ConstructionTest(_ModelTestCase):
	def test_default_model_is_empty(self) -> None:
		model = DictionaryEntryListModel()

		self.assertUnchanged(model, [], [], "")
		self.assertEqual(model.visible_count, 0)

	def test_entries_are_copied_and_all_visible(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta")
		source = [alpha, beta]

		model = DictionaryEntryListModel(source)
		source.append(_entry("Gamma"))

		self.assertUnchanged(model, [alpha, beta], [alpha, beta], "")
		self.assertSameObjects(model.visible_entries, [alpha, beta])
		self.assertEqual(model.visible_count, 2)

	def test_returned_tuples_are_snapshots(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha")])
		entries, visible = model.entries, model.visible_entries

		model.add(_entry("Beta"))

		self.assertIsInstance(entries, tuple)
		self.assertEqual(len(entries), 1)
		self.assertEqual(len(visible), 1)


class VisibleEntryTest(unittest.TestCase):
	def test_returns_the_visible_object_or_none_out_of_range(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta")
		model = DictionaryEntryListModel([alpha, beta])
		model.apply_filter("bet")

		self.assertIs(model.visible_entry(0), beta)
		for index in (None, -1, 1):
			with self.subTest(index=index):
				self.assertIsNone(model.visible_entry(index))


class MatchesTest(unittest.TestCase):
	def test_casefolded_substring_of_text_or_braille(self) -> None:
		cases = [
			(_entry("Stra\u00dfe", "\u280e"), "STRASSE", True),
			(_entry("STRASSE", ""), "\u00df", True),
			(_entry("Alpha", "Needle"), "need", True),
			(_entry("Alpha", "\u2801"), "PH", True),
			(_entry("New York"), " ", True),
			(_entry("Alpha"), " ", False),
			(_entry("Alpha", "\u2801", "Bopomofo"), "bopomofo", False),
			(_entry("Alpha", "\u2801", "General"), GENERAL, False),
			(_entry("Alpha"), "", True),
		]
		for entry, filter_text, expected in cases:
			with self.subTest(entry=entry, filter_text=filter_text):
				self.assertIs(DictionaryEntryListModel.matches(entry, filter_text), expected)


class CellTextTest(unittest.TestCase):
	def test_columns_show_text_braille_and_the_translated_type_label(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha", "\u2801", "General"), _entry("Beta", "\u3105\u311a\u02c7", "Bopomofo")])

		self.assertEqual([model.cell_text(0, column) for column in range(3)], ["Alpha", "\u2801", GENERAL])
		self.assertEqual([model.cell_text(1, column) for column in range(3)], ["Beta", "\u3105\u311a\u02c7", BOPOMOFO])

	def test_rows_are_visible_rows(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha"), _entry("Beta")])
		model.apply_filter("bet")

		self.assertEqual(model.cell_text(0, 0), "Beta")
		with self.assertRaises(IndexError):
			model.cell_text(1, 0)

	def test_unknown_type_is_shown_as_is(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha", "\u2801", "Custom")])

		self.assertEqual(model.cell_text(0, 2), "Custom")

	def test_unknown_column_raises_value_error(self) -> None:
		model = DictionaryEntryListModel([_entry("Alpha")])

		with self.assertRaises(ValueError) as caught:
			model.cell_text(0, 3)

		self.assertEqual(str(caught.exception), "Unknown column: 3")


class SourceTextExistsTest(unittest.TestCase):
	def test_exact_text_over_the_full_list_with_identity_exclusion(self) -> None:
		alpha, beta = _entry("Alpha"), _entry("Beta", "\u2803")
		twin = _entry("Alpha")
		model = DictionaryEntryListModel([alpha, beta])
		model.apply_filter("bet")

		self.assertTrue(model.source_text_exists("Alpha"))
		self.assertFalse(model.source_text_exists("alpha"))
		self.assertFalse(model.source_text_exists("Alpha", exclude_entry=alpha))
		self.assertTrue(model.source_text_exists("Alpha", exclude_entry=twin))
		self.assertTrue(model.source_text_exists("Beta", exclude_entry=alpha))
		self.assertTrue(model.is_duplicate("Alpha"))

	def test_is_duplicate_excludes_the_edited_entry_and_lets_it_keep_its_text(self) -> None:
		# F-11 (D9, O6): with two identical rows, either one can be edited without changing
		# its source text; the edit adds no new duplicate.
		first, beta, second = _entry("a"), _entry("b", "\u2803"), _entry("a")
		model = DictionaryEntryListModel([first, beta, second])

		self.assertTrue(model.is_duplicate("a"))
		self.assertFalse(model.is_duplicate("c"))
		self.assertFalse(model.is_duplicate("a", editing=second))
		self.assertFalse(model.is_duplicate("c", editing=second))
		self.assertTrue(model.is_duplicate("b", editing=second))
		self.assertTrue(model.is_duplicate("a", editing=beta))
		self.assertFalse(model.is_duplicate("A", editing=beta))


class ApplyFilterTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.alpine = _entry("Alpine", "\u2801\u2807")
		self.model = DictionaryEntryListModel([self.alpha, self.beta, self.alpine])

	def test_filter_keeps_matching_entries_in_full_list_order(self) -> None:
		update = self.model.apply_filter("alp")

		self.assertEqual(update, EntryListUpdate(0))
		self.assertUnchanged(self.model, [self.alpha, self.beta, self.alpine], [self.alpha, self.alpine], "alp")
		self.assertEqual(self.model.visible_count, 2)

	def test_empty_filter_shows_everything(self) -> None:
		self.model.apply_filter("alp")

		self.model.apply_filter("")

		self.assertSameObjects(self.model.visible_entries, [self.alpha, self.beta, self.alpine])

	def test_selection_is_read_from_the_visible_list_before_the_change(self) -> None:
		self.model.apply_filter("")

		update = self.model.apply_filter("alp", selected_index=2)

		self.assertEqual(update, EntryListUpdate(1))

	def test_hidden_or_missing_selection_falls_back_to_the_first_row(self) -> None:
		for selected_index in (1, None, -1, 3):
			with self.subTest(selected_index=selected_index):
				self.model.apply_filter("")

				self.assertEqual(self.model.apply_filter("alp", selected_index=selected_index), EntryListUpdate(0))

	def test_selection_is_restored_by_equality_so_identical_rows_select_the_first(self) -> None:
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])

		update = model.apply_filter("a", selected_index=2)

		self.assertEqual(update, EntryListUpdate(0))

	def test_empty_result_has_no_selection(self) -> None:
		self.assertEqual(self.model.apply_filter("zzz", selected_index=0), EntryListUpdate(None))
		self.assertEqual(self.model.visible_count, 0)


class AddTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.model = DictionaryEntryListModel([self.alpha, self.beta])

	def test_appends_at_the_end_and_selects_the_new_entry(self) -> None:
		gamma = _entry("Gamma", "\u281b")

		update = self.model.add(gamma)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.beta, gamma])

	def test_matching_filter_is_kept(self) -> None:
		self.model.apply_filter("alp")
		alpine = _entry("Alpine", "\u2801\u2807")

		update = self.model.add(alpine)

		self.assertEqual(update, EntryListUpdate(1, filter_cleared=False))
		self.assertUnchanged(self.model, [self.alpha, self.beta, alpine], [self.alpha, alpine], "alp")

	def test_nonmatching_filter_is_cleared(self) -> None:
		self.model.apply_filter("alp")
		gamma = _entry("Gamma", "\u281b")

		update = self.model.add(gamma)

		self.assertEqual(update, EntryListUpdate(2, filter_cleared=True))
		self.assertUnchanged(self.model, [self.alpha, self.beta, gamma], [self.alpha, self.beta, gamma], "")

	def test_duplicate_of_a_hidden_entry_raises_and_changes_nothing(self) -> None:
		self.model.apply_filter("bet")

		with self.assertRaises(DuplicateEntryError) as caught:
			self.model.add(_entry("Alpha", "\u281b", "Braille"))

		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.beta], "bet")

	def test_case_different_text_is_not_a_duplicate(self) -> None:
		self.model.add(_entry("alpha"))

		self.assertEqual([entry.text for entry in self.model.entries], ["Alpha", "Beta", "alpha"])


class ReplaceTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.alpine = _entry("Alpine", "\u2801\u2807")
		self.beta = _entry("Beta", "\u2803")
		self.model = DictionaryEntryListModel([self.alpha, self.alpine, self.beta])

	def test_replaces_in_place_and_selects_the_new_entry(self) -> None:
		bravo = _entry("Bravo", "\u2803\u2817")

		update = self.model.replace(2, bravo)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertSameObjects(self.model.entries, [self.alpha, self.alpine, bravo])

	def test_replacement_gets_the_fields_of_the_replaced_row_and_a_new_entry_has_none(self) -> None:
		# F-11 (D5, O5): an edited row keeps its extra columns; the entry dialog gives none.
		self.alpine.fields = ("Alpine", "note", "\u2801\u2807", "General")
		bravo, gamma = _entry("Bravo", "\u2803\u2817"), _entry("Gamma", "\u281b")

		self.model.replace(1, bravo)
		self.model.add(gamma)

		self.assertEqual(self.model.entries[1].fields, ("Alpine", "note", "\u2801\u2807", "General"))
		self.assertIs(self.model.entries[1], bravo)
		self.assertEqual(gamma.fields, ())

	def test_same_text_is_accepted(self) -> None:
		changed = _entry("Alpha", "\u2801\u2801", "Braille")

		self.model.replace(0, changed)

		self.assertSameObjects(self.model.entries, [changed, self.alpine, self.beta])

	def test_filter_is_kept_and_a_hidden_result_selects_the_same_index_clamped(self) -> None:
		self.model.apply_filter("alp")
		gamma = _entry("Gamma", "\u281b")

		update = self.model.replace(1, gamma)

		self.assertEqual(update, EntryListUpdate(0))
		self.assertUnchanged(self.model, [self.alpha, gamma, self.beta], [self.alpha], "alp")

	def test_hidden_result_with_nothing_left_has_no_selection(self) -> None:
		self.model.apply_filter("bet")

		update = self.model.replace(0, _entry("Gamma", "\u281b"))

		self.assertEqual(update, EntryListUpdate(None))
		self.assertEqual(self.model.visible_count, 0)

	def test_duplicate_raises_and_changes_nothing(self) -> None:
		self.model.apply_filter("bet")

		with self.assertRaises(DuplicateEntryError) as caught:
			self.model.replace(0, _entry("Alpha", "\u2803"))

		self.assertEqual(caught.exception.identifier, "Alpha")
		self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.beta], "bet")

	def test_identical_rows_replace_the_visible_object_and_can_keep_their_text(self) -> None:
		# Was the P2-2 Q4 KNOWN BUG (first half): the other identical row made the text a
		# duplicate. Fixed by F-11 (D9, O6).
		first, second = _entry("a"), _entry("a")
		model = DictionaryEntryListModel([first, _entry("b"), second])
		changed = _entry("a", "\u2803")

		update = model.replace(2, changed)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[0], first)
		self.assertIs(model.entries[2], changed)

	def test_replacement_is_selected_by_identity_even_when_it_equals_another_row(self) -> None:
		# F-11 (D9): equality would select the first of two identical rows.
		first, braille = _entry("a"), _entry("a", "\u2801", "Braille")
		model = DictionaryEntryListModel([first, _entry("b"), braille])
		twin = _entry("a")

		update = model.replace(2, twin)

		self.assertEqual(update, EntryListUpdate(2))
		self.assertIs(model.entries[2], twin)

	def test_another_row_cannot_take_the_text_of_an_identical_pair(self) -> None:
		first, beta, second = _entry("a"), _entry("b"), _entry("a")
		model = DictionaryEntryListModel([first, beta, second])

		with self.assertRaises(DuplicateEntryError):
			model.replace(1, _entry("a", "\u2803"))

		self.assertSameObjects(model.entries, [first, beta, second])

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		self.model.apply_filter("alp")
		for index in (-1, 2):
			with self.subTest(index=index):
				with self.assertRaises(IndexError):
					self.model.replace(index, _entry("Gamma"))

				self.assertUnchanged(self.model, [self.alpha, self.alpine, self.beta], [self.alpha, self.alpine], "alp")


class RemoveTest(_ModelTestCase):
	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.beta = _entry("Beta", "\u2803")
		self.gamma = _entry("Gamma", "\u281b")
		self.model = DictionaryEntryListModel([self.alpha, self.beta, self.gamma])

	def test_selects_the_row_now_at_the_same_index(self) -> None:
		update = self.model.remove(1)

		self.assertEqual(update, EntryListUpdate(1))
		self.assertSameObjects(self.model.entries, [self.alpha, self.gamma])

	def test_removing_the_last_row_selects_the_new_last_row(self) -> None:
		self.assertEqual(self.model.remove(2), EntryListUpdate(1))

	def test_removing_the_only_visible_row_has_no_selection(self) -> None:
		self.model.apply_filter("gam")

		self.assertEqual(self.model.remove(0), EntryListUpdate(None))
		self.assertUnchanged(self.model, [self.alpha, self.beta], [], "gam")

	def test_identical_rows_remove_the_selected_one_and_select_the_remaining_twin(self) -> None:
		# Was the P2-2 Q4 KNOWN BUG (second half): the first equal row was removed. Fixed by
		# F-11 (D9); the selection still goes to an equal row (by equality, as the golden
		# trace records).
		first, braille, second = _entry("a"), _entry("a", "\u2801", "Braille"), _entry("a")
		beta = _entry("Beta", "\u2803")
		model = DictionaryEntryListModel([first, beta, braille, second])

		update = model.remove(3)

		self.assertEqual(update, EntryListUpdate(0))
		self.assertSameObjects(model.entries, [first, beta, braille])

	def test_removing_the_second_of_two_identical_rows_keeps_the_fields_of_the_first(self) -> None:
		# F-11 (D9, B2): the saved order is a, b, with the first a's record.
		first, beta, second = _entry("a"), _entry("b", "\u2803"), _entry("a")
		first.fields, second.fields = ("a", "\u2801", "General", "first"), ("a", "\u2801", "General", "third")
		model = DictionaryEntryListModel([first, beta, second])

		model.remove(2)

		self.assertEqual([entry.fields for entry in model.entries], [("a", "\u2801", "General", "first"), ()])
		self.assertIs(model.entries[0], first)

	def test_out_of_range_index_raises_index_error_and_changes_nothing(self) -> None:
		for index in (-1, 3):
			with self.subTest(index=index):
				with self.assertRaises(IndexError):
					self.model.remove(index)

				self.assertUnchanged(
					self.model, [self.alpha, self.beta, self.gamma], [self.alpha, self.beta, self.gamma], ""
				)


class PreservedRowsTest(_ModelTestCase):
	"""Rows the editor does not show stay hidden and keep their place (F-4); since F-11 (D2)
	their source texts are not duplicates."""

	def setUp(self) -> None:
		self.alpha = _entry("Alpha", "\u2801")
		self.kept = PreservedDictionaryRow(DUZI, INVALID_DUZI, "Bopomofo")
		self.beta = _entry("Beta", "\u2803")
		self.blank = PreservedDictionaryRow("", "\u2803", "General")
		self.model = DictionaryEntryListModel([self.alpha, self.kept, self.beta, self.blank])

	def test_preserved_rows_are_not_entries_and_never_visible(self) -> None:
		self.assertUnchanged(self.model, [self.alpha, self.beta], [self.alpha, self.beta], "")
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank])
		for filter_text in (INVALID_DUZI[0], DUZI[0], "|"):
			with self.subTest(filter_text=filter_text):
				self.assertEqual(self.model.apply_filter(filter_text), EntryListUpdate(None))
				self.assertEqual(self.model.visible_entries, ())

	def test_remove_and_add_leave_preserved_rows_in_place(self) -> None:
		gamma = _entry("Gamma", "\u281b")

		self.assertEqual(self.model.remove(1), EntryListUpdate(0))
		self.assertEqual(self.model.add(gamma), EntryListUpdate(1))

		# The new entry goes to the end of the file, after the trailing preserved row.
		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.blank, gamma])
		self.assertSameObjects(self.model.entries, [self.alpha, gamma])

	def test_replace_leaves_preserved_rows_in_place(self) -> None:
		delta = _entry("Delta", "\u2819")

		self.assertEqual(self.model.replace(1, delta), EntryListUpdate(1))

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, delta, self.blank])

	def test_the_source_text_of_a_preserved_row_is_not_a_duplicate(self) -> None:
		# F-4 D5 refused it; F-11 (D2) accepts it: OK lists the hidden row, so the user sees
		# which row the new entry replaces (D1).
		self.assertFalse(self.model.source_text_exists(DUZI))
		self.assertFalse(self.model.is_duplicate(DUZI))
		self.assertFalse(self.model.is_duplicate("", editing=self.alpha))
		valid = _entry(DUZI, VALID_DUZI, "Bopomofo")

		self.assertEqual(self.model.add(valid), EntryListUpdate(2))

		self.assertSameObjects(self.model.rows, [self.alpha, self.kept, self.beta, self.blank, valid])

	def test_remove_of_an_entry_leaves_a_preserved_row_with_the_same_source_text(self) -> None:
		# Only a file can hold both rows (D5); remove must not match the hidden row by its text.
		visible = _entry(DUZI, "⠁")
		model = DictionaryEntryListModel([self.alpha, self.kept, visible])

		self.assertEqual(model.remove(1), EntryListUpdate(0))

		self.assertSameObjects(model.rows, [self.alpha, self.kept])



class LoadSaveTest(unittest.TestCase):
	def setUp(self) -> None:
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.directory = Path(temp_dir.name)

	def test_load_of_a_missing_file_gives_an_empty_model(self) -> None:
		model = DictionaryEntryListModel.load(self.directory / "missing.csv")

		self.assertEqual(model.entries, ())
		self.assertEqual(model.filter_text, "")

	def test_save_writes_the_full_list_while_filtered_and_load_reads_it_back(self) -> None:
		path = self.directory / "nested" / "dictionary.csv"
		model = DictionaryEntryListModel([_entry("Beta", "\u2803"), _entry("Alpha", "\u2801", "Braille")])
		model.apply_filter("alp")

		model.save(path)

		self.assertEqual(
			path.read_bytes().decode("utf-8"),
			"text,braille,type\r\nBeta,\u2803,General\r\nAlpha,\u2801,Braille\r\n",
		)
		self.assertEqual(DictionaryEntryListModel.load(path).entries, model.entries)

	def test_load_errors_propagate(self) -> None:
		path = self.directory / "broken.csv"
		path.write_bytes(b"text,braille,type\r\n\xff\xfe,x,General\r\n")

		with self.assertRaises(UnicodeDecodeError):
			DictionaryEntryListModel.load(path)

	def test_save_of_an_unchanged_model_writes_preserved_rows_back_in_place(self) -> None:
		source = self.directory / "source.csv"
		source.write_bytes(MIXED_CSV)
		target = self.directory / "target.csv"

		DictionaryEntryListModel.load(source).save(target)

		self.assertEqual(target.read_bytes(), MIXED_CSV_SAVED)

	def test_save_keeps_the_bom_header_and_extra_columns_of_the_loaded_file(self) -> None:
		# F-11 (D5): the layout comes from the load; a new entry gets empty extra fields.
		path = self.directory / "excel.csv"
		path.write_bytes(b"\xef\xbb\xbf" + "text,note,braille,type\r\nAlpha,first,\u2801,General\r\n".encode("utf-8"))
		model = DictionaryEntryListModel.load(path)
		model.add(_entry("Beta", "\u2803"))

		model.save(path)

		self.assertEqual(
			path.read_bytes(),
			b"\xef\xbb\xbf" + "text,note,braille,type\r\nAlpha,first,\u2801,General\r\nBeta,,\u2803,General\r\n".encode("utf-8"),
		)


class ImportGuardTest(unittest.TestCase):
	def test_model_imports_no_ui_or_translation_module(self) -> None:
		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name for alias in node.names)
			elif isinstance(node, ast.ImportFrom):
				imported.add(node.module or "")

		self.assertEqual(imported, {"__future__", "collections.abc", "dataclasses", "pathlib", "dictionaries.entries"})
		forbidden = ("wx", "gui", "dialog", "ui", "settings", "i18n")
		for name in imported:
			with self.subTest(name=name):
				self.assertNotIn(name.split(".")[0], forbidden)


if __name__ == "__main__":
	unittest.main()
