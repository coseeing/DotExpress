import logging
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import log


class FileLoggerTest(unittest.TestCase):
    def test_logger_defers_file_creation_and_uses_application_log_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "log"
            logger_name = f"dotexpress.test.{uuid4().hex}"
            with patch.object(log, "get_log_directory", return_value=log_dir):
                logger = log.get_logger(logger_name, "sample.log")

            handler = next(item for item in logger.handlers if isinstance(item, logging.FileHandler))
            self.assertEqual(Path(handler.baseFilename), log_dir / "sample.log")
            self.assertIsNone(handler.stream)
            self.assertFalse(log_dir.exists())

            log_dir.mkdir()
            logger.error("written after validation")
            self.assertTrue((log_dir / "sample.log").is_file())

            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
