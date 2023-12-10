"""GBP signal handlers for gbp-ps"""
import datetime as dt
import platform
from typing import Any

from gentoo_build_publisher.common import Build
from gentoo_build_publisher.signals import dispatcher

from gbp_ps import add_process
from gbp_ps.types import BuildProcess

_now = dt.datetime.now


def create_build_process(
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


def prepull_handler(*, build: Build) -> None:
    """Signal handler for pre-pulls"""
    add_process(create_build_process(build, platform.node(), "pull", _now(tz=dt.UTC)))


def postpull_handler(*, build: Build, **_kwargs: Any) -> None:
    """Signal handler for post-pulls"""
    add_process(create_build_process(build, platform.node(), "clean", _now(tz=dt.UTC)))


dispatcher.bind(prepull=prepull_handler)
dispatcher.bind(postpull=postpull_handler)
