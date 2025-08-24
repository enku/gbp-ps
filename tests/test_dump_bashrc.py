"""CLI unit tests for gbp-ps add-process subcommand"""

# pylint: disable=missing-docstring
import argparse

import gbp_testkit.fixtures as testkit
from unittest_fixtures import Fixtures, given, where

from gbp_ps.cli import dump_bashrc

from .lib import TestCase


@given(testkit.gbpcli, popen=testkit.patch)
@where(popen__target="gbp_ps.cli.dump_bashrc.sp.Popen")
class DumpBashrcHandlerTests(TestCase):
    def test_without_local(self, fixtures: Fixtures) -> None:
        exit_status = fixtures.gbpcli("gbp ps-dump-bashrc")

        self.assertEqual(exit_status, 0)

        lines = fixtures.console.stdout.split("\n")
        self.assertTrue(lines[1].startswith("if [[ -f /Makefile.gbp"))
        self.assertTrue("http://gbp.invalid/graphql" in lines[-4], lines[-4])

    def test_local(self, fixtures: Fixtures) -> None:
        tmpdir = "/var/bogus"

        process = fixtures.popen.return_value.__enter__.return_value
        process.wait.return_value = 0
        process.stdout.read.return_value = tmpdir.encode("utf-8")
        exit_status = fixtures.gbpcli("gbp ps-dump-bashrc --local")

        self.assertEqual(exit_status, 0)

        output = fixtures.console.stdout
        self.assertTrue(f"{tmpdir}/portage/gbpps.db" in output, output)

    def test_local_portageq_fail(self, fixtures: Fixtures) -> None:
        process = fixtures.popen.return_value.__enter__.return_value
        process.wait.return_value = 1

        exit_status = fixtures.gbpcli("gbp ps-dump-bashrc --local")

        self.assertEqual(exit_status, 0)

        output = fixtures.console.stdout
        self.assertTrue("/var/tmp/portage/gbpps.db" in output, output)


class ParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = argparse.ArgumentParser()
        dump_bashrc.parse_args(parser)
