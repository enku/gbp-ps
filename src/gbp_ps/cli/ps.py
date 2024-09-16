"""Show currently building packages"""

import argparse
import datetime as dt
import time
from typing import Any, Callable, TypeAlias

from gbpcli import GBP, render
from gbpcli.graphql import Query, check
from gbpcli.types import Console
from rich import box
from rich.console import RenderableType
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from gbp_ps import utils
from gbp_ps.exceptions import swallow_exception
from gbp_ps.types import BuildProcess

ModeHandler = Callable[[argparse.Namespace, Query, Console], int]
ProcessList: TypeAlias = list[dict[str, Any]]

BUILD_PHASE_COUNT = len(BuildProcess.build_phases)
PHASE_PADDING = max(len(i) for i in BuildProcess.build_phases)


def handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Show currently building packages"""
    mode: ModeHandler = MODES[args.continuous]

    return mode(args, gbp.query.gbp_ps.get_processes, console)  # type: ignore[attr-defined]


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "--node", action="store_true", default=False, help="display the build node"
    )
    parser.add_argument(
        "--continuous",
        "-c",
        action="store_true",
        default=False,
        help="Run and continuously poll and update",
    )
    parser.add_argument(
        "--update-interval",
        "-i",
        type=float,
        default=1,
        help="In continuous mode, the interval, in seconds, between updates",
    )
    parser.add_argument(
        "--progress",
        "-p",
        action="store_true",
        default=False,
        help="Display progress bars for package phase",
    )


def single_handler(
    args: argparse.Namespace, get_processes: Query, console: Console
) -> int:
    """Handler for the single-mode run of `gbp ps`"""
    processes: ProcessList

    if processes := check(get_processes())["buildProcesses"]:
        console.out.print(create_table(processes, args))

    return 0


@swallow_exception(KeyboardInterrupt, returns=0)
def continuous_handler(
    args: argparse.Namespace, get_processes: Query, console: Console
) -> int:
    """Handler for the continuous-mode run of `gbp ps`"""

    def update() -> Table:
        return create_table(check(get_processes())["buildProcesses"], args)

    rate = 1 / args.update_interval
    out = console.out
    ctx = Live(update(), console=out, screen=out.is_terminal, refresh_per_second=rate)
    with ctx as live:
        while True:
            time.sleep(args.update_interval)
            live.update(update())
    return 0


def create_table(processes: ProcessList, args: argparse.Namespace) -> Table:
    """Return a rich Table given the list of processes"""
    table = Table(
        title="Ebuild Processes",
        box=box.ROUNDED,
        expand=True,
        title_style="header",
        style="box",
    )
    table.add_column("Machine", header_style="header")
    table.add_column("ID", header_style="header")
    table.add_column("Package", header_style="header")
    table.add_column("Start", header_style="header")
    table.add_column("Phase", header_style="header")

    if args.node:
        table.add_column("Node", header_style="header")

    for process in processes:
        table.add_row(*row(process, args))

    return table


def row(process: dict[str, Any], args: argparse.Namespace) -> list[RenderableType]:
    """Return a process row (list) given the process and args"""
    return [
        render.format_machine(process["machine"], args),
        render.format_build_number(process["id"]),
        f"[package]{process['package']}[/package]",
        utils.format_timestamp(
            dt.datetime.fromisoformat(process["startTime"]).astimezone(
                render.LOCAL_TIMEZONE
            )
        ),
        phase_column(process["phase"], args),
        *([f"[build_host]{process['buildHost']}[/build_host]"] if args.node else []),
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
