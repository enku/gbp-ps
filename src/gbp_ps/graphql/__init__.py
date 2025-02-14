"""GraphQL interface for gbp-ps"""

from importlib import resources

from ariadne import gql

from .build_process import BuildProcessType
from .mutations import Mutation
from .queries import Query

type_defs = gql(resources.read_text("gbp_ps.graphql", "schema.graphql"))
resolvers = [BuildProcessType, Mutation, Query]
