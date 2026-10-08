import io
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import log
from tests.file_log_isolation import isolate_file_logs


def forget_logger(name: str) -> None:
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.propagate = True


class FileLogIsolationTest(unittest.TestCase):
    def test_swaps_handlers_for_a_null_handler_and_restores_them_exactly(self) -> None:
        name = "tests.file_log_isolation.configured"
        self.addCleanup(forget_logger, name)
        logger = logging.getLogger(name)
        stream = io.StringIO()
        first = logging.StreamHandler(stream)
        second = logging.StreamHandler(stream)
        logger.addHandler(first)
        logger.addHandler(second)
        logger.propagate = True

        restore = isolate_file_logs(name)
        logger.error("hidden")
        isolated = (list(logger.handlers), logger.propagate)
        restore()

        self.assertEqual(len(isolated[0]), 1)
        self.assertIsInstance(isolated[0][0], logging.NullHandler)
        self.assertIs(isolated[1], False)
        self.assertEqual(stream.getvalue(), "")
        self.assertEqual(logger.handlers, [first, second])
        self.assertIs(logger.propagate, True)

    def test_logger_without_handlers_gets_no_file_while_isolated(self) -> None:
        name = "tests.file_log_isolation.unconfigured"
        self.addCleanup(forget_logger, name)
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(log, "_log_directory", return_value=folder))

        restore = isolate_file_logs(name)
        logger = log.get_logger(name, "isolated.log")
        logger.error("hidden")
        restore()

        self.assertFalse((folder / "isolated.log").exists())
        self.assertEqual(logger.handlers, [])
        self.assertIs(logger.propagate, True)


if __name__ == "__main__":
    unittest.main()
