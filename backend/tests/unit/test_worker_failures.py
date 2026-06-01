"""Unit tests for the fail-loud background-task policy (pure, no DB)."""
from __future__ import annotations

import asyncio

import pytest
from arq import Retry

from src.shared.worker_failures import backoff_seconds, handle_task_exception


def test_backoff_is_monotonic_and_capped():
    assert backoff_seconds(1) <= backoff_seconds(3)
    assert backoff_seconds(100) <= 300
    assert backoff_seconds(1) >= 1


def test_connection_error_is_transient_retry():
    with pytest.raises(Retry):
        handle_task_exception({"job_try": 1}, ConnectionError("boom"), task="t")


def test_timeout_is_transient_retry():
    with pytest.raises(Retry):
        handle_task_exception({"job_try": 2}, asyncio.TimeoutError(), task="t")


def test_terminal_error_reraises_original():
    # A programming/data error is not transient: it must surface (fail loud),
    # not be swallowed or retried forever.
    with pytest.raises(ValueError, match="bad data"):
        handle_task_exception({"job_try": 1}, ValueError("bad data"), task="t")
