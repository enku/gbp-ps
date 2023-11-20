"""Tests for gbp-ps repositories"""
# pylint: disable=missing-docstring, duplicate-code
import datetime as dt
from dataclasses import replace

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.repository import DjangoRepository, RedisRepository
from gbp_ps.types import BuildProcess, RepositoryType

from . import TestCase, parametrized

BACKENDS: list[tuple[type[RepositoryType]]] = [(DjangoRepository,), (RedisRepository,)]


class RepositoryTests(TestCase):
    @parametrized(BACKENDS)
    def test_add_process(self, backend: type[RepositoryType]) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(build_process)
        self.assertEqual([*backend().get_processes()], [build_process])

    @parametrized(BACKENDS)
    def test_add_process_when_already_exists(
        self, backend: type[RepositoryType]
    ) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(build_process)

        with self.assertRaises(RecordAlreadyExists):
            backend().add_process(build_process)

    @parametrized(BACKENDS)
    def test_add_process_same_package_in_different_builds_exist_only_once(
        self, backend: type[RepositoryType]
    ) -> None:
        dead_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(dead_process)
        new_process = BuildProcess(
            machine="babette",
            build_id="1032",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 13, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(new_process)

        self.assertEqual([*backend().get_processes()], [new_process])

    @parametrized(BACKENDS)
    def test_update_process(self, backend: type[RepositoryType]) -> None:
        orig_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(orig_process)

        updated_process = replace(
            orig_process,
            phase="postinst",
            start_time=dt.datetime(2023, 11, 11, 12, 25, 18, tzinfo=dt.timezone.utc),
        )

        backend().update_process(updated_process)

        expected = replace(orig_process, phase="postinst")
        self.assertEqual([*backend().get_processes()], [expected])

    @parametrized(BACKENDS)
    def test_update_process_when_process_not_in_db(
        self, backend: type[RepositoryType]
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
            backend().update_process(build_process)

    @parametrized(BACKENDS)
    def test_get_processes_with_empty_list(self, backend: type[RepositoryType]) -> None:
        self.assertEqual([*backend().get_processes()], [])

    @parametrized(BACKENDS)
    def test_get_processes_with_process(self, backend: type[RepositoryType]) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="compile",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(build_process)

        self.assertEqual([*backend().get_processes()], [build_process])

    @parametrized(BACKENDS)
    def test_get_processes_with_final_process(
        self, backend: type[RepositoryType]
    ) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(build_process)

        self.assertEqual([*backend().get_processes()], [])

    @parametrized(BACKENDS)
    def test_get_processes_with_include_final_process(
        self, backend: type[RepositoryType]
    ) -> None:
        build_process = BuildProcess(
            machine="babette",
            build_id="1031",
            build_host="jenkins",
            package="sys-apps/systemd-254.5-r1",
            phase="postrm",
            start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        )
        backend().add_process(build_process)

        self.assertEqual(
            [*backend().get_processes(include_final=True)], [build_process]
        )
