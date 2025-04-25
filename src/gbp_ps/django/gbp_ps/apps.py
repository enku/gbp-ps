"""AppConfigs for gbp-ps"""

from django.apps import AppConfig


class GBPPSConfig(AppConfig):
    """AppConfig for gbp-ps"""

    name = "gbp_ps.django.gbp_ps"
    verbose_name = "GBP-ps"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Django app initialization"""
        # pylint: disable=import-outside-toplevel,unused-import
        # register signal handlers
        import gbp_ps.signals
