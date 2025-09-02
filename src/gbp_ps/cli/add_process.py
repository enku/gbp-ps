"""add/update a process in the process table"""

import argparse
import datetime as dt
import platform
from functools import partial
from typing import Any, Callable, TypeAlias

from gbpcli.gbp import GBP
from gbpcli.graphql import check
from gbpcli.types import Console

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

ProcessAdder: TypeAlias = Callable[[BuildProcess], Any]
now = partial(dt.datetime.now, tz=dt.UTC)


def handler(args: argparse.Namespace, gbp: GBP, _console: Console) -> int:
    """Show add/update an entry in the process table"""
    local: str | None = getattr(args, "local", None)
    add_process = add_local_process(local) if local else add_gbp_process(gbp)
    add_process(build_process_from_args(args))

    return 0


def add_gbp_process(gbp: GBP) -> ProcessAdder:
    """Return a function that can use GBP to add/update a given BuildProcess"""
    query = gbp.query.gbp_ps.add_process  # type: ignore[attr-defined]

    def add_process(process: BuildProcess) -> None:
        check(query(process=process.to_dict()))

    return add_process


def add_local_process(database: str) -> ProcessAdder:
    """Return a function that can use SqliteRepository to add/update a given BuildProcess"""
    repo = Repo(Settings(STORAGE_BACKEND="sqlite", SQLITE_DATABASE=database))

    def add_process(process: BuildProcess) -> None:
        add_or_update_process(repo, process)

    return add_process


def build_process_from_args(args: argparse.Namespace) -> BuildProcess:
    """Build and return a BuildProcess given the command-line args

    start_time will be the current time.
    build_host will be the current host.
    """
    return BuildProcess(
        build_host=platform.node(),
        build_id=args.number,
        machine=args.machine,
        package=args.package,
        phase=args.phase,
        start_time=now(),
    )


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "-l", "--local", default=None, help="(Where to) Use a local process database"
    )
    parser.add_argument("machine", metavar="MACHINE", help="name of the machine")
    parser.add_argument("number", metavar="NUMBER", help="build number")
    parser.add_argument("package", metavar="PACKAGE", help="package CPV")
    parser.add_argument("phase", metavar="PHASE", help="ebuild phase")
