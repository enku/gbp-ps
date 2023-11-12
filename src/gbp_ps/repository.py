"""Database Repository for build processes"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import django.db.utils

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.types import BuildProcess

FINAL_PROCESS_PHASES = {"", "clean", "cleanrm", "postrm"}


class Repository:
    """Django ORM-based BuildProcess repository"""

    def __init__(self, **_kwargs: Any) -> None:
        # pylint: disable=import-outside-toplevel
        from gbp_ps.models import BuildProcess as BuildProcessModel

        self.model: type[BuildProcessModel] = BuildProcessModel

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        build_process_model = self.model.from_object(process)

        try:
            build_process_model.save()
        except django.db.utils.IntegrityError:
            raise RecordAlreadyExists(process) from None

    def update_process(self, process: BuildProcess) -> None:
        """Update the given build process

        Only updates the phase field

        If the build process doesn't exist in the repo, RecordNotFoundError is raised.
        """
        try:
            build_process_model = self.model.objects.get(
                machine=process.machine,
                build_id=process.build_id,
                build_host=process.build_host,
                package=process.package,
            )
        except self.model.DoesNotExist:
            raise RecordNotFoundError(process) from None

        build_process_model.phase = process.phase
        build_process_model.save()

    def get_processes(self, include_final: bool = False) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        query = self.model.objects.order_by("start_time")
        if not include_final:
            query = query.exclude(phase__in=FINAL_PROCESS_PHASES)

        return (model.to_object() for model in query)
