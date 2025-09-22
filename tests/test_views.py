"""Tests for the gbp-ps Django views"""

# pylint: disable=missing-docstring,unused-argument
from unittest import TestCase

from django.contrib.staticfiles import finders
from gbp_testkit import fixtures as testkit
from unittest_fixtures import Fixtures, given, where


@given(response=lambda f: f.client.get("/ps/"))
@given(testkit.client, testkit.environ)
@where(environ={"GBP_PS_WEB_UI_UPDATE_INTERVAL": "20250922"})
class PSViewTests(TestCase):
    def test_200(self, fixtures: Fixtures) -> None:
        """Returns 200 response"""
        response = fixtures.response

        self.assertEqual(response.status_code, 200)

    def test_renders_template(self, fixtures: Fixtures) -> None:
        """Renders the main.html template"""
        response = fixtures.response
        templates = [i.name for i in response.templates]

        expected = "gbp_ps/ps/main.html"
        self.assertIn(expected, templates)

    def test_pulls_in_the_js(self, fixtures: Fixtures) -> None:
        response = fixtures.response

        expected = '<script src="/static/gbp_ps/ps.js"></script>'
        self.assertIn(expected, response.text)

    def test_js_exists(self, fixtures: Fixtures) -> None:
        path = finders.find("gbp_ps/ps.js")

        self.assertIsNotNone(path)

    def test_gradient_for_phases(self, fixtures: Fixtures) -> None:
        """Each ebuild phase has its own color"""
        response = fixtures.response
        context = response.context
        gradient = context["gradient_colors"]

        self.assertEqual(len(gradient), 12)

    def test_has_update_interval(self, fixtures: Fixtures) -> None:
        response = fixtures.response
        context = response.context

        self.assertEqual(context["default_interval"], 20250922)

        expected = (
            '<script id="defaultInterval" type="application/json">20250922</script>'
        )
        self.assertIn(expected, response.text)
