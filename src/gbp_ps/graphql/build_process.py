"""BuildProcess GraphQL resolver for gbp-ps"""

from ariadne import ObjectType
from graphql import GraphQLResolveInfo

from gbp_ps import types

BuildProcess = ObjectType("BuildProcess")
type Info = GraphQLResolveInfo

# pylint: disable=missing-docstring


@BuildProcess.field("id")
def _(process: types.BuildProcess, _info: Info) -> str:
    return process.build_id
