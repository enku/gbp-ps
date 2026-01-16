"""BuildProcess GraphQL resolver for gbp-ps"""

from ariadne import ObjectType
from graphql import GraphQLResolveInfo

from gbp_ps import types

BUILD_PROCESS = ObjectType("BuildProcess")
type Info = GraphQLResolveInfo

# pylint: disable=missing-docstring,redefined-builtin


@BUILD_PROCESS.field("id")
def id(process: types.BuildProcess, _info: Info) -> str:
    return process.build_id
