"""Redis RepositoryType"""

import datetime as dt
import json
from typing import Iterable

import redis

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

ENCODING = "UTF-8"


class RedisRepository:
    """Redis backend for the process table"""

    def __init__(self, settings: Settings) -> None:
        self._redis = redis.Redis.from_url(settings.REDIS_URL)
        self._key = settings.REDIS_KEY
        self.time = settings.REDIS_KEY_EXPIRATION

    def key(self, process: BuildProcess) -> bytes:
        """Return the redis key for the given BuildProcess"""
        return f"{self._key}:{process.machine}:{process.package}:{process.build_id}".encode(
            ENCODING
        )

    def value(self, process: BuildProcess) -> bytes:
        """Return the redis value for the given BuildProcess"""
        return json.dumps(
            {
                "build_host": process.build_host,
                "phase": process.phase,
                "start_time": process.start_time.isoformat(),
            }
        ).encode(ENCODING)

    def process_to_redis(self, process: BuildProcess) -> tuple[bytes, bytes]:
        """Return the redis key and value for the given BuildProcess"""
        return self.key(process), self.value(process)

    def redis_to_process(self, key: bytes, value: bytes) -> BuildProcess:
        """Convert the given key and value to a BuildProcess"""
        machine, package, build_id = key.decode(ENCODING).split(":")[1:]
        data = json.loads(value.decode(ENCODING))

        return BuildProcess(
            build_host=data["build_host"],
            build_id=build_id,
            machine=machine,
            package=package,
            phase=data["phase"],
            start_time=dt.datetime.fromisoformat(data["start_time"]),
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
        build_id = process.build_id.encode(ENCODING)
        deleted_count = 0
        pattern = f"{self._key}:{process.machine}:{process.package}:*".encode(ENCODING)
        for key in self._redis.keys(pattern):
            if key.split(b":")[3] != build_id:
                self._redis.delete(key)
                deleted_count += 1
        return deleted_count

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        key = self.key(process)
        previous_value = self._redis.get(key)

        if previous_value is None:
            raise RecordNotFoundError(process)

        self.redis_to_process(key, previous_value).ensure_updateable(process)
        new_value = {
            **json.loads(previous_value),
            **{"phase": process.phase, "build_host": process.build_host},
        }
        self._redis.setex(key, self.time, json.dumps(new_value).encode(ENCODING))

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        processes = []

        for key in self._redis.keys(f"{self._key}:*".encode(ENCODING)):
            if value := self._redis.get(key):
                process = self.redis_to_process(key, value)

                if include_final or not process.is_finished():
                    processes.append(process)

        processes.sort(key=lambda process: process.start_time)
        return processes
