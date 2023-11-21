"""gbp-ps data types"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Protocol

# BuildProcesses in any of these phases are considered "final"
FINAL_PROCESS_PHASES = {"", "clean", "cleanrm", "postrm"}


class RepositoryType(Protocol):
    """BuildProcess Repository"""

    def __init__(self, **_kwargs: Any) -> None:
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


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildProcess:
    """The basic build process type"""

    machine: str
    build_id: str
    build_host: str
    package: str
    phase: str
    start_time: dt.datetime

    def is_same_as(self, other: BuildProcess) -> bool:
        """Return true if the other build process is the same process

        Two process are considered the "same" if the machine, package and build_id are
        the same.
        """
        return (
            self.package == other.package
            and self.machine == other.machine
            and self.build_id == other.build_id
        )

    def to_dict(self) -> dict[str, Any]:
        """Return BuildProcess as a GraphQL dict"""
        bp_dict = asdict(self)
        bp_dict["buildHost"] = bp_dict.pop("build_host")
        bp_dict["id"] = bp_dict.pop("build_id")
        bp_dict["startTime"] = bp_dict.pop("start_time").isoformat()

        return bp_dict
