"""Tests for the GraphQL interface for gbp-ps"""

# pylint: disable=missing-docstring,unused-argument

from typing import Any

from django.test.client import Client
from unittest_fixtures import Fixtures, given

from . import TestCase, make_build_process


def graphql(query: str, variables: dict[str, Any] | None = None) -> Any:
    """Execute GraphQL query on the Django test client.

    Return the parsed JSON response
    """
    client = Client()
    response = client.post(
        "/graphql",
        {"query": query, "variables": variables},
        content_type="application/json",
    )

    return response.json()


class GetProcessesTests(TestCase):
    query = """
    {
      buildProcesses {
        machine
        id
        buildHost
        package
        phase
         startTime
      }
    }
    """

    def test_empty(self) -> None:
        result = graphql(self.query)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["buildProcesses"], [])

    def test_nonempty(self) -> None:
        build_process = make_build_process()

        result = graphql(self.query)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["buildProcesses"], [build_process.to_dict()])

    def test_non_empty_with_final_processes(self) -> None:
        live_process = make_build_process(package="sys-apps/systemd-254.5-r1")
        make_build_process(package="sys-libs/efivar-38", phase="clean")

        result = graphql(self.query)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["buildProcesses"], [live_process.to_dict()])

    def test_non_empty_with_final_processes_included(self) -> None:
        make_build_process(package="sys-apps/systemd-254.5-r1")
        make_build_process(package="sys-libs/efivar-38", phase="clean")
        query = "{buildProcesses(includeFinal: true) { machine id package startTime }}"

        result = graphql(query)

        self.assertNotIn("errors", result)
        self.assertEqual(len(result["data"]["buildProcesses"]), 2)


@given("repo")
class AddBuildProcessesTests(TestCase):
    query = """
    mutation (
      $process: BuildProcessInput!,
    ) {
      addBuildProcess(
        process: $process,
      ) {
        message
      }
    }
    """

    def test(self, fixtures: Fixtures) -> None:
        process = make_build_process()
        result = graphql(self.query, {"process": process.to_dict()})

        self.assertNotIn("errors", result)
        processes = [*fixtures.repo.get_processes()]
        self.assertEqual(processes, [process])

    def test_update(self, fixtures: Fixtures) -> None:
        p_dict = make_build_process().to_dict()
        graphql(self.query, {"process": p_dict})

        p_dict["phase"] = "postinst"
        result = graphql(self.query, {"process": p_dict})
        self.assertNotIn("errors", result)
        processes = [*fixtures.repo.get_processes()]
        self.assertEqual(processes[0].phase, "postinst")

    def test_empty_phase_does_not_get_added(self, fixtures: Fixtures) -> None:
        p_dict = make_build_process(phase="", add_to_repo=False).to_dict()
        result = graphql(self.query, {"process": p_dict})

        self.assertNotIn("errors", result)
        self.assertEqual([*fixtures.repo.get_processes(include_final=True)], [])

    def test_empty_machine_does_not_get_added(self, fixtures: Fixtures) -> None:
        p_dict = make_build_process(machine="", add_to_repo=False).to_dict()
        result = graphql(self.query, {"process": p_dict})

        self.assertNotIn("errors", result)
        self.assertEqual([*fixtures.repo.get_processes(include_final=True)], [])
