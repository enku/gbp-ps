"""Database Repository for build processes"""

from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable
from typing import Any, Protocol

from gbp_ps.exceptions import RecordNotFoundError, UpdateNotAllowedError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

try:
    from gentoo_build_publisher.signals import dispatcher
except ImportError:
    dispatcher = None  # type: ignore[assignment]
else:
    from gentoo_build_publisher.types import Build

BACKENDS = {ep.name: ep for ep in importlib.metadata.entry_points(group="gbp_ps.repos")}


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

    def get_processes(
        self, include_final: bool = False, machine: str | None = None
    ) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """


def Repo(settings: Settings) -> RepositoryType:  # pylint: disable=invalid-name
    """Return a Repository

    If the GBP_PS_REDIS_URL environment variable is defined and non-empty, return the
    RedisRepository. Otherwise the DjangoRepository is returned.
    """
    if entry_point := BACKENDS.get(settings.STORAGE_BACKEND):
        cls: type[RepositoryType] = entry_point.load()
        return cls(settings)

    raise ValueError(f"Invalid storage backend: {settings.STORAGE_BACKEND!r}")


def add_or_update_process(repo: RepositoryType, process: BuildProcess) -> None:
    """Add or update the process

    Adds the process to the process table. If the process already exists, does an
    update.

    If the update is not allowed (e.g. the previous build host is attempting to finalize
    the process) update is not ignored.
    """
    try:
        repo.update_process(process)
        maybe_emit("gbp_ps_update_process", process=process)
    except RecordNotFoundError:
        repo.add_process(process)
        maybe_emit("gbp_ps_add_process", process=process)
    except UpdateNotAllowedError:
        pass


def maybe_emit(signal: str, process: BuildProcess, **kwargs: Any) -> bool:
    """Emit the given signal if running under Gentoo Build Publisher

    Return True if the signal was emitted. Otherwise return False.
    """
    if dispatcher:
        build = Build(machine=process.machine, build_id=process.build_id)
        dispatcher.emit(signal, build=build, process=process, **kwargs)
        return True
    return False
