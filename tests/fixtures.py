# pylint: disable=missing-docstring
import io
import tempfile
from typing import Mapping
from unittest import mock

from django.test.client import Client
from gbpcli import GBP
from requests import PreparedRequest, Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from unittest_fixtures import FixtureContext, FixtureOptions, Fixtures, depends

from gbp_ps.repository import Repo, RepositoryType
from gbp_ps.settings import Settings


def tempdir(_options: FixtureOptions, _fixtures: Fixtures) -> FixtureContext[str]:
    with tempfile.TemporaryDirectory() as tempdir_:
        yield tempdir_


def environ(
    options: FixtureOptions, _fixtures: Fixtures
) -> FixtureContext[dict[str, str]]:
    new_environ = options.get("environ", {})
    with mock.patch.dict("os.environ", new_environ, clear=True):
        yield new_environ


@depends("environ")
def repo(_options: FixtureOptions, _fixtures: Fixtures) -> RepositoryType:
    return Repo(Settings.from_environ())


def gbp(options: FixtureOptions, _fixtures: Fixtures) -> GBP:
    url = options.get("gbp", {}).get("url", "http://gbp.invalid/")
    gbp_ = GBP(url)
    gbp_.query._session.mount(  # pylint: disable=protected-access
        url, DjangoToRequestsAdapter()
    )

    return gbp_


class DjangoToRequestsAdapter(BaseAdapter):  # pylint: disable=abstract-method
    """Requests Adapter to call Django views"""

    def send(  # pylint: disable=too-many-arguments
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