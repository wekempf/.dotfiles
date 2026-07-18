from __future__ import annotations

import pytest
from pytest_bdd import parsers, then, when

from tests.integration.support import (
    NONROOT_GID,
    NONROOT_HOME,
    NONROOT_UID,
    ROOT_HOME,
    ContainerRuntime,
    IntegrationWorld,
    detect_runtime,
)

@pytest.fixture(scope="session")
def container_runtime() -> ContainerRuntime:
    return ContainerRuntime(detect_runtime())


@pytest.fixture
def integration_world() -> IntegrationWorld:
    return IntegrationWorld()


@pytest.fixture(autouse=True)
def cleanup_session(integration_world: IntegrationWorld):
    yield
    if integration_world.session is not None:
        integration_world.session.cleanup()


@when(parsers.parse('I run "{command}"'))
def run_command(command: str, integration_world: IntegrationWorld) -> None:
    assert integration_world.session is not None
    integration_world.result = integration_world.session.run(command, home=ROOT_HOME)


@when(parsers.parse('I run "{command}" as an unprivileged user'))
def run_command_unprivileged(command: str, integration_world: IntegrationWorld) -> None:
    assert integration_world.session is not None
    integration_world.result = integration_world.session.run(
        command,
        user=f"{NONROOT_UID}:{NONROOT_GID}",
        home=NONROOT_HOME,
    )


@then("the command should succeed")
def command_should_succeed(integration_world: IntegrationWorld) -> None:
    assert integration_world.result is not None
    assert integration_world.result.exit_code == 0, integration_world.result.stderr


@then("the command should fail")
def command_should_fail(integration_world: IntegrationWorld) -> None:
    assert integration_world.result is not None
    assert integration_world.result.exit_code != 0


@then(parsers.parse('"{binary}" should be available in the container'))
def binary_should_be_available(binary: str, integration_world: IntegrationWorld) -> None:
    assert integration_world.session is not None
    result = integration_world.session.run(f"command -v {binary}", home=ROOT_HOME)
    assert result.exit_code == 0, result.stderr


@then(parsers.parse('stdout should contain "{text}"'))
def stdout_should_contain(text: str, integration_world: IntegrationWorld) -> None:
    assert integration_world.result is not None
    assert text in integration_world.result.stdout


@then(parsers.parse('stderr should contain "{text}"'))
def stderr_should_contain(text: str, integration_world: IntegrationWorld) -> None:
    assert integration_world.result is not None
    assert text in integration_world.result.stderr