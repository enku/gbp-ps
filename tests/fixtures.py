# pylint: disable=missing-docstring
import io
import os
import tempfile
from typing import Mapping
from unittest import mock

import rich.console
from django.test.client import Client
from gbpcli.gbp import GBP
from gbpcli.theme import get_theme_from_string
from gbpcli.types import Console
from requests import PreparedRequest, Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from unittest_fixtures import FixtureContext, FixtureOptions, Fixtures, depends

from gbp_ps.repository import Repo, RepositoryType, sqlite
from gbp_ps.settings import Settings

COUNTER = 0


def tempdir(_options: FixtureOptions, _fixtures: Fixtures) -> FixtureContext[str]:
    with tempfile.TemporaryDirectory() as tempdir_:
        yield tempdir_


@depends("tempdir")
def environ(
    options: FixtureOptions, fixtures: Fixtures
) -> FixtureContext[dict[str, str]]:
    new_environ = options.get("environ", {}).copy()
    new_environ["GBP_PS_SQLITE_DATABASE"] = f"{fixtures.tempdir}/db.sqlite"
    with mock.patch.dict("os.environ", new_environ, clear=True):
        yield new_environ


@depends("environ")
def settings(_options: FixtureOptions, _fixtures: Fixtures) -> Settings:
    return Settings.from_environ()


@depends("settings")
def repo(_options: FixtureOptions, fixtures: Fixtures) -> RepositoryType:
    return Repo(fixtures.settings)


def gbp(options: FixtureOptions, _fixtures: Fixtures) -> GBP:
    url = options.get("gbp", {}).get("url", "http://gbp.invalid/")
    gbp_ = GBP(url)
    gbp_.query._session.mount(  # pylint: disable=protected-access
        url, DjangoToRequestsAdapter()
    )

    return gbp_


@depends("tempdir")
def tempdb(_options: FixtureOptions, fixtures: Fixtures) -> str:
    return f"{fixtures.tempdir}/processes.db"


@depends(tempdb)
def repo_fixture(
    _options: FixtureOptions, fixtures: Fixtures
) -> sqlite.SqliteRepository:
    return sqlite.SqliteRepository(Settings(SQLITE_DATABASE=fixtures.tempdb))


class DjangoToRequestsAdapter(BaseAdapter):  # pylint: disable=abstract-method
    """Requests Adapter to call Django views"""

    def send(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        assert request.method is not None
        django_response = Client().generic(
            request.method,
            request.path_url,
            data=request.body,
            content_type=request.headers["Content-Type"],
            **request.headers,
        )

        requests_response = Response()
        requests_response.raw = io.BytesIO(django_response.content)
        requests_response.raw.seek(0)
        requests_response.status_code = django_response.status_code
        requests_response.headers = CaseInsensitiveDict(django_response.headers)
        requests_response.encoding = django_response.get("Content-Type", None)
        requests_response.url = str(request.url)
        requests_response.request = request

        return requests_response


@depends()
def console(_options: FixtureOptions, _fixtures: Fixtures) -> FixtureContext[Console]:
    outfile = io.StringIO()
    errfile = io.StringIO()
    theme = get_theme_from_string(os.getenv("GBPCLI_COLORS", ""))
    out = rich.console.Console(
        file=outfile, width=88, theme=theme, highlight=False, record=True
    )
    err = rich.console.Console(file=errfile, width=88, record=True)
    c = Console(out=out, err=err)

    yield c

    # pylint: disable=no-member,global-statement
    if "SAVE_VIRTUAL_CONSOLE" in os.environ and c.out.file.getvalue():
        global COUNTER

        COUNTER += 1
        filename = f"{COUNTER}.svg"
        c.out.save_svg(filename, title="Gentoo Build Publisher")
