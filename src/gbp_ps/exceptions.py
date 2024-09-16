"""gbp-ps exceptions"""

from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")
RETURN_EXCEPTION = object()


class GBPPSException(Exception):
    """Base exception for gbp-ps"""


class RecordNotFoundError(GBPPSException, LookupError):
    """Raised when a record is not found in the repository"""


class RecordAlreadyExists(GBPPSException):
    """Raised when adding a record that already exists in the repository"""


class UpdateNotAllowedError(GBPPSException):
    """Raised when an update is not allowed"""


def swallow_exception(
    *exceptions: type[BaseException], returns: Any = RETURN_EXCEPTION
) -> Callable[[Callable[P, T]], Callable[P, T | Any]]:
    """Swallow the given exceptions"""

    def decorator(func: Callable[P, T]) -> Callable[P, T | Any]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Any:
            try:
                return func(*args, **kwargs)
            except exceptions as exception:
                if returns is RETURN_EXCEPTION:
                    return exception
                return returns

        return wrapper

    return decorator
