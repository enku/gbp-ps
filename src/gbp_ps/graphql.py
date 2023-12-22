"""GraphQL interface for gbp-ps"""
# pylint: disable=missing-docstring
from importlib import resources
from typing import Any

from ariadne import ObjectType, convert_kwargs_to_snake_case, gql
from graphql import GraphQLResolveInfo

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

type_defs = gql(resources.read_text("gbp_ps", "schema.graphql"))
resolvers = [
    build_process := ObjectType("BuildProcess"),
    query := ObjectType("Query"),
    mutation := ObjectType("Mutation"),
]


@build_process.field("id")
def resolve_build_process_id(process: BuildProcess, _info: GraphQLResolveInfo) -> str:
    return process.build_id


@query.field("buildProcesses")
@convert_kwargs_to_snake_case
def resolve_query_build_processes(
    _obj: Any, _info: GraphQLResolveInfo, *, include_final: bool = False
) -> list[BuildProcess]:
    """Return the list of BuildProcesses

    If include_final is True also include processes in their "final" phase. The default
    value is False.
    """
    return [*Repo(Settings.from_environ()).get_processes(include_final=include_final)]


@mutation.field("addBuildProcess")
@convert_kwargs_to_snake_case
def resolve_mutation_add_build_process(
    _obj: Any, _info: GraphQLResolveInfo, process: dict[str, Any]
) -> None:
    """Add the given process to the process table

    If the process already exists in the table, it is updated with the new value
    """
    # Don't bother when required fields are empty.
    if not all(process[field] for field in ["machine", "id", "package", "phase"]):
        return

    process["build_id"] = process.pop("id")
    add_or_update_process(Repo(Settings.from_environ()), BuildProcess(**process))
