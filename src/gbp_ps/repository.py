"""Database Repository for build processes"""
from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterable
from typing import Protocol

import redis

from gbp_ps.exceptions import (
    RecordAlreadyExists,
    RecordNotFoundError,
    UpdateNotAllowedError,
)
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

ENCODING = "UTF-8"


class RepositoryType(Protocol):
    """BuildProcess Repository"""

    def __init__(self, settings: Settings) -> None:
        """Initializer"""

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """


def Repo(settings: Settings) -> RepositoryType:  # pylint: disable=invalid-name
    """Return a Repository

    If the GBP_PS_REDIS_URL environment variable is defined and non-empty, return the
    RedisRepository. Otherwise the DjangoRepository is returned.
    """
    if settings.STORAGE_BACKEND == "redis":
        return RedisRepository(settings)

    return DjangoRepository(settings)  # pragma: no cover


class RedisRepository:
    """Redis backend for the process table"""

    def __init__(self, settings: Settings) -> None:
        self._redis = redis.Redis.from_url(settings.REDIS_URL)
        self._key = settings.REDIS_KEY
        self.time = settings.REDIS_KEY_EXPIRATION

    def __repr__(self) -> str:
        return type(self).__name__

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

        ensure_updateable(self.redis_to_process(key, previous_value), process)

        new_value: dict[str, str] = json.loads(previous_value)
        new_value["phase"] = process.phase
        new_value["build_host"] = process.build_host
        self._redis.set(key, json.dumps(new_value).encode(ENCODING))

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        keys = self._redis.keys(f"{self._key}:*".encode(ENCODING))
        processes = []

        for key in keys:
            if not (value := self._redis.get(key)):
                continue

            process = self.redis_to_process(key, value)

            if include_final or not process.is_finished():
                processes.append(process)

        processes.sort(key=lambda process: process.start_time)
        return processes


class DjangoRepository:
    """Django ORM-based BuildProcess repository"""

    def __init__(self, _settings: Settings) -> None:
        # pylint: disable=import-outside-toplevel
        from gbp_ps.models import BuildProcess as BuildProcessModel

        self.model: type[BuildProcessModel] = BuildProcessModel

    def __repr__(self) -> str:
        return type(self).__name__

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        # pylint: disable=import-outside-toplevel
        import django.db.utils
        from django.db.models import Q

        # If this package exists in another build, remove it. This (usually) means the
        # other build failed
        self.model.objects.filter(
            ~Q(build_id=process.build_id),
            machine=process.machine,
            package=process.package,
        ).delete()

        build_process_model = self.model.from_object(process)

        try:
            build_process_model.save()
        except django.db.utils.IntegrityError:
            raise RecordAlreadyExists(process) from None

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        try:
            build_process_model = self.model.objects.get(
                machine=process.machine,
                build_id=process.build_id,
                package=process.package,
            )
        except self.model.DoesNotExist:
            raise RecordNotFoundError(process) from None

        ensure_updateable(build_process_model.to_object(), process)

        build_process_model.phase = process.phase
        build_process_model.build_host = process.build_host
        build_process_model.save()

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        query = self.model.objects.order_by("start_time")
        if not include_final:
            query = query.exclude(phase__in=BuildProcess.final_phases)

        return (model.to_object() for model in query)


def ensure_updateable(old: BuildProcess, new: BuildProcess) -> None:
    """Raise an exception if old should not be updated to new"""
    if old.build_host != new.build_host and new.phase in BuildProcess.final_phases:
        raise UpdateNotAllowedError(old, new)


def add_or_update_process(repo: RepositoryType, process: BuildProcess) -> None:
    """Add or update the process

    Adds the process to the process table. If the process already exists, does an
    update.

    If the update is not allowed (e.g. the previous build host is attempting to finalize
    the process) update is not ignored.
    """
    try:
        repo.update_process(process)
    except RecordNotFoundError:
        repo.add_process(process)
    except UpdateNotAllowedError:
        pass
