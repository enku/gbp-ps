"""BuildProcess GraphQL resolver for gbp-ps"""

from typing import TypeAlias

from ariadne import ObjectType
from graphql import GraphQLResolveInfo

from gbp_ps import types

BuildProcess = ObjectType("BuildProcess")
Info: TypeAlias = GraphQLResolveInfo

# pylint: disable=missing-docstring


@BuildProcess.field("id")
def _(process: types.BuildProcess, _info: Info) -> str:
    return process.build_id
