"""Tests for gbp-ps signal handlers"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
from unittest import mock

from gentoo_build_publisher.signals import dispatcher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given

from gbp_ps import signals
from gbp_ps.types import BuildProcess

from . import TestCase, factories

NODE = "wopr"
START_TIME = dt.datetime(2023, 12, 10, 13, 53, 46, tzinfo=dt.UTC)
BUILD = Build(machine="babette", build_id="10")


@given("repo")
@mock.patch("gbp_ps.signals._NODE", new=NODE)
@mock.patch("gbp_ps.signals._now", mock.Mock(return_value=START_TIME))
class SignalsTest(TestCase):
    def test_create_build_process(self, fixtures: Fixtures) -> None:
        process = signals.build_process(BUILD, NODE, "test", START_TIME)

        expected: BuildProcess = factories.BuildProcessFactory(
            build_id=BUILD.build_id,
            build_host=NODE,
            machine=BUILD.machine,
            package="pipeline",
            phase="test",
            start_time=START_TIME,
        )
        self.assertEqual(process, expected)

    def test_prepull_handler(self, fixtures: Fixtures) -> None:
        signals.prepull_handler(build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "pull", START_TIME)
        self.assertEqual(processes, [expected])

    def test_postpull_handler(self, fixtures: Fixtures) -> None:
        signals.postpull_handler(build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_handler_updates(self, fixtures: Fixtures) -> None:
        signals.prepull_handler(build=BUILD)
        signals.postpull_handler(build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_prepull_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("prepull", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "pull", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_postpull_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("postpull", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_predelete_handler(self, fixtures: Fixtures) -> None:
        signals.predelete_handler(build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "delete", START_TIME)
        self.assertEqual(processes, [expected])

    def test_postdelete_handler(self, fixtures: Fixtures) -> None:
        signals.postdelete_handler(build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_predelete_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("predelete", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "delete", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_postdelete_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("postdelete", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])
