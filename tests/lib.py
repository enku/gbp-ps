# pylint: disable=missing-docstring,too-few-public-methods,redefined-outer-name
import datetime as dt
from typing import Any
from unittest import mock

import factory
import gbp_testkit.fixtures as testkit
from django.test import TestCase as DjangoTestCase
from unittest_fixtures import FixtureContext, Fixtures, fixture

from gbp_ps.repository import Repo, RepositoryType, add_or_update_process, sqlite
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

LOCAL_TIMEZONE = dt.timezone(dt.timedelta(days=-1, seconds=61200), "PDT")
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


@fixture(testkit.tmpdir)
def environ(
    fixtures: Fixtures,
    environ: dict[str, str] | None = None,  # pylint: disable=redefined-outer-name
) -> FixtureContext[dict[str, str]]:
    new_environ: dict[str, str] = next(testkit.environ(fixtures), {}).copy()
    new_environ["GBP_PS_SQLITE_DATABASE"] = f"{fixtures.tmpdir}/db.sqlite"
    new_environ.update(environ or {})
    with mock.patch.dict("os.environ", new_environ):
        yield new_environ


@fixture(environ)
def settings(_fixtures: Fixtures) -> Settings:
    return Settings.from_environ()


@fixture(settings)
def repo(fixtures: Fixtures) -> RepositoryType:
    return Repo(fixtures.settings)


@fixture(tempdb)
def repo_fixture(fixtures: Fixtures) -> sqlite.SqliteRepository:
    return sqlite.SqliteRepository(Settings(SQLITE_DATABASE=fixtures.tempdb))


@fixture()
def patch(
    _: Fixtures, target: str = "", attrs: dict[str, Any] | None = None, **kwargs: Any
) -> FixtureContext[mock.Mock]:
    attrs = attrs or {}

    if target:
        patch = mock.patch(target, **kwargs)
        fake = patch.start()
    else:
        patch = None
        fake = mock.Mock(**kwargs)

    for name, value in attrs.items():
        setattr(fake, name, value)

    yield fake

    if patch:
        patch.stop()


@fixture()
def local_timezone(
    _: Fixtures, local_timezone: dt.timezone = LOCAL_TIMEZONE
) -> FixtureContext[dt.timezone]:
    with mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=local_timezone):
        yield local_timezone
