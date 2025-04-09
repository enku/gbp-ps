"""Tests for gbp_ps.utils"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
from unittest import TestCase, mock

from unittest_fixtures import Fixtures, given

from gbp_ps import utils


@given("local_timezone")
class GetTodayTests(TestCase):
    def test(self, fixtures: Fixtures) -> None:
        now = dt.datetime(2024, 2, 7, 20, 10, 57, 312885)
        with mock.patch.object(utils, "now", return_value=now):
            expected = dt.date(2024, 2, 7)
            self.assertEqual(expected, utils.get_today())


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


class FormatElapsedTests(TestCase):
    def test(self) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10, 37)
        since = dt.datetime(2024, 2, 7, 20, 14, 51)

        date_str = utils.format_elapsed(timestamp, since)

        self.assertEqual("[timestamp]0:04:14[/timestamp]", date_str)

    def test_with_default_since(self) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10, 37)
        since = dt.datetime(2024, 2, 7, 20, 14, 51)

        with mock.patch("gbp_ps.utils.now", return_value=since):
            date_str = utils.format_elapsed(timestamp)

        self.assertEqual("[timestamp]0:04:14[/timestamp]", date_str)
