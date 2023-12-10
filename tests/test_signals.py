"""Tests for gbp-ps signal handlers"""
# pylint: disable=missing-docstring
import datetime as dt
import os
import tempfile
from unittest import mock

from gentoo_build_publisher.common import Build
from gentoo_build_publisher.signals import dispatcher

from gbp_ps import get_processes, signals
from gbp_ps.types import BuildProcess

from . import TestCase

NODE = "wopr"
START_TIME = dt.datetime(2023, 12, 10, 13, 53, 46, tzinfo=dt.UTC)
BUILD = Build(machine="babette", build_id="10")


@mock.patch("gbp_ps.signals.platform.node", mock.Mock(return_value=NODE))
@mock.patch("gbp_ps.signals._now", mock.Mock(return_value=START_TIME))
class SignalsTest(TestCase):
    def setUp(self) -> None:
        super().setUp()

        tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(tempdir.cleanup)
        gbp_settings = {
            "BUILD_PUBLISHER_JENKINS_BASE_URL": "http://jenkins.invalid",
            "BUILD_PUBLISHER_STORAGE_PATH": tempdir.name,
        }
        patcher = mock.patch.dict(os.environ, gbp_settings)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_create_build_process(self) -> None:
        build_process = signals.create_build_process(BUILD, NODE, "test", START_TIME)

        expected = BuildProcess(
            build_id=BUILD.build_id,
            build_host=NODE,
            machine=BUILD.machine,
            package="pipeline",
            phase="test",
            start_time=START_TIME,
        )
        self.assertEqual(build_process, expected)

    def test_prepull_handler(self) -> None:
        signals.prepull_handler(build=BUILD)

        processes = get_processes(include_final=True)
        expected = signals.create_build_process(BUILD, NODE, "pull", START_TIME)
        self.assertEqual(processes, [expected])

    def test_postpull_handler(self) -> None:
        signals.postpull_handler(build=BUILD)

        processes = get_processes(include_final=True)
        expected = signals.create_build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_prepull_handler(self) -> None:
        dispatcher.emit("prepull", build=BUILD)

        processes = get_processes(include_final=True)
        expected = signals.create_build_process(BUILD, NODE, "pull", START_TIME)
        self.assertEqual(processes, [expected])

    def test_dispatcher_calls_postpull_handler(self) -> None:
        dispatcher.emit("postpull", build=BUILD)

        processes = get_processes(include_final=True)
        expected = signals.create_build_process(BUILD, NODE, "clean", START_TIME)
        self.assertEqual(processes, [expected])
