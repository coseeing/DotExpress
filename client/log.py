import logging
from pathlib import Path

from app_paths import build_application_paths


def _log_directory() -> Path:
    return build_application_paths().log


def get_logger(
    name: str,
    filename: str = "init.log",
    level: int = logging.ERROR,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = logging.FileHandler(
            _log_directory() / Path(filename).name,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(file_handler)
        logger.propagate = False

    return logger
