"""Helper utilities"""

import datetime as dt
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, ClassVar, Self, Sequence

from gbpcli.render import LOCAL_TIMEZONE

FALSE_VALUES = {"0", "f", "false", "n", "no", "off"}
TRUE_VALUES = {"1", "on", "t", "true", "y", "yes"}


# XXX: copied from gentoo-build-publisher  # pylint: disable=fixme
@dataclass(frozen=True)
class BaseSettings:
    """Base class for Settings"""

    # Subclasses should define me as the prefix for environment variables for these
    # settings. For example if prefix is "BUILD_PUBLISHER_" and the field is named "FOO"
    # then the environment variable for that field is "BUILD_PUBLISHER_FOO"
    env_prefix: ClassVar = ""

    @classmethod
    def from_dict(cls: type[Self], prefix: str, data_dict: dict[str, Any]) -> Self:
        """Return Settings instantiated from a dict"""
        params: dict[str, Any] = {}
        value: Any
        for field in fields(cls):
            if (key := f"{prefix}{field.name}") not in data_dict:
                continue

            match field.type:
                case "bool":
                    value = get_bool(data_dict[key])
                case "int":
                    value = int(data_dict[key])
                case "Path":
                    value = Path(data_dict[key])
                case _:
                    value = data_dict[key]

            params[field.name] = value
        return cls(**params)

    @classmethod
    def from_environ(cls: type[Self], prefix: str | None = None) -> Self:
        """Return settings instantiated from environment variables"""
        if prefix is None:
            prefix = cls.env_prefix

        return cls.from_dict(prefix, dict(os.environ))


def get_today() -> dt.date:
    """Return today's date"""
    return dt.datetime.now().astimezone(LOCAL_TIMEZONE).date()


def format_timestamp(timestamp: dt.datetime) -> str:
    """Format the timestamp as a string

    Like render.from_timestamp(), but if the date is today's date then only display the
    time. If the date is not today's date then only return the date.
    """
    if (date := timestamp.date()) == get_today():
        return f"[timestamp]{timestamp.strftime('%X')}[/timestamp]"
    return f"[timestamp]{date.strftime('%b%d')}[/timestamp]"


def get_bool(value: str | bytes | bool) -> bool:
    """Return the boolean value of the truthy/falsey string"""
    if isinstance(value, bool):
        return value

    if isinstance(value, bytes):
        value = value.decode("UTF-8")

    if value.lower() in FALSE_VALUES:
        return False

    if value.lower() in TRUE_VALUES:
        return True

    raise ValueError(value)


def find(item: Any, items: Sequence[Any]) -> int:
    """Return the index of the first item in items

    If item is not found in items, return -1.
    """
    try:
        return items.index(item)
    except ValueError:
        return -1
