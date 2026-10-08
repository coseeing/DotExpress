"""Keep tests from appending to the real application log files.

``log.get_logger`` binds a ``FileHandler`` in ``<root>/log/`` when a module first
creates its logger, so a test that makes production code log would write there.
"""

import logging
from collections.abc import Callable


def isolate_file_logs(*names: str) -> Callable[[], None]:
    """Swap the handlers of the named loggers for a ``NullHandler``.

    Sets ``propagate`` to ``False`` as well. Works for loggers that do not exist
    yet: ``log.get_logger`` then finds a handler and adds no file handler.
    Returns a function that puts back the exact previous handlers and ``propagate``.
    """
    saved = []
    for name in names:
        logger = logging.getLogger(name)
        saved.append((logger, list(logger.handlers), logger.propagate))
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.addHandler(logging.NullHandler())
        logger.propagate = False

    def restore() -> None:
        for logger, handlers, propagate in reversed(saved):
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
            for handler in handlers:
                logger.addHandler(handler)
            logger.propagate = propagate

    return restore
