"""Tests for the GraphQL interface for gbp-ps"""

# pylint: disable=missing-docstring,unused-argument

from dataclasses import replace
from typing import Any

from django.test.client import Client
from gentoo_build_publisher.signals import dispatcher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given

from . import lib


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


class GetProcessesTests(lib.TestCase):
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
        build_process = lib.make_build_process()

        result = graphql(self.query)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["buildProcesses"], [build_process.to_dict()])

    def test_non_empty_with_final_processes(self) -> None:
        live_process = lib.make_build_process(package="sys-apps/systemd-254.5-r1")
        lib.make_build_process(package="sys-libs/efivar-38", phase="clean")

        result = graphql(self.query)

        self.assertNotIn("errors", result)
        self.assertEqual(result["data"]["buildProcesses"], [live_process.to_dict()])

    def test_non_empty_with_final_processes_included(self) -> None:
        lib.make_build_process(package="sys-apps/systemd-254.5-r1")
        lib.make_build_process(package="sys-libs/efivar-38", phase="clean")
        query = "{buildProcesses(includeFinal: true) { machine id package startTime }}"

        result = graphql(query)

        self.assertNotIn("errors", result)
        self.assertEqual(len(result["data"]["buildProcesses"]), 2)


@given(lib.repo)
class AddBuildProcessesTests(lib.TestCase):
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
        process = lib.make_build_process()
        result = graphql(self.query, {"process": process.to_dict()})

        self.assertNotIn("errors", result)
        processes = [*fixtures.repo.get_processes()]
        self.assertEqual(processes, [process])

    def test_add_process_emits_signal(self, fixtures: Fixtures) -> None:
        process = lib.make_build_process(add_to_repo=False)
        callback_args: dict[str, Any] = {}

        def callback(*args: Any, **kwargs: Any) -> None:
            callback_args["args"] = args
            callback_args["kwargs"] = kwargs

        dispatcher.bind(gbp_ps_add_process=callback)

        try:
            graphql(self.query, {"process": process.to_dict()})
        finally:
            dispatcher.unbind(callback)

        build = Build(machine=process.machine, build_id=process.build_id)
        self.assertEqual(
            callback_args, {"args": (), "kwargs": {"build": build, "process": process}}
        )

    def test_update_process_emits_signal(self, fixtures: Fixtures) -> None:
        process = lib.make_build_process()
        updated = replace(process, phase="clean")
        callback_args: dict[str, Any] = {}

        def callback(*args: Any, **kwargs: Any) -> None:
            callback_args["args"] = args
            callback_args["kwargs"] = kwargs

        dispatcher.bind(gbp_ps_update_process=callback)

        try:
            graphql(self.query, {"process": updated.to_dict()})
        finally:
            dispatcher.unbind(callback)

        build = Build(machine=process.machine, build_id=process.build_id)
        self.assertEqual(
            callback_args, {"args": (), "kwargs": {"build": build, "process": updated}}
        )

    def test_update(self, fixtures: Fixtures) -> None:
        p_dict = lib.make_build_process().to_dict()
        graphql(self.query, {"process": p_dict})

        p_dict["phase"] = "postinst"
        result = graphql(self.query, {"process": p_dict})
        self.assertNotIn("errors", result)
        processes = [*fixtures.repo.get_processes()]
        self.assertEqual(processes[0].phase, "postinst")

    def test_empty_phase_does_not_get_added(self, fixtures: Fixtures) -> None:
        p_dict = lib.make_build_process(phase="", add_to_repo=False).to_dict()
        result = graphql(self.query, {"process": p_dict})

        self.assertNotIn("errors", result)
        self.assertEqual([*fixtures.repo.get_processes(include_final=True)], [])

    def test_empty_machine_does_not_get_added(self, fixtures: Fixtures) -> None:
        p_dict = lib.make_build_process(machine="", add_to_repo=False).to_dict()
        result = graphql(self.query, {"process": p_dict})

        self.assertNotIn("errors", result)
        self.assertEqual([*fixtures.repo.get_processes(include_final=True)], [])
