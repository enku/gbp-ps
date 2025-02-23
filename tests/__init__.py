"""gbp-ps tests"""

# pylint: disable=missing-docstring
import argparse
import datetime as dt
import shlex
from functools import wraps
from typing import Any, Callable, Iterable, TypeVar

import gbpcli
from django.test import TestCase as DjangoTestCase
from gbpcli.config import Config
from gbpcli.types import Console

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""


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
