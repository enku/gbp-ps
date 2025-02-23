"""unittest fixtures for gbp-ps"""

# pylint: disable=missing-docstring

from typing import Any
from unittest import mock

from gbp_testkit import fixtures as testkit
from unittest_fixtures import FixtureContext, Fixtures, fixture

from gbp_ps.repository import Repo, RepositoryType, sqlite
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

from .factories import BuildProcessFactory

console = testkit.console
gbp = testkit.gbp
publisher = testkit.publisher
tmpdir = testkit.tmpdir


@fixture()
def build_process(_fixtures: Fixtures, **options: Any) -> BuildProcess:
    return BuildProcessFactory(**options)


@fixture("tmpdir")
def tempdb(fixtures: Fixtures) -> str:
    return f"{fixtures.tmpdir}/processes.db"


@fixture("settings")
def repo(fixtures: Fixtures) -> RepositoryType:
    return Repo(fixtures.settings)


@fixture("tempdb")
def repo_fixture(fixtures: Fixtures) -> sqlite.SqliteRepository:
    return sqlite.SqliteRepository(Settings(SQLITE_DATABASE=fixtures.tempdb))


@fixture("environ")
def settings(_fixtures: Fixtures) -> Settings:
    return Settings.from_environ()


@fixture("tmpdir")
def environ(
    fixtures: Fixtures,
    environ: dict[str, str] | None = None,  # pylint: disable=redefined-outer-name
) -> FixtureContext[dict[str, str]]:
    new_environ: dict[str, str] = next(testkit.environ(fixtures), {}).copy()
    new_environ["GBP_PS_SQLITE_DATABASE"] = f"{fixtures.tmpdir}/db.sqlite"
    new_environ.update(environ or {})
    with mock.patch.dict("os.environ", new_environ):
        yield new_environ
