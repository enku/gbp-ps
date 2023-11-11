"""gbp-ps"""

from gbp_ps.repository import Repository
from gbp_ps.types import BuildProcess


def get_processes() -> list[BuildProcess]:
    """Return the list of build processes"""
    return list(Repository().get_processes())

def update_process(process: BuildProcess) -> None:
    """Update the process in the database"""
    Repository().update_process(process)
