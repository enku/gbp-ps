"""Mutation GraphQL type for gbp-ps"""

from typing import Any, TypeAlias

from ariadne import ObjectType, convert_kwargs_to_snake_case
from graphql import GraphQLResolveInfo

from gbp_ps.repository import Repo, add_or_update_process
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

Info: TypeAlias = GraphQLResolveInfo
Mutation = ObjectType("Mutation")

ADD_BUILD_FIELDS = {"machine", "id", "package", "phase"}


@Mutation.field("addBuildProcess")
@convert_kwargs_to_snake_case
def _(_obj: Any, _info: Info, process: dict[str, Any]) -> None:
    """Add the given process to the process table

    If the process already exists in the table, it is updated with the new value
    """
    # Don't bother when required fields are empty.
    if not all(process[field] for field in ADD_BUILD_FIELDS):
        return

    process["build_id"] = process.pop("id")
    add_or_update_process(Repo(Settings.from_environ()), BuildProcess(**process))
