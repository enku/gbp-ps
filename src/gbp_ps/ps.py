"""Show currently building packages"""
import argparse
import datetime as dt
from typing import Any

from gbpcli import GBP, Console, render
from gbpcli.graphql import check
from rich import box
from rich.table import Table


def handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Show currently building packages"""
    # NOTE: This was unintentional, but ^ GBP can only see the queries for the "gbpcli"
    # distribution.  It needs a collector like gentoo-build-publisher has a collector
    # for schemas
    gbp.query._distribution = "gbp_ps"  # pylint: disable=protected-access
    processes: list[dict[str, Any]] = check(gbp.query.get_processes())["buildProcesses"]

    if not processes:
        return 0

    table = Table(title="Processes", box=box.ROUNDED, title_style="header", style="box")
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
            render.format_timestamp(
                dt.datetime.fromisoformat(process["startTime"]).astimezone(
                    render.LOCAL_TIMEZONE
                )
            ),
            f"[tag]{process['phase']}[/tag]",
        ]
        if args.node:
            row.append(process["buildHost"])
        table.add_row(*row)

    console.out.print(table)
    return 0


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "--node", action="store_true", default=False, help="display the build node"
    )
