"""gbp-ps tests"""
# pylint: disable=missing-docstring
import datetime as dt
import os
import tempfile
from functools import wraps
from typing import Any, Callable, Iterable
from unittest import mock

from django.test import TestCase as DjangoTestCase

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""

    def setUp(self) -> None:
        super().setUp()

        tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(tempdir.cleanup)
        gbp_settings = {
            "BUILD_PUBLISHER_JENKINS_BASE_URL": "http://jenkins.invalid",
            "BUILD_PUBLISHER_STORAGE_PATH": tempdir.name,
        }
        patcher = mock.patch.dict(os.environ, gbp_settings)
        self.addCleanup(patcher.stop)
        patcher.start()
        self.repo = Repo(Settings.from_environ())


def make_build_process(**kwargs: Any) -> BuildProcess:
    """Create (and save) a BuildProcess"""
    settings = Settings.from_environ()
    add_to_repo = kwargs.pop("add_to_repo", True)
    update_repo = kwargs.pop("update_repo", False)
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
        repo = Repo(settings)
        if update_repo:
            add_or_update_process(repo, build_process)
        else:
            repo.add_process(build_process)

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
