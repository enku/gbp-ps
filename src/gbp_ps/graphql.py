"""GraphQL interface for gbp-ps"""
from importlib import resources
from typing import Any

from ariadne import ObjectType, gql
from graphql import GraphQLResolveInfo

import gbp_ps
from gbp_ps.exceptions import RecordNotFoundError
from gbp_ps.types import BuildProcess

type_defs = gql(resources.read_text("gbp_ps", "schema.graphql"))
resolvers = [query := ObjectType("Query"), mutation := ObjectType("Mutation")]


@query.field("buildProcesses")
def resolve_query_build_processes(
    _obj: Any, _info: GraphQLResolveInfo, *, includeFinal: bool = False
) -> list[dict[str, Any]]:
    """Return the list of BuildProcesses

    If includeFinal is True also include processes in their "final" phase. The default
    value is False.
    """
    return [
        {
            "build_host": process.build_host,
            "id": process.build_id,
            "machine": process.machine,
            "package": process.package,
            "phase": process.phase,
            "start_time": process.start_time,
        }
        for process in gbp_ps.get_processes(include_final=includeFinal)
    ]


@mutation.field("addBuildProcess")
def resolve_mutation_add_build_process(
    _obj: Any, _info: GraphQLResolveInfo, process: dict[str, Any]
) -> None:
    """Add the given process to the process table

    If the process already exists in the table, it is updated with the new value
    """
    # Don't bother when required fields are empty.
    if not all(
        [process["machine"], process["id"], process["package"], process["phase"]]
    ):
        return

    build_process = make_build_process(process)

    try:
        gbp_ps.update_process(build_process)
    except RecordNotFoundError:
        gbp_ps.add_process(build_process)


def make_build_process(process_dict: dict[str, Any]) -> BuildProcess:
    """Convert the BuildProcessType to a BuildProcess"""
    return BuildProcess(
        machine=process_dict["machine"],
        build_id=process_dict["id"],
        build_host=process_dict["buildHost"],
        package=process_dict["package"],
        phase=process_dict["phase"],
        start_time=process_dict["startTime"],
    )
