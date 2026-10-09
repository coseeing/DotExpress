"""A case-insensitive, case-preserving file model for document package tests (F-1).

``CaseInsensitivePackageFiles`` works on a real directory but resolves every path it is
given the way NTFS and APFS do: to the existing entry in the same directory whose name is
casefold-equal, if there is one. Linux tests use it to run the Windows and macOS
case-collision scenarios. It is a model; the real check is the Windows verification debt.
"""

from __future__ import annotations

import os
from pathlib import Path

from documents.workspace import Document, PackageFiles


class CaseInsensitivePackageFiles(PackageFiles):
    def __init__(self, *, replace_keeps_existing_spelling: bool = True) -> None:
        # Replacing onto a case variant of another existing entry: True keeps that entry's
        # spelling (the pessimistic reading), False gives it the destination spelling.
        self.replace_keeps_existing_spelling = replace_keeps_existing_spelling

    @staticmethod
    def resolve(path: Path | str) -> Path:
        """The existing entry that ``path`` names on a case-insensitive file system, else ``path``."""
        path = Path(path)
        if not path.parent.is_dir():
            return path
        # Names from the listing, never Path equality or exists(): both ignore case on a
        # case-insensitive host, and the model must behave the same on every host.
        names = sorted(entry.name for entry in path.parent.iterdir())
        if path.name in names:
            return path
        folded_name = path.name.casefold()
        for name in names:
            if name.casefold() == folded_name:
                return path.parent / name
        return path

    def ensure_writable(self, path: Path) -> None:
        super().ensure_writable(self.resolve(path))

    def exists(self, path: Path) -> bool:
        return self.resolve(path).exists()

    def write(self, path: Path, document: Document) -> None:
        super().write(self.resolve(path), document)

    def remove(self, path: Path) -> None:
        super().remove(self.resolve(path))

    def replace(self, source: Path, destination: Path) -> None:
        source_entry = self.resolve(source)
        destination = Path(destination)
        destination_entry = self.resolve(destination)
        if str(source_entry) == str(destination_entry):
            # One entry renamed to its own case variant takes the new spelling.
            os.replace(source_entry, destination)
            return
        os.replace(source_entry, destination_entry)
        if destination_entry.name != destination.name and not self.replace_keeps_existing_spelling:
            os.replace(destination_entry, destination)
