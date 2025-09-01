"""Tests for gbp-ps repositories"""

# pylint: disable=missing-docstring, duplicate-code
import importlib.metadata
from dataclasses import replace
from unittest import mock

import fakeredis
from unittest_fixtures import Fixtures, given, params, where

from gbp_ps.exceptions import (
    RecordAlreadyExists,
    RecordNotFoundError,
    UpdateNotAllowedError,
)
from gbp_ps.repository import Repo, RepositoryType, add_or_update_process, sqlite
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

from . import lib

BACKENDS = [ep.name for ep in importlib.metadata.entry_points(group="gbp_ps.repos")]
ENVIRON = {
    "GBP_PS_KEY_EXPIRATION": "3600",
    "GBP_PS_REDIS_KEY": "gbp-ps-test",
    "GBP_PS_STORAGE_BACKEND": "sqlite",
}
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


@params(backend=BACKENDS)
@given(repo=lambda f: get_repo(f.backend, f.settings))
@given(lib.settings, lib.build_process)
@where(environ=ENVIRON, build_process__phase="compile")
class RepositoryTests(lib.TestCase):
    def test_add_process(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)
        self.assertEqual([*repo.get_processes()], [build_process])

    def test_add_process_when_already_exists(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)

        with self.assertRaises(RecordAlreadyExists):
            repo.add_process(build_process)

    def test_add_process_same_package_in_different_builds_exist_only_once(
        self, fixtures: Fixtures
    ) -> None:
        repo = fixtures.repo
        dead_process: BuildProcess = fixtures.build_process
        repo.add_process(dead_process)
        new_process = replace(
            dead_process, build_id=str(int(dead_process.build_id) + 1)
        )
        repo.add_process(new_process)

        self.assertEqual([*repo.get_processes()], [new_process])

    def test_update_process(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        orig_process: BuildProcess = replace(fixtures.build_process, phase="compile")
        repo.add_process(orig_process)

        updated_process = replace(orig_process, phase="postinst")

        repo.update_process(updated_process)

        expected = replace(orig_process, phase="postinst")
        self.assertEqual([*repo.get_processes()], [expected])

    def test_update_process_finalize_when_not_owned(self, fixtures: Fixtures) -> None:
        # This demonstrates the concept of build host "ownership". A a process can only
        # be updated with a "final" phase if the build host is the same. Otherwise it
        # should raise an exception
        repo = fixtures.repo
        process1 = lib.make_build_process(add_to_repo=False)
        repo.add_process(process1)
        process2 = replace(process1, build_host="badhost", phase="clean")

        with self.assertRaises(UpdateNotAllowedError):
            repo.update_process(process2)

    def test_new_build_does_not_wipe_out_previous_if_no_packages(
        self, fixtures: Fixtures
    ) -> None:
        # We want to demonstrate the following scenario
        #
        # | t | machine | build | package  | phase |
        # |---|---------|-------|----------|-------|
        # | 1 | babette |     1 | pipeline | clean |
        # | 2 | babette |     2 | pipeline | world |
        # | 3 | babette |     1 | pipeline | index |
        #
        # In this scenario, the update in t3 should not wipe out t2
        repo = fixtures.repo

        t1 = lib.make_build_process(
            machine="babette",
            build_id="1",
            package="pipeline",
            phase="clean",
            add_to_repo=False,
        )
        t2 = lib.make_build_process(
            machine="babette",
            build_id="2",
            package="pipeline",
            phase="world",
            add_to_repo=False,
        )
        t3 = lib.make_build_process(
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

    def test_add_or_update_process_can_handle_buildhost_changes(
        self, fixtures: Fixtures
    ) -> None:
        if fixtures.backend == "sqlite":
            return

        repo = fixtures.repo
        orig_process: BuildProcess = replace(fixtures.build_process, phase="clean")
        repo.add_process(orig_process)

        updated_process = replace(orig_process, build_host="gbp", phase="pull")

        add_or_update_process(repo, updated_process)

        expected = replace(orig_process, build_host="gbp", phase="pull")
        self.assertEqual([*repo.get_processes()], [expected])

    def test_add_or_update_ignores_notallowederror(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        process1 = lib.make_build_process(add_to_repo=False)
        repo.add_process(process1)
        process2 = replace(process1, build_host="badhost", phase="clean")

        add_or_update_process(repo, process2)

        self.assertEqual([*repo.get_processes()], [process1])

    def test_update_process_when_process_not_in_db(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = fixtures.build_process

        with self.assertRaises(RecordNotFoundError):
            repo.update_process(build_process)

    def test_get_processes_with_empty_list(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        self.assertEqual([*repo.get_processes()], [])

    def test_get_processes_with_process(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = fixtures.build_process
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes()], [build_process])

    def test_get_processes_with_final_process(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = replace(fixtures.build_process, phase="postrm")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes()], [])

    def test_get_processes_with_include_final_process(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        build_process: BuildProcess = replace(fixtures.build_process, phase="postrm")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes(include_final=True)], [build_process])

    def test_get_processes_with_machine(self, fixtures: Fixtures) -> None:
        repo = fixtures.repo
        repo.add_process(fixtures.build_process)
        build_process = replace(fixtures.build_process, machine="laika")
        repo.add_process(build_process)

        self.assertEqual([*repo.get_processes(machine="laika")], [build_process])


@given(lib.settings)
class OtherRepositoryTests(lib.TestCase):
    def test_repo_factory_success(self, fixtures: Fixtures) -> None:
        settings = replace(fixtures.settings, STORAGE_BACKEND="sqlite")
        repo = Repo(settings)

        self.assertTrue(isinstance(repo, sqlite.SqliteRepository))

    def test_repo_factory_failure(self, fixtures: Fixtures) -> None:
        settings = replace(fixtures.settings, STORAGE_BACKEND="bogus")

        with self.assertRaises(ValueError):
            Repo(settings)
