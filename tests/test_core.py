"""Unit tests for gbp-ps"""
# pylint: disable=missing-docstring
import datetime as dt
from dataclasses import replace

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.types import BuildProcess

from . import TestCase


class GetProcessesTests(TestCase):
    def test_with_empty_list(self) -> None:
        self.assertEqual([*self.repo.get_processes()], [])

    def test_with_process(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)

        self.assertEqual([*self.repo.get_processes()], [build_process])

    def test_with_final_process(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)

        self.assertEqual([*self.repo.get_processes()], [])

    def test_with_include_final_process(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)

        self.assertEqual(
            [*self.repo.get_processes(include_final=True)], [build_process]
        )


class AddProcessTests(TestCase):
    def test(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)
        self.assertEqual([*self.repo.get_processes()], [build_process])

    def test_when_already_exists(self) -> None:
        # Records should key on machine, build_id, build_host, package
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)

        with self.assertRaises(RecordAlreadyExists):
            self.repo.add_process(build_process)


class UpdateProcessTests(TestCase):
    def test(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        self.repo.add_process(build_process)

        build_process = replace(build_process, phase="postinst")

        self.repo.update_process(build_process)

        self.assertEqual([*self.repo.get_processes()], [build_process])

    def test_when_process_not_in_db(self) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )

        with self.assertRaises(RecordNotFoundError):
            self.repo.update_process(build_process)
