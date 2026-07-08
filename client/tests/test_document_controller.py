import sys
import types
import unittest

if "mammoth" not in sys.modules:
    mammoth = types.ModuleType("mammoth")
    mammoth.convert_to_html = lambda *args, **kwargs: types.SimpleNamespace(value="")
    sys.modules["mammoth"] = mammoth

if "ebooklib" not in sys.modules:
    ebooklib = types.ModuleType("ebooklib")
    epub = types.ModuleType("ebooklib.epub")
    epub.read_epub = lambda *_args, **_kwargs: types.SimpleNamespace(spine=[], get_item_with_id=lambda _item_id: None)
    ebooklib.epub = epub
    sys.modules["ebooklib"] = ebooklib
    sys.modules["ebooklib.epub"] = epub

if "pymupdf" not in sys.modules:
    sys.modules["pymupdf"] = types.ModuleType("pymupdf")

if "pypdf" not in sys.modules:
    pypdf = types.ModuleType("pypdf")
    pypdf.PdfReader = type("PdfReader", (), {})
    sys.modules["pypdf"] = pypdf

if "lxml" not in sys.modules:
    lxml = types.ModuleType("lxml")
    etree = types.ModuleType("lxml.etree")
    html = types.ModuleType("lxml.html")

    class _QName:
        def __init__(self, element):
            self.localname = getattr(element, "tag", "")

    etree.QName = _QName
    etree.XMLParser = lambda *args, **kwargs: object()
    etree.fromstring = lambda *args, **kwargs: types.SimpleNamespace(xpath=lambda *_a, **_k: [])
    html.fragment_fromstring = lambda *args, **kwargs: types.SimpleNamespace()
    lxml.etree = etree
    lxml.html = html
    sys.modules["lxml"] = lxml
    sys.modules["lxml.etree"] = etree
    sys.modules["lxml.html"] = html

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


if __name__ == "__main__":
    unittest.main()
