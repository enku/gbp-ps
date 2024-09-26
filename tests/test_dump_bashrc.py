"""CLI unit tests for gbp-ps add-process subcommand"""

# pylint: disable=missing-docstring
import argparse
from unittest import mock

from unittest_fixtures import requires

from gbp_ps.cli import dump_bashrc

from . import TestCase, string_console


@requires("gbp")
class DumpBashrcHandlerTests(TestCase):
    def test_without_local(self) -> None:
        args = argparse.Namespace(url="http://gbp.invalid/", local=False)
        console, stdout = string_console()[:2]
        fixtures = self.fixtures

        exit_status = dump_bashrc.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)

        lines = stdout.getvalue().split("\n")
        self.assertTrue(lines[0].startswith("if [[ -f /Makefile.gbp"))
        self.assertTrue("http://gbp.invalid/graphql" in lines[-4], lines[-4])

    def test_local(self) -> None:
        args = argparse.Namespace(url="http://gbp.invalid/", local=True)
        console, stdout = string_console()[:2]
        fixtures = self.fixtures
        tmpdir = "/var/bogus"

        with mock.patch("gbp_ps.cli.dump_bashrc.sp.Popen") as popen:
            process = popen.return_value.__enter__.return_value
            process.wait.return_value = 0
            process.stdout.read.return_value = tmpdir.encode("utf-8")
            exit_status = dump_bashrc.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)

        output = stdout.getvalue()
        self.assertTrue(f"{tmpdir}/portage/gbpps.db" in output, output)

    def test_local_portageq_fail(self) -> None:
        args = argparse.Namespace(url="http://gbp.invalid/", local=True)
        console, stdout = string_console()[:2]
        fixtures = self.fixtures

        with mock.patch("gbp_ps.cli.dump_bashrc.sp.Popen") as popen:
            process = popen.return_value.__enter__.return_value
            process.wait.return_value = 1
            exit_status = dump_bashrc.handler(args, fixtures.gbp, console)

        self.assertEqual(exit_status, 0)

        output = stdout.getvalue()
        self.assertTrue("/var/tmp/portage/gbpps.db" in output, output)


class ParseArgsTests(TestCase):
    def test(self) -> None:
        # Just ensure that parse_args is there and works
        parser = argparse.ArgumentParser()
        dump_bashrc.parse_args(parser)
