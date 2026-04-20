from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "dotexpress.sqlite3"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    version: str = "1.3"
    minimum_supported_version: str = "1.0"
    download_url: str = "https://dotexpress.coseeing.org/download"
    release_notes_url: str = "https://dotexpress.coseeing.org/releases/1.3"
    message: str = "DotExpress 1.3 is available."
    severity: str = "optional"


def build_version_response(settings: Settings) -> dict[str, str]:
    return {
        "version": settings.version,
        "minimum_supported_version": settings.minimum_supported_version,
        "download_url": settings.download_url,
        "release_notes_url": settings.release_notes_url,
        "message": settings.message,
        "severity": settings.severity,
    }
