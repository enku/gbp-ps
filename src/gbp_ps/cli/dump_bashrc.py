"""Show dump an appropriate /etc/portage/bashrc for gbp-ps"""

import argparse
import subprocess as sp
from importlib import resources
from typing import Callable

from gbpcli.gbp import GBP
from gbpcli.types import Console

BASHRC_FILENAME = "bashrc.bash"
LOCAL_BASHRC_FILENAME = "bashrc-local.bash"


def handler(args: argparse.Namespace, gbp: GBP, console: Console) -> int:
    """Show dump an appropriate /etc/portage/bashrc for gbp-ps"""
    formatter: Callable[[str, GBP], str]
    if args.local:
        filename = LOCAL_BASHRC_FILENAME
        formatter = format_local
    else:
        filename = BASHRC_FILENAME
        formatter = format_bashrc

    with resources.open_text("gbp_ps.assets", filename, encoding="utf-8") as fp:
        bashrc = fp.read()

    bashrc = formatter(bashrc, gbp)

    console.out.print(bashrc)

    return 0


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Parse command-line arguments"""
    parser.add_argument(
        "--local",
        "-l",
        action="store_true",
        default=False,
        help="Generate a bashrc for local ebuild processes",
    )


def format_bashrc(bashrc: str, gbp: GBP) -> str:
    """Format the given GPB node's bashrc"""
    # pylint: disable=protected-access
    return bashrc.replace("http://gbp/graphql", gbp.query._url)


def format_local(bashrc: str, _gbp: GBP) -> str:
    """Format the given local bashrc"""
    return bashrc.replace("/var/tmp", portage_tmpdir())


def portage_tmpdir() -> str:
    """Get the local PORTAGE_TMPDIR

    If this cannot be determined, return the default ("/var/tmp")
    """
    with sp.Popen(["portageq", "envvar", "PORTAGE_TMPDIR"], stdout=sp.PIPE) as proc:
        stdout = proc.stdout
        assert stdout
        output = stdout.read().decode("utf-8")

    if proc.wait() == 0:
        return output.strip()
    return "/var/tmp"
