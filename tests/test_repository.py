"""Tests for gbp-ps repositories"""
# pylint: disable=missing-docstring, duplicate-code
import datetime as dt
from dataclasses import replace

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.repository import DjangoRepository, RedisRepository, RepositoryType
from gbp_ps.types import BuildProcess

from . import TestCase, parametrized

BACKENDS: list[tuple[RepositoryType]] = [(DjangoRepository(),), (RedisRepository(),)]


class RepositoryTests(TestCase):
    def setUp(self) -> None:
        for [backend] in BACKENDS:
            backend.clear()

    @parametrized(BACKENDS)
    def test_add_process(self, backend: RepositoryType) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)
        self.assertEqual([*backend.get_processes()], [build_process])

    @parametrized(BACKENDS)
    def test_add_process_when_already_exists(self, backend: RepositoryType) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)

        with self.assertRaises(RecordAlreadyExists):
            backend.add_process(build_process)

    @parametrized(BACKENDS)
    def test_update_process(self, backend: RepositoryType) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)

        build_process = replace(build_process, phase="postinst")

        backend.update_process(build_process)

        self.assertEqual([*backend.get_processes()], [build_process])

    @parametrized(BACKENDS)
    def test_update_process_when_process_not_in_db(
        self, backend: RepositoryType
    ) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )

        with self.assertRaises(RecordNotFoundError):
            backend.update_process(build_process)

    @parametrized(BACKENDS)
    def test_get_processes_with_empty_list(self, backend: RepositoryType) -> None:
        self.assertEqual([*backend.get_processes()], [])

    @parametrized(BACKENDS)
    def test_get_processes_with_process(self, backend: RepositoryType) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)

        self.assertEqual([*backend.get_processes()], [build_process])

    @parametrized(BACKENDS)
    def test_get_processes_with_final_process(self, backend: RepositoryType) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)

        self.assertEqual([*backend.get_processes()], [])

    @parametrized(BACKENDS)
    def test_get_processes_with_include_final_process(
        self, backend: RepositoryType
    ) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend.add_process(build_process)

        self.assertEqual([*backend.get_processes(include_final=True)], [build_process])
