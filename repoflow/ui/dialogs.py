from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from repoflow.core.models import GitHubRepository, GitHubUser


class CloneDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Clone Repository")
        self.setMinimumWidth(520)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://github.com/user/repository.git")
        self.destination_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)

        dest_row = QHBoxLayout()
        dest_row.addWidget(self.destination_edit, 1)
        dest_row.addWidget(browse)

        form = QFormLayout()
        form.addRow("Repository URL", self.url_edit)
        holder = QWidget()
        holder.setLayout(dest_row)
        form.addRow("Destination", holder)

        note = QLabel("Use Clone when the repository is not on this computer yet. Connected GitHub credentials are used automatically for GitHub HTTPS URLs.")
        note.setObjectName("muted")
        note.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Clone")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose parent folder")
        if folder:
            repo_name = Path(self.url_edit.text().rstrip("/")).stem or "repository"
            self.destination_edit.setText(str(Path(folder) / repo_name))

    def values(self) -> tuple[str, str]:
        return self.url_edit.text().strip(), self.destination_edit.text().strip()


class RemoteDialog(QDialog):
    def __init__(self, current_url: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Connect Remote Repository")
        self.setMinimumWidth(520)
        self.name_edit = QLineEdit("origin")
        self.url_edit = QLineEdit(current_url)
        self.url_edit.setPlaceholderText("https://github.com/user/repository.git")

        form = QFormLayout()
        form.addRow("Remote name", self.name_edit)
        form.addRow("Repository URL", self.url_edit)

        note = QLabel("If the remote name already exists, RepoFlow updates its URL instead of creating a duplicate.")
        note.setWordWrap(True)
        note.setObjectName("muted")

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip() or "origin", self.url_edit.text().strip()


class BranchDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create Branch")
        self.setMinimumWidth(420)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("feature/my-change")

        note = QLabel(
            "Create a new local branch from the current commit and switch to it immediately."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Branch name", self.name_edit)

        buttons = QDialogButtonBox()
        self.cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self.create_button = buttons.addButton(
            "Create and Switch",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.create_button.setDefault(True)
        self.create_button.setEnabled(False)

        self.name_edit.textChanged.connect(
            lambda value: self.create_button.setEnabled(bool(value.strip()))
        )
        self.name_edit.returnPressed.connect(self._submit)
        self.create_button.clicked.connect(self._submit)
        self.cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.name_edit.setFocus()

    def _submit(self) -> None:
        if self.name():
            self.accept()

    def name(self) -> str:
        return self.name_edit.text().strip()


class GitHubTokenDialog(QDialog):
    TOKEN_URL = "https://github.com/settings/personal-access-tokens/new"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Connect GitHub")
        self.setMinimumWidth(560)

        title = QLabel("Connect your GitHub account")
        title.setObjectName("title")
        description = QLabel(
            "RepoFlow never asks for your GitHub password. Paste a Personal Access Token (PAT). "
            "GitHub controls what the token can access."
        )
        description.setWordWrap(True)
        description.setObjectName("muted")

        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.Password)
        self.token_edit.setPlaceholderText("github_pat_… or ghp_…")

        self.remember = QCheckBox("Remember using secure system credential storage")
        self.remember.setChecked(True)

        permission_note = QLabel(
            "For repository creation, the token needs permission to administer repositories. "
            "For private repositories, grant access only to the repositories you need whenever possible."
        )
        permission_note.setWordWrap(True)
        permission_note.setObjectName("muted")

        create_token = QPushButton("Create Token on GitHub")
        create_token.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.TOKEN_URL)))

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Personal Access Token"))
        layout.addWidget(self.token_edit)
        layout.addWidget(self.remember)
        layout.addWidget(permission_note)
        layout.addWidget(create_token, alignment=Qt.AlignLeft)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, bool]:
        return self.token_edit.text().strip(), self.remember.isChecked()


class GitHubAccountDialog(QDialog):
    def __init__(self, user: GitHubUser, storage_note: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Account")
        self.setMinimumWidth(520)
        self.disconnect_requested = False

        title = QLabel(f"@{user.login}")
        title.setObjectName("title")
        name = QLabel(user.name or "GitHub account")
        name.setObjectName("muted")

        details = QLabel(f"Public repositories: {user.public_repos}")
        details.setObjectName("muted")

        if storage_note:
            storage = QLabel(storage_note)
            storage.setWordWrap(True)
            storage.setObjectName("muted")
        else:
            storage = None

        open_profile = QPushButton("Open GitHub Profile")
        open_profile.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(user.html_url)))
        disconnect = QPushButton("Disconnect")
        disconnect.clicked.connect(self._disconnect)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)

        row = QHBoxLayout()
        row.addWidget(open_profile)
        row.addStretch(1)
        row.addWidget(disconnect)
        row.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(name)
        layout.addWidget(details)
        if storage:
            layout.addWidget(storage)
        layout.addSpacing(10)
        layout.addLayout(row)

    def _disconnect(self) -> None:
        self.disconnect_requested = True
        self.accept()


class CreateGitHubRepositoryDialog(QDialog):
    def __init__(self, suggested_name: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Create GitHub Repository")
        self.setMinimumWidth(560)

        self.name_edit = QLineEdit(suggested_name)
        self.name_edit.setPlaceholderText("my-project")
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Short repository description (optional)")
        self.description_edit.setFixedHeight(82)
        self.private_check = QCheckBox("Private repository")

        note = QLabel(
            "RepoFlow creates the GitHub repository without an initial README/commit. "
            "That keeps it safe to connect an existing local project without unrelated history."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")

        form = QFormLayout()
        form.addRow("Repository name", self.name_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Visibility", self.private_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Create Repository")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, bool]:
        return self.name_edit.text().strip(), self.description_edit.toPlainText().strip(), self.private_check.isChecked()


class GitHubRepositoriesDialog(QDialog):
    def __init__(self, repositories: list[GitHubRepository], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Repositories")
        self.resize(720, 560)
        self.repositories = repositories
        self.selected_repository: GitHubRepository | None = None
        self.action = ""

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search repositories…")
        self.search.textChanged.connect(self._filter)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._selection_changed)
        self.list.itemDoubleClicked.connect(lambda _item: self._choose("clone"))

        self.details = QLabel("Select a repository.")
        self.details.setWordWrap(True)
        self.details.setObjectName("muted")

        clone = QPushButton("Clone")
        clone.setObjectName("primary")
        clone.clicked.connect(lambda: self._choose("clone"))
        open_button = QPushButton("Open on GitHub")
        open_button.clicked.connect(lambda: self._choose("open"))
        close = QPushButton("Close")
        close.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(open_button)
        row.addWidget(clone)
        row.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.details)
        layout.addLayout(row)
        self._populate(repositories)

    def _populate(self, repositories: list[GitHubRepository]) -> None:
        self.list.clear()
        for repo in repositories:
            visibility = "Private" if repo.private else "Public"
            item = QListWidgetItem(f"{repo.full_name}\n{visibility} • default: {repo.default_branch}")
            item.setData(Qt.UserRole, repo)
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for index in range(self.list.count()):
            item = self.list.item(index)
            repo: GitHubRepository = item.data(Qt.UserRole)
            hay = f"{repo.full_name} {repo.description or ''}".lower()
            item.setHidden(bool(needle) and needle not in hay)

    def _selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if not current:
            self.selected_repository = None
            self.details.setText("Select a repository.")
            return
        repo: GitHubRepository = current.data(Qt.UserRole)
        self.selected_repository = repo
        visibility = "Private" if repo.private else "Public"
        self.details.setText(f"{visibility} • {repo.description or 'No description'}\n{repo.html_url}")

    def _choose(self, action: str) -> None:
        if not self.selected_repository:
            return
        self.action = action
        self.accept()
