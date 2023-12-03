"""add/update a process in the process table"""
import argparse
import datetime as dt
import platform

from gbpcli import GBP, Console
from gbpcli.graphql import Query, check

from gbp_ps.types import BuildProcess

now = dt.datetime.now


def handler(args: argparse.Namespace, gbp: GBP, _console: Console) -> int:
    """Show add/update an entry in the process table"""
    add_process: Query
    if hasattr(gbp.query, "_distribution"):
        # Older GBP can only see the queries for the "gbpcli" distribution and need to
        # be overridden to see queries from other distributions
        gbp.query._distribution = "gbp_ps"  # pylint: disable=protected-access
        add_process = gbp.query.add_process
    else:
        add_process = gbp.query.gbp_ps.add_process  # type: ignore[attr-defined]
    check(
        add_process(
            process=BuildProcess(
                build_host=platform.node(),
                build_id=args.number,
                machine=args.machine,
                package=args.package,
                phase=args.phase,
                start_time=now(tz=dt.UTC),
            ).to_dict()
        )
    )

    return 0


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument("machine", metavar="MACHINE", help="name of the machine")
    parser.add_argument("number", metavar="NUMBER", help="build number")
    parser.add_argument("package", metavar="PACKAGE", help="package CPV")
    parser.add_argument("phase", metavar="PHASE", help="ebuild phase")
