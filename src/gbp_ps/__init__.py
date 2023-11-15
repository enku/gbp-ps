"""gbp-ps"""

from gbp_ps.repository import get_repo
from gbp_ps.types import BuildProcess


def get_processes(include_final: bool = False) -> list[BuildProcess]:
    """Return the list of build processes

    If include_final is True also include processes in their "final" phase. The default
    value is False.
    """
    return list(get_repo().get_processes(include_final))


def add_process(process: BuildProcess) -> None:
    """Add the given process to the database"""
    get_repo().add_process(process)


def update_process(process: BuildProcess) -> None:
    """Update the process in the database"""
    get_repo().update_process(process)
