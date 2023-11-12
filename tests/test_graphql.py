"""Tests for the GraphQL interface for gbp-ps"""
# pylint: disable=missing-docstring

import datetime as dt
from dataclasses import asdict
from typing import Any

from django.test import TestCase
from django.test.client import Client

import gbp_ps
from gbp_ps.repository import Repository
from gbp_ps.types import BuildProcess


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
        self.assertEqual(
            result["data"]["buildProcesses"], [build_process_dict(build_process)]
        )


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

    def test(self) -> None:
        p_obj = make_build_process()
        p_dict = build_process_dict(p_obj)
        result = graphql(self.query, {"process": p_dict})

        self.assertNotIn("errors", result)
        [process] = gbp_ps.get_processes()
        self.assertEqual(process, p_obj)

    def test_update(self) -> None:
        p_dict = build_process_dict(make_build_process())
        graphql(self.query, {"process": p_dict})

        p_dict["phase"] = "postinst"
        result = graphql(self.query, {"process": p_dict})
        self.assertNotIn("errors", result)
        [p_obj] = Repository().get_processes()
        self.assertEqual(p_obj.phase, "postinst")


def build_process_dict(build_process: BuildProcess) -> dict[str, Any]:
    bp_dict = asdict(build_process)
    bp_dict["buildHost"] = bp_dict.pop("build_host")
    bp_dict["id"] = bp_dict.pop("build_id")
    bp_dict["startTime"] = bp_dict.pop("start_time").isoformat()

    return bp_dict


def make_build_process(**kwargs: Any) -> BuildProcess:
    repo = Repository()
    build_process = BuildProcess(
        machine="babette",
        build_id="1031",
        build_host="jenkins",
        package="sys-apps/systemd-254.5-r1",
        phase="compile",
        start_time=dt.datetime(2023, 11, 11, 12, 20, 52, tzinfo=dt.timezone.utc),
        **kwargs,
    )
    repo.add_process(build_process)

    return build_process
