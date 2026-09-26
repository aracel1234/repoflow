# Changelog

## v0.2.4

### Fixed

- Fixed the New Branch dialog flow so accepting the dialog reliably creates and switches branches.
- Replaced the mnemonic label `Create & Switch` with the clearer `Create and Switch`.
- Refresh branch UI only after Git confirms the active branch.
- Added clear errors for invalid, duplicate, or missing local branch names.

### Added

- Git branch-name validation through `git check-ref-format --branch`.
- Post-create and post-switch branch verification.
- Branch workflow logging and status-bar feedback.
- Automated regression tests for create/switch branch workflows.

## v0.2.3

### Fixed

- Represent files with simultaneous staged and unstaged changes as `Partially staged`.
- Use a partial checkbox state instead of incorrectly presenting such files as fully staged.
- Separate staged and unstaged diffs in the Changes panel.
- Clarify that only staged changes are included in the next commit.

### Added

- Automated regression tests for partial staging.
- Source repository `.gitignore` and test runner.

## v0.2.2

- Fixed native Qt crash during stage/unstage refresh.
- Deferred Changes tree rebuild until after `itemChanged` returns.
- Added signal blocking while rebuilding the Changes tree.
- Switched installation runtime to system Python instead of Conda/Miniconda.
- Added startup/native-failure diagnostics.

## v0.2.1

- Removed Python `keyring` dependency to avoid Linux dependency-resolution problems.
- Added Linux Secret Service integration through `secret-tool` when available.

## v0.2.0

- Added GitHub account integration.
- Added GitHub repository browser and repository creation.
- Added authenticated HTTPS Git operations through `GIT_ASKPASS`.

## v0.1.x

- Initial local Git desktop workflow: repository management, status, staging, diff, commit, history, branches, fetch, pull, and push.
