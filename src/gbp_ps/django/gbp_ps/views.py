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


class MainContext(TypedDict):
    """Template context for the main ps page"""

    gradient_colors: Gradient


@view("ps/", name="gbp-ps-main")
@render("gbp_ps/ps/main.html")
def _(request: HttpRequest) -> MainContext:
    return {"gradient_colors": gradient_colors(*color_range_from_settings(), 10)}
