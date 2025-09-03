"""noxfile for ci/cd testing"""

# pylint: disable=missing-docstring
import nox


@nox.session(python=("3.12", "3.13", "3.14"))
def tests(session: nox.Session) -> None:
    pyproject = nox.project.load_toml("pyproject.toml")
    dev_deps = pyproject["dependency-groups"]["dev"]
    server_deps = pyproject["project"]["optional-dependencies"]["server"]
    redis_deps = pyproject["project"]["optional-dependencies"]["redis"]
    session.install(".", *dev_deps, *server_deps, *redis_deps)

    session.run("python", "-m", "tests")
