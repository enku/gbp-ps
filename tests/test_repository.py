"""Tests for gbp-ps repositories"""

# pylint: disable=missing-docstring, duplicate-code
from dataclasses import replace
from typing import Any, Callable
from unittest import mock

import fakeredis
from unittest_fixtures import Fixtures, given, parametrized, where

from gbp_ps.exceptions import (
    RecordAlreadyExists,
    RecordNotFoundError,
    UpdateNotAllowedError,
)
from gbp_ps.repository import Repo, RepositoryType, add_or_update_process, sqlite
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

from . import TestCase, make_build_process

HOST = 0
REDIS_FROM_URL = "gbp_ps.repository.redis.redis.Redis.from_url"


def get_repo(backend: str, settings: Settings) -> RepositoryType:
    global HOST  # pylint: disable=global-statement
    settings = replace(settings, STORAGE_BACKEND=backend)
    if backend == "redis":
        fake_redis = fakeredis.FakeRedis(host=f"host{(HOST := HOST + 1)}")
        repo_patch = mock.patch(REDIS_FROM_URL, return_value=fake_redis)
    else:
        repo_patch = mock.MagicMock()

    with repo_patch:
        return Repo(settings)


def repos(*names: str) -> Callable[[Callable[[Any, str], None]], None]:
    return parametrized([[name] for name in names])


@given("environ", "settings", "build_process")
@where(
    environ={
        "GBP_PS_KEY_EXPIRATION": "3600",
        "GBP_PS_REDIS_KEY": "gbp-ps-test",
        "GBP_PS_STORAGE_BACKEND": "sqlite",
    },
    build_process__phase="compile",
)
class RepositoryTests(TestCase):
    @repos("django", "redis", "sqlite")
    def test_add_process(self, backend: str, fixtures: Fixtures) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)
        self.assertEqual([*repo.get_processes()], [build_process])

    @repos("django", "redis", "sqlite")
    def test_add_process_when_already_exists(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)

        with self.assertRaises(RecordAlreadyExists):
            repo.add_process(build_process)

    @repos("django", "redis", "sqlite")
    def test_add_process_same_package_in_different_builds_exist_only_once(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        dead_process: BuildProcess = fixtures.build_process
        repo.add_process(dead_process)
        new_process = replace(
            dead_process, build_id=str(int(dead_process.build_id) + 1)
        )
        repo.add_process(new_process)

        self.assertEqual([*repo.get_processes()], [new_process])

    @repos("django", "redis", "sqlite")
    def test_update_process(self, backend: str, fixtures: Fixtures) -> None:
        repo = get_repo(backend, fixtures.settings)
        orig_process: BuildProcess = replace(fixtures.build_process, phase="compile")
        repo.add_process(orig_process)

        updated_process = replace(orig_process, phase="postinst")

        repo.update_process(updated_process)

        expected = replace(orig_process, phase="postinst")
        self.assertEqual([*repo.get_processes()], [expected])

    @repos("django", "redis", "sqlite")
    def test_update_process_finalize_when_not_owned(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        # This demonstrates the concept of build host "ownership". A a process can only
        # be updated with a "final" phase if the build host is the same. Otherwise it
        # should raise an exception
        repo = get_repo(backend, fixtures.settings)
        process1 = make_build_process(add_to_repo=False)
        repo.add_process(process1)
        process2 = replace(process1, build_host="badhost", phase="clean")

        with self.assertRaises(UpdateNotAllowedError):
            repo.update_process(process2)

    @repos("django", "redis", "sqlite")
    def test_new_build_does_not_wipe_out_previous_if_no_packages(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        # We want to demonstate the following scenario
        #
        # | t | machine | build | package  | phase |
        # |---|---------|-------|----------|-------|
        # | 1 | babette |     1 | pipeline | clean |
        # | 2 | babette |     2 | pipeline | world |
        # | 3 | babette |     1 | pipeline | index |
        #
        # In this scenario, the update in t3 should not wipe out t2
        repo = get_repo(backend, fixtures.settings)

        t1 = make_build_process(
            machine="babette",
            build_id="1",
            package="pipeline",
            phase="clean",
            add_to_repo=False,
        )
        t2 = make_build_process(
            machine="babette",
            build_id="2",
            package="pipeline",
            phase="world",
            add_to_repo=False,
        )
        t3 = make_build_process(
            machine="babette",
            build_id="1",
            package="pipeline",
            phase="index",
            add_to_repo=False,
        )
        add_or_update_process(repo, t1)
        add_or_update_process(repo, t2)
        add_or_update_process(repo, t3)

        processes = set(repo.get_processes())

        self.assertEqual({t2, t3}, processes)

    @repos("django", "redis")
    def test_add_or_update_process_can_handle_buildhost_changes(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        orig_process: BuildProcess = replace(fixtures.build_process, phase="clean")
        repo.add_process(orig_process)

        updated_process = replace(orig_process, build_host="gbp", phase="pull")

        add_or_update_process(repo, updated_process)

        expected = replace(orig_process, build_host="gbp", phase="pull")
        self.assertEqual([*repo.get_processes()], [expected])

    @repos("django", "redis", "sqlite")
    def test_add_or_update_ignores_notallowederror(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        process1 = make_build_process(add_to_repo=False)
        repo.add_process(process1)
        process2 = replace(process1, build_host="badhost", phase="clean")

        add_or_update_process(repo, process2)

        self.assertEqual([*repo.get_processes()], [process1])

    @repos("django", "redis", "sqlite")
    def test_update_process_when_process_not_in_db(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = fixtures.build_process

        with self.assertRaises(RecordNotFoundError):
            repo.update_process(build_process)

    @repos("django", "redis", "sqlite")
    def test_get_processes_with_empty_list(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        self.assertEqual([*repo.get_processes()], [])

    @repos("django", "redis", "sqlite")
    def test_get_processes_with_process(self, backend: str, fixtures: Fixtures) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes()], [build_process])

    @repos("django", "redis", "sqlite")
    def test_get_processes_with_final_process(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = replace(fixtures.build_process, phase="postrm")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes()], [])

    @repos("django", "redis", "sqlite")
    def test_get_processes_with_include_final_process(
        self, backend: str, fixtures: Fixtures
    ) -> None:
        repo = get_repo(backend, fixtures.settings)
        build_process: BuildProcess = replace(fixtures.build_process, phase="postrm")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes(include_final=True)], [build_process])

    @repos("django", "redis", "sqlite")
    def test_get_processes_with_machine(self, backend: str, fixtures: Fixtures) -> None:
        repo = get_repo(backend, fixtures.settings)
        repo.add_process(fixtures.build_process)
        build_process = replace(fixtures.build_process, machine="laika")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes(machine="laika")], [build_process])

    def test_repo_factory_success(self, fixtures: Fixtures) -> None:
        settings = replace(fixtures.settings, STORAGE_BACKEND="sqlite")
        repo = Repo(settings)

        self.assertTrue(isinstance(repo, sqlite.SqliteRepository))

    def test_repo_factory_failure(self, fixtures: Fixtures) -> None:
        settings = replace(fixtures.settings, STORAGE_BACKEND="bogus")

        with self.assertRaises(ValueError):
            Repo(settings)
