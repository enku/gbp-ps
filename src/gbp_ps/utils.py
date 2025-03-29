"""Helper utilities"""

import datetime as dt
from typing import Any, Sequence

from gbpcli.render import LOCAL_TIMEZONE

now = dt.datetime.now


def get_today() -> dt.date:
    """Return today's date"""
    return now().astimezone(LOCAL_TIMEZONE).date()


def format_timestamp(timestamp: dt.datetime) -> str:
    """Format the timestamp as a string

    If the date is today's date then only display the time. If the date is not today's
    date then only return the date.
    """
    if (date := timestamp.date()) == get_today():
        return f"[timestamp]{timestamp.strftime('%X')}[/timestamp]"
    return f"[timestamp]{date.strftime('%b%d')}[/timestamp]"


def format_elapsed(timestamp: dt.datetime, since: dt.datetime | None = None) -> str:
    """Format the timestamp as elapsed time since `since`

    `since` defaults to "now".
    """
    total_seconds = round(((since or now(dt.UTC)) - timestamp).total_seconds())
    hours, seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"[timestamp]{hours}:{minutes:02d}:{seconds:02d}[/timestamp]"


def find(item: Any, items: Sequence[Any]) -> int:
    """Return the index of the first item in items

    If item is not found in items, return -1.
    """
    try:
        return items.index(item)
    except ValueError:
        return -1
