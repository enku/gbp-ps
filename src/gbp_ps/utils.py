"""Helper utilities"""

import datetime as dt
from typing import Any, Sequence

from gbpcli.render import LOCAL_TIMEZONE


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


def find(item: Any, items: Sequence[Any]) -> int:
    """Return the index of the first item in items

    If item is not found in items, return -1.
    """
    try:
        return items.index(item)
    except ValueError:
        return -1
