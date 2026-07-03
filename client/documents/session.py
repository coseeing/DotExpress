from dataclasses import dataclass

from documents.workspace import Document, choose_selection_after_delete


@dataclass(frozen=True)
class OpenDocumentDecision:
	document: Document | None
	open_name: str | None
	selected_name: str | None


@dataclass(frozen=True)
class DeleteDocumentDecision:
	preferred_name: str | None
	was_open: bool


def get_document_names(documents: list[Document]) -> list[str]:
	return [document.name for document in documents]


def find_document(documents: list[Document], name: str | None) -> Document | None:
	if not name:
		return None
	for document in documents:
		if document.name == name:
			return document
	return None


def replace_document(documents: list[Document], updated_document: Document) -> bool:
	for index, document in enumerate(documents):
		if document.name == updated_document.name:
			documents[index] = updated_document
			return True
	return False


def get_adjacent_document_name(documents: list[Document], current_name: str | None, step: int) -> str | None:
	if not documents:
		return None
	if step == 0:
		return current_name if find_document(documents, current_name) is not None else documents[0].name
	current_index = next((index for index, document in enumerate(documents) if document.name == current_name), None)
	if current_index is None:
		return documents[0].name if step > 0 else documents[-1].name
	target_index = (current_index + step) % len(documents)
	return documents[target_index].name


def document_name_exists(documents: list[Document], name: str, exclude_name: str | None = None) -> bool:
	return any(document.name == name and document.name != exclude_name for document in documents)


def plan_open_document(documents: list[Document], name: str | None) -> OpenDocumentDecision:
	document = find_document(documents, name)
	if document is None:
		return OpenDocumentDecision(document=None, open_name=None, selected_name=None)
	return OpenDocumentDecision(document=document, open_name=document.name, selected_name=document.name)


def plan_delete_document(documents: list[Document], deleted_name: str, open_name: str | None) -> DeleteDocumentDecision:
	return DeleteDocumentDecision(
		preferred_name=choose_selection_after_delete(get_document_names(documents), deleted_name),
		was_open=open_name == deleted_name,
	)


def format_window_title(open_name: str | None) -> str:
	if not open_name:
		return "DotExpress"
	return f"{open_name} - DotExpress"


def rename_document_in_list(documents: list[Document], source_name: str, new_name: str) -> Document | None:
	selected_document = find_document(documents, source_name)
	if selected_document is None:
		return None
	renamed_document = Document(name=new_name, text=selected_document.text, braille=selected_document.braille)
	for index, document in enumerate(documents):
		if document.name == source_name:
			documents[index] = renamed_document
			return renamed_document
	return None
