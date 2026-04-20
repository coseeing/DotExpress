from collections.abc import Generator

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from .config import Settings, build_version_response
from .crud import record_client_init
from .database import create_engine_for_url, create_session_factory, init_database
from .schemas import ClientInitRequest, ClientInitResponse


def create_app(database_url: str | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    if database_url is not None:
        settings = Settings(
            database_url=database_url,
            version=settings.version,
            minimum_supported_version=settings.minimum_supported_version,
            download_url=settings.download_url,
            release_notes_url=settings.release_notes_url,
            message=settings.message,
            severity=settings.severity,
        )

    engine = create_engine_for_url(settings.database_url)
    init_database(engine)
    SessionLocal = create_session_factory(engine)

    app = FastAPI(title="DotExpress Client Init Server")
    app.state.settings = settings
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    def get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @app.post("/client/init", response_model=ClientInitResponse)
    def client_init(payload: ClientInitRequest, db: Session = Depends(get_db)):
        record_client_init(db, payload)
        return build_version_response(settings)

    return app


app = create_app()
