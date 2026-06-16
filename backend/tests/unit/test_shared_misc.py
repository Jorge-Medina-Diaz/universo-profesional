"""Unit tests for small shared modules with missing coverage."""
from __future__ import annotations

from src.shared.errors import DomainError, ValidationError
from src.shared.result import Failure, Success, ok, err
from src.shared.value_objects import Email


class TestErrors:
    def test_domain_error_to_problem(self):
        e = DomainError("oops", details={"x": 1})
        problem = e.to_problem()
        assert problem["title"] == "oops"
        assert problem["code"] == "domain.error"
        assert problem["status"] == 400
        assert problem["details"] == {"x": 1}

    def test_validation_error_to_problem(self):
        e = ValidationError("bad")
        problem = e.to_problem()
        assert problem["code"] == "validation.failed"
        assert problem["status"] == 422


class TestResult:
    def test_success_properties(self):
        s = Success(42)
        assert s.is_success is True
        assert s.is_failure is False
        assert s.unwrap() == 42

    def test_failure_properties(self):
        f = Failure(ValidationError("bad"))
        assert f.is_success is False
        assert f.is_failure is True
        with pytest.raises(ValidationError):
            f.unwrap()

    def test_ok_with_value(self):
        assert ok(5).value == 5

    def test_ok_without_value(self):
        assert ok().value is None

    def test_err(self):
        e = ValidationError("x")
        assert err(e).error is e


import pytest


class TestValueObjectsStr:
    def test_email_str(self):
        e = Email.parse("test@example.com")
        assert str(e) == "test@example.com"
