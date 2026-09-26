# RepoFlow

RepoFlow is a lightweight desktop Git and GitHub client designed for Linux, with KDE-friendly installation and a workflow focused on everyday repository tasks without requiring terminal commands.

> Current development version: **v0.2.7**
> v0.2.7 improves secure GitHub-token persistence on KDE Neon/Ubuntu by detecting `libsecret-tools`, offering installation, and reporting Secret Service failures clearly.

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
- Detect **partially staged files**.
- Display staged and unstaged diffs separately.
- Create commits from staged changes.
- Create multiple local commits before pushing.
- View commit history.
- Create and switch local branches.
- Fetch remote changes.
- Pull using fast-forward-only mode.
- Push and automatically establish the upstream branch on the first push.
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

Expected result for v0.2.3:

```text
Ran 6 tests
OK
```

## Project Structure

```text
RepoFlow/
├── repoflow/
│   ├── core/
│   │   ├── models.py
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

- `.gitignore` management UI
- sensitive-file warnings
- large-file warnings
- richer conflict detection and resolution
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
