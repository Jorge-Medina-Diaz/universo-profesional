"""Result[T, E] — explicit success/failure type for application services.

Used at the boundary between application use cases and the interfaces layer
to make error paths first-class. The HTTP/MCP interfaces map `Failure` to
appropriate responses, never propagating raw exceptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, NoReturn, TypeVar, overload

from .errors import DomainError

T = TypeVar("T")
E = TypeVar("E", bound=DomainError)


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    value: T

    # `Literal[True]`/`Literal[False]` (rather than plain `bool`) makes
    # Success/Failure a discriminated union, so `if result.is_failure: ...`
    # actually NARROWS `Result` for the type checker. With `bool` every
    # `result.value` after a guard was a union-attr error, which is what
    # pushed callers toward `# type: ignore` instead of real narrowing.
    @property
    def is_success(self) -> Literal[True]:
        return True

    @property
    def is_failure(self) -> Literal[False]:
        return False

    def unwrap(self) -> T:
        return self.value


@dataclass(frozen=True, slots=True)
class Failure(Generic[E]):
    error: E

    @property
    def is_success(self) -> Literal[False]:
        return False

    @property
    def is_failure(self) -> Literal[True]:
        return True

    def unwrap(self) -> NoReturn:
        raise self.error


Result = Success[T] | Failure[E]


@overload
def ok(value: T) -> Success[T]: ...
@overload
def ok() -> Success[None]: ...


def ok(value: T | None = None) -> Success[T] | Success[None]:
    if value is None:
        return Success(None)
    return Success(value)


def err(error: E) -> Failure[E]:
    return Failure(error)
