import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from server.app.main import create_app
from server.app.models import Client, ClientEvent


def _payload(**overrides):
    data = {
        "app": "DotExpress",
        "version": "1.2",
        "client_id": "client-123",
        "os": "Windows",
        "os_version": "10.0.22631",
        "arch": "AMD64",
        "locale": "zh_TW",
        "event": "startup",
    }
    data.update(overrides)
    return data


class ClientInitServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "server.sqlite3"
        self.app = create_app(database_url=f"sqlite:///{db_path}")
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _session(self):
        return self.app.state.SessionLocal()

    def test_database_uses_general_events_table(self) -> None:
        table_names = set(inspect(self.app.state.engine).get_table_names())

        self.assertIn("events", table_names)
        self.assertNotIn("client_startup_events", table_names)

    def test_valid_request_persists_new_client_and_event(self) -> None:
        response = self.client.post("/client/init", json=_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json().keys()),
            {
                "version",
                "minimum_supported_version",
                "download_url",
                "release_notes_url",
                "message",
                "severity",
            },
        )
        self.assertIn(response.json()["severity"], {"optional", "recommended", "required"})

        with self._session() as session:
            clients = session.query(Client).all()
            events = session.query(ClientEvent).all()

        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0].client_id, "client-123")
        self.assertEqual(clients[0].last_app_version, "1.2")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].client_id, "client-123")
        self.assertEqual(events[0].event, "startup")

    def test_existing_client_is_updated_and_event_is_recorded(self) -> None:
        self.client.post("/client/init", json=_payload())
        response = self.client.post(
            "/client/init",
            json=_payload(version="1.3", os="Linux", os_version="6.8", locale="en_US"),
        )

        self.assertEqual(response.status_code, 200)
        with self._session() as session:
            clients = session.query(Client).all()
            events = session.query(ClientEvent).order_by(ClientEvent.id).all()

        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0].last_app_version, "1.3")
        self.assertEqual(clients[0].last_os, "Linux")
        self.assertEqual(clients[0].last_os_version, "6.8")
        self.assertEqual(clients[0].last_locale, "en_US")
        self.assertEqual(len(events), 2)

    def test_invalid_request_is_rejected(self) -> None:
        response = self.client.post("/client/init", json={"app": "DotExpress"})

        self.assertEqual(response.status_code, 422)

    def test_statistics_endpoint_is_not_exposed(self) -> None:
        response = self.client.get("/admin/stats")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
