from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class BrowserDefinition:
    executable_names: tuple[str, ...]
    installed_paths: tuple[tuple[str, tuple[str, ...]], ...]


BROWSER_ORDER = ("chrome", "edge", "firefox")
_DEFAULT_STARTFILE = object()
BROWSERS = {
    "chrome": BrowserDefinition(
        executable_names=("chrome.exe", "chrome"),
        installed_paths=(
            ("LOCALAPPDATA", ("Google", "Chrome", "Application", "chrome.exe")),
            ("PROGRAMFILES", ("Google", "Chrome", "Application", "chrome.exe")),
            ("PROGRAMFILES(X86)", ("Google", "Chrome", "Application", "chrome.exe")),
        ),
    ),
    "edge": BrowserDefinition(
        executable_names=("msedge.exe", "msedge"),
        installed_paths=(
            ("LOCALAPPDATA", ("Microsoft", "Edge", "Application", "msedge.exe")),
            ("PROGRAMFILES", ("Microsoft", "Edge", "Application", "msedge.exe")),
            ("PROGRAMFILES(X86)", ("Microsoft", "Edge", "Application", "msedge.exe")),
        ),
    ),
    "firefox": BrowserDefinition(
        executable_names=("firefox.exe", "firefox"),
        installed_paths=(
            ("LOCALAPPDATA", ("Mozilla Firefox", "firefox.exe")),
            ("PROGRAMFILES", ("Mozilla Firefox", "firefox.exe")),
            ("PROGRAMFILES(X86)", ("Mozilla Firefox", "firefox.exe")),
        ),
    ),
}


def find_browser_executable(
    browser: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    environ: Mapping[str, str] = os.environ,
) -> Path | None:
    definition = BROWSERS[browser]
    for executable_name in definition.executable_names:
        located = which(executable_name)
        if located:
            return Path(located)
    for environment_name, relative_parts in definition.installed_paths:
        base = environ.get(environment_name)
        if not base:
            continue
        candidate = Path(base).joinpath(*relative_parts)
        if candidate.is_file():
            return candidate
    return None


def build_browser_command(
    browser: str,
    executable: Path,
    html_path: Path,
    window_size: tuple[int, int],
) -> list[str]:
    width, height = window_size
    uri = html_path.resolve().as_uri()
    if browser in ("chrome", "edge"):
        return [str(executable), "--new-window", f"--window-size={width},{height}", uri]
    if browser == "firefox":
        return [str(executable), "-new-window", uri, "-width", str(width), "-height", str(height)]
    raise ValueError(f'Unsupported browser: "{browser}"')


def open_html_in_browser(
    html_path: Path,
    window_size: tuple[int, int],
    *,
    finder: Callable[[str], Path | None] = find_browser_executable,
    popen: Callable[[list[str]], object] = subprocess.Popen,
    startfile: Callable[[str], object] | None | object = _DEFAULT_STARTFILE,
) -> str:
    for browser in BROWSER_ORDER:
        executable = finder(browser)
        if executable is None:
            continue
        try:
            popen(build_browser_command(browser, executable, html_path, window_size))
        except OSError:
            continue
        return browser

    fallback = getattr(os, "startfile", None) if startfile is _DEFAULT_STARTFILE else startfile
    if fallback is None:
        raise OSError("No supported browser or system HTML opener is available.")
    fallback(str(html_path.resolve()))
    return "system"
