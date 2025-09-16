"""GBP signal handlers for gbp-ps"""

import datetime as dt
import platform
from functools import cache, partial
from typing import Any, Protocol

from gentoo_build_publisher.signals import dispatcher
from gentoo_build_publisher.types import Build

from gbp_ps.repository import Repo, RepositoryType, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

_now = partial(dt.datetime.now, tz=dt.UTC)
_HANDLERS: list["Handler"] = []
_NODE = platform.node()

dispatcher.register_event("gbp_ps_add_process")
dispatcher.register_event("gbp_ps_update_process")


class Handler(Protocol):
    # pylint: disable=too-few-public-methods,missing-docstring
    def __call__(self, *, build: Build, **_kwargs: Any) -> Any: ...


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


def handle(phase: str) -> Handler:
    """Return a event handler for the given phase"""

    def handler(*, build: Build, **_kwargs: Any) -> None:
        set_process(build, phase)

    _HANDLERS.append(handler)
    return handler


def set_process(build: Build, phase: str) -> None:
    """Add or update the given Build process in the repo"""
    add_or_update_process(repo(), build_process(build, _NODE, phase, _now()))


dispatcher.bind(prepull=handle("pull"))
dispatcher.bind(postpull=handle("clean"))
dispatcher.bind(predelete=handle("delete"))
dispatcher.bind(postdelete=handle("clean"))
