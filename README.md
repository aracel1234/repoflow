# RepoFlow

RepoFlow is a lightweight desktop Git and GitHub client designed for Linux, with KDE-friendly installation and a workflow focused on everyday repository tasks without requiring terminal commands.

> Current development version: **v0.3.1**
> v0.3.1 continues Stage 3 with stash management, explicit hunk staging, safer branch management, and a richer conflict-review workflow while preserving RepoFlow's non-destructive defaults.

RepoFlow is currently under active development. The project is being tested incrementally before a stable release is published.

## Why RepoFlow?

Git is powerful, but routine commands such as staging files, creating commits, checking repository status, pushing, pulling, cloning, and connecting remotes can become repetitive when performed from a terminal.

RepoFlow provides a simple graphical workflow for those operations while keeping Git itself as the source of truth.

The application does **not** implement a separate version-control system. It operates on standard Git repositories and uses the Git CLI internally.

## Current Features

### Local Git workflow

- Open an existing local Git repository.
- Initialize an existing folder as a Git repository.
- Remember recently opened repositories.
- Automatically detect:
  - repository root;
  - active branch;
  - remote URL;
  - upstream branch;
  - ahead/behind commit counts.
- Display changed files including:
  - modified;
  - new/untracked;
  - added;
  - deleted;
  - renamed;
  - conflicted files.
- Stage and unstage files using checkboxes.
- Stage selected text hunks explicitly with **Stage Selected Hunks…** while leaving other hunks unstaged.
- Detect **partially staged files**.
- Display staged and unstaged diffs separately.
- Detect binary files and show a safe metadata preview instead of decoding raw bytes.
- Create commits from staged changes.
- Create multiple local commits before pushing.
- View commit history.
- Create and switch local branches.
- Rename local branches and safely delete merged branches without force deletion.
- Save, apply, and drop Git stashes from **Repository → Stashes…**.
- Warn before staging likely credential/key files and unusually large files.
- Review risky staged files again before commit when they were staged outside RepoFlow.
- Manage `.gitignore` from the Repository menu with optional common presets.
- Surface unresolved conflicts and diverged histories with explicit safety banners.
- Review conflicted files and conflict markers from RepoFlow without automatically choosing `ours` or `theirs`.
- Block Pull/Push during unresolved conflict/divergence states without force-pushing or choosing a reconciliation strategy automatically.
- Fetch remote changes.
- Pull using fast-forward-only mode.
- Push and automatically establish the upstream branch on the first push.
- Show explicit completion feedback for fetch, pull, and push operations, including `Already up to date.`
- Connect or update a Git remote without using a terminal.
- Open the configured GitHub remote in a browser.

### GitHub integration

- Connect a GitHub account using a Personal Access Token.
- Validate the authenticated account through the GitHub API.
- Browse accessible GitHub repositories.
- Search repositories from the repository browser.
- Clone repositories from the connected GitHub account.
- Clone repositories directly from a URL.
- Create a public or private GitHub repository.
- Connect a newly created GitHub repository to the current local repository as `origin`.
- Use GitHub credentials for HTTPS Git operations through `GIT_ASKPASS` without embedding the token in the remote URL.
- Use Linux Secret Service through `secret-tool` when available; otherwise the token remains session-only.

## Partial Staging

RepoFlow v0.2.3 introduces explicit support for files that contain both staged and unstaged changes.

For example:

```text
README.md
├── staged:   VERSION A
└── unstaged: VERSION B
```

RepoFlow displays the file as:

```text
◩ README.md    Modified · Partially staged
```

The diff panel is separated into:

```text
STAGED CHANGES
+ VERSION A

UNSTAGED CHANGES
+ VERSION B
```

Only **STAGED CHANGES** are included in the next commit.

Checkbox meaning:

```text
☐  Unstaged
☑  Fully staged
◩  Partially staged
```

When a partially staged file is checked, RepoFlow stages the complete current file. When it is unchecked, RepoFlow removes the file from the staging area.

## Advanced Working-Tree Tools

### Selected-hunk staging

For a tracked text file with multiple unstaged hunks, select the file and click **Stage Selected Hunks…**. RepoFlow shows each `@@` diff hunk separately and stages only the checked hunks. Whole-file checkbox behavior is unchanged.

Hunk staging is intentionally unavailable for untracked, binary, renamed, deleted, conflicted, and mode-only changes; use whole-file staging for those cases.

### Stashes

Open **Repository → Stashes…** to temporarily save local work. RepoFlow can include untracked files, restores staged state when applying a stash, keeps an applied stash in the list, and asks before permanently dropping one.

### Branch management

Open **Repository → Manage Branches…** or use the branch button menu. Rename is local-only. Delete uses Git's safe `-d` mode so Git refuses to delete work that has not been merged.

## Safety Decisions

RepoFlow intentionally avoids several destructive or ambiguous automatic operations.

- No automatic force push.
- Pull uses `git pull --ff-only`.
- Diverged local/remote history is stopped instead of being silently merged or rebased.
- GitHub tokens are not written into repository remote URLs.
- Git status is always read from Git instead of being maintained as a separate application database.

More advanced conflict resolution and merge/rebase workflows are planned for later development stages.

## Requirements

Recommended environment:

- Linux / KDE Plasma
- Git
- Python 3.10+
- Python `venv`
- PySide6 6.7+
- `libsecret-tools` (recommended for securely remembering GitHub tokens across restarts)

The KDE Neon installer explicitly prefers `/usr/bin/python3` to isolate RepoFlow from Conda/Miniconda Python and Qt libraries.

## Install on KDE Neon

Extract or clone the repository, then run:

```bash
cd RepoFlow
./install_kde_neon.sh
```

If Python venv support is missing:

```bash
sudo apt install python3-venv
```

For secure GitHub-token persistence, the installer can install `libsecret-tools` when `secret-tool` is missing. It can also be installed manually:

```bash
sudo apt install libsecret-tools
```

To verify the desktop Secret Service end to end:

```bash
./scripts/check_secure_storage.sh
```

After installation, search for **RepoFlow** in the KDE Application Launcher.

Installed application files are placed under:

```text
~/.local/share/repoflow/
```

The launcher is installed at:

```text
~/.local/bin/repoflow
```

The desktop entry is installed at:

```text
~/.local/share/applications/repoflow.desktop
```

Runtime logs are stored at:

```text
~/.local/state/repoflow/repoflow.log
```

## Run From Source

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run RepoFlow:

```bash
python run.py
```

or:

```bash
python -m repoflow.main
```

## Run Automated Tests

The repository contains regression tests for Git staging behavior, including the partially staged file scenario introduced in v0.2.3.

Run:

```bash
./scripts/run_tests.sh
```

or:

```bash
python3 -m unittest discover -s tests -v
```

The exact count grows as regression coverage is added. For v0.3.0, run the suite and confirm that every discovered test finishes with `OK`.

## Project Structure

```text
RepoFlow/
├── repoflow/
│   ├── core/
│   │   ├── models.py
│   │   ├── safety.py
│   │   ├── settings.py
│   │   └── workers.py
│   ├── services/
│   │   ├── credential_service.py
│   │   ├── git_service.py
│   │   └── github_service.py
│   ├── ui/
│   │   ├── dialogs.py
│   │   ├── main_window.py
│   │   └── theme.py
│   └── main.py
├── tests/
│   ├── test_git_partial_staging.py
│   └── test_models.py
├── scripts/
│   └── run_tests.sh
├── install_kde_neon.sh
├── uninstall.sh
├── requirements.txt
├── pyproject.toml
├── run.py
├── .gitignore
└── README.md
```

## Architecture

```text
Qt / PySide6 UI
      │
      ├── GitService ─────── Git CLI ─────── Local repository
      │
      ├── GitHubService ─── GitHub REST API
      │
      └── CredentialService ─ Linux Secret Service / session memory
```

Network Git operations run outside the main UI thread so clone, fetch, pull, and push do not intentionally block the interface.

## Development Status

### Completed foundation

- Local repository management
- Changes and diff viewer
- Staging / unstaging
- Partial staging representation
- Commit workflow
- Commit history
- Basic branch management
- Fetch / fast-forward pull / push
- GitHub account integration
- GitHub repository browser
- GitHub repository creation
- HTTPS credential bridge
- KDE application launcher installation

### Planned

- in-app conflict resolution assistance
- merge/rebase decision workflow
- hunk/line staging
- stash support
- richer branch management
- distributable AppImage / `.deb`
- stable release workflow

## Security Notes

Do not commit secrets to this repository or to repositories managed with RepoFlow.

Examples include:

```text
.env
private keys
keystores
GitHub Personal Access Tokens
API credentials
```

RepoFlow's own `.gitignore` excludes common local secret and environment files, but users remain responsible for reviewing files before committing them.

## License

No open-source license has been selected yet. Until a license is added, the source is published without granting additional reuse rights beyond those provided by applicable law and the hosting platform.


## v0.2.8 QA Polish

The v0.2.8 milestone follows the T01–T50 validation pass. It does not add new destructive Git behavior; it improves feedback and presentation around the already validated workflows.

- `Commit and Push` avoids Qt mnemonic rendering from `&`.
- Background operations display an indeterminate activity indicator in the status bar.
- Success/error messages are no longer immediately overwritten by `Ready`.
- Pulling an already synchronized repository explicitly reports `Already up to date.`
- Binary files show a safe preview rather than raw byte output.
- The installer registers the RepoFlow application icon with KDE.


## v0.3.0 Stage 3 — Safety & Quality of Life

The first Stage 3 milestone adds guardrails around common repository mistakes while deliberately preserving user control. RepoFlow warns; it does not silently delete files, rewrite history, choose a merge/rebase strategy, or force-push.

### Safety review

RepoFlow reviews filenames and file size before staging/committing. Examples that trigger review include `.env`, common credential files, private-key/keystore formats, service-account files, Terraform state, and files above the large-file warning threshold. `.env.example`, `.env.sample`, and `.env.template` are intentionally treated as examples rather than secrets.

For an untracked risky file, the staging dialog offers three choices:

- **Cancel** — leave the working tree unchanged.
- **Add to .gitignore** — add a repository-root anchored rule and do not stage the file.
- **Stage Anyway** — acknowledge the warning and stage normally.

A second commit-time review catches risky files that were staged outside RepoFlow.

### `.gitignore` manager

Open **Repository → Manage .gitignore…** to edit the repository `.gitignore` directly. Optional Python, Node, Android, and Secrets presets append missing rules without deleting existing content.

### Conflict and divergence protection

If Git reports unresolved conflicts, RepoFlow shows a safety banner and disables Pull/Push until the conflicts are resolved and staged. If the current branch is both ahead and behind its upstream, RepoFlow shows a divergence banner and disables Pull/Push rather than choosing merge, rebase, reset, or force-push automatically. Fetch remains available so remote state can still be refreshed.
