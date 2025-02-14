"""BuildProcess GraphQL resolver for gbp-ps"""

from typing import TypeAlias

from ariadne import ObjectType
from graphql import GraphQLResolveInfo

from gbp_ps.types import BuildProcess

BuildProcessType = ObjectType("BuildProcess")
Info: TypeAlias = GraphQLResolveInfo

# pylint: disable=missing-docstring


@BuildProcessType.field("id")
def process_id(process: BuildProcess, _info: Info) -> str:
    return process.build_id
