import logging
import os
from openrelik_worker_common.logging import Logger
import pytest_structlog


def log_plain():
    os.environ["LOG_TYPE"] = ""
    logger = Logger().get_logger(__name__)
    logger.info("test")


def log_wrap():
    os.environ["LOG_TYPE"] = ""
    logger = Logger().get_logger(name=__name__, wrap_logger=logging.getLogger())
    logger.info("test")


def log_bind_structlog():
    os.environ["LOG_TYPE"] = "structlog"
    log = Logger()
    logger = log.get_logger(__name__)
    log.bind(workflow_id=12345)
    logger.info("test")


def log_structlog():
    os.environ["LOG_TYPE"] = "structlog"
    logger = Logger().get_logger(__name__)
    logger.info("test")


def test_structlog(log: pytest_structlog.StructuredLogCapture):
    log_structlog()
    assert log.has("test", level="info")


def test_bind_structlog(log: pytest_structlog.StructuredLogCapture):
    log_bind_structlog()
    assert log.has("test", level="info", workflow_id=12345)


def test_get_plain_python(caplog):
    caplog.set_level(logging.INFO)
    log_plain()
    assert "INFO     tests.test_logging:test_logging.py:10 test\n" == caplog.text


def test_get_wrap(log: pytest_structlog.StructuredLogCapture):
    log_wrap()
    assert log.has("test", level="info")
