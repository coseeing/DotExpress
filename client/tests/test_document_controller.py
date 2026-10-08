import unittest

from documents.workspace import Document

from documents.controller import DocumentController


class DocumentControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            Document(name="alpha", text="a", braille="1"),
            Document(name="beta", text="b", braille="2"),
            Document(name="zoo", text="z", braille="3"),
        ]

    def test_document_accessors_expose_current_state(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="beta",
            selected_name="alpha",
        )

        self.assertEqual(controller.document_names, ["alpha", "beta", "zoo"])
        self.assertEqual(controller.open_document_name, "beta")
        self.assertEqual(controller.selected_document_name, "alpha")
        self.assertEqual(controller.get_document("beta"), self.documents[1])
        self.assertIsNone(controller.get_document("missing"))

    def test_sort_documents_orders_in_place(self) -> None:
        controller = DocumentController(
            documents=[self.documents[2], self.documents[0], self.documents[1]]
        )

        controller.sort_documents()

        self.assertEqual(controller.document_names, ["alpha", "beta", "zoo"])

    def test_open_existing_document_updates_open_and_selected_names(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        opened_document = controller.open_document("beta")

        self.assertEqual(opened_document, self.documents[1])
        self.assertEqual(controller.open_name, "beta")
        self.assertEqual(controller.selected_name, "beta")

    def test_open_missing_document_clears_names(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="alpha",
        )

        opened_document = controller.open_document("missing")

        self.assertIsNone(opened_document)
        self.assertIsNone(controller.open_name)
        self.assertIsNone(controller.selected_name)

    def test_replace_matching_document_without_changing_selection(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="alpha",
        )
        updated_document = Document(name="beta", text="updated", braille="24")

        replaced = controller.replace_document(updated_document)

        self.assertTrue(replaced)
        self.assertEqual(controller.documents[1], updated_document)
        self.assertEqual(controller.open_name, "alpha")
        self.assertEqual(controller.selected_name, "alpha")

    def test_rename_updates_names_and_dual_view_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="alpha",
            dual_view_results_by_document={"alpha": ("segment",), "beta": ("keep",)},
        )

        renamed_document = controller.rename_document("alpha", "renamed")

        self.assertEqual(renamed_document, Document(name="renamed", text="a", braille="1"))
        self.assertEqual(controller.documents[0], renamed_document)
        self.assertEqual(controller.open_name, "renamed")
        self.assertEqual(controller.selected_name, "renamed")
        self.assertEqual(
            controller.dual_view_results_by_document,
            {"renamed": ("segment",), "beta": ("keep",)},
        )

    def test_delete_open_document_prefers_neighbor_and_removes_dual_view_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="beta",
            selected_name="beta",
            dual_view_results_by_document={"alpha": ("keep",), "beta": ("remove",)},
        )

        decision = controller.delete_document("beta")

        self.assertTrue(decision.was_open)
        self.assertEqual(decision.preferred_name, "alpha")
        self.assertEqual(
            controller.documents,
            [self.documents[0], self.documents[2]],
        )
        self.assertEqual(controller.open_name, "alpha")
        self.assertEqual(controller.selected_name, "alpha")
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": ("keep",)})

    def test_delete_all_clears_state_and_cache(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="beta",
            dual_view_results_by_document={"alpha": ("segment",)},
        )

        controller.delete_all_documents()

        self.assertEqual(controller.documents, [])
        self.assertIsNone(controller.open_name)
        self.assertIsNone(controller.selected_name)
        self.assertEqual(controller.dual_view_results_by_document, {})

    def test_restore_after_delete_all_failure_reconciles_cache_and_missing_names(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="zoo",
            dual_view_results_by_document={
                "alpha": ("drop",),
                "beta": ("keep",),
                "ghost": ("drop",),
            },
        )

        controller.restore_documents_after_delete_all_failure([Document(name="beta", text="b2", braille="22")])

        self.assertEqual(controller.documents, [Document(name="beta", text="b2", braille="22")])
        self.assertIsNone(controller.open_name)
        self.assertIsNone(controller.selected_name)
        self.assertEqual(controller.dual_view_results_by_document, {"beta": ("keep",)})

    def test_rename_document_moves_dual_view_cache_entries(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="alpha",
            selected_name="alpha",
            dual_view_results_by_document={"alpha": ("segment",), "beta": ("keep",)},
        )

        renamed_document = controller.rename_document("alpha", "renamed")

        self.assertEqual(renamed_document, Document(name="renamed", text="a", braille="1"))
        self.assertEqual(controller.dual_view_results_by_document, {"renamed": ("segment",), "beta": ("keep",)})

    def test_delete_document_removes_dual_view_cache_entry_and_preserves_preferred_selection(self) -> None:
        controller = DocumentController(
            documents=list(self.documents),
            open_name="beta",
            selected_name="beta",
            dual_view_results_by_document={"alpha": ("keep",), "beta": ("remove",), "zoo": ("keep-zoo",)},
        )

        decision = controller.delete_document("beta")

        self.assertTrue(decision.was_open)
        self.assertEqual(controller.open_document_name, "alpha")
        self.assertEqual(controller.selected_document_name, "alpha")
        self.assertEqual(controller.dual_view_results_by_document, {"alpha": ("keep",), "zoo": ("keep-zoo",)})

    def test_add_document_appends_without_sorting(self) -> None:
        controller = DocumentController(documents=[self.documents[2]])

        controller.add_document(self.documents[0])

        self.assertEqual(controller.document_names, ["zoo", "alpha"])

    def test_add_documents_appends_in_given_order(self) -> None:
        controller = DocumentController(documents=[self.documents[1]])

        controller.add_documents([self.documents[2], self.documents[0]])

        self.assertEqual(controller.document_names, ["beta", "zoo", "alpha"])

    def test_load_documents_replaces_list_and_clears_names_and_cache(self) -> None:
        loaded = [self.documents[1], self.documents[2]]
        controller = DocumentController(
            documents=[self.documents[0]],
            open_name="alpha",
            selected_name="alpha",
            dual_view_results_by_document={"alpha": ("segment",)},
        )

        controller.load_documents(loaded)
        loaded.append(self.documents[0])

        self.assertEqual(controller.document_names, ["beta", "zoo"])
        self.assertIsNone(controller.open_document_name)
        self.assertIsNone(controller.selected_document_name)
        self.assertEqual(controller.get_dual_view_results("alpha"), ())

    def test_select_document_sets_name_without_validation(self) -> None:
        controller = DocumentController(documents=list(self.documents), selected_name="alpha")

        controller.select_document("missing")
        self.assertEqual(controller.selected_document_name, "missing")
        controller.select_document(None)
        self.assertIsNone(controller.selected_document_name)

    def test_document_name_at_returns_none_outside_the_list(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        self.assertEqual(controller.document_name_at(0), "alpha")
        self.assertEqual(controller.document_name_at(2), "zoo")
        self.assertIsNone(controller.document_name_at(-1))
        self.assertIsNone(controller.document_name_at(3))

    def test_has_documents_and_first_document_name(self) -> None:
        empty = DocumentController()
        controller = DocumentController(documents=[self.documents[1], self.documents[0]])

        self.assertFalse(empty.has_documents)
        self.assertIsNone(empty.first_document_name)
        self.assertTrue(controller.has_documents)
        self.assertEqual(controller.first_document_name, "beta")

    def test_documents_snapshot_is_a_copy(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        snapshot = controller.documents_snapshot()
        snapshot.clear()

        self.assertEqual(controller.document_names, ["alpha", "beta", "zoo"])
        self.assertEqual(controller.documents_snapshot(), self.documents)
        self.assertIsNot(controller.documents_snapshot(), controller.documents)

    def test_adjacent_document_name_prefers_open_over_selected(self) -> None:
        controller = DocumentController(documents=list(self.documents), open_name="beta", selected_name="zoo")

        self.assertEqual(controller.adjacent_document_name(1), "zoo")
        self.assertEqual(controller.adjacent_document_name(-1), "alpha")

        controller.open_name = None
        self.assertEqual(controller.adjacent_document_name(1), "alpha")
        self.assertIsNone(DocumentController().adjacent_document_name(1))

    def test_document_name_exists_is_exact_and_honours_exclude(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        self.assertTrue(controller.document_name_exists("beta"))
        self.assertFalse(controller.document_name_exists("Beta"))
        self.assertFalse(controller.document_name_exists("beta", exclude_name="beta"))
        self.assertTrue(controller.document_name_exists("zoo", exclude_name="beta"))

    def test_dual_view_results_get_and_set(self) -> None:
        controller = DocumentController(documents=list(self.documents))

        self.assertEqual(controller.get_dual_view_results("alpha"), ())
        self.assertEqual(controller.get_dual_view_results(None), ())
        controller.set_dual_view_results("alpha", ("segment",))
        controller.set_dual_view_results("ghost", ("other",))

        self.assertEqual(controller.get_dual_view_results("alpha"), ("segment",))
        self.assertEqual(
            controller.dual_view_results_by_document,
            {"alpha": ("segment",), "ghost": ("other",)},
        )


if __name__ == "__main__":
    unittest.main()
