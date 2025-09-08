"""Tests for the exceptions module"""

# pylint: disable=missing-docstring
from unittest import TestCase, mock

from unittest_fixtures import Fixtures, params

from gbp_ps.exceptions import RETURN_EXCEPTION, swallow_exception


@params(returns=[None, 6, RETURN_EXCEPTION])
@params(expected=["test", 6, "test"])
@params(side_effect=[None, Exception, Exception])
class SwallowExceptionTests(TestCase):
    def test_swallow_exception(self, fixtures: Fixtures) -> None:
        with mock.patch.object(
            self, "func", wraps=self.func, side_effect=fixtures.side_effect
        ):
            wrapped = swallow_exception(Exception, returns=fixtures.returns)(self.func)
            result = wrapped()

        if fixtures.returns is RETURN_EXCEPTION:
            self.assertIsInstance(result, fixtures.side_effect)
        else:
            self.assertEqual(result, fixtures.expected)

    @staticmethod
    def func() -> str:
        return "test"
