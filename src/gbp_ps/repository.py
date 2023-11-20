"""Database Repository for build processes"""
from __future__ import annotations

import datetime as dt
import json
import os
from collections.abc import Iterable
from typing import Any

import redis

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.types import FINAL_PROCESS_PHASES, BuildProcess, RepositoryType

ENCODING = "UTF-8"
DEFAULT_REDIS_KEY_EXPIRATION = 3600 * 24


def get_repo() -> RepositoryType:
    """Return a Repository

    If the GBP_PS_REDIS_URL environment variable is defined and non-empty, return the
    RedisRepository. Otherwise the DjangoRepository is returned.
    """
    if os.environ.get("GBP_PS_REDIS_URL"):
        return RedisRepository()

    return DjangoRepository()  # pragma: no cover


class RedisRepository:
    """Redis backend for the process table"""

    def __init__(
        self,
        *,
        url: str | None = None,
        key: str | None = None,
        key_expiration: int | None = None,
        **_kwargs: Any,
    ) -> None:
        if not url:
            url = os.environ.get("GBP_PS_REDIS_URL", "redis://localhost:6379")

        if not key:
            key = os.environ.get("GBP_PS_REDIS_KEY", "gbp-ps")

        if not key_expiration:
            key_expiration = int(
                os.environ.get("GBP_PS_KEY_EXPIRATION", DEFAULT_REDIS_KEY_EXPIRATION)
            )

        self._redis = redis.Redis.from_url(url)
        self._key = key
        self.time = key_expiration

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
        build_id = process.build_id.encode(ENCODING)
        pattern = f"{self._key}:{process.machine}:{process.package}:*".encode(ENCODING)
        for key in self._redis.keys(pattern):
            if key.split(b":")[3] != build_id:
                self._redis.delete(key)

        key, value = self.process_to_redis(process)
        previous = self._redis.get(key)

        if previous and self.redis_to_process(key, previous).is_same_as(process):
            raise RecordAlreadyExists(process)

        self._redis.setex(key, self.time, value)

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        key = self.key(process)
        previous_value = self._redis.get(key)

        if previous_value is None:
            raise RecordNotFoundError(process)

        new_value: dict[str, str] = json.loads(previous_value)
        new_value["phase"] = process.phase
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

            if include_final or process.phase not in FINAL_PROCESS_PHASES:
                processes.append(process)

        processes.sort(key=lambda process: process.start_time)
        return processes


class DjangoRepository:
    """Django ORM-based BuildProcess repository"""

    def __init__(self, **_kwargs: Any) -> None:
        # pylint: disable=import-outside-toplevel
        from gbp_ps.models import BuildProcess as BuildProcessModel

        self.model: type[BuildProcessModel] = BuildProcessModel

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
                build_host=process.build_host,
                package=process.package,
            )
        except self.model.DoesNotExist:
            raise RecordNotFoundError(process) from None

        build_process_model.phase = process.phase
        build_process_model.save()

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        query = self.model.objects.order_by("start_time")
        if not include_final:
            query = query.exclude(phase__in=FINAL_PROCESS_PHASES)

        return (model.to_object() for model in query)
