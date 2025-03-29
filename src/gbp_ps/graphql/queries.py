"""Query GraphQL resolver for gbp-ps"""

from typing import Any, Iterable, TypeAlias

from ariadne import ObjectType, convert_kwargs_to_snake_case
from graphql import GraphQLResolveInfo

from gbp_ps.repository import Repo
from gbp_ps.settings import Settings
from gbp_ps.types import BuildProcess

Info: TypeAlias = GraphQLResolveInfo
Query = ObjectType("Query")


get_processes = Repo(Settings.from_environ()).get_processes


@Query.field("buildProcesses")
@convert_kwargs_to_snake_case
def _(
    _obj: Any, _info: Info, *, include_final: bool = False, machine: str
) -> Iterable[BuildProcess]:
    """Return the list of BuildProcesses

    If include_final is True also include processes in their "final" phase. The default
    value is False.
    """
    return get_processes(include_final=include_final, machine=machine)
