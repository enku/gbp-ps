"""gbp-ps tests"""
import datetime as dt
from dataclasses import asdict
from typing import Any

from django.test import TestCase as DjangoTestCase

from gbp_ps.repository import Repository
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""

    # Nothing here yet


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
        Repository().add_process(build_process)

    return build_process


def build_process_dict(build_process: BuildProcess) -> dict[str, Any]:
    """Return BuildProcess as a GraphQL dict"""
    bp_dict = asdict(build_process)
    bp_dict["buildHost"] = bp_dict.pop("build_host")
    bp_dict["id"] = bp_dict.pop("build_id")
    bp_dict["startTime"] = bp_dict.pop("start_time").isoformat()

    return bp_dict
