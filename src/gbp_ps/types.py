"""gbp-ps data types"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

# BuildProcesses in any of these phases are considered "final"
FINAL_PROCESS_PHASES = {"", "clean", "cleanrm", "postrm"}


@dataclass(frozen=True)
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
