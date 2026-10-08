import json
import os
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from uuid import UUID

import client_init
import config


class _Response:
    def __init__(self, body: dict | str):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        if isinstance(self._body, str):
            return self._body.encode("utf-8")
        return json.dumps(self._body).encode("utf-8")


class ClientInitPayloadTest(unittest.TestCase):
    def test_payload_contains_only_approved_fields(self) -> None:
        payload = client_init.build_startup_payload(
            version="1.2",
            client_id="client-123",
            os_name="Windows",
            os_version="10.0.22631",
            arch="AMD64",
            locale="zh_TW",
        )

        self.assertEqual(
            payload,
            {
                "app": "DotExpress",
                "version": "1.2",
                "client_id": "client-123",
                "os": "Windows",
                "os_version": "10.0.22631",
                "arch": "AMD64",
                "locale": "zh_TW",
                "event": "startup",
            },
        )

    def test_payload_excludes_sensitive_local_data(self) -> None:
        payload = client_init.build_startup_payload(
            version="1.2",
            client_id="client-123",
            os_name="Windows",
            os_version="10.0.22631",
            arch="AMD64",
            locale="zh_TW",
        )

        forbidden_keys = {
            "mac",
            "mac_address",
            "username",
            "user",
            "computer_name",
            "hostname",
            "document",
            "filename",
            "dictionary",
            "path",
        }
        self.assertTrue(forbidden_keys.isdisjoint(payload.keys()))


class ClientInitResponseTest(unittest.TestCase):
    def test_parse_complete_response(self) -> None:
        result = client_init.parse_init_response(
            {
                "version": "1.3",
                "minimum_supported_version": "1.0",
                "download_url": "https://dotexpress.coseeing.org/download",
                "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
                "message": "DotExpress 1.3 is available.",
                "severity": "optional",
            }
        )

        self.assertTrue(result.ok)
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.metadata)
        self.assertEqual(result.metadata.version, "1.3")
        self.assertEqual(result.metadata.minimum_supported_version, "1.0")
        self.assertEqual(result.metadata.severity, "optional")

    def test_parse_malformed_response_returns_failure_result(self) -> None:
        result = client_init.parse_init_response({"version": "1.3"})

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "invalid_response")
        self.assertIsNone(result.metadata)


class ClientInitRequestTest(unittest.TestCase):
    def test_post_init_request_sends_json_and_parses_response(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _Response(
                {
                    "version": "1.3",
                    "minimum_supported_version": "1.0",
                    "download_url": "https://dotexpress.coseeing.org/download",
                    "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
                    "message": "DotExpress 1.3 is available.",
                    "severity": "recommended",
                }
            )

        payload = {
            "app": "DotExpress",
            "version": "1.2",
            "client_id": "client-123",
            "os": "Windows",
            "os_version": "10.0.22631",
            "arch": "AMD64",
            "locale": "zh_TW",
            "event": "startup",
        }

        result = client_init.post_client_init(payload, opener=opener, timeout=2.5)

        self.assertTrue(result.ok)
        self.assertEqual(captured["url"], client_init.CLIENT_INIT_URL)
        self.assertEqual(captured["timeout"], 2.5)
        self.assertEqual(captured["headers"]["Content-type"], "application/json")
        self.assertEqual(captured["body"], payload)
        self.assertEqual(result.metadata.severity, "recommended")

    def test_post_init_request_returns_failure_result_on_network_error(self) -> None:
        def opener(request, timeout):
            raise URLError("offline")

        result = client_init.post_client_init({}, opener=opener)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "request_failed")
        self.assertIsNone(result.metadata)

    def test_run_client_init_builds_payload_from_runtime_values(self) -> None:
        captured = {}

        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _Response(
                {
                    "version": "1.3",
                    "minimum_supported_version": "1.0",
                    "download_url": "https://dotexpress.coseeing.org/download",
                    "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
                    "message": "DotExpress 1.3 is available.",
                    "severity": "optional",
                }
            )

        result = client_init.run_client_init(
            version="1.2",
            client_id_provider=lambda: "client-123",
            os_name_provider=lambda: "Windows",
            os_version_provider=lambda: "10.0.22631",
            arch_provider=lambda: "AMD64",
            locale_provider=lambda: "zh_TW",
            opener=opener,
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            captured["body"],
            {
                "app": "DotExpress",
                "version": "1.2",
                "client_id": "client-123",
                "os": "Windows",
                "os_version": "10.0.22631",
                "arch": "AMD64",
                "locale": "zh_TW",
                "event": "startup",
            },
        )


class _InlineThread:
    """Thread stand-in that runs its target on ``start()``, on the calling thread."""

    def __init__(self, *, target, daemon):
        self.target = target
        self.daemon = daemon
        self.started = False

    def start(self) -> None:
        self.started = True
        self.target()


class _NeverRunThread(_InlineThread):
    """Thread stand-in whose worker never gets to run."""

    def start(self) -> None:
        self.started = True


class ClientInitConfigCharacterizationTest(unittest.TestCase):
    """P2-6 characterization: background client init reads and writes one config file.

    Every test starts client init through ``start``, the only part that changes when the
    config store is injected (P2-6 step 3).
    """

    RESPONSE = {
        "version": "1.3",
        "minimum_supported_version": "1.0",
        "download_url": "https://dotexpress.coseeing.org/download",
        "release_notes_url": "https://dotexpress.coseeing.org/releases/1.3",
        "message": "DotExpress 1.3 is available.",
        "severity": "optional",
    }

    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.config_path = Path(temp_dir.name) / "config.json"
        self.bodies: list[dict] = []
        for patcher in (patch.dict(os.environ), patch.object(config, "_runtime_lang", None)):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop(config.LANG_ENV, None)

    def opener(self, request, timeout):
        self.bodies.append(json.loads(request.data.decode("utf-8")))
        return _Response(self.RESPONSE)

    def start(self, thread_factory=_InlineThread):
        """Start background client init against ``self.config_path`` (today: the module-level config path)."""
        with patch.object(config, "CONFIG_PATH", str(self.config_path)):
            return client_init.start_client_init_background(
                run_client_init=partial(client_init.run_client_init, opener=self.opener),
                thread_factory=thread_factory,
            )

    def test_first_start_creates_saves_and_sends_one_client_id(self) -> None:
        thread = self.start()

        client_id = self.bodies[0]["client_id"]
        UUID(client_id)
        self.assertTrue(thread.daemon)
        self.assertEqual(self.bodies[0]["locale"], "zh_TW")
        self.assertEqual(
            json.loads(self.config_path.read_text(encoding="utf-8")),
            {
                "language_detection": {"charset_maps": config.DEFAULT_CHARSET_MAPS},
                "client": {"id": client_id},
            },
        )

        self.start()

        self.assertEqual([body["client_id"] for body in self.bodies], [client_id, client_id])

    def test_the_configured_language_is_sent_as_locale(self) -> None:
        self.config_path.write_text(json.dumps({"language": "ja"}), encoding="utf-8")

        self.start()

        self.assertEqual(self.bodies[0]["locale"], "ja")

    def test_no_client_id_is_created_before_the_worker_runs(self) -> None:
        thread = self.start(_NeverRunThread)

        self.assertTrue(thread.started)
        self.assertFalse(self.config_path.exists())
        self.assertEqual(self.bodies, [])


if __name__ == "__main__":
    unittest.main()
