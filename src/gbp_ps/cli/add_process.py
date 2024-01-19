"""add/update a process in the process table"""
import argparse
import datetime as dt
import platform

from gbpcli import GBP, Console
from gbpcli.graphql import check

from gbp_ps.types import BuildProcess

now = dt.datetime.now


def handler(args: argparse.Namespace, gbp: GBP, _console: Console) -> int:
    """Show add/update an entry in the process table"""
    check(
        gbp.query.gbp_ps.add_process(
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
