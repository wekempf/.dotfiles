Feature: bootstrap script
  Bootstrap should provision the minimum prerequisites needed to hand off to qenv.

  Scenario: bootstrap provisions python and qenv in a minimal container
    Given a fresh Debian bootstrap container without python
    When I run "./bootstrap.sh"
    Then the command should succeed
    And "python3" should be available in the container
    And "qenv" should be available in the container

  Scenario: bootstrap fails clearly without root access when python is missing
    Given a fresh Debian bootstrap container without python
    When I run "./bootstrap.sh" as an unprivileged user
    Then the command should fail
    And stderr should contain "install Python 3 manually"

  Scenario: bootstrap can be run twice without failing
    Given a fresh Debian bootstrap container without python
    When I run "./bootstrap.sh"
    Then the command should succeed
    When I run "./bootstrap.sh"
    Then the command should succeed
    And "qenv" should be available in the container