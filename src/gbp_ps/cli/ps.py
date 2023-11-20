"""Show currently building packages"""
import argparse
import datetime as dt
import time
from typing import Any, Callable, TypeAlias

from gbpcli import GBP, Console, render
from gbpcli.graphql import check
from rich import box
from rich.live import Live
from rich.table import Table

ModeHandler = Callable[[argparse.Namespace, GBP, Console], int]
ProcessList: TypeAlias = list[dict[str, Any]]


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
        phase = process["phase"]
        row = [
            render.format_machine(process["machine"], args),
            render.format_build_number(process["id"]),
            f"[package]{process['package']}[/package]",
            format_timestamp(
                dt.datetime.fromisoformat(process["startTime"]).astimezone(
                    render.LOCAL_TIMEZONE
                )
            ),
            f"[{phase}_phase]{phase:9}[/{phase}_phase]",
        ]
        if args.node:
            row.append(process["buildHost"])
        table.add_row(*row)

    return table


def single_handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Handler for the single-mode run of `gbp ps`"""
    processes: ProcessList

    if processes := check(gbp.query.get_processes())["buildProcesses"]:
        console.out.print(create_table(processes, args))

    return 0


def continuous_handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Handler for the continuous-mode run of `gbp ps`"""

    def update() -> Table:
        return create_table(check(gbp.query.get_processes())["buildProcesses"], args)

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


MODES = [single_handler, continuous_handler]


def handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Show currently building packages"""
    # NOTE: This was unintentional, but ^ GBP can only see the queries for the "gbpcli"
    # distribution.  It needs a collector like gentoo-build-publisher has a collector
    # for schemas
    gbp.query._distribution = "gbp_ps"  # pylint: disable=protected-access

    mode: ModeHandler = MODES[args.continuous]
    return mode(args, gbp, console)


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
