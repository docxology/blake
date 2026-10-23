"""Explicit fallback contracts retain success values and propagate unrelated errors."""

from datetime import datetime
import json

import pytest
from tests.utility_fixtures import isolated_utility_logs as isolated_utility_logs

from blake.utils.error_handling import (
    APIError,
    AnalysisError,
    DownloadError,
    ValidationError,
    handle_graceful_degradation,
    safe_file_operation,
    safe_json_loads,
    validate_input,
)


@pytest.mark.parametrize(
    "error_type", [APIError, AnalysisError, DownloadError, ValidationError]
)
def test_error_context_and_timestamp(error_type):
    before = datetime.now()
    error = error_type("source unavailable", error_code="INPUT", context={"id": "x"})
    assert str(error) == "source unavailable"
    assert error.error_code == "INPUT" and error.context == {"id": "x"}
    assert before <= error.timestamp <= datetime.now()
    assert error_type("empty context").context == {}


@pytest.mark.parametrize("log_errors", [True, False])
@pytest.mark.asyncio
async def test_explicit_fallback_and_success(tmp_path, log_errors):
    fallback = {"unavailable": True}

    @handle_graceful_degradation(fallback, log_errors=log_errors)
    def read(path):
        return path.read_text()

    @handle_graceful_degradation(fallback, log_errors=log_errors)
    async def async_read(path):
        return path.read_text()

    path = tmp_path / "source"
    assert read(path) is fallback
    assert await async_read(path) is fallback
    path.write_text("original")
    assert read(path) == "original"
    assert await async_read(path) == "original"
    assert read.__name__ == "read" and async_read.__name__ == "async_read"


def test_validation_and_json_fallback_are_explicit():
    original = ["retained"]
    assert validate_input(original, bool) is original
    with pytest.raises(ValidationError, match="empty") as caught:
        validate_input([], bool, "empty")
    assert caught.value.context == {"data": "[]"}
    assert safe_json_loads('{"text":"retained"}') == {"text": "retained"}
    assert safe_json_loads("null", original) is None
    assert safe_json_loads("{", original) is original
    assert safe_json_loads(None, original) is original


def test_safe_file_operation_keeps_success_and_non_io_errors(tmp_path):
    path = tmp_path / "source.json"
    path.write_text('{"retained":true}')

    def load(source, *, encoding):
        return json.loads(source.read_text(encoding=encoding))

    assert safe_file_operation(load, path, encoding="utf8") == {"retained": True}
    fallback = object()
    assert (
        safe_file_operation(load, tmp_path / "absent", fallback, encoding="utf8")
        is fallback
    )
    path.write_text("invalid JSON")
    with pytest.raises(json.JSONDecodeError):
        safe_file_operation(load, path, fallback, encoding="utf8")
    assert path.read_text() == "invalid JSON"
