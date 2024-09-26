"""CLI unit tests for gbp-ps ps subcommand"""

# pylint: disable=missing-docstring
import datetime as dt
from argparse import ArgumentParser, Namespace
from functools import partial
from unittest import mock

from unittest_fixtures import requires

from gbp_ps.cli import ps
from gbp_ps.types import BuildProcess

from . import LOCAL_TIMEZONE, TestCase, factories, make_build_process, string_console


@requires("gbp")
class PSTests(TestCase):
    """Tests for gbp ps"""

    maxDiff = None

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    @mock.patch("gbp_ps.cli.ps.utils.get_today", new=lambda: dt.date(2023, 11, 15))
    def test(self) -> None:
        t = dt.datetime
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 14, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 15, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 15, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        args = Namespace(
            url="http://gbp.invalid/", node=False, continuous=False, progress=False
        )
        console, stdout = string_console()[:2]

        exit_status = ps.handler(args, self.fixtures.gbp, console)

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
    @mock.patch("gbp_ps.cli.ps.utils.get_today", new=lambda: dt.date(2024, 8, 16))
    def test_with_progress(self) -> None:
        t = dt.datetime
        for cpv, phase, start_time in [
            ["pipeline", "world", t(2024, 8, 16, 16, 20, 1)],
            ["sys-apps/shadow-4.14-r4", "package", t(2024, 8, 16, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2024, 8, 16, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        args = Namespace(
            url="http://gbp.invalid/", node=False, continuous=False, progress=True
        )
        console, stdout = string_console()[:2]

        exit_status = ps.handler(args, self.fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        expected = """\
                                    Ebuild Processes                                    
╭─────────┬──────┬─────────────────────────┬──────────┬────────────────────────────────╮
│ Machine │ ID   │ Package                 │ Start    │ Phase                          │
├─────────┼──────┼─────────────────────────┼──────────┼────────────────────────────────┤
│ babette │ 1031 │ pipeline                │ 14:20:01 │ world     ━━━━━━━━━━━━━━━━━━━━ │
│ babette │ 1031 │ sys-apps/shadow-4.14-r4 │ 14:20:01 │ package   ━━━━━━━━━━━━━━━      │
│ babette │ 1031 │ net-misc/wget-1.21.4    │ 14:20:02 │ compile   ━━━━━━━━━━           │
╰─────────┴──────┴─────────────────────────┴──────────┴────────────────────────────────╯
"""
        self.assertEqual(stdout.getvalue(), expected)

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    @mock.patch("gbp_ps.cli.ps.utils.get_today", new=lambda: dt.date(2023, 11, 15))
    def test_with_node(self) -> None:
        t = dt.datetime
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 15, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 15, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 15, 16, 20, 2)],
        ]:
            make_build_process(package=cpv, phase=phase, start_time=start_time)
        args = Namespace(
            url="http://gbp.invalid/", node=True, continuous=False, progress=False
        )
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.fixtures.gbp, console)

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
        args = Namespace(
            url="http://gbp.invalid/", node=True, continuous=False, progress=False
        )
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
        ps.handler(args, self.fixtures.gbp, console)

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
        ps.handler(args, self.fixtures.gbp, console)

        self.assertEqual(stdout.getvalue(), "")

        # Now it's being pulled by GBP on another node
        update(
            build_host="gbp",
            phase="pull",
            start_time=orig_start + dt.timedelta(seconds=120),
        )
        console, stdout, _ = string_console()
        ps.handler(args, self.fixtures.gbp, console)

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
        args = Namespace(
            url="http://gbp.invalid/", node=False, continuous=False, progress=False
        )
        console, stdout = string_console()[:2]
        exit_status = ps.handler(args, self.fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual(stdout.getvalue(), "")

    @mock.patch("gbpcli.render.LOCAL_TIMEZONE", new=LOCAL_TIMEZONE)
    @mock.patch("gbp_ps.cli.ps.time.sleep")
    @mock.patch("gbp_ps.cli.ps.utils.get_today", new=lambda: dt.date(2023, 11, 11))
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
            url="http://gbp.invalid/",
            node=False,
            continuous=True,
            update_interval=4,
            progress=False,
        )
        console, stdout = string_console()[:2]

        gbp = mock.Mock()
        mock_graphql_resp = [process.to_dict() for process in processes]
        gbp.query.gbp_ps.get_processes.side_effect = (
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
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ 05:20:52    │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 05:20:52    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 05:20:52    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯"""
        self.assertEqual(stdout.getvalue(), expected)
        mock_sleep.assert_called_with(4)


class PSParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        ps.parse_args(parser)


@requires("tempdb", "repo_fixture")
class PSGetLocalProcessesTests(TestCase):
    def test_with_0_processes(self) -> None:
        p = ps.get_local_processes(self.fixtures.tempdb)()

        self.assertEqual(p, [])

    def test_with_1_process(self) -> None:
        process = factories.BuildProcessFactory()
        self.fixtures.repo.add_process(process)

        p = ps.get_local_processes(self.fixtures.tempdb)()

        self.assertEqual(p, [process])

    def test_with_multiple_processes(self) -> None:
        for _ in range(5):
            process = factories.BuildProcessFactory()
            self.fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(self.fixtures.tempdb)()), 5)

    def test_with_final_processes(self) -> None:
        for phase in BuildProcess.final_phases:
            process = factories.BuildProcessFactory(phase=phase)
            self.fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(self.fixtures.tempdb)()), 0)
