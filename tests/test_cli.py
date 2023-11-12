"""CLI unit tests for gbp-ps"""
# pylint: disable=missing-docstring
import io
from argparse import Namespace, ArgumentParser
from unittest import mock

import rich.console
from django.test import TestCase
from django.test.client import Client
from gbpcli import GBP, Console
from gbpcli.theme import DEFAULT_THEME
from requests import Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from rich.theme import Theme

from gbp_ps import ps

from . import LOCAL_TIMEZONE, make_build_process


def string_console() -> tuple[Console, io.StringIO, io.StringIO]:
    """StringIO Console"""
    out = io.StringIO()
    err = io.StringIO()

    return (
        Console(
            out=rich.console.Console(file=out, theme=Theme(DEFAULT_THEME)),
            err=rich.console.Console(file=err),
        ),
        out,
        err,
    )


def test_gbp(url: str) -> GBP:
    """Return a gbp instance capable of calling the /graphql view"""
    gbp = GBP(url, distribution="gbpcli")
    gbp.query._session.mount(  # pylint: disable=protected-access
        url, DjangoToRequestsAdapter()
    )

    return gbp


class DjangoToRequestsAdapter(BaseAdapter):  # pylint: disable=abstract-method
    """Requests Adapter to call Django views"""

    def send(  # pylint: disable=too-many-arguments
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ) -> Response:
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
        requests_response.encoding = django_response.get("Conent-Type", None)
        requests_response.url = str(request.url)
        requests_response.request = request

        return requests_response


class PSTests(TestCase):
    """Tests for gbp ps"""

    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        self.gbp = test_gbp("http://gbp.invalid/")

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    def test(self) -> None:
        for cpv, phase in [
            ["sys-apps/portage-3.0.51", "postinst"],
            ["sys-apps/shadow-4.14-r4", "package"],
            ["net-misc/wget-1.21.4", "compile"],
        ]:
            make_build_process(package=cpv, phase=phase)
        args = Namespace(url="http://gbp.invalid/", node=False)
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                 Processes                                  
╭──────────┬──────┬─────────────────────────┬───────────────────┬──────────╮
│ Machine  │ ID   │ Package                 │ Start             │ Phase    │
├──────────┼──────┼─────────────────────────┼───────────────────┼──────────┤
│ babbette │ 1031 │ sys-apps/portage-3.0.51 │ 11/11/23 05:20:52 │ postinst │
│ babbette │ 1031 │ sys-apps/shadow-4.14-r4 │ 11/11/23 05:20:52 │ package  │
│ babbette │ 1031 │ net-misc/wget-1.21.4    │ 11/11/23 05:20:52 │ compile  │
╰──────────┴──────┴─────────────────────────┴───────────────────┴──────────╯
"""
        self.assertEqual(stdout.getvalue(), expected)

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    def test_with_node(self) -> None:
        for cpv, phase in [
            ["sys-apps/portage-3.0.51", "postinst"],
            ["sys-apps/shadow-4.14-r4", "package"],
            ["net-misc/wget-1.21.4", "compile"],
        ]:
            make_build_process(package=cpv, phase=phase)
        args = Namespace(url="http://gbp.invalid/", node=True)
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                      Processes                                       
╭──────────┬──────┬─────────────────────────┬───────────────────┬──────────┬─────────╮
│ Machine  │ ID   │ Package                 │ Start             │ Phase    │ Node    │
├──────────┼──────┼─────────────────────────┼───────────────────┼──────────┼─────────┤
│ babbette │ 1031 │ sys-apps/portage-3.0.51 │ 11/11/23 05:20:52 │ postinst │ jenkins │
│ babbette │ 1031 │ sys-apps/shadow-4.14-r4 │ 11/11/23 05:20:52 │ package  │ jenkins │
│ babbette │ 1031 │ net-misc/wget-1.21.4    │ 11/11/23 05:20:52 │ compile  │ jenkins │
╰──────────┴──────┴─────────────────────────┴───────────────────┴──────────┴─────────╯
"""
        self.assertEqual(stdout.getvalue(), expected)

    def test_empty(self) -> None:
        args = Namespace(url="http://gbp.invalid/", node=False)
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual(stdout.getvalue(), "")


class ParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        ps.parse_args(parser)
