Feature: qenv apply
  qenv should be usable from a real bootstrapped container without mocks.

  Scenario: qenv can plan package installation after bootstrap
    Given a bootstrapped Debian container
    When I run "qenv apply bat --dry-run"
    Then the command should succeed
    And stdout should contain "install bat via apt"

  Scenario: qenv can list managed packages after bootstrap
    Given a bootstrapped Debian container
    When I run "qenv package list"
    Then the command should succeed
    And stdout should contain "bootstrap-tools: Bootstrap prerequisites managed by qenv"
    And stdout should contain "bat: bat pager configuration"

  Scenario: qenv can inspect host details after bootstrap
    Given a bootstrapped Debian container
    When I run "qenv --verbose host show"
    Then the command should succeed
    And stdout should contain "Package Managers: apt"
    And stdout should contain "Discovered Providers:"

  Scenario: qenv reports no changes for bootstrap-tools after bootstrap
    Given a bootstrapped Debian container
    When I run "qenv apply bootstrap-tools --dry-run"
    Then the command should succeed
    And stdout should contain "No changes required for package 'bootstrap-tools'."

  Scenario: qenv reports helpful errors for unknown packages
    Given a bootstrapped Debian container
    When I run "qenv apply nonexistent --dry-run"
    Then the command should fail
    And stderr should contain "unknown package 'nonexistent'"
    And stderr should contain "Run qenv package list to see available package names."