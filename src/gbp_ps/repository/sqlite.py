"""Sqlite RepositoryType"""

import datetime as dt
import sqlite3
from contextlib import contextmanager
from typing import Generator, Iterable

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess


class SqliteRepository:
    """Sqlite Based Repository"""

    final_phases_t = tuple(BuildProcess.final_phases)
    filter_phases = f"phase NOT IN ({','.join(['?' for _ in final_phases_t])})"
    row_names = "machine, build_id, build_host, package, phase, start_time"

    def __init__(self, settings: Settings) -> None:
        database: bytes | str = settings.SQLITE_DATABASE
        self._database = database
        self.init_db()

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        # If this package exists in another build, remove it. This (usually) means the
        # other build failed
        build_phases = BuildProcess.build_phases
        placeholders = ", ".join("?" for _ in build_phases)
        query = f"""
            DELETE FROM ebuild_process
            WHERE
              build_id != ?
              AND machine = ?
              AND package = ?
              AND phase in ({placeholders})
        """
        params = (process.build_id, process.machine, process.package, *build_phases)
        with self.cursor() as cursor:
            cursor.execute(query, params)

        query = f"""
            INSERT INTO ebuild_process ({self.row_names})
            VALUES (?,?,?,?,?,?)
        """
        with self.cursor() as cursor:
            try:
                cursor.execute(query, self.process_to_row(process))
            except sqlite3.IntegrityError:
                raise RecordAlreadyExists(process) from None

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        query = """
            SELECT machine,build_id,build_host,package,phase,start_time
            FROM ebuild_process
            WHERE machine = ? AND build_id = ? AND package = ?
        """
        with self.cursor() as cursor:
            result = cursor.execute(
                query, (process.machine, process.build_id, process.package)
            )
            row = result.fetchone()
        if not row:
            raise RecordNotFoundError(process) from None
        previous = self.row_to_process(*row)
        previous.ensure_updateable(process)
        query = """
            UPDATE ebuild_process
            SET phase = ?
            WHERE machine = ? AND build_id = ? AND package = ?
        """
        with self.cursor() as cursor:
            result = cursor.execute(
                query,
                (process.phase, process.machine, process.build_id, process.package),
            )

    def get_processes(
        self, include_final: bool = False, machine: str | None = None
    ) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        wheres: list[str] = []
        params: tuple[str, ...] = ()

        if not include_final:
            wheres.append(self.filter_phases)
            params = params + self.final_phases_t

        if machine:
            wheres.append("machine=?")
            params = params + (machine,)

        wheres_s = "WHERE " + " AND ".join(wheres) if wheres else ""

        query = f"""
            SELECT machine,build_id,build_host,package,phase,start_time
            FROM ebuild_process
            {wheres_s}
            ORDER BY start_time
        """

        with self.cursor() as cursor:
            result = cursor.execute(query, params)
            for row in result:
                yield self.row_to_process(*row)

    @staticmethod
    def row_to_process(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        machine: str,
        build_id: str,
        build_host: str,
        package: str,
        phase: str,
        start_time: int,
    ) -> BuildProcess:
        """Return a BuildProcess given the sql row data"""
        return BuildProcess(
            machine=machine,
            build_id=build_id,
            build_host=build_host,
            package=package,
            phase=phase,
            start_time=dt.datetime.fromtimestamp(start_time, tz=dt.UTC),
        )

    @staticmethod
    def process_to_row(process: BuildProcess) -> tuple[str, str, str, str, str, int]:
        """Return the tuple of rows given the BuildProcess"""
        p = process
        start_time = int(p.start_time.timestamp())
        return (p.machine, p.build_id, p.build_host, p.package, p.phase, start_time)

    def init_db(self) -> None:
        """Initialize the database"""
        create_table = """
CREATE TABLE IF NOT EXISTS ebuild_process (
    machine VARCHAR(255),
    build_id VARCHAR(255),
    build_host VARCHAR(255),
    package VARCHAR(255),
    phase VARCHAR(255),
    start_time INTEGER
);
"""
        create_machine_idx = """
CREATE INDEX IF NOT EXISTS idx_machine
ON ebuild_process (machine)
"""
        create_phase_idx = """
CREATE INDEX IF NOT EXISTS idx_phase
ON ebuild_process (phase)
"""
        create_unique_idx = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_process
ON ebuild_process (machine, build_id, build_host, package)
"""
        with self.cursor() as cursor:
            cursor.execute(create_table)
            cursor.execute(create_machine_idx)
            cursor.execute(create_phase_idx)
            cursor.execute(create_unique_idx)

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Connect to the db and return a cursor object"""
        with sqlite3.connect(self._database) as connection:
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
