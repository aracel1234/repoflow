# Changelog

## v0.2.7

- Added KDE Neon/Ubuntu detection for the `libsecret-tools` system dependency used by secure GitHub token persistence.
- Installer now offers to install `libsecret-tools` when `secret-tool` is missing.
- Improved credential diagnostics to distinguish a missing helper from a Secret Service backend failure.
- Added `scripts/check_secure_storage.sh` for an end-to-end Secret Service store/lookup/clear probe.
- Added automated tests for secure credential fallback, successful persistence, and backend failure messages.


## v0.2.6

- Fixed Qt dialog acceptance checks for PySide6 6.11 by using `QDialog.DialogCode.Accepted`.
- Fixed GitHub token dialog flow so valid and invalid tokens now reach API validation.
- Applied the same dialog-result fix to Clone, GitHub repository browser, Create GitHub Repository, and Connect Remote flows.
- Added regression coverage preventing instance-level `dialog.Accepted` checks from returning.


## v0.2.5

- Fixed silent GitHub authentication failures by keeping background worker objects alive until completion.
- Added explicit invalid-token feedback with a `GitHub Authentication Failed` dialog and status-bar message.
- Added background task lifecycle logging for GitHub and network operations.
- Added regression coverage for GitHub 401 authentication errors and worker error signal delivery.

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
