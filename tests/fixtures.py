"""unittest fixtures for gbp-ps"""

# pylint: disable=missing-docstring

from typing import Any
from unittest import mock

from gbp_testkit import fixtures as testkit
from gbp_testkit.helpers import DjangoToRequestsAdapter
from gbpcli.gbp import GBP
from unittest_fixtures import FixtureContext, Fixtures, fixture

from gbp_ps.repository import Repo, RepositoryType, sqlite
from gbp_ps.settings import Settings

console = testkit.console
tmpdir = testkit.tmpdir


@fixture("tmpdir")
def tempdb(_options: None, fixtures: Fixtures) -> str:
    return f"{fixtures.tmpdir}/processes.db"


@fixture("settings")
def repo(_options: None, fixtures: Fixtures) -> RepositoryType:
    return Repo(fixtures.settings)


@fixture("tempdb")
def repo_fixture(_options: None, fixtures: Fixtures) -> sqlite.SqliteRepository:
    return sqlite.SqliteRepository(Settings(SQLITE_DATABASE=fixtures.tempdb))


@fixture("environ")
def settings(_options: None, _fixtures: Fixtures) -> Settings:
    return Settings.from_environ()


@fixture()
def gbp(options: dict[str, Any] | None, _fixtures: Fixtures) -> GBP:
    options = options or {}
    url = options.get("url", "http://gbp.invalid/")
    gbp_ = GBP(url)
    gbp_.query._session.mount(  # pylint: disable=protected-access
        url, DjangoToRequestsAdapter()
    )

    return gbp_


@fixture("tmpdir")
def environ(
    options: dict[str, str], fixtures: Fixtures
) -> FixtureContext[dict[str, str]]:
    new_environ = next(testkit.environ(options, fixtures), {}).copy()
    new_environ["GBP_PS_SQLITE_DATABASE"] = f"{fixtures.tmpdir}/db.sqlite"
    with mock.patch.dict("os.environ", new_environ):
        yield new_environ
