"""gbp-ps data types"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from typing import Any

from .exceptions import UpdateNotAllowedError


@dataclass(frozen=True, slots=True, kw_only=True)
class BuildProcess:
    """The basic build process type"""

    machine: str
    build_id: str
    build_host: str
    package: str
    phase: str
    start_time: dt.datetime

    # BuildProcesses in any of these phases are considered "final"
    final_phases = {"", "clean", "cleanrm", "postrm"}

    # Build phases, in order (best as I can determine)
    build_phases = (
        "pretend",
        "setup",
        "unpack",
        "prepare",
        "configure",
        "compile",
        "test",
        "install",
        "package",
        "instprep",
        "preinst",
        "postinst",
    )

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

    def ensure_updateable(self, new: BuildProcess) -> None:
        """Raise an exception if process should not be updated to new"""
        if self.build_host != new.build_host and new.phase in BuildProcess.final_phases:
            raise UpdateNotAllowedError(self, new)

    def to_dict(self) -> dict[str, Any]:
        """Return BuildProcess as a GraphQL dict"""
        bp_dict = asdict(self)
        bp_dict["buildHost"] = bp_dict.pop("build_host")
        bp_dict["id"] = bp_dict.pop("build_id")
        bp_dict["startTime"] = bp_dict.pop("start_time").isoformat()

        return bp_dict

    def is_finished(self) -> bool:
        """Return True iff the BuildProcess is in a "final" phase"""
        return self.phase in self.final_phases
