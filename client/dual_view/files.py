from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from collections.abc import Callable

from app_paths import get_dual_view_directory


OWNED_HTML_PATTERN = "dual-view-*.html"


def _new_token() -> str:
    return uuid4().hex


def write_dual_view_html(
    content: str,
    directory: Path | None = None,
    *,
    token_factory: Callable[[], str] = _new_token,
) -> Path:
    target_directory = get_dual_view_directory(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / f"dual-view-{token_factory()}.html"
    target.write_text(content, encoding="utf-8")
    return target


def cleanup_dual_view_html(directory: Path | None = None) -> None:
    target_directory = get_dual_view_directory(directory)
    if not target_directory.exists():
        return
    for path in target_directory.glob(OWNED_HTML_PATTERN):
        if path.is_file():
            path.unlink()
