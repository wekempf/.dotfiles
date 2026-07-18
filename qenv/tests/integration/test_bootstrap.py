from __future__ import annotations

from pytest_bdd import given, scenarios

from tests.integration.support import ContainerRuntime, IntegrationWorld


scenarios("features/bootstrap.feature")


@given("a fresh Debian bootstrap container without python")
def fresh_bootstrap_container(
    container_runtime: ContainerRuntime,
    integration_world: IntegrationWorld,
) -> None:
    session = container_runtime.create_session()
    result = session.run("command -v python3")
    assert result.exit_code != 0, (
        "expected a minimal bootstrap container without python3; "
        "command unexpectedly succeeded: command -v python3"
    )
    integration_world.session = session