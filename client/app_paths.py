from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
from collections.abc import Callable
from typing import BinaryIO


@dataclass(frozen=True)
class ApplicationPaths:
    root: Path
    config: Path
    dictionary: Path
    workspace: Path
    log: Path
    dual_view: Path

    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.dictionary, self.workspace, self.log, self.dual_view)


class ApplicationDataError(OSError):
    def __init__(self, path: Path, cause: OSError):
        self.path = Path(path)
        self.cause = cause
        super().__init__(f'Cannot write to "{self.path}": {cause}')


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def build_application_paths(root: Path | None = None) -> ApplicationPaths:
    application_root = Path(root) if root is not None else get_application_root()
    return ApplicationPaths(
        root=application_root,
        config=application_root / "config.json",
        dictionary=application_root / "dictionary",
        workspace=application_root / "workspace",
        log=application_root / "log",
        dual_view=application_root / "dual_view",
    )


def get_config_path(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().config


def get_dictionary_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().dictionary


def get_workspace_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().workspace


def get_log_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().log


def get_dual_view_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().dual_view


def prepare_application_directories(
    paths: ApplicationPaths | None = None,
    *,
    probe_factory: Callable[..., BinaryIO] = tempfile.TemporaryFile,
) -> ApplicationPaths:
    managed_paths = paths or build_application_paths()
    for directory in managed_paths.writable_directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with probe_factory(dir=directory):
                pass
        except OSError as error:
            raise ApplicationDataError(directory, error) from error
    if managed_paths.config.exists():
        try:
            with managed_paths.config.open("a", encoding="utf-8"):
                pass
        except OSError as error:
            raise ApplicationDataError(managed_paths.config, error) from error
    return managed_paths
