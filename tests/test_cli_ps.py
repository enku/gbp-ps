"""CLI unit tests for gbp-ps ps subcommand"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
from argparse import ArgumentParser
from functools import partial

import gbp_testkit.fixtures as testkit
from gbp_testkit.helpers import LOCAL_TIMEZONE
from unittest_fixtures import Fixtures, fixture, given, where

from gbp_ps.cli import ps
from gbp_ps.types import BuildProcess

from . import lib


@fixture(local_timezone=testkit.patch)
def build_processes_fixture(fixtures: Fixtures) -> list[BuildProcess]:
    t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
    return [
        lib.make_build_process(package=cpv, phase=phase, start_time=start_time)
        for cpv, phase, start_time in [
            ["sys-apps/portage-3.0.51", "postinst", t(2023, 11, 10, 16, 20, 0)],
            ["sys-apps/shadow-4.14-r4", "package", t(2023, 11, 11, 16, 20, 1)],
            ["net-misc/wget-1.21.4", "compile", t(2023, 11, 11, 16, 20, 2)],
        ]
    ]


@given(build_processes_fixture)
@given(testkit.gbpcli, now=testkit.patch, sleep=testkit.patch, get_today=testkit.patch)
@where(sleep__target="gbp_ps.cli.ps.time.sleep", sleep__side_effect=KeyboardInterrupt)
@where(now__target="gbp_ps.utils.now")
@where(now__return_value=dt.datetime(2023, 11, 11, 16, 30, tzinfo=LOCAL_TIMEZONE))
@where(get_today__target="gbp_ps.cli.ps.utils.get_today")
@where(get_today__return_value=dt.date(2023, 11, 11))
@where(local_timezone__target="gbpcli.render.LOCAL_TIMEZONE")
@where(local_timezone__new=LOCAL_TIMEZONE)
class PSTests(lib.TestCase):
    """Tests for gbp ps"""

    maxDiff = None

    def test(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps")

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
        self.assertEqual(fixtures.console.stdout, expected)

    def test_without_title(self, fixtures: Fixtures) -> None:
        fixtures.gbpcli("gbp ps -t")

        expected = """$ gbp ps -t
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ Nov10       │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 16:20:01    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 16:20:02    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯
"""
        self.assertEqual(fixtures.console.stdout, expected)

    def test_with_progress(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps --progress")

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps --progress
                                    Build Processes                                     
╭─────────┬──────┬─────────────────────────┬──────────┬────────────────────────────────╮
│ Machine │ ID   │ Package                 │ Start    │ Phase                          │
├─────────┼──────┼─────────────────────────┼──────────┼────────────────────────────────┤
│ babette │ 1031 │ sys-apps/portage-3.0.51 │ Nov10    │ postinst  ━━━━━━━━━━━━━━━━━━━━ │
│ babette │ 1031 │ sys-apps/shadow-4.14-r4 │ 16:20:01 │ package   ━━━━━━━━━━━━━━━      │
│ babette │ 1031 │ net-misc/wget-1.21.4    │ 16:20:02 │ compile   ━━━━━━━━━━           │
╰─────────┴──────┴─────────────────────────┴──────────┴────────────────────────────────╯
"""
        self.assertEqual(fixtures.console.stdout, expected)

    def test_with_node(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps --node")

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps --node
                                    Build Processes                                     
╭───────────┬───────┬─────────────────────────────┬────────────┬─────────────┬─────────╮
│ Machine   │ ID    │ Package                     │ Start      │ Phase       │ Node    │
├───────────┼───────┼─────────────────────────────┼────────────┼─────────────┼─────────┤
│ babette   │ 1031  │ sys-apps/portage-3.0.51     │ Nov10      │ postinst    │ jenkins │
│ babette   │ 1031  │ sys-apps/shadow-4.14-r4     │ 16:20:01   │ package     │ jenkins │
│ babette   │ 1031  │ net-misc/wget-1.21.4        │ 16:20:02   │ compile     │ jenkins │
╰───────────┴───────┴─────────────────────────────┴────────────┴─────────────┴─────────╯
"""
        self.assertEqual(fixtures.console.stdout, expected)

    def test_from_install_to_pull(self, fixtures: Fixtures) -> None:
        # Clean out existing processes
        for bp in fixtures.build_processes:
            lib.make_build_process(package=bp.package, phase="clean", update_repo=True)

        t = partial(dt.datetime, tzinfo=fixtures.local_timezone)
        machine = "babette"
        build_id = "1032"
        package = "sys-apps/portage-3.0.51"
        build_host = "jenkins"
        orig_start = t(2023, 11, 15, 16, 20, 0)
        update = partial(
            lib.make_build_process,
            machine=machine,
            build_id=build_id,
            package=package,
            build_host=build_host,
            start_time=orig_start,
            update_repo=True,
        )
        update(phase="world")

        # First compile it
        fixtures.gbpcli("gbp ps --node")

        self.assertEqual(
            fixtures.console.stdout,
            """$ gbp ps --node
                                    Build Processes                                     
╭───────────┬────────┬──────────────────────────────┬─────────┬─────────────┬──────────╮
│ Machine   │ ID     │ Package                      │ Start   │ Phase       │ Node     │
├───────────┼────────┼──────────────────────────────┼─────────┼─────────────┼──────────┤
│ babette   │ 1032   │ sys-apps/portage-3.0.51      │ Nov15   │ world       │ jenkins  │
╰───────────┴────────┴──────────────────────────────┴─────────┴─────────────┴──────────╯
""",
        )

        # Now it's done compiling
        update(phase="clean", start_time=orig_start + dt.timedelta(seconds=60))
        fixtures.console.out.file.seek(0)
        fixtures.console.out.file.truncate()
        fixtures.gbpcli("gbp ps --node")

        self.assertEqual(fixtures.console.stdout, "$ gbp ps --node\n")

        # Now it's being pulled by GBP on another node
        update(
            build_host="gbp",
            phase="pull",
            start_time=orig_start + dt.timedelta(seconds=120),
        )
        fixtures.console.out.file.seek(0)
        fixtures.console.out.file.truncate()
        fixtures.gbpcli("gbp ps --node")

        self.assertEqual(
            fixtures.console.stdout,
            """$ gbp ps --node
                                    Build Processes                                     
╭────────────┬────────┬────────────────────────────────┬─────────┬─────────────┬───────╮
│ Machine    │ ID     │ Package                        │ Start   │ Phase       │ Node  │
├────────────┼────────┼────────────────────────────────┼─────────┼─────────────┼───────┤
│ babette    │ 1032   │ sys-apps/portage-3.0.51        │ Nov15   │ pull        │ gbp   │
╰────────────┴────────┴────────────────────────────────┴─────────┴─────────────┴───────╯
""",
        )

    def test_empty(self, fixtures: Fixtures) -> None:
        # Clean out existing processes
        for bp in fixtures.build_processes:
            lib.make_build_process(package=bp.package, phase="clean", update_repo=True)

        exit_status = fixtures.gbpcli("gbp ps")

        self.assertEqual(exit_status, 0)
        self.assertEqual(fixtures.console.stdout, "$ gbp ps\n")

    def test_continuous_mode(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps -c -i4")

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps -c -i4
                                    Build Processes                                     
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Start       │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ Nov10       │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 16:20:01    │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 16:20:02    │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯"""
        self.assertEqual(fixtures.console.stdout, expected)
        fixtures.sleep.assert_called_with(4)

    def test_elapsed_mode(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps -e")

        self.assertEqual(exit_status, 0)
        expected = """$ gbp ps -e
                                    Build Processes                                     
╭─────────────┬────────┬──────────────────────────────────┬─────────────┬──────────────╮
│ Machine     │ ID     │ Package                          │ Elapsed     │ Phase        │
├─────────────┼────────┼──────────────────────────────────┼─────────────┼──────────────┤
│ babette     │ 1031   │ sys-apps/portage-3.0.51          │ 24:10:00    │ postinst     │
│ babette     │ 1031   │ sys-apps/shadow-4.14-r4          │ 0:09:59     │ package      │
│ babette     │ 1031   │ net-misc/wget-1.21.4             │ 0:09:58     │ compile      │
╰─────────────┴────────┴──────────────────────────────────┴─────────────┴──────────────╯
"""
        self.assertEqual(fixtures.console.stdout, expected)


@given(testkit.gbpcli, local_timezone=testkit.patch, get_today=testkit.patch)
@where(get_today__target="gbp_ps.cli.ps.utils.get_today")
@where(get_today__return_value=dt.date(2023, 11, 11))
@where(local_timezone__target="gbpcli.render.LOCAL_TIMEZONE")
@where(local_timezone__new=LOCAL_TIMEZONE)
class PSWithMFlagTests(lib.TestCase):
    maxDiff = None

    def test(self, fixtures: Fixtures) -> None:
        lib.make_build_process(
            machine="babette", package="sys-devel/gcc-14.2.1_p20241221"
        )
        lib.make_build_process(machine="lighthouse", package="app-i18n/ibus-1.5.31-r1")
        lib.make_build_process(machine="babette", package="sys-devel/flex-2.6.4-r6")
        lib.make_build_process(machine="lighthouse", package="media-libs/gd-2.3.3-r4")

        exit_status = fixtures.gbpcli("gbp ps -m lighthouse")

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
        self.assertEqual(expected, fixtures.console.stdout)


class PSParseArgsTests(lib.TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        ps.parse_args(parser)


@given(lib.tempdb, repo=lib.repo_fixture, process=lib.build_process)
class PSGetLocalProcessesTests(lib.TestCase):
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
            process = lib.BuildProcessFactory()
            fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(fixtures.tempdb)()), 5)

    def test_with_final_processes(self, fixtures: Fixtures) -> None:
        for phase in BuildProcess.final_phases:
            process = lib.BuildProcessFactory(phase=phase)
            fixtures.repo.add_process(process)

        self.assertEqual(len(ps.get_local_processes(fixtures.tempdb)()), 0)
