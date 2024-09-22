# pylint: disable=missing-docstring,too-few-public-methods
import datetime as dt

import factory

from gbp_ps.types import BuildProcess

PACKAGES = (
    "media-libs/tiff-4.7.0",
    "app-misc/pax-utils-1.3.8",
    "media-libs/x265-3.6-r1",
    "sys-fs/cryptsetup-2.7.5-r1",
    "sys-devel/gcc-14.2.1_p20240921",
    "sys-fs/cryptsetup-2.7.5",
)


class BuildProcessFactory(factory.Factory):
    class Meta:
        model = BuildProcess

    machine = "babette"
    build_id = factory.Sequence(str)
    build_host = "builder"
    package = factory.Iterator(PACKAGES)
    phase = factory.Iterator(BuildProcess.build_phases)
    start_time = factory.LazyFunction(
        lambda: dt.datetime.now(tz=dt.UTC).replace(microsecond=0)
    )
