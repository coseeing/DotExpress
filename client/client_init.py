from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import platform
import threading
import traceback
import urllib.error
import urllib.request
from urllib.error import URLError

import about
from config import get_lang, get_or_create_client_id
from log import get_logger

logger = get_logger("dotexpress.client_init", "log/init.log")

CLIENT_INIT_URL = "https://dotexpress.coseeing.org/client/init"

DEFAULT_TIMEOUT = 3.0
_REQUIRED_RESPONSE_FIELDS = {
    "version",
    "minimum_supported_version",
    "download_url",
    "release_notes_url",
    "message",
    "severity",
}
_ALLOWED_SEVERITIES = {"optional", "recommended", "required"}


@dataclass(frozen=True)
class VersionMetadata:
    version: str
    minimum_supported_version: str
    download_url: str
    release_notes_url: str
    message: str
    severity: str


@dataclass(frozen=True)
class ClientInitResult:
    ok: bool
    metadata: VersionMetadata | None = None
    error: str | None = None


def build_startup_payload(
    *,
    version: str,
    client_id: str,
    os_name: str,
    os_version: str,
    arch: str,
    locale: str,
) -> dict[str, str]:
    return {
        "app": "DotExpress",
        "version": version,
        "client_id": client_id,
        "os": os_name,
        "os_version": os_version,
        "arch": arch,
        "locale": locale,
        "event": "startup",
    }


def parse_init_response(data: object) -> ClientInitResult:
    if not isinstance(data, dict):
        return ClientInitResult(ok=False, error="invalid_response")
    if not _REQUIRED_RESPONSE_FIELDS.issubset(data.keys()):
        return ClientInitResult(ok=False, error="invalid_response")
    values = {key: data[key] for key in _REQUIRED_RESPONSE_FIELDS}
    if not all(isinstance(value, str) and value for value in values.values()):
        return ClientInitResult(ok=False, error="invalid_response")
    if values["severity"] not in _ALLOWED_SEVERITIES:
        return ClientInitResult(ok=False, error="invalid_response")
    return ClientInitResult(
        ok=True,
        metadata=VersionMetadata(
            version=values["version"],
            minimum_supported_version=values["minimum_supported_version"],
            download_url=values["download_url"],
            release_notes_url=values["release_notes_url"],
            message=values["message"],
            severity=values["severity"],
        ),
    )


def post_client_init(
    payload: dict[str, str],
    *,
    opener=urllib.request.urlopen,
    timeout: float = DEFAULT_TIMEOUT,
) -> ClientInitResult:
    request_body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        CLIENT_INIT_URL,
        data=request_body,
        headers={
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "curl/8.0.0",
        },
        method="POST",
    )

    try:
        with opener(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
            data = json.loads(response_text)
            return parse_init_response(data)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")

        logger.exception(
            "HTTPError occurred | code=%s url=%s body=%r",
            e.code,
            e.url,
            error_body,
        )

        return ClientInitResult(
            ok=False,
            error=f"http_error_{e.code}",
        )

    except (OSError, URLError, TimeoutError):
        logger.exception("Network error during client init")
        return ClientInitResult(ok=False, error="request_failed")

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception("Invalid response format during client init")
        return ClientInitResult(ok=False, error="invalid_response")


def run_client_init(
    *,
    version: str = about.version,
    client_id_provider=get_or_create_client_id,
    os_name_provider=platform.system,
    os_version_provider=platform.version,
    arch_provider=platform.machine,
    locale_provider=get_lang,
    opener=urllib.request.urlopen,
    timeout: float = DEFAULT_TIMEOUT,
) -> ClientInitResult:
    payload = build_startup_payload(
        version=version,
        client_id=client_id_provider(),
        os_name=os_name_provider(),
        os_version=os_version_provider(),
        arch=arch_provider(),
        locale=locale_provider(),
    )
    return post_client_init(payload, opener=opener, timeout=timeout)


def start_client_init_background(
    *,
    run_client_init=run_client_init,
    thread_factory=threading.Thread,
):
    def worker():
        try:
            run_client_init()
        except Exception:
            pass

    thread = thread_factory(target=worker, daemon=True)
    thread.start()
    return thread
