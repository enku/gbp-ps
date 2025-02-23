"""Tests for the exceptions module"""

# pylint: disable=missing-docstring
from typing import Any
from unittest import TestCase, mock

from unittest_fixtures import parametrized

from gbp_ps.exceptions import RETURN_EXCEPTION, swallow_exception


class SwallowExceptionTests(TestCase):
    @parametrized(
        [(None, "test", None), (6, 6, Exception), (RETURN_EXCEPTION, "test", Exception)]
    )
    def test_swallow_exception(
        self, returns: Any, expected: Any, side_effect: type[BaseException]
    ) -> None:

        with mock.patch.object(self, "func", wraps=self.func, side_effect=side_effect):
            wrapped = swallow_exception(Exception, returns=returns)(self.func)
            result = wrapped()

        if returns is RETURN_EXCEPTION:
            self.assertIsInstance(result, side_effect)
        else:
            self.assertEqual(result, expected)

    @staticmethod
    def func() -> str:
        return "test"
