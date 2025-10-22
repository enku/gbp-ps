"""Repository that uses GBP's site cache"""

# This was originally envisioned to simply be a nearly identical implementation as the
# redis.RedisRepository storage backend however, as it turns out, it is in fact very
# different and so here is the explanation and rationale:
#
# The redis implementation has a 1:1 key:process ratio. Each process is an entry in
# redis. The key is calculated from the parts of a process that don't change: that being
# the machine, build_id, and package. Getting a list of processes is as simple as
# listing the KEYS in the redis db. The values for each key are the "remaining" parts of
# the build process that are not part of the key. With they key they get "assembled"
# into a BuildProcess and returned in the .get_processes() method. Each entry in redis
# is set with an expiration, and so redis automatically expires any keys (processes)
# after the expiration period.
#
# As it turns out, we can not simply reimplement this design when using Django's cache
# API. The main reason is that, unlike the redis API, Django doesn't have a method for
# "listing keys". It's simply not part of the API. Therefore this design keeps all the
# processes in a single key, "table". The table is a Python dict with keys similar to
# the redis keys and value being the entire BuildProcess serialized. However having
# everything in one key poses a couple of challenges: number one being simultaneous
# access. Because there is only one key that may need to be updated by multiple
# requests, we need to implement locking. Therefore anything that needs to update the
# table must do it within a lock context. We're implementing our own locking here, also
# using Django's cache API, and I'll have to keep an eye on things for a while to see if
# the locking is actually a good enough implementation.  The second issue is that since
# each process is not a separate key we don't get the redis auto-expire. So we need to
# "manually" expire old processes. This is done by periodically  (when get_processes()
# is called) scanning through the table for "old" processes and removing them.
#
# So this is implementing its own distributed locking and its own expiration. Not fun.
# We'll see if it actually works. This is so much not the "simple port" from the redis
# implementation that I thought it would be.


import datetime as dt
import uuid
from contextlib import contextmanager
from dataclasses import replace
from functools import cache as func_cache
from functools import lru_cache
from time import monotonic, sleep
from typing import TYPE_CHECKING, Generator, Iterable, cast

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

if TYPE_CHECKING:
    from gentoo_build_publisher.cache import GBPSiteCache


type ProcessTable = dict[str, BuildProcess]
now = dt.datetime.now


class SiteCacheRepository:
    """GBP site cache backend for the process table"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.expiration = dt.timedelta(seconds=settings.SITECACHE_PROCESS_EXPIRATION)

        self.cache.set("table", self.cache.get("table", {}))

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        self.delete_existing_processes(process)
        key = get_key(process)

        if key in self.get_table():
            raise RecordAlreadyExists(process)

        with self.lock():
            self.set_table({**self.get_table(), **{key: process}})

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        key = get_key(process)

        if (existing := self.get_table().get(key, None)) is None:
            raise RecordNotFoundError(process)

        existing.ensure_updateable(process)
        new = replace(existing, phase=process.phase, build_host=process.build_host)

        with self.lock():
            self.set_table({**self.get_table(), **{key: new}})

    def get_processes(
        self, include_final: bool = False, machine: str | None = None
    ) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        return [
            process
            for process in self.ps()
            if (not machine or process.machine == machine)
            and (include_final or not process.is_finished())
        ]

    def delete_existing_processes(self, process: BuildProcess) -> None:
        """Delete existing processes like process

        By "existing" we mean processes in cache that have the same machine and package
        but different build_id.
        """
        with self.lock():
            self.set_table(
                {
                    key: existing
                    for key, existing in self.get_table().items()
                    if not same_proc_different_build(existing, process)
                }
            )

    def ps(self) -> Iterable[BuildProcess]:
        """Return a list of all processes"""
        if self.cache.contains("purged"):
            yield from self.get_table().values()
            return

        expired: set[str] = set()

        with self.lock():
            for key, process in self.get_table().items():
                if (now(dt.UTC) - process.start_time) < self.expiration:
                    yield process
                else:
                    expired.add(key)

            self.cache.set("purged", monotonic())

            if not expired:
                return

            # purge out expired keys
            self.set_table(
                {
                    key: process
                    for key, process in self.get_table().items()
                    if key not in expired
                }
            )

    def get_table(self) -> ProcessTable:
        """Return the process table from cache"""
        return cast(ProcessTable, self.cache.get("table"))

    def set_table(self, table: ProcessTable) -> None:
        """Set the given process table in the cache"""
        self.cache.set("table", table)

    @contextmanager
    def lock(self, timeout: float = 10.0) -> Generator[str, None, None]:
        """Use the cache create a lock

        The lock automatically times out after settings.SITECACHE_PROCESS_EXPIRATION
        """
        start = monotonic()
        key = str(uuid.uuid4())
        cache = self.cache

        while True:
            if monotonic() - start >= timeout:
                raise TimeoutError()

            if cache.contains("lock"):
                sleep(0.1)
                continue

            self._set_lock(key)

            if cache.get("lock", None) == key:
                break

        yield key

        cache.delete("lock")

    def _set_lock(self, key: str) -> None:
        """Sets the lock with the given key

        A separate method so that it can be patched for testing.
        """
        self.cache.set("lock", key)

    @property
    @func_cache  # pylint: disable=method-cache-max-size-none
    def cache(self) -> "GBPSiteCache":
        """Return the root gbp-ps cache"""
        # avoid race with django
        # pylint: disable=import-outside-toplevel
        from gentoo_build_publisher.cache import cache as site_cache

        cache = site_cache / "ps"
        cache.set_timeout(self.settings.SITECACHE_PROCESS_EXPIRATION)

        return cache


@lru_cache
def get_key(process: BuildProcess) -> str:
    """Return process table key for the given process"""
    return f"{process.machine}:{process.build_id}:{process.package}"


def same_proc_different_build(proc1: BuildProcess, proc2: BuildProcess) -> bool:
    """Return True if the two procs are the same except on different builds"""
    return (
        proc1.package == proc2.package
        and proc1.machine == proc2.machine
        and proc1.build_id != proc2.build_id
        and proc1.phase in BuildProcess.build_phases
    )
