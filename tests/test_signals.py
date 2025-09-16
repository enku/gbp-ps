"""Tests for gbp-ps signal handlers"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt

import gbp_testkit.fixtures as testkit
from gentoo_build_publisher.signals import dispatcher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given, where

from gbp_ps import signals
from gbp_ps.types import BuildProcess

from . import lib

NODE = "wopr"
START_TIME = dt.datetime(2023, 12, 10, 13, 53, 46, tzinfo=dt.UTC)
BUILD = Build(machine="babette", build_id="10")

TestCase = lib.TestCase


@given(lib.repo, node=testkit.patch, now=testkit.patch)
@where(node__target="gbp_ps.signals._NODE", node__new=NODE)
@where(now__target="gbp_ps.signals._now", now__return_value=START_TIME)
class SignalsTest(TestCase):
    def test_create_build_process(self, fixtures: Fixtures) -> None:
        process = signals.build_process(BUILD, NODE, "test", START_TIME)

        expected: BuildProcess = lib.BuildProcessFactory(
            build_id=BUILD.build_id,
            build_host=NODE,
            machine=BUILD.machine,
            package="pipeline",
            phase="test",
            start_time=START_TIME,
        )
        self.assertEqual(process, expected)

    def test_prepull_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("prepull", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "pull", START_TIME)
        self.assertEqual(processes, [expected])

    def test_postpull_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("postpull", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_handler_updates(self, fixtures: Fixtures) -> None:
        dispatcher.emit("prepull", build=BUILD)
        dispatcher.emit("postpull", build=BUILD)

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
        dispatcher.emit("predelete", build=BUILD)

        processes = [*fixtures.repo.get_processes(include_final=True)]
        expected = signals.build_process(BUILD, NODE, "delete", START_TIME)
        self.assertEqual(processes, [expected])

    def test_postdelete_handler(self, fixtures: Fixtures) -> None:
        dispatcher.emit("postdelete", build=BUILD)

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


class AddProcessSignalTests(TestCase):
    def test(self) -> None:
        """dispatcher has the add_process signal"""
        process: BuildProcess = lib.BuildProcessFactory()
        build = Build(machine=process.machine, build_id=process.build_id)
        kwarg: BuildProcess | None = None

        def callback(*, build: Build, process: BuildProcess) -> None:
            nonlocal kwarg

            kwarg = process

        dispatcher.bind(gbp_ps_add_process=callback)

        try:
            dispatcher.emit("gbp_ps_add_process", build=build, process=process)
        finally:
            dispatcher.unbind(callback)

        self.assertEqual(kwarg, process)


class UpdateProcessSignalTests(TestCase):
    def test(self) -> None:
        """dispatcher has the update_process signal"""
        process: BuildProcess = lib.BuildProcessFactory()
        build = Build(machine=process.machine, build_id=process.build_id)
        kwarg: BuildProcess | None = None

        def callback(*, build: Build, process: BuildProcess) -> None:
            nonlocal kwarg

            kwarg = process

        dispatcher.bind(gbp_ps_update_process=callback)

        try:
            dispatcher.emit("gbp_ps_update_process", build=build, process=process)
        finally:
            dispatcher.unbind(callback)

        self.assertEqual(kwarg, process)
