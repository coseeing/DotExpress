import json
import unittest
from urllib.error import URLError

import client_init


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


if __name__ == "__main__":
    unittest.main()
