"""CLI unit tests for gbp-ps add-process subcommand"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
import platform
from argparse import ArgumentParser
from unittest import mock

import gbp_testkit.fixtures as testkit
from gbp_testkit.helpers import parse_args
from unittest_fixtures import Fixtures, given

from gbp_ps.cli import add_process

from . import lib


@given(lib.repo, testkit.gbp, testkit.console)
class AddProcessTests(lib.TestCase):
    """Tests for gbp add-process"""

    maxDiff = None

    @mock.patch("gbp_ps.cli.add_process.now")
    def test(self, mock_now: mock.Mock, fixtures: Fixtures) -> None:
        now = mock_now.return_value = dt.datetime(2023, 11, 20, 17, 57, tzinfo=dt.UTC)
        proc = lib.make_build_process(
            add_to_repo=False, build_host=platform.node(), start_time=now
        )
        console = fixtures.console
        cmdline = f"gbp add-process {proc.machine} {proc.build_id} {proc.package} {proc.phase}"
        args = parse_args(cmdline)
        exit_status = add_process.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual([*fixtures.repo.get_processes()], [proc])

    def test_parse_args(self, fixtures: Fixtures) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        add_process.parse_args(parser)


@given(lib.tempdb, lib.repo_fixture, process=lib.build_process)
class AddProcessAddLocalProcessesTests(lib.TestCase):
    def test(self, fixtures: Fixtures) -> None:
        process = fixtures.process

        add_process.add_local_process(fixtures.tempdb)(process)

        result = fixtures.repo.get_processes()

        self.assertEqual(list(result), [process])


@given(lib.build_process)
@mock.patch("gbp_ps.cli.add_process.now")
@mock.patch("gbp_ps.cli.add_process.platform.node")
class BuildProcessFromArgsTests(lib.TestCase):
    def test(self, node: mock.Mock, now: mock.Mock, fixtures: Fixtures) -> None:
        expected = fixtures.build_process
        node.return_value = expected.build_host
        now.return_value = expected.start_time
        cmdline = (
            f"gbp add-process {expected.machine} {expected.build_id} {expected.package}"
            f" {expected.phase}"
        )
        args = parse_args(cmdline)

        process = add_process.build_process_from_args(args)

        self.assertEqual(process, expected)
