"""Show currently building packages"""

import argparse
import datetime as dt
import time
from typing import Any, Callable, NoReturn, TypeAlias

from gbpcli import render
from gbpcli.gbp import GBP
from gbpcli.graphql import check
from gbpcli.types import Console
from rich import box
from rich.console import RenderableType
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from gbp_ps import utils
from gbp_ps.exceptions import swallow_exception
from gbp_ps.repository import Repo
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

ProcessList: TypeAlias = list[BuildProcess]
ProcessGetter: TypeAlias = Callable[[], ProcessList]
ModeHandler = Callable[[argparse.Namespace, ProcessGetter, Console], int]

BUILD_PHASE_COUNT = len(BuildProcess.build_phases)
PHASE_PADDING = max(len(i) for i in BuildProcess.build_phases)


def handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Show currently building packages"""
    mode: ModeHandler = MODES[args.continuous]
    local: str | None = getattr(args, "local", None)
    machine: str | None = args.machine

    get_processes = (
        get_local_processes(local) if local else get_gbp_processes(gbp, machine)
    )

    return mode(args, get_processes, console)


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "-m", "--machine", default=None, help="Exclude processes to the given machine"
    )
    parser.add_argument(
        "--node", action="store_true", default=False, help="display the build node"
    )
    parser.add_argument(
        "-l", "--local", default=None, help="(Where to) Use a local process database"
    )
    parser.add_argument(
        "-c",
        "--continuous",
        action="store_true",
        default=False,
        help="Run and continuously poll and update",
    )
    parser.add_argument(
        "-i",
        "--update-interval",
        type=float,
        default=1,
        help="In continuous mode, the interval, in seconds, between updates",
    )
    parser.add_argument(
        "-p",
        "--progress",
        action="store_true",
        default=False,
        help="Display progress bars for package phase",
    )
    parser.add_argument(
        "-e",
        "--elapsed",
        action="store_true",
        default=False,
        help="Dispay elapsed time instead of wall time",
    )


def single_handler(
    args: argparse.Namespace, get_processes: ProcessGetter, console: Console
) -> int:
    """Handler for the single-mode run of `gbp ps`"""
    if processes := get_processes():
        console.out.print(create_table(processes, args))

    return 0


def get_gbp_processes(gbp: GBP, machine: str | None) -> ProcessGetter:
    """Retrieve and return the ProcessList"""

    def get_processes() -> ProcessList:
        query = gbp.query.gbp_ps.get_processes  # type: ignore[attr-defined]
        results = check(query(machine=machine))

        return [graphql_to_process(result) for result in results["buildProcesses"]]

    return get_processes


def get_local_processes(database: str) -> ProcessGetter:
    """Return a list of processes given the database path"""
    repo = Repo(Settings(STORAGE_BACKEND="sqlite", SQLITE_DATABASE=database))

    def get_processes() -> ProcessList:
        return list(repo.get_processes())

    return get_processes


@swallow_exception(KeyboardInterrupt, returns=0)
def continuous_handler(
    args: argparse.Namespace, get_processes: ProcessGetter, console: Console
) -> NoReturn:
    """Handler for the continuous-mode run of `gbp ps`"""

    def update() -> Table:
        return create_table(get_processes(), args)

    rate = 1 / args.update_interval
    out = console.out
    ctx = Live(update(), console=out, screen=out.is_terminal, refresh_per_second=rate)
    with ctx as live:
        while True:
            time.sleep(args.update_interval)
            live.update(update())


def graphql_to_process(result: dict[str, Any]) -> BuildProcess:
    """Return GraphQL build process output as BuildProcess object"""
    return BuildProcess(
        machine=result["machine"],
        build_id=result["id"],
        build_host=result["buildHost"],
        package=result["package"],
        phase=result["phase"],
        start_time=dt.datetime.fromisoformat(result["startTime"]),
    )


def create_table(processes: ProcessList, args: argparse.Namespace) -> Table:
    """Return a rich Table given the list of processes"""
    table = Table(
        title="Build Processes",
        box=box.ROUNDED,
        expand=True,
        title_style="header",
        style="box",
    )
    table.add_column("Machine", header_style="header")
    table.add_column("ID", header_style="header")
    table.add_column("Package", header_style="header")
    table.add_column("Elapsed" if args.elapsed else "Start", header_style="header")
    table.add_column("Phase", header_style="header")

    if args.node:
        table.add_column("Node", header_style="header")

    for process in processes:
        table.add_row(*row(process, args))

    return table


def row(process: BuildProcess, args: argparse.Namespace) -> list[RenderableType]:
    """Return a process row (list) given the process and args"""
    return [
        render.format_machine(process.machine, args),
        render.format_build_number(int(process.build_id)),
        f"[package]{process.package}[/package]",
        (utils.format_elapsed if args.elapsed else utils.format_timestamp)(
            process.start_time.astimezone(render.LOCAL_TIMEZONE)
        ),
        phase_column(process.phase, args),
        *([f"[build_host]{process.build_host}[/build_host]"] if args.node else []),
    ]


def phase_column(phase: str, args: argparse.Namespace) -> str | Progress:
    """Return the ebuild phase rendered for the process table column

    This will be the text of the ebuild phase and a progress bar depending on the
    args.progress flag and whether the phase is an ebuild build phase.
    """
    text = f"[{phase}_phase]{phase:{PHASE_PADDING}}[/{phase}_phase]"

    if not args.progress:
        return text

    position = utils.find(phase, BuildProcess.build_phases) + 1
    return progress(text, (position, BUILD_PHASE_COUNT) if position > 0 else None)


def progress(text: str, steps: tuple[int, int] | None) -> Progress:
    """Return Progress object with given text and steps (completed, total)

    If steps is None, a pulsing Progress bar is used.
    """
    prog = Progress(TextColumn(text), BarColumn())

    if steps is None:
        task = prog.add_task(text, total=None)
        return prog

    completed, total = steps
    task = prog.add_task(text, total=total)
    prog.update(task, advance=completed)
    return prog


MODES = [single_handler, continuous_handler]
