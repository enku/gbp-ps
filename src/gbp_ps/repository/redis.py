"""Redis RepositoryType"""

import datetime as dt
import functools
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Self

import ormsgpack
import redis

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

ENCODING = "ascii"

dumps: Callable[[Any], bytes] = functools.partial(
    ormsgpack.packb, option=ormsgpack.OPT_NAIVE_UTC
)
loads: Callable[[bytes], Any] = ormsgpack.unpackb  # pylint: disable=no-member


@dataclass(kw_only=True, frozen=True, slots=True)
class Key:
    """Redis key bytes parsed"""

    redis_key: str
    machine: str
    build_id: str
    package: str

    def __bytes__(self) -> bytes:
        return (
            f"{self.redis_key}:{self.machine}:{self.package}:{self.build_id}"
        ).encode(ENCODING)

    @classmethod
    def from_bytes(cls, b: bytes) -> Self:
        """Return the redis key from bytes"""
        string = b.decode(ENCODING)
        redis_key, machine, package, build_id = string.split(":")

        return cls(
            redis_key=redis_key, machine=machine, build_id=build_id, package=package
        )

    @classmethod
    def from_process(cls, process: BuildProcess, redis_key: str) -> Self:
        """Return Key given BuildProcess and redis_key"""
        return cls(
            redis_key=redis_key,
            machine=process.machine,
            build_id=process.build_id,
            package=process.package,
        )


class RedisRepository:
    """Redis backend for the process table"""

    def __init__(self, settings: Settings) -> None:
        self._redis = redis.Redis.from_url(settings.REDIS_URL)
        self._key = settings.REDIS_KEY
        self.time = settings.REDIS_KEY_EXPIRATION

    def key(self, process: BuildProcess) -> bytes:
        """Return the redis key for the given BuildProcess"""
        return bytes(Key.from_process(process, self._key))

    def value(self, process: BuildProcess) -> bytes:
        """Return the redis value for the given BuildProcess"""
        return dumps((process.build_host, process.phase, process.start_time))

    def process_to_redis(self, process: BuildProcess) -> tuple[bytes, bytes]:
        """Return the redis key and value for the given BuildProcess"""
        return self.key(process), self.value(process)

    def redis_to_process(self, key_bytes: bytes, value: bytes) -> BuildProcess:
        """Convert the given key and value to a BuildProcess"""
        key = Key.from_bytes(key_bytes)
        data = loads(value)

        return BuildProcess(
            build_host=data[0],
            build_id=key.build_id,
            machine=key.machine,
            package=key.package,
            phase=data[1],
            start_time=dt.datetime.fromisoformat(data[2]),
        )

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        # If this package exists in another build, remove it. This (usually) means the
        # other build failed
        self.delete_existing_processes(process)
        key, value = self.process_to_redis(process)
        previous = self._redis.get(key)

        if previous and self.redis_to_process(key, previous).is_same_as(process):
            raise RecordAlreadyExists(process)

        self._redis.setex(key, self.time, value)

    def delete_existing_processes(self, process: BuildProcess) -> int:
        """Delete existing processes like process

        By "existing" we mean processes in Redis that have the same machine and package
        but different build_id.

        Return the number of processes deleted.
        """
        build_id = process.build_id
        deleted_count = 0
        pattern = f"{self._key}:{process.machine}:{process.package}:*".encode(ENCODING)
        for key_bytes in self._redis.keys(pattern):
            key = Key.from_bytes(key_bytes)
            if key.build_id != build_id:
                value = self._redis.get(key_bytes)
                assert value
                existing_process = self.redis_to_process(key_bytes, value)
                if existing_process.phase in BuildProcess.build_phases:
                    self._redis.delete(key_bytes)
                    deleted_count += 1
        return deleted_count

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        key_bytes = self.key(process)
        previous_value = self._redis.get(key_bytes)

        if previous_value is None:
            raise RecordNotFoundError(process)

        self.redis_to_process(key_bytes, previous_value).ensure_updateable(process)
        new_value = (process.build_host, process.phase, loads(previous_value)[2])
        self._redis.setex(key_bytes, self.time, dumps(new_value))

    def get_processes(
        self, include_final: bool = False, machine: str | None = None
    ) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        processes = []

        for key_bytes in self._redis.keys(f"{self._key}:*".encode(ENCODING)):
            if machine and Key.from_bytes(key_bytes).machine != machine:
                continue
            if value := self._redis.get(key_bytes):
                process = self.redis_to_process(key_bytes, value)

                if include_final or not process.is_finished():
                    processes.append(process)

        processes.sort(key=lambda process: process.start_time)
        return processes
