"""CLI unit tests for gbp-ps ps subcommand"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
from argparse import ArgumentParser
from functools import partial
from unittest import mock

from gbp_testkit.helpers import parse_args, print_command
from unittest_fixtures import Fixtures, given

from gbp_ps.cli import ps
from gbp_ps.types import BuildProcess

from . import TestCase, factories, make_build_process


@given("gbp", "console", "local_timezone", "get_today", "now")
class PSTests(TestCase):
    """Tests for gbp ps"""

    maxDiff = None

    def test(self, fixtures: Fixtures) -> None:
        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 10, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 11, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 11, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        cmdline = "gbp ps"
        args = parse_args(cmdline)
        console = fixtures.console

        print_command(cmdline, console)
        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps
                                    Build Processes                                     
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ Nov10       │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 16:20:01    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 16:20:02    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯
"""
        self.assertEqual(console.out.file.getvalue(), expected)

    def test_with_progress(self, fixtures: Fixtures) -> None:
        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        for cpv, phase, start_time in [
            ["pipeline", "world", t(2023, 11, 11, 16, 20, 1)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 11, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 11, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        cmdline = "gbp ps --progress"
        args = parse_args(cmdline)
        console = fixtures.console

        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Build Processes                                     
╭─────────┬──────┬─────────────────────────┬──────────┬────────────────────────────────╮
│ Machine │ ID   │ Package                 │ Start    │ Phase                          │
├─────────┼──────┼─────────────────────────┼──────────┼────────────────────────────────┤
│ babette │ 1031 │ pipeline                │ 16:20:01 │ world     ━━━━━━━━━━━━━━━━━━━━ │
│ babette │ 1031 │ sys-apps/shadow-4.14-r4 │ 16:20:01 │ package   ━━━━━━━━━━━━━━━      │
│ babette │ 1031 │ net-misc/wget-1.21.4    │ 16:20:02 │ compile   ━━━━━━━━━━           │
╰─────────┴──────┴─────────────────────────┴──────────┴────────────────────────────────╯
"""
        self.assertEqual(console.out.file.getvalue(), expected)

    def test_with_node(self, fixtures: Fixtures) -> None:
        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 11, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 11, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 11, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        cmdline = "gbp ps --node"
        args = parse_args(cmdline)
        console = fixtures.console

        print_command(cmdline, console)
        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps --node
                                    Build Processes                                     
╭───────────┬───────┬─────────────────────────────┬────────────┬─────────────┬─────────╮
│ Machine   │ ID    │ Package                     │ Start      │ Phase       │ Node    │
├───────────┼───────┼─────────────────────────────┼────────────┼─────────────┼─────────┤
│ babette   │ 1031  │ sys-apps/portage-3.0.51     │ 16:20:00   │ postinst    │ jenkins │
│ babette   │ 1031  │ sys-apps/shadow-4.14-r4     │ 16:20:01   │ package     │ jenkins │
│ babette   │ 1031  │ net-misc/wget-1.21.4        │ 16:20:02   │ compile     │ jenkins │
╰───────────┴───────┴─────────────────────────────┴────────────┴─────────────┴─────────╯
"""
        self.assertEqual(console.out.file.getvalue(), expected)

    def test_from_install_to_pull(self, fixtures: Fixtures) -> None:
        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        machine = "babette"
        build_id = "1031"
        package = "sys-apps/portage-3.0.51"
        build_host = "jenkins"
        orig_start = t(2023, 11, 15, 16, 20, 0)
        cmdline = "gbp ps --node"
        args = parse_args(cmdline)
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
        console = fixtures.console
        ps.handler(args, fixtures.gbp, console)

        self.assertEqual(
            console.out.file.getvalue(),
            """\
                                    Build Processes                                     
╭───────────┬────────┬──────────────────────────────┬─────────┬─────────────┬──────────╮
│ Machine   │ ID     │ Package                      │ Start   │ Phase       │ Node     │
├───────────┼────────┼──────────────────────────────┼─────────┼─────────────┼──────────┤
│ babette   │ 1031   │ sys-apps/portage-3.0.51      │ Nov15   │ world       │ jenkins  │
╰───────────┴────────┴──────────────────────────────┴─────────┴─────────────┴──────────╯
""",
        )

        # Now it's done compiling
        update(phase="clean", start_time=orig_start + dt.timedelta(seconds=60))
        console.out.file.seek(0)
        console.out.file.truncate()
        ps.handler(args, fixtures.gbp, console)

        self.assertEqual(console.out.file.getvalue(), "")

        # Now it's being pulled by GBP on another node
        update(
            build_host="gbp",
            phase="pull",
            start_time=orig_start + dt.timedelta(seconds=120),
        )
        console.out.file.seek(0)
        console.out.file.truncate()
        ps.handler(args, fixtures.gbp, console)

        self.assertEqual(
            console.out.file.getvalue(),
            """\
                                    Build Processes                                     
╭────────────┬────────┬────────────────────────────────┬─────────┬─────────────┬───────╮
│ Machine    │ ID     │ Package                        │ Start   │ Phase       │ Node  │
├────────────┼────────┼────────────────────────────────┼─────────┼─────────────┼───────┤
│ babette    │ 1031   │ sys-apps/portage-3.0.51        │ Nov15   │ pull        │ gbp   │
╰────────────┴────────┴────────────────────────────────┴─────────┴─────────────┴───────╯
""",
        )

    def test_empty(self, fixtures: Fixtures) -> None:
        cmdline = "gbp ps"
        args = parse_args(cmdline)
        console = fixtures.console
        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual(console.out.file.getvalue(), "")

    @mock.patch("gbp_ps.cli.ps.time.sleep")
    def test_continuous_mode(self, mock_sleep: mock.Mock, fixtures: Fixtures) -> None:
        processes = [
            make_build_process(package=cpv, phase=phase)
            for cpv, phase in [
                ["sys-apps/portage-3.0.51", "postinst"],
                ["sys-apps/shadow-4.14-r4", "package"],
                ["net-misc/wget-1.21.4", "compile"],
            ]
        ]
        cmdline = "gbp ps -c -i4"
        args = parse_args(cmdline)
        console = fixtures.console

        gbp = mock.Mock()
        mock_graphql_resp = [process.to_dict() for process in processes]
        gbp.query.gbp_ps.get_processes.side_effect = (
            ({"buildProcesses": mock_graphql_resp}, None),
            KeyboardInterrupt,
        )
        exit_status = ps.handler(args, gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Build Processes                                     
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ 05:20:52    │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 05:20:52    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 05:20:52    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯"""
        self.assertEqual(console.out.file.getvalue(), expected)
        mock_sleep.assert_called_with(4)

    def test_elapsed_mode(self, fixtures: Fixtures) -> None:
        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        for cpv, phase, start_time in [
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 11, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 11, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        cmdline = "gbp ps -e"
        args = parse_args(cmdline)
        console = fixtures.console

        print_command(cmdline, console)
        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps -e
                                    Build Processes                                     
╭─────────────┬─────────┬──────────────────────────────────┬────────────┬──────────────╮
│ Machine     │ ID      │ Package                          │ Elapsed    │ Phase        │
├─────────────┼─────────┼──────────────────────────────────┼────────────┼──────────────┤
│ babette     │ 1031    │ sys-apps/shadow-4.14-r4          │ 0:09:59    │ package      │
│ babette     │ 1031    │ net-misc/wget-1.21.4             │ 0:09:58    │ compile      │
╰─────────────┴─────────┴──────────────────────────────────┴────────────┴──────────────╯
"""
        self.assertEqual(console.out.file.getvalue(), expected)


@given("local_timezone", "console", "gbp", "get_today")
class PSWithMFlagTests(TestCase):
    maxDiff = None

    def test(self, fixtures: Fixtures) -> None:
        make_build_process(machine="babette", package="sys-devel/gcc-14.2.1_p20241221")
        make_build_process(machine="lighthouse", package="app-i18n/ibus-1.5.31-r1")
        make_build_process(machine="babette", package="sys-devel/flex-2.6.4-r6")
        make_build_process(machine="lighthouse", package="media-libs/gd-2.3.3-r4")

        cmdline = "gbp ps -m lighthouse"
        args = parse_args(cmdline)
        console = fixtures.console

        print_command(cmdline, console)
        exit_status = ps.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)

        expected = """\
$ gbp ps -m lighthouse
                                    Build Processes                                     
╭────────────────┬────────┬────────────────────────────────┬─────────────┬─────────────╮
│ Machine        │ ID     │ Package                        │ Start       │ Phase       │
├────────────────┼────────┼────────────────────────────────┼─────────────┼─────────────┤
│ lighthouse     │ 1031   │ app-i18n/ibus-1.5.31-r1        │ 05:20:52    │ compile     │
│ lighthouse     │ 1031   │ media-libs/gd-2.3.3-r4         │ 05:20:52    │ compile     │
╰────────────────┴────────┴────────────────────────────────┴─────────────┴─────────────╯
"""
        self.assertEqual(expected, console.out.file.getvalue())


class PSParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        ps.parse_args(parser)


@given("tempdb", repo="repo_fixture", process="build_process")
class PSGetLocalProcessesTests(TestCase):
    def test_with_0_processes(self, fixtures: Fixtures) -> None:
        p = ps.get_local_processes(fixtures.tempdb)()

        self.assertEqual(p, [])

    def test_with_1_process(self, fixtures: Fixtures) -> None:
        process = fixtures.process
        fixtures.repo.add_process(process)

        p = ps.get_local_processes(fixtures.tempdb)()

        self.assertEqual(p, [process])

    def test_with_multiple_processes(self, fixtures: Fixtures) -> None:
        for _ in range(5):
            process = factories.BuildProcessFactory()
            fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(fixtures.tempdb)()), 5)

    def test_with_final_processes(self, fixtures: Fixtures) -> None:
        for phase in BuildProcess.final_phases:
            process = factories.BuildProcessFactory(phase=phase)
            fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(fixtures.tempdb)()), 0)
