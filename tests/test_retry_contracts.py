"""Exercise retry and circuit state using real file operations."""

from datetime import datetime, timedelta

import pytest
from tests.utility_fixtures import isolated_utility_logs as isolated_utility_logs

from blake.utils.error_handling import (
    BlakeError,
    CircuitBreaker,
    ErrorRecovery,
    RetryConfig,
    retry_on_failure,
)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.asyncio
async def test_retry_preserves_arguments_and_attempts(tmp_path, asynchronous):
    recovery = ErrorRecovery(tmp_path / "logs")
    attempts = tmp_path / "attempts.txt"
    source = tmp_path / "source.txt"

    def read(path, *, encoding):
        with attempts.open("a") as stream:
            stream.write("attempt\n")
        if len(attempts.read_text().splitlines()) == 3:
            path.write_text("recovered")
        return path.read_text(encoding=encoding)

    async def async_read(*args, **kwargs):
        return read(*args, **kwargs)

    config = RetryConfig(base_delay=0.001, max_delay=0.001, jitter=False)
    kwargs = dict(retry_config=config, exceptions=(FileNotFoundError,), encoding="utf8")
    if asynchronous:
        result = await recovery.retry_async(async_read, source, **kwargs)
    else:
        result = recovery.retry_sync(read, source, **kwargs)
    assert result == "recovered"
    assert attempts.read_text() == "attempt\nattempt\nattempt\n"
    assert source.read_text() == "recovered"


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("retryable", [False, True])
@pytest.mark.asyncio
async def test_retry_exhaustion_and_exception_selection(
    tmp_path, asynchronous, retryable
):
    recovery = ErrorRecovery(tmp_path / "logs")
    attempts = []
    error = FileNotFoundError("retained missing input")

    def fail():
        attempts.append(len(attempts))
        raise error

    async def async_fail():
        return fail()

    config = RetryConfig(max_attempts=2, base_delay=0, jitter=True)
    exceptions = (OSError,) if retryable else (ValueError,)
    with pytest.raises(FileNotFoundError) as caught:
        if asynchronous:
            await recovery.retry_async(
                async_fail, retry_config=config, exceptions=exceptions
            )
        else:
            recovery.retry_sync(fail, retry_config=config, exceptions=exceptions)
    assert caught.value is error
    assert len(attempts) == (2 if retryable else 1)


@pytest.mark.asyncio
async def test_default_retry_and_decorators_keep_results(tmp_path):
    recovery = ErrorRecovery(tmp_path / "logs")

    def read(path):
        return path.read_text()

    async def async_read(path):
        return read(path)

    path = tmp_path / "source"
    path.write_text("retained")
    assert recovery.retry_sync(read, path) == "retained"
    assert await recovery.retry_async(async_read, path) == "retained"
    wrapped = retry_on_failure(RetryConfig(max_attempts=1))(read)
    async_wrapped = retry_on_failure(RetryConfig(max_attempts=1))(async_read)
    assert wrapped.__name__ == "read"
    assert async_wrapped.__name__ == "async_read"
    assert wrapped(path) == "retained"
    assert await async_wrapped(path) == "retained"
    with pytest.raises(FileNotFoundError):
        wrapped(tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        await async_wrapped(tmp_path / "absent")
    logs = list((tmp_path / "logs").glob("blake*.log"))
    assert logs and any("async_read" in path.read_text() for path in logs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_attempts": 0},
        {"max_attempts": -1},
        {"base_delay": -1},
        {"max_delay": -1},
        {"exponential_base": -1},
        {"max_attempts": 1.5},
        {"base_delay": float("nan")},
        {"max_delay": float("inf")},
    ],
)
def test_invalid_retry_policy_fails_at_configuration(kwargs):
    with pytest.raises(ValueError):
        RetryConfig(**kwargs)


def test_recovery_log_appends_original_error_and_context(tmp_path):
    recovery = ErrorRecovery(tmp_path)
    try:
        (tmp_path / "missing").read_text()
    except OSError as error:
        recovery.log_error_recovery(
            error, "restore snapshot", False, {"path": tmp_path}
        )
        first = recovery.error_log.read_text()
        recovery.log_error_recovery(error, "retry restore", True)
    result = recovery.error_log.read_text()
    assert result.startswith(first)
    assert "FileNotFoundError" in first
    assert "restore snapshot" in first and str(tmp_path) in first
    assert "retry restore" in result[len(first) :]


def test_circuit_failure_refusal_and_reset_preserve_side_effects(tmp_path):
    breaker = CircuitBreaker(failure_threshold=2, expected_exception=OSError)
    source = tmp_path / "source"
    for expected_count in (1, 2):
        with pytest.raises(FileNotFoundError):
            breaker.call(source.read_text)
        assert breaker.failure_count == expected_count
    assert breaker.state == "OPEN"
    with pytest.raises(BlakeError, match="OPEN"):
        breaker.call(source.write_text, "must not appear")
    assert not source.exists()
    breaker.last_failure_time = datetime.now() - timedelta(seconds=61)
    assert breaker.call(source.write_text, "restored") == 8
    assert breaker.state == "CLOSED" and breaker.failure_count == 0
    assert source.read_text() == "restored"


def test_circuit_elapsed_days_and_unexpected_exception(tmp_path):
    breaker = CircuitBreaker(expected_exception=OSError)
    assert breaker._should_attempt_reset()
    breaker.last_failure_time = datetime.now() - timedelta(days=1, seconds=1)
    assert breaker._should_attempt_reset(), "Elapsed days must count toward recovery"
    with pytest.raises(ValueError):
        breaker.call(int, "invalid")
    assert breaker.failure_count == 0 and breaker.state == "CLOSED"


def test_half_open_failure_reopens(tmp_path):
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
    for _ in range(2):
        with pytest.raises(FileNotFoundError):
            breaker.call((tmp_path / "missing").read_text)
        assert breaker.state == "OPEN"
    assert breaker.failure_count == 2
