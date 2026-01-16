"""GraphQL interface for gbp-ps"""

from importlib import resources

from ariadne import gql

from .build_process import BUILD_PROCESS
from .mutations import MUTATION
from .queries import QUERY

type_defs = gql(resources.read_text("gbp_ps.graphql", "schema.graphql"))
resolvers = [BUILD_PROCESS, MUTATION, QUERY]
