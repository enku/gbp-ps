"""Django views for gbp-ps"""

from typing import TypedDict

from django.http import HttpRequest
from gentoo_build_publisher.django.gentoo_build_publisher.views.utils import (
    Gradient,
    color_range_from_settings,
    gradient_colors,
    render,
    view,
)

from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

BUILD_PHASE_COUNT = len(BuildProcess.build_phases)


class MainContext(TypedDict):
    """Template context for the main ps page"""

    default_interval: int
    gradient_colors: Gradient


@view("ps/", name="gbp-ps-main")
@render("gbp_ps/ps/main.html")
def _(request: HttpRequest) -> MainContext:
    settings = Settings.from_environ()

    return {
        "default_interval": settings.WEB_UI_UPDATE_INTERVAL,
        "gradient_colors": gradient_colors(
            *color_range_from_settings(), BUILD_PHASE_COUNT
        ),
    }
