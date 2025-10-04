"""AppConfigs for gbp-ps"""

import importlib

from django.apps import AppConfig


class GBPPSConfig(AppConfig):
    """AppConfig for gbp-ps"""

    name = "gbp_ps.django.gbp_ps"
    verbose_name = "GBP-ps"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Django app initialization"""
        # register signal handlers
        signals = importlib.import_module("gbp_ps.signals")

        signals.init()
