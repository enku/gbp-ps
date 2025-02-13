"""GBP signal handlers for gbp-ps"""

import datetime as dt
import platform
from functools import cache, partial
from typing import Any

from gentoo_build_publisher.signals import dispatcher
from gentoo_build_publisher.types import Build

from gbp_ps.repository import Repo, RepositoryType, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

_now = partial(dt.datetime.now, tz=dt.UTC)
_NODE = platform.node()


def build_process(
    build: Build, build_host: str, phase: str, start_time: dt.datetime
) -> BuildProcess:
    """Return a BuildProcess with the given phase and timestamp"""
    return BuildProcess(
        build_host=build_host,
        build_id=build.build_id,
        machine=build.machine,
        package="pipeline",
        phase=phase,
        start_time=start_time,
    )


@cache
def repo() -> RepositoryType:
    """Return the Repository from from the environment variable settings"""
    return Repo(Settings.from_environ())


def set_process(build: Build, phase: str) -> None:
    """Add or update the given Build process in the repo"""
    add_or_update_process(repo(), build_process(build, _NODE, phase, _now()))


def prepull_handler(*, build: Build) -> None:
    """Signal handler for pre-pulls"""
    set_process(build, "pull")


def postpull_handler(*, build: Build, **_kwargs: Any) -> None:
    """Signal handler for post-pulls"""
    set_process(build, "clean")


def predelete_handler(*, build: Build) -> None:
    """Signal handler for pre-deletes"""
    set_process(build, "delete")


def postdelete_handler(*, build: Build) -> None:
    """Signal handler for pre-deletes"""
    set_process(build, "clean")


dispatcher.bind(prepull=prepull_handler)
dispatcher.bind(postpull=postpull_handler)
dispatcher.bind(predelete=predelete_handler)
dispatcher.bind(postdelete=postdelete_handler)
