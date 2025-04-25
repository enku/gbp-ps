"""Django RepositoryType"""

from typing import Iterable

from gbp_ps.exceptions import RecordAlreadyExists, RecordNotFoundError
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess


class DjangoRepository:
    """Django ORM-based BuildProcess repository"""

    def __init__(self, _settings: Settings) -> None:
        # pylint: disable=import-outside-toplevel
        from gbp_ps.django.gbp_ps.models import BuildProcess as BuildProcessModel

        self.model: type[BuildProcessModel] = BuildProcessModel

    def add_process(self, process: BuildProcess) -> None:
        """Add the given BuildProcess to the repository

        If the process already exists in the repo, RecordAlreadyExists is raised
        """
        # pylint: disable=import-outside-toplevel
        import django.db.utils
        from django.db.models import Q

        # If this package exists in another build, remove it. This (usually) means the
        # other build failed
        self.model.objects.filter(
            ~Q(build_id=process.build_id),
            machine=process.machine,
            package=process.package,
            phase__in=BuildProcess.build_phases,
        ).delete()

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
                package=process.package,
            )
        except self.model.DoesNotExist:
            raise RecordNotFoundError(process) from None

        build_process_model.to_object().ensure_updateable(process)

        build_process_model.phase = process.phase
        build_process_model.build_host = process.build_host
        build_process_model.save()

    def get_processes(
        self, include_final: bool = False, machine: str | None = None
    ) -> Iterable[BuildProcess]:
        """Return the process records from the repository

        If include_final is True also include processes in their "final" phase. The
        default value is False.
        """
        query = self.model.objects.order_by("start_time")

        if not include_final:
            query = query.exclude(phase__in=BuildProcess.final_phases)

        if machine:
            query = query.filter(machine=machine)

        return (model.to_object() for model in query)
