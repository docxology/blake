"""Real filesystem and logging ownership for utility tests."""

import logging
import os

import pytest


@pytest.fixture(autouse=True)
def isolated_utility_logs(tmp_path):
    previous_directory = os.getcwd()
    previous = {
        name: (list(logger.handlers), logger.level, logger.propagate)
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    os.chdir(tmp_path)
    try:
        yield
    finally:
        os.chdir(previous_directory)
        for name, logger in list(logging.Logger.manager.loggerDict.items()):
            if not isinstance(logger, logging.Logger):
                continue
            handlers, level, propagate = previous.get(name, ([], logging.NOTSET, True))
            for handler in logger.handlers:
                if handler not in handlers:
                    handler.close()
            logger.handlers[:] = handlers
            logger.setLevel(level)
            logger.propagate = propagate
