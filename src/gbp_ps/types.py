"""gbp-ps data types"""
import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildProcess:
    """The basic build process type"""
    machine: str
    build_id: str
    build_host: str
    package: str
    phase: str
    start_time: dt.datetime
