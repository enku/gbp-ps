"""Show currently building packages"""

import argparse
import datetime as dt
import time
from typing import Any, Callable, TypeAlias

from gbpcli import GBP, render
from gbpcli.graphql import Query, check
from gbpcli.types import Console
from rich import box
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

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


def continuous_handler(
    args: argparse.Namespace, get_processes: Query, console: Console
) -> int:
    """Handler for the continuous-mode run of `gbp ps`"""

    def update() -> Table:
        return create_table(check(get_processes())["buildProcesses"], args)

    console.out.clear()
    with Live(
        update(), console=console.out, refresh_per_second=1 / args.update_interval
    ) as live:
        try:
            while True:
                time.sleep(args.update_interval)
                live.update(update())
        except KeyboardInterrupt:
            pass
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
        row = [
            render.format_machine(process["machine"], args),
            render.format_build_number(process["id"]),
            f"[package]{process['package']}[/package]",
            format_timestamp(
                dt.datetime.fromisoformat(process["startTime"]).astimezone(
                    render.LOCAL_TIMEZONE
                )
            ),
            phase_column(process["phase"], args),
        ]
        if args.node:
            row.append(f"[build_host]{process['buildHost']}[/build_host]")
        table.add_row(*row)

    return table


def phase_column(phase: str, args: argparse.Namespace) -> str | Progress:
    """Return the ebuild phase rendered for the process table column

    This will be the text of the ebuild phase and a progress bar depending on the
    args.progress flag and whether the phase is an ebuild build phase.
    """
    if not args.progress or phase not in BuildProcess.build_phases:
        return f"[{phase}_phase]{phase:{PHASE_PADDING}}[/{phase}_phase]"

    return phase_progress(phase)


def phase_progress(phase: str) -> Progress:
    """Render the phase as a Progress bar"""
    position = BuildProcess.build_phases.index(phase) + 1
    progress = Progress(
        TextColumn(f"[{phase}_phase]{phase:{PHASE_PADDING}}[/{phase}_phase]"),
        BarColumn(),
    )
    task = progress.add_task(phase, total=BUILD_PHASE_COUNT)
    progress.update(task, advance=position)

    return progress


def get_today() -> dt.date:
    """Return today's date"""
    return dt.datetime.now().astimezone(render.LOCAL_TIMEZONE).date()


def format_timestamp(timestamp: dt.datetime) -> str:
    """Format the timestamp as a string

    Like render.from_timestamp(), but if the date is today's date then only display the
    time. If the date is not today's date then only return the date.
    """
    if (date := timestamp.date()) == get_today():
        return f"[timestamp]{timestamp.strftime('%X')}[/timestamp]"
    return f"[timestamp]{date.strftime('%b%d')}[/timestamp]"


MODES = [single_handler, continuous_handler]
