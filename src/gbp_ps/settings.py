"""gbp-ps settings"""

from dataclasses import dataclass
from typing import ClassVar

from gbpcli.settings import BaseSettings

DEFAULT_REDIS_KEY_EXPIRATION = 3600 * 24


@dataclass(frozen=True, slots=True)
class Settings(BaseSettings):
    """Settings for gbp-ps"""

    # pylint: disable=invalid-name
    env_prefix: ClassVar = "GBP_PS_"

    REDIS_KEY: str = "gbp-ps"
    REDIS_KEY_EXPIRATION: int = DEFAULT_REDIS_KEY_EXPIRATION
    REDIS_URL: str = "redis://redis.invalid:6379/0"
    SQLITE_DATABASE: str = ":memory:"
    STORAGE_BACKEND: str = "django"
