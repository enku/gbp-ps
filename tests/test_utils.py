"""Tests for gbp_ps.utils"""

# pylint: disable=missing-docstring,unused-argument
import datetime as dt
from unittest import TestCase

import gbp_testkit.fixtures as testkit
from gbp_testkit.helpers import LOCAL_TIMEZONE
from unittest_fixtures import Fixtures, given, where

from gbp_ps import utils


@given(local_timezone=testkit.patch, now=testkit.patch)
@where(now__target="gbp_ps.utils.now")
@where(now__return_value=dt.datetime(2024, 2, 7, 20, 10, 57, 312885))
@where(local_timezone__target="gbpcli.render.LOCAL_TIMEZONE")
@where(local_timezone__new=LOCAL_TIMEZONE)
class GetTodayTests(TestCase):
    def test(self, fixtures: Fixtures) -> None:
        self.assertEqual(dt.date(2024, 2, 7), utils.get_today())


@given(get_today=testkit.patch)
@where(get_today__target="gbp_ps.utils.get_today")
class FormatTimestampTests(TestCase):

    def test_when_today(self, fixtures: Fixtures) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10)
        today = timestamp.date()
        fixtures.get_today.return_value = today

        date_str = utils.format_timestamp(timestamp)

        self.assertEqual(date_str, "[timestamp]20:10:00[/timestamp]")

    def test_when_not_today(self, fixtures: Fixtures) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10)
        today = (timestamp + dt.timedelta(hours=24)).date()
        fixtures.get_today.return_value = today

        date_str = utils.format_timestamp(timestamp)

        self.assertEqual(date_str, "[timestamp]Feb07[/timestamp]")


@given(now=testkit.patch)
@where(now__target="gbp_ps.utils.now")
class FormatElapsedTests(TestCase):
    def test(self, fixtures: Fixtures) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10, 37)
        since = dt.datetime(2024, 2, 7, 20, 14, 51)

        date_str = utils.format_elapsed(timestamp, since)

        self.assertEqual("[timestamp]0:04:14[/timestamp]", date_str)

    def test_with_default_since(self, fixtures: Fixtures) -> None:
        timestamp = dt.datetime(2024, 2, 7, 20, 10, 37)
        since = dt.datetime(2024, 2, 7, 20, 14, 51)
        fixtures.now.return_value = since

        date_str = utils.format_elapsed(timestamp)

        self.assertEqual("[timestamp]0:04:14[/timestamp]", date_str)


class FindTests(TestCase):
    def test_item_in_sequence(self) -> None:
        self.assertEqual(1, utils.find("test", ("this", "test", "is", "a")))

    def test_item_not_insequence(self) -> None:
        self.assertEqual(-1, utils.find("test", ("a", "is", "this")))

    def test_empty_sequence_self(self) -> None:
        self.assertEqual(-1, utils.find("test", ()))

    def test_item_exists_twice_in_sequence(self) -> None:
        self.assertEqual(1, utils.find("test", ("is", "test", "a", "this", "test")))
