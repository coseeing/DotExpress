from sqlalchemy.orm import Session

from .models import Client, ClientStartupEvent, utcnow
from .schemas import ClientInitRequest


def record_client_init(db: Session, payload: ClientInitRequest) -> None:
    now = utcnow()
    client = db.query(Client).filter(Client.client_id == payload.client_id).one_or_none()
    if client is None:
        client = Client(
            client_id=payload.client_id,
            first_seen_at=now,
            last_seen_at=now,
            last_app_version=payload.version,
            last_os=payload.os,
            last_os_version=payload.os_version,
            last_arch=payload.arch,
            last_locale=payload.locale,
        )
        db.add(client)
    else:
        client.last_seen_at = now
        client.last_app_version = payload.version
        client.last_os = payload.os
        client.last_os_version = payload.os_version
        client.last_arch = payload.arch
        client.last_locale = payload.locale

    db.add(
        ClientStartupEvent(
            client_id=payload.client_id,
            app=payload.app,
            version=payload.version,
            os=payload.os,
            os_version=payload.os_version,
            arch=payload.arch,
            locale=payload.locale,
            event=payload.event,
            received_at=now,
        )
    )
    db.commit()
