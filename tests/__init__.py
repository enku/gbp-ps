"""gbp-ps tests"""
import datetime as dt
import os
from dataclasses import asdict
from functools import wraps
from typing import Any, Callable, Iterable

from django.test import TestCase as DjangoTestCase

from gbp_ps.repository import DjangoRepository, RedisRepository, get_repo
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")

os.environ["GBP_PS_KEY"] = "gbp-ps-test"
os.environ["GBP_PS_KEY_EXPIRATION"] = "3600"


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""

    def setUp(self) -> None:
        super().setUp()
        for backend in [DjangoRepository, RedisRepository]:
            backend().clear()


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


def build_process_dict(build_process: BuildProcess) -> dict[str, Any]:
    """Return BuildProcess as a GraphQL dict"""
    bp_dict = asdict(build_process)
    bp_dict["buildHost"] = bp_dict.pop("build_host")
    bp_dict["id"] = bp_dict.pop("build_id")
    bp_dict["startTime"] = bp_dict.pop("start_time").isoformat()

    return bp_dict


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
