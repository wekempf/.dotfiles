from __future__ import annotations

from pytest_bdd import given, scenarios

from tests.integration.support import ROOT_HOME, ContainerRuntime, IntegrationWorld


scenarios("features/qenv_apply.feature")


@given("a bootstrapped Debian container")
def bootstrapped_container(
    container_runtime: ContainerRuntime,
    integration_world: IntegrationWorld,
) -> None:
    session = container_runtime.create_session()
    bootstrap = session.run("./bootstrap.sh", home=ROOT_HOME)
    assert bootstrap.exit_code == 0, bootstrap.stderr
    integration_world.session = session