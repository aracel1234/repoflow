# Changelog

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
