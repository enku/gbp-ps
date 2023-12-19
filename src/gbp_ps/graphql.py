"""GraphQL interface for gbp-ps"""
from importlib import resources
from typing import Any

from ariadne import ObjectType, convert_kwargs_to_snake_case, gql
from graphql import GraphQLResolveInfo

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

type_defs = gql(resources.read_text("gbp_ps", "schema.graphql"))
resolvers = [query := ObjectType("Query"), mutation := ObjectType("Mutation")]


@query.field("buildProcesses")
@convert_kwargs_to_snake_case
def resolve_query_build_processes(
    _obj: Any, _info: GraphQLResolveInfo, *, include_final: bool = False
) -> list[dict[str, Any]]:
    """Return the list of BuildProcesses

    If include_final is True also include processes in their "final" phase. The default
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
        for process in Repo(Settings.from_environ()).get_processes(
            include_final=include_final
        )
    ]


@mutation.field("addBuildProcess")
def resolve_mutation_add_build_process(
    _obj: Any, _info: GraphQLResolveInfo, process: dict[str, Any]
) -> None:
    """Add the given process to the process table

    If the process already exists in the table, it is updated with the new value
    """
    # Don't bother when required fields are empty.
    if not all(process[field] for field in ["machine", "id", "package", "phase"]):
        return

    add_or_update_process(Repo(Settings.from_environ()), make_build_process(process))


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
