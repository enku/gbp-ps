"""Django models for gbp_ps"""

from typing import TypeVar

from django.db import models

from gbp_ps.types import BuildProcess as BuildProcessObject

T = TypeVar("T", bound="BuildProcess")


class BuildProcess(models.Model):
    """A BuildProcess record in the database"""

    machine = models.CharField(max_length=255, db_index=True)
    build_id = models.CharField(max_length=255)
    build_host = models.CharField(max_length=255)
    package = models.CharField(max_length=255)
    phase = models.CharField(max_length=255, db_index=True)
    start_time = models.DateTimeField()

    class Meta:
        unique_together = [["machine", "build_id", "build_host", "package"]]

    def to_object(self) -> BuildProcessObject:
        """Convert to the non-ORM object"""
        return BuildProcessObject(
            machine=self.machine,
            build_id=self.build_id,
            build_host=self.build_host,
            package=self.package,
            phase=self.phase,
            start_time=self.start_time,
        )

    @classmethod
    def from_object(cls: type[T], obj: BuildProcessObject) -> T:
        """Convert the non-ORM object to an ORM model"""
        return cls(
            machine=obj.machine,
            build_id=obj.build_id,
            build_host=obj.build_host,
            package=obj.package,
            phase=obj.phase,
            start_time=obj.start_time,
        )
