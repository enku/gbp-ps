"""CLI unit tests for gbp-ps"""
# pylint: disable=missing-docstring
import datetime as dt
import importlib.resources
import io
import platform
from argparse import ArgumentParser, Namespace
from functools import partial
from unittest import mock

import rich.console
from django.test.client import Client
from gbpcli import GBP, Console
from gbpcli.graphql import Query
from gbpcli.theme import DEFAULT_THEME
from requests import Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from rich.theme import Theme

from gbp_ps.cli import add_process, get_dist_query, ps

from . import LOCAL_TIMEZONE, TestCase, make_build_process


def string_console() -> tuple[Console, io.StringIO, io.StringIO]:
    """StringIO Console"""
    out = io.StringIO()
    err = io.StringIO()

    return (
        Console(
            out=rich.console.Console(file=out, width=88, theme=Theme(DEFAULT_THEME)),
            err=rich.console.Console(file=err),
        ),
        out,
        err,
    )


def test_gbp(url: str) -> GBP:
    """Return a gbp instance capable of calling the /graphql view"""
    gbp = GBP(url)
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
        requests_response.encoding = django_response.get("Content-Type", None)
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
    @mock.patch("gbp_ps.cli.ps.get_today", new=lambda: dt.date(2023, 11, 15))
    def test(self) -> None:
        t = dt.datetime
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 14, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 15, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 15, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        args = Namespace(url="http://gbp.invalid/", node=False, continuous=False)
        console, stdout = string_console()[:2]

        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Ebuild Processes                                    
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ Nov14       │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 15:20:01    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 15:20:02    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯
"""
        self.assertEqual(stdout.getvalue(), expected)

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    @mock.patch("gbp_ps.cli.ps.get_today", new=lambda: dt.date(2023, 11, 15))
    def test_with_node(self) -> None:
        t = dt.datetime
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 15, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 15, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 15, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        args = Namespace(url="http://gbp.invalid/", node=True, continuous=False)
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Ebuild Processes                                    
╭───────────┬───────┬─────────────────────────────┬────────────┬─────────────┬─────────╮
│ Machine   │ ID    │ Package                     │ Start      │ Phase       │ Node    │
├───────────┼───────┼─────────────────────────────┼────────────┼─────────────┼─────────┤
│ babette   │ 1031  │ sys-apps/portage-3.0.51     │ 15:20:00   │ postinst    │ jenkins │
│ babette   │ 1031  │ sys-apps/shadow-4.14-r4     │ 15:20:01   │ package     │ jenkins │
│ babette   │ 1031  │ net-misc/wget-1.21.4        │ 15:20:02   │ compile     │ jenkins │
╰───────────┴───────┴─────────────────────────────┴────────────┴─────────────┴─────────╯
"""
        self.assertEqual(stdout.getvalue(), expected)

    def test_from_install_to_pull(self) -> None:
        t = dt.datetime
        machine = "babette"
        build_id = "1031"
        package = "sys-apps/portage-3.0.51"
        build_host = "jenkins"
        orig_start = t(2023, 11, 15, 16, 20, 0)
        args = Namespace(url="http://gbp.invalid/", node=True, continuous=False)
        update = partial(
            make_build_process,
            machine=machine,
            build_id=build_id,
            package=package,
            build_host=build_host,
            start_time=orig_start,
            update_repo=True,
        )
        update(phase="world")

        # First compile it
        console, stdout, _ = string_console()
        ps.handler(args, self.gbp, console)

        self.assertEqual(
            stdout.getvalue(),
            """\
                                    Ebuild Processes                                    
╭───────────┬────────┬──────────────────────────────┬─────────┬─────────────┬──────────╮
│ Machine   │ ID     │ Package                      │ Start   │ Phase       │ Node     │
├───────────┼────────┼──────────────────────────────┼─────────┼─────────────┼──────────┤
│ babette   │ 1031   │ sys-apps/portage-3.0.51      │ Nov15   │ world       │ jenkins  │
╰───────────┴────────┴──────────────────────────────┴─────────┴─────────────┴──────────╯
""",
        )

        # Now it's done compiling
        update(phase="clean", start_time=orig_start + dt.timedelta(seconds=60))
        console, stdout, _ = string_console()
        ps.handler(args, self.gbp, console)

        self.assertEqual(stdout.getvalue(), "")

        # Now it's being pulled by GBP on another node
        update(
            build_host="gbp",
            phase="pull",
            start_time=orig_start + dt.timedelta(seconds=120),
        )
        console, stdout, _ = string_console()
        ps.handler(args, self.gbp, console)

        self.assertEqual(
            stdout.getvalue(),
            """\
                                    Ebuild Processes                                    
╭────────────┬────────┬────────────────────────────────┬─────────┬─────────────┬───────╮
│ Machine    │ ID     │ Package                        │ Start   │ Phase       │ Node  │
├────────────┼────────┼────────────────────────────────┼─────────┼─────────────┼───────┤
│ babette    │ 1031   │ sys-apps/portage-3.0.51        │ Nov15   │ pull        │ gbp   │
╰────────────┴────────┴────────────────────────────────┴─────────┴─────────────┴───────╯
""",
        )

    def test_empty(self) -> None:
        args = Namespace(url="http://gbp.invalid/", node=False, continuous=False)
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual(stdout.getvalue(), "")

    @mock.patch("gbp_ps.cli.ps.time.sleep")
    @mock.patch("gbp_ps.cli.ps.get_today", new=lambda: dt.date(2023, 11, 11))
    def test_continuous_mode(self, mock_sleep: mock.Mock) -> None:
        processes = [
            make_build_process(package=cpv, phase=phase)
            for cpv, phase in [
                ["sys-apps/portage-3.0.51", "postinst"],
                ["sys-apps/shadow-4.14-r4", "package"],
                ["net-misc/wget-1.21.4", "compile"],
            ]
        ]
        args = Namespace(
            url="http://gbp.invalid/", node=False, continuous=True, update_interval=4
        )
        console, stdout = string_console()[:2]

        gbp = mock.Mock()
        mock_graphql_resp = [process.to_dict() for process in processes]
        gbp.query.get_processes.side_effect = (
            ({"buildProcesses": mock_graphql_resp}, None),
            KeyboardInterrupt,
        )
        exit_status = ps.handler(args, gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Ebuild Processes                                    
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ 06:20:52    │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 06:20:52    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 06:20:52    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯"""
        self.assertEqual(stdout.getvalue(), expected)
        mock_sleep.assert_called_with(4)


class PSParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        ps.parse_args(parser)


class AddProcessTests(TestCase):
    """Tests for gbp add-process"""

    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        self.gbp = test_gbp("http://gbp.invalid/")

    @mock.patch("gbp_ps.cli.add_process.now")
    def test(self, mock_now: mock.Mock) -> None:
        now = mock_now.return_value = dt.datetime(2023, 11, 20, 17, 57, tzinfo=dt.UTC)
        process = make_build_process(
            add_to_repo=False, build_host=platform.node(), start_time=now
        )
        console = string_console()[0]
        args = Namespace(
            machine=process.machine,
            number=process.build_id,
            package=process.package,
            phase=process.phase,
            url="http://gbp.invalid/",
        )
        exit_status = add_process.handler(args, self.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual([*self.repo.get_processes()], [process])

    def test_parse_args(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        add_process.parse_args(parser)


GET_PROCESSES_QUERY_STR = (
    importlib.resources.files("gbp_ps") / "queries/get_processes.graphql"
).read_text(encoding="UTF-8")


class GetDistQueryTests(TestCase):
    """Tests for the get_dist_query helper"""

    def test_old_world(self) -> None:
        # Pre gbpcli-2.0
        gbp = test_gbp("http://test.invalid/")
        query = get_dist_query("get_processes", gbp, distribution="gbp_ps")

        self.assertEqual(str(query), GET_PROCESSES_QUERY_STR)

    def test_new_world(self) -> None:
        # post gbpcli-2.0. Not yet released so we mock the expected behavior
        gbp = mock.MagicMock()
        del gbp.query._distribution
        gbp.query.gbp_ps.get_processes = Query(
            GET_PROCESSES_QUERY_STR, "http://test.invalid", mock.Mock()
        )
        query = get_dist_query("get_processes", gbp, distribution="gbp_ps")

        self.assertEqual(str(query), GET_PROCESSES_QUERY_STR)
