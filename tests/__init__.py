"""gbp-ps tests"""
# pylint: disable=missing-docstring
import datetime as dt
from functools import wraps
from typing import Any, Callable, Iterable

from django.test import TestCase as DjangoTestCase

from gbp_ps.repository import get_repo
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""


def make_build_process(**kwargs: Any) -> BuildProcess:
    """Create (and save) a BuildProcess"""
    add_to_repo = kwargs.pop("add_to_repo", True)
    attrs: dict[str, Any] = {
        "build_host": "jenkins",
        "build_id": "1031",
        "machine": "babette",
        "package": "sys-apps/systemd-254.5-r1",
        "phase": "compile",
        "start_time": dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
    }
    attrs.update(**kwargs)
    build_process = BuildProcess(**attrs)
    if add_to_repo:
        get_repo().add_process(build_process)

    return build_process


def parametrized(lists_of_args: Iterable[Iterable[Any]]) -> Callable:
    """Parameterized test"""

    def dec(func: Callable):
        @wraps(func)
        def wrapper(self: TestCase, *args: Any, **kwargs: Any) -> None:
            for list_of_args in lists_of_args:
                name = ",".join(str(i) for i in list_of_args)
                with self.subTest(name):
                    func(self, *args, *list_of_args, **kwargs)

        return wrapper

    return dec
