"""Tests for gbp_ps.utils"""

# pylint: disable=missing-docstring
import datetime as dt
from unittest import TestCase, mock

from gbp_ps import utils


class FormatTimestampTests(TestCase):

    def test_when_today(self) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10)
        today = timestamp.date()

        with mock.patch("gbp_ps.utils.get_today", return_value=today):
            date_str = utils.format_timestamp(timestamp)

        self.assertEqual(date_str, "[timestamp]20:10:00[/timestamp]")

    def test_when_not_today(self) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10)
        today = (timestamp + dt.timedelta(hours=24)).date()

        with mock.patch("gbp_ps.utils.get_today", return_value=today):
            date_str = utils.format_timestamp(timestamp)

        self.assertEqual(date_str, "[timestamp]Feb07[/timestamp]")
