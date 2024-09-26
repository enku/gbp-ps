"""CLI unit tests for gbp-ps add-process subcommand"""

# pylint: disable=missing-docstring
import datetime as dt
import platform
from argparse import ArgumentParser, Namespace
from unittest import mock

from unittest_fixtures import requires

from gbp_ps.cli import add_process

from . import TestCase, factories, make_build_process, string_console


@requires("repo", "gbp")
class AddProcessTests(TestCase):
    """Tests for gbp add-process"""

    maxDiff = None

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
            progress=False,
        )
        exit_status = add_process.handler(args, self.fixtures.gbp, console)

        self.assertEqual(exit_status, 0)
        self.assertEqual([*self.fixtures.repo.get_processes()], [process])

    def test_parse_args(self) -> None:
        # Just ensure that parse_args is there and works
        parser = ArgumentParser()
        add_process.parse_args(parser)


@requires("tempdb", "repo_fixture")
class AddProcessAddLocalProcessesTests(TestCase):
    def test(self) -> None:
        process = factories.BuildProcessFactory()

        add_process.add_local_process(self.fixtures.tempdb)(process)

        result = self.fixtures.repo.get_processes()

        self.assertEqual(list(result), [process])


class BuildProcessFromArgsTests(TestCase):
    def test(self) -> None:
        expected = factories.BuildProcessFactory()
        args = Namespace(
            machine=expected.machine,
            number=expected.build_id,
            package=expected.package,
            phase=expected.phase,
        )

        with mock.patch("gbp_ps.cli.add_process.now", return_value=expected.start_time):
            with mock.patch(
                "gbp_ps.cli.add_process.platform.node", return_value=expected.build_host
            ):
                process = add_process.build_process_from_args(args)

        self.assertEqual(process, expected)
