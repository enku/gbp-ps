# pylint: disable=missing-docstring
import threading
import time
from dataclasses import replace
from unittest import mock

from gbp_testkit import fixtures as testkit
from gentoo_build_publisher.cache import clear as cache_clear
from unittest_fixtures import Fixtures, fixture, given, where

from gbp_ps.repository import Repo
from gbp_ps.repository.sitecache import SiteCacheRepository, get_key
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

from . import lib


@fixture()
def table_fixture(_: Fixtures, count: int = 7) -> dict[str, BuildProcess]:
    return {
        get_key(build_process): build_process
        for build_process in lib.BuildProcessFactory.create_batch(count)
    }


@given(monotonic=testkit.patch)
@where(monotonic__target="gbp_ps.repository.sitecache.monotonic")
@given(sleep=testkit.patch)
@where(sleep__target="gbp_ps.repository.sitecache.sleep")
@given(cache_clear=lambda _: cache_clear())
@given(repo=lambda _: Repo(Settings(STORAGE_BACKEND="sitecache")))
class SiteCacheLockTests(lib.TestCase):
    def test_unlocked(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        monotonic = fixtures.monotonic
        monotonic.return_value = 100.0

        with repo.lock() as key:
            self.assertEqual(repo.cache.get("lock"), key)

        self.assertFalse(hasattr(repo.cache, "lock"))

    def test_already_locked(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        repo.cache.set("lock", "mykey")
        monotonic = fixtures.monotonic
        monotonic.return_value = 100.0

        locked = threading.Event()
        release = threading.Event()
        thread = threading.Thread(target=lock_in_thread, args=(repo, locked, release))
        thread.start()

        try:
            self.assertEqual(repo.cache.get("lock"), "mykey")
            repo.cache.delete("lock")
            locked.wait(timeout=5)
            self.assertNotEqual(repo.cache.get("lock"), "mykey")
        finally:
            release.set()

    def test_set_but_not_my_key(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        orig_set_lock = repo._set_lock  # pylint: disable=protected-access
        monotonic = fixtures.monotonic
        monotonic.return_value = 100.0

        def hijack_lock(_: str) -> None:
            repo.cache.set("lock", "otherkey")

        try:
            with mock.patch.object(repo, "_set_lock") as set_lock:
                set_lock.side_effect = hijack_lock

                locked = threading.Event()
                release = threading.Event()
                thread = threading.Thread(
                    target=lock_in_thread, args=(repo, locked, release)
                )
                thread.start()

                time.sleep(0.5)
                self.assertEqual(repo.cache.get("lock"), "otherkey")

                set_lock.side_effect = orig_set_lock
                repo.cache.delete("lock")
                locked.wait(timeout=5)
                self.assertNotEqual(repo.cache.get("lock"), "otherkey")
        finally:
            release.set()

    def test_timeout(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        monotonic = fixtures.monotonic
        monotonic.side_effect = 100.0, 120.0

        with self.assertRaises(TimeoutError):
            with repo.lock():
                pass


@given(cache_clear=lambda _: cache_clear())
@given(repo=lambda _: Repo(Settings(STORAGE_BACKEND="sitecache")))
@given(table_fixture)
@given(lock=testkit.patch)
@where(lock__target="gbp_ps.repository.sitecache.SiteCacheRepository.lock")
class SiteCachePSTests(lib.TestCase):
    def test_yields_table(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        table = fixtures.table
        repo.set_table(table)

        entries = set(repo.ps())

        self.assertEqual(entries, set(table.values()))

    def test_with_purged_key_does_not_lock(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        repo.cache.set("purged", "whatever")
        repo.set_table({})

        set(repo.ps())

        fixtures.lock.assert_not_called()

    def test_no_expired_and_no_purge_key_does_not_lock(
        self, fixtures: Fixtures
    ) -> None:
        repo: SiteCacheRepository = fixtures.repo
        repo.cache.set("purged", "whatever")
        repo.set_table({})

        set(repo.ps())

        fixtures.lock.assert_not_called()

    def test_expired_and_no_purge_key_does_lock(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        table = fixtures.table
        key, process = list(table.items())[0]
        table[key] = replace(process, start_time=process.start_time - repo.expiration)
        repo.set_table(table)

        set(repo.ps())

        fixtures.lock.assert_called()

    def test_expired_and_no_purge_key_sets_purge_key(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        repo.set_table({})

        set(repo.ps())

        self.assertTrue(repo.cache.contains("purged"))

    def test_expired_keys_are_not_returned(self, fixtures: Fixtures) -> None:
        repo: SiteCacheRepository = fixtures.repo
        table = fixtures.table
        key, process = list(table.items())[0]
        table[key] = replace(process, start_time=process.start_time - repo.expiration)
        repo.set_table(table)

        entries = set(repo.ps())

        del table[key]
        self.assertEqual(entries, set(table.values()))


def lock_in_thread(
    repo: SiteCacheRepository, locked: threading.Event, release: threading.Event
) -> None:
    with repo.lock():
        locked.set()
        release.wait(timeout=5)
