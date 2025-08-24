# pylint: disable=missing-docstring,too-few-public-methods,redefined-outer-name
import datetime as dt
import os
from typing import Any

import factory
import gbp_testkit.fixtures as testkit
from django.test import TestCase as DjangoTestCase
from unittest_fixtures import Fixtures, fixture

from gbp_ps.repository import Repo, RepositoryType, add_or_update_process, sqlite
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

PACKAGES = (
    "media-libs/tiff-4.7.0",
    "app-misc/pax-utils-1.3.8",
    "media-libs/x265-3.6-r1",
    "sys-fs/cryptsetup-2.7.5-r1",
    "sys-devel/gcc-14.2.1_p20240921",
    "sys-fs/cryptsetup-2.7.5",
)


class TestCase(DjangoTestCase):
    """Custom TestCase for gbp-ps tests"""


class BuildProcessFactory(factory.Factory):
    class Meta:
        model = BuildProcess

    machine = "babette"
    build_id = factory.Sequence(str)
    build_host = "builder"
    package = factory.Iterator(PACKAGES)
    phase = factory.Iterator(BuildProcess.build_phases)
    start_time = factory.LazyFunction(
        lambda: dt.datetime.now(tz=dt.UTC).replace(microsecond=0)
    )


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


@fixture()
def build_process(_fixtures: Fixtures, **options: Any) -> BuildProcess:
    return BuildProcessFactory(**options)


@fixture(testkit.tmpdir)
def tempdb(fixtures: Fixtures) -> str:
    return f"{fixtures.tmpdir}/processes.db"


@fixture(testkit.environ)
def settings(fixtures: Fixtures) -> Settings:
    os.environ["GBP_PS_SQLITE_DATABASE"] = f"{fixtures.tmpdir}/db.sqlite"

    return Settings.from_environ()


@fixture(settings)
def repo(fixtures: Fixtures) -> RepositoryType:
    return Repo(fixtures.settings)


@fixture(tempdb)
def repo_fixture(fixtures: Fixtures) -> sqlite.SqliteRepository:
    return sqlite.SqliteRepository(Settings(SQLITE_DATABASE=fixtures.tempdb))
