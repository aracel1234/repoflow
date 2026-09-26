from __future__ import annotations

from pathlib import Path
import logging

from PySide6.QtCore import Qt, QSignalBlocker, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repoflow.core.models import GitFile, GitHubRepository, GitHubUser
from repoflow.core.settings import AppSettings
from repoflow.core.workers import FunctionWorker
from repoflow.services.credential_service import CredentialService
from repoflow.services.git_service import GitError, GitService
from repoflow.services.github_service import GitHubError, GitHubService
logger = logging.getLogger(__name__)


from repoflow.ui.dialogs import (
    BranchDialog,
    CloneDialog,
    CreateGitHubRepositoryDialog,
    GitHubAccountDialog,
    GitHubRepositoriesDialog,
    GitHubTokenDialog,
    RemoteDialog,
)


class MainWindow(QMainWindow):
    COL_CHECK = 0
    COL_STATUS = 1
    COL_PATH = 2

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RepoFlow")
        self.resize(1320, 800)
        self.setMinimumSize(1020, 640)

        self.settings = AppSettings()
        self.credentials = CredentialService()
        self.git: GitService | None = None
        self.repo_path: str | None = None
        self.file_rows: dict[str, QTreeWidgetItem] = {}
        self._loading_checks = False
        self._change_refresh_pending = False
        self.pool = QThreadPool.globalInstance()
        self.github_user: GitHubUser | None = None
        self.github_storage_note = ""

        self._build_ui()
        self._build_menu()
        self._load_sidebar()
        self._update_github_button()

        last = self.settings.data.get("last_repository")
        if last and Path(last).exists() and GitService.is_repository(last):
            QTimer.singleShot(100, lambda: self.open_repository(last))
        else:
            self._show_empty_state()

    # ---------- UI construction ----------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(265)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 18, 16, 16)
        side_layout.setSpacing(10)

        brand = QLabel("RepoFlow")
        brand.setObjectName("title")
        subtitle = QLabel("Git, without the terminal")
        subtitle.setObjectName("muted")

        self.repo_list = QListWidget()
        self.repo_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repo_list.customContextMenuRequested.connect(self._repo_context_menu)
        self.repo_list.itemClicked.connect(self._sidebar_repo_clicked)

        add_button = QPushButton("+ Add Repository")
        add_button.clicked.connect(self._show_add_menu)
        self.github_account_button = QPushButton("Connect GitHub")
        self.github_account_button.clicked.connect(self.show_github_account)

        side_layout.addWidget(brand)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(8)
        side_layout.addWidget(QLabel("Repositories"))
        side_layout.addWidget(self.repo_list, 1)
        side_layout.addWidget(add_button)
        side_layout.addWidget(self.github_account_button)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 16, 18, 12)
        content_layout.setSpacing(12)

        self.header = QFrame()
        self.header.setObjectName("header")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        header_text = QVBoxLayout()
        self.repo_title = QLabel("No repository selected")
        self.repo_title.setObjectName("title")
        self.repo_meta = QLabel("Open a local repository or clone one from a URL.")
        self.repo_meta.setObjectName("muted")
        header_text.addWidget(self.repo_title)
        header_text.addWidget(self.repo_meta)

        self.branch_button = QPushButton("Branch")
        self.branch_button.clicked.connect(self._branch_menu)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all)
        self.fetch_button = QPushButton("Fetch")
        self.fetch_button.clicked.connect(self.fetch)
        self.pull_button = QPushButton("Pull")
        self.pull_button.clicked.connect(self.pull)
        self.push_button = QPushButton("Push")
        self.push_button.setObjectName("primary")
        self.push_button.clicked.connect(self.push)
        self.remote_button = QPushButton("Remote")
        self.remote_button.clicked.connect(self.connect_remote)
        self.remote_open_button = QPushButton("Open Remote")
        self.remote_open_button.clicked.connect(self.open_remote_in_browser)

        header_layout.addLayout(header_text, 1)
        for button in (
            self.branch_button,
            self.refresh_button,
            self.fetch_button,
            self.pull_button,
            self.push_button,
            self.remote_button,
            self.remote_open_button,
        ):
            header_layout.addWidget(button)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_changes_tab(), "Changes")
        self.tabs.addTab(self._build_history_tab(), "History")
        self.tabs.currentChanged.connect(self._tab_changed)

        content_layout.addWidget(self.header)
        content_layout.addWidget(self.tabs, 1)

        root.addWidget(sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready")

    def _build_changes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.sync_label = QLabel("Select a repository to view changes.")
        self.sync_label.setObjectName("muted")
        self.stage_legend = QLabel("Checkbox: ☐ unstaged   ☑ staged   ◩ partially staged")
        self.stage_legend.setObjectName("muted")

        splitter = QSplitter(Qt.Horizontal)
        self.change_tree = QTreeWidget()
        self.change_tree.setHeaderLabels(["Commit", "Status", "File"])
        self.change_tree.setColumnWidth(self.COL_CHECK, 70)
        self.change_tree.setColumnWidth(self.COL_STATUS, 190)
        self.change_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.change_tree.itemChanged.connect(self._file_check_changed)
        self.change_tree.currentItemChanged.connect(self._file_selected)

        self.diff_view = QPlainTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.diff_view.setPlaceholderText("Select a file to inspect its changes.")
        splitter.addWidget(self.change_tree)
        splitter.addWidget(self.diff_view)
        splitter.setSizes([470, 780])

        commit_panel = QFrame()
        commit_panel.setObjectName("commitPanel")
        commit_layout = QHBoxLayout(commit_panel)
        commit_layout.setContentsMargins(12, 10, 12, 10)
        self.commit_message = QPlainTextEdit()
        self.commit_message.setPlaceholderText("Commit message")
        self.commit_message.setFixedHeight(64)
        self.commit_button = QPushButton("Commit Staged")
        self.commit_button.setObjectName("primary")
        self.commit_button.clicked.connect(self.commit)
        self.commit_push_button = QPushButton("Commit & Push")
        self.commit_push_button.clicked.connect(lambda: self.commit(push_after=True))
        commit_layout.addWidget(self.commit_message, 1)
        commit_layout.addWidget(self.commit_button)
        commit_layout.addWidget(self.commit_push_button)

        layout.addWidget(self.sync_label)
        layout.addWidget(self.stage_legend)
        layout.addWidget(splitter, 1)
        layout.addWidget(commit_panel)
        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        return page

    def _build_menu(self) -> None:
        repo_menu = self.menuBar().addMenu("Repository")
        open_action = QAction("Open Local Repository…", self)
        open_action.triggered.connect(self.choose_repository)
        clone_action = QAction("Clone Repository…", self)
        clone_action.triggered.connect(self.clone_repository)
        init_action = QAction("Initialize Folder…", self)
        init_action.triggered.connect(self.initialize_repository)
        repo_menu.addAction(open_action)
        repo_menu.addAction(clone_action)
        repo_menu.addAction(init_action)
        repo_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        repo_menu.addAction(quit_action)

        github_menu = self.menuBar().addMenu("GitHub")
        account_action = QAction("Account…", self)
        account_action.triggered.connect(self.show_github_account)
        repos_action = QAction("My Repositories…", self)
        repos_action.triggered.connect(self.show_github_repositories)
        create_action = QAction("Create Repository on GitHub…", self)
        create_action.triggered.connect(self.create_github_repository)
        github_menu.addAction(account_action)
        github_menu.addSeparator()
        github_menu.addAction(repos_action)
        github_menu.addAction(create_action)

    # ---------- Repository list ----------
    def _load_sidebar(self) -> None:
        current = self.repo_path
        self.repo_list.clear()
        for path in self.settings.repositories:
            if not Path(path).exists():
                continue
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.repo_list.addItem(item)
            if current == path:
                self.repo_list.setCurrentItem(item)

    def _sidebar_repo_clicked(self, item: QListWidgetItem) -> None:
        self.open_repository(item.data(Qt.UserRole))

    def _repo_context_menu(self, pos) -> None:
        item = self.repo_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        remove = menu.addAction("Remove from RepoFlow")
        reveal = menu.addAction("Open Folder")
        chosen = menu.exec(self.repo_list.mapToGlobal(pos))
        path = item.data(Qt.UserRole)
        if chosen == remove:
            self.settings.remove_repository(path)
            self._load_sidebar()
        elif chosen == reveal:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _show_add_menu(self) -> None:
        menu = QMenu(self)
        open_action = menu.addAction("Open Local Repository")
        clone_action = menu.addAction("Clone Repository from URL")
        github_clone = menu.addAction("Clone from My GitHub")
        init_action = menu.addAction("Initialize Existing Folder")
        chosen = menu.exec(self.cursor().pos())
        if chosen == open_action:
            self.choose_repository()
        elif chosen == clone_action:
            self.clone_repository()
        elif chosen == github_clone:
            self.show_github_repositories()
        elif chosen == init_action:
            self.initialize_repository()

    # ---------- Open / clone / init ----------
    def choose_repository(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Local Repository", str(Path.home()))
        if not folder:
            return
        if GitService.is_repository(folder):
            self.open_repository(folder)
            return
        result = QMessageBox.question(self, "Not a Git repository", "This folder is not a Git repository. Initialize it now?")
        if result == QMessageBox.Yes:
            try:
                GitService.init_repository(folder)
                self.open_repository(folder)
            except GitError as exc:
                self._error(str(exc))

    def initialize_repository(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to Initialize", str(Path.home()))
        if not folder:
            return
        if GitService.is_repository(folder):
            self.open_repository(folder)
            return
        try:
            GitService.init_repository(folder)
            self.open_repository(folder)
            self.statusBar().showMessage("Repository initialized on branch main.", 5000)
        except GitError as exc:
            self._error(str(exc))

    def _github_auth(self) -> tuple[str | None, str | None]:
        return self.credentials.get_token(), self.settings.github_login

    def clone_repository(self) -> None:
        dialog = CloneDialog(self)
        if dialog.exec() != dialog.Accepted:
            return
        url, destination = dialog.values()
        if not url or not destination:
            self._error("Repository URL and destination are required.")
            return
        token, username = self._github_auth()
        self._run_background(
            lambda: GitService.clone_repository(url, destination, token=token, username=username),
            on_success=lambda path: self.open_repository(str(path)),
            busy="Cloning repository…",
        )

    def open_repository(self, path: str) -> None:
        path = str(Path(path).expanduser().resolve())
        if not GitService.is_repository(path):
            self._error("The selected folder is not a Git repository.")
            return
        try:
            service = GitService(path)
            root = service.root()
        except GitError as exc:
            self._error(str(exc))
            return
        self.repo_path = root
        self.git = GitService(root)
        self.settings.add_repository(root)
        self._load_sidebar()
        self.refresh_all()

    # ---------- GitHub account / API ----------
    def _update_github_button(self) -> None:
        token = self.credentials.get_token()
        login = self.settings.github_login
        if token and login:
            self.github_account_button.setText(f"GitHub  •  @{login}")
        elif token:
            self.github_account_button.setText("GitHub  •  Connected")
        else:
            self.github_account_button.setText("Connect GitHub")

    def connect_github(self) -> None:
        dialog = GitHubTokenDialog(self)
        if dialog.exec() != dialog.Accepted:
            return
        token, remember = dialog.values()
        if not token:
            self._error("Paste a GitHub Personal Access Token first.")
            return

        def validate() -> GitHubUser:
            return GitHubService(token).get_user()

        def connected(user: GitHubUser) -> None:
            result = self.credentials.set_token(token, remember=remember)
            self.github_storage_note = result.message
            self.github_user = user
            self.settings.set_github_identity(user.login, user.name)
            self._update_github_button()
            self.statusBar().showMessage(f"Connected to GitHub as @{user.login}. {result.message}", 8000)
            QMessageBox.information(self, "RepoFlow", f"GitHub connected as @{user.login}.\n\n{result.message}")

        self._run_background(validate, on_success=connected, busy="Connecting to GitHub…")

    def show_github_account(self) -> None:
        token = self.credentials.get_token()
        if not token:
            self.connect_github()
            return

        def task() -> GitHubUser:
            return GitHubService(token).get_user()

        def loaded(user: GitHubUser) -> None:
            self.github_user = user
            self.settings.set_github_identity(user.login, user.name)
            self._update_github_button()
            dialog = GitHubAccountDialog(user, self.github_storage_note, self)
            dialog.exec()
            if dialog.disconnect_requested:
                self.disconnect_github()

        self._run_background(task, on_success=loaded, busy="Loading GitHub account…")

    def disconnect_github(self) -> None:
        self.credentials.clear()
        self.github_user = None
        self.github_storage_note = ""
        self.settings.set_github_identity(None, None)
        self._update_github_button()
        self.statusBar().showMessage("GitHub account disconnected.", 5000)

    def _require_github_token(self) -> str | None:
        token = self.credentials.get_token()
        if token:
            return token
        QMessageBox.information(self, "GitHub", "Connect a GitHub account first.")
        self.connect_github()
        return None

    def show_github_repositories(self) -> None:
        token = self._require_github_token()
        if not token:
            return

        def task() -> list[GitHubRepository]:
            return GitHubService(token).list_repositories()

        self._run_background(task, on_success=self._open_github_repository_browser, busy="Loading GitHub repositories…")

    def _open_github_repository_browser(self, repositories: list[GitHubRepository]) -> None:
        dialog = GitHubRepositoriesDialog(repositories, self)
        if dialog.exec() != dialog.Accepted or not dialog.selected_repository:
            return
        repo = dialog.selected_repository
        if dialog.action == "open":
            QDesktopServices.openUrl(QUrl(repo.html_url))
            return
        if dialog.action == "clone":
            parent = QFileDialog.getExistingDirectory(self, "Choose Clone Location", str(Path.home()))
            if not parent:
                return
            destination = str(Path(parent) / repo.name)
            if Path(destination).exists():
                self._error(f"Destination already exists:\n{destination}")
                return
            token, username = self._github_auth()
            self._run_background(
                lambda: GitService.clone_repository(repo.clone_url, destination, token=token, username=username),
                on_success=lambda path: self.open_repository(str(path)),
                busy=f"Cloning {repo.full_name}…",
            )

    def create_github_repository(self) -> None:
        token = self._require_github_token()
        if not token:
            return
        suggested = self.git.repo_info().name if self.git else ""
        dialog = CreateGitHubRepositoryDialog(suggested, self)
        if dialog.exec() != dialog.Accepted:
            return
        name, description, private = dialog.values()
        if not name:
            self._error("Repository name is required.")
            return

        def task() -> GitHubRepository:
            return GitHubService(token).create_repository(name, description, private)

        self._run_background(task, on_success=self._github_repository_created, busy="Creating GitHub repository…")

    def _github_repository_created(self, repo: GitHubRepository) -> None:
        connected = False
        if self.git and not self.git.remote_url("origin"):
            answer = QMessageBox.question(
                self,
                "Repository Created",
                f"{repo.full_name} was created on GitHub.\n\nConnect the currently open local repository as 'origin'?",
            )
            if answer == QMessageBox.Yes:
                try:
                    self.git.add_remote(repo.clone_url, "origin")
                    connected = True
                    self.refresh_all()
                except GitError as exc:
                    self._error(str(exc))
                    return
        suffix = "\n\nThe current repository is now connected as origin." if connected else ""
        QMessageBox.information(self, "GitHub Repository Created", f"Created {repo.full_name}.\n{repo.html_url}{suffix}")
        self.statusBar().showMessage(f"Created {repo.full_name} on GitHub.", 6000)

    # ---------- Refresh ----------
    def refresh_all(self) -> None:
        if not self.git:
            self._show_empty_state()
            return
        try:
            info = self.git.repo_info()
            files = self.git.status()
            self.repo_title.setText(info.name)
            remote = info.remote_url or "Local only"
            upstream = info.upstream or "No upstream"
            self.repo_meta.setText(f"{info.root}   •   {info.branch}   •   {remote}")
            self.branch_button.setText(info.branch)
            self.remote_open_button.setEnabled(bool(info.remote_url))
            self.fetch_button.setEnabled(bool(info.remote_name))
            self.pull_button.setEnabled(bool(info.remote_name))
            self.push_button.setEnabled(bool(info.remote_name))
            self.remote_button.setText("Remote ✓" if info.remote_url else "Connect Remote")

            if info.ahead == 0 and info.behind == 0:
                sync = "Up to date" if info.upstream else "No upstream yet"
            else:
                sync = f"↑ {info.ahead} commit(s) to push   ↓ {info.behind} commit(s) to pull"
            self.sync_label.setText(f"{len(files)} changed file(s)   •   {sync}   •   {upstream}")
            self._populate_changes(files)
            if self.tabs.currentIndex() == 1:
                self._populate_history()
            self.statusBar().showMessage("Repository refreshed", 2500)
        except GitError as exc:
            self._error(str(exc))

    def _show_empty_state(self) -> None:
        self.repo_title.setText("No repository selected")
        self.repo_meta.setText("Open a local repository, clone one, or initialize a folder.")
        self.change_tree.clear()
        self.history_list.clear()
        self.diff_view.clear()
        self.sync_label.setText("No repository selected.")
        for button in (
            self.branch_button,
            self.refresh_button,
            self.fetch_button,
            self.pull_button,
            self.push_button,
            self.remote_button,
            self.remote_open_button,
        ):
            button.setEnabled(False)

    def _populate_changes(self, files: list[GitFile]) -> None:
        current_path = None
        selected = self.change_tree.currentItem()
        if selected:
            current_path = selected.data(self.COL_PATH, Qt.UserRole)

        # Rebuilding a QTreeWidget can emit itemChanged/currentItemChanged.
        # Block native Qt signals while rows are destroyed/recreated so a
        # staging callback can never observe a QTreeWidgetItem being deleted.
        self._loading_checks = True
        blocker = QSignalBlocker(self.change_tree)
        try:
            self.change_tree.clear()
            self.file_rows.clear()
            for entry in files:
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                if entry.partially_staged:
                    check_state = Qt.PartiallyChecked
                elif entry.fully_staged:
                    check_state = Qt.Checked
                else:
                    check_state = Qt.Unchecked
                item.setCheckState(self.COL_CHECK, check_state)

                status_text = entry.kind.value
                if entry.partially_staged:
                    status_text += " · Partially staged"
                elif entry.fully_staged:
                    status_text += " · Staged"
                item.setText(self.COL_STATUS, status_text)
                item.setText(self.COL_PATH, entry.path)
                item.setData(self.COL_PATH, Qt.UserRole, entry.path)

                tooltip = (
                    f"Index: {entry.index_status or ' '} | Working tree: {entry.worktree_status or ' '}"
                    f" | {entry.stage_label}"
                )
                if entry.partially_staged:
                    tooltip += " | Only staged changes will be included in the next commit."
                if entry.original_path:
                    tooltip += f" | From: {entry.original_path}"
                for column in (self.COL_CHECK, self.COL_STATUS, self.COL_PATH):
                    item.setToolTip(column, tooltip)

                self.change_tree.addTopLevelItem(item)
                self.file_rows[entry.path] = item
                if current_path == entry.path:
                    self.change_tree.setCurrentItem(item)
        finally:
            del blocker
            self._loading_checks = False

        if current_path and current_path in self.file_rows:
            # Selection signals were blocked above; update the diff explicitly.
            current = self.file_rows[current_path]
            self._file_selected(current, None)
        elif not files:
            self.diff_view.setPlainText("Working tree clean. Nothing to commit.")
        elif not current_path:
            self.diff_view.clear()

    # ---------- Staging / diff / commit ----------
    def _schedule_change_refresh(self) -> None:
        # Never clear/rebuild QTreeWidget from inside its itemChanged signal.
        # Defer it until the current Qt signal has fully returned.
        if self._change_refresh_pending:
            return
        self._change_refresh_pending = True
        QTimer.singleShot(0, self._finish_change_refresh)

    def _finish_change_refresh(self) -> None:
        self._change_refresh_pending = False
        self.refresh_all()

    def _file_check_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading_checks or column != self.COL_CHECK or not self.git:
            return
        path = item.data(self.COL_PATH, Qt.UserRole)
        if not path:
            return

        state = item.checkState(self.COL_CHECK)
        logger.info("Staging checkbox changed path=%r state=%s", path, state)
        try:
            # From a partially staged row, checking means "stage the complete
            # current file" while unchecking means "unstage the complete file".
            # The partial state itself is display-only and is recalculated from Git.
            if state == Qt.Checked:
                self.git.stage([path])
                self.statusBar().showMessage(f"Staged all current changes in {path}", 2200)
            elif state == Qt.Unchecked:
                self.git.unstage([path])
                self.statusBar().showMessage(f"Unstaged {path}", 2200)
            else:
                # Qt should normally move a user click away from PartiallyChecked.
                # If a platform/theme leaves it partial, simply restore Git's truth.
                self.statusBar().showMessage(f"{path} is partially staged", 1800)
        except GitError as exc:
            logger.exception("Stage/unstage failed for %r", path)
            self._error(str(exc))
        finally:
            self._schedule_change_refresh()

    def _status_entry_for_path(self, path: str) -> GitFile | None:
        if not self.git:
            return None
        return next((entry for entry in self.git.status() if entry.path == path), None)

    @staticmethod
    def _diff_section(title: str, body: str, note: str = "") -> str:
        rule = "─" * 72
        header = f"{title}\n{rule}"
        if note:
            header += f"\n{note}"
        return f"{header}\n\n{body.strip()}"

    def _file_selected(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        if not current or not self.git:
            return
        path = current.data(self.COL_PATH, Qt.UserRole)
        try:
            entry = self._status_entry_for_path(path)
            if not entry:
                self.diff_view.setPlainText("This file no longer has pending changes.")
                return

            if entry.partially_staged:
                staged = self.git.staged_diff(path)
                unstaged = self.git.diff(path)
                content = (
                    "PARTIALLY STAGED\n"
                    "Only the STAGED CHANGES section will be included in the next commit.\n"
                    "The UNSTAGED CHANGES section remains in your working tree.\n\n"
                    + self._diff_section("STAGED CHANGES", staged)
                    + "\n\n"
                    + self._diff_section("UNSTAGED CHANGES", unstaged)
                )
            elif entry.fully_staged:
                content = self._diff_section(
                    "STAGED CHANGES",
                    self.git.staged_diff(path),
                    "These changes will be included in the next commit.",
                )
            else:
                content = self._diff_section(
                    "UNSTAGED CHANGES",
                    self.git.diff(path),
                    "These changes are not yet included in the next commit.",
                )
            self.diff_view.setPlainText(content)
        except GitError as exc:
            self.diff_view.setPlainText(str(exc))

    def commit(self, push_after: bool = False) -> None:
        if not self.git:
            return
        message = self.commit_message.toPlainText().strip()
        if not message:
            self._error("Write a commit message first.")
            return
        try:
            staged = [f for f in self.git.status() if f.staged]
            if not staged:
                self._error("No files are staged. Tick at least one checkbox first.")
                return
            output = self.git.commit(message)
            self.commit_message.clear()
            self.refresh_all()
            self.statusBar().showMessage(output.splitlines()[0] if output else "Commit created.", 5000)
            if push_after:
                self.push()
        except GitError as exc:
            self._error(str(exc))

    # ---------- Remote operations ----------
    def connect_remote(self) -> None:
        if not self.git:
            return
        current = self.git.remote_url("origin") or ""
        dialog = RemoteDialog(current, self)
        if dialog.exec() != dialog.Accepted:
            return
        name, url = dialog.values()
        if not url:
            self._error("Repository URL is required.")
            return
        try:
            self.git.add_remote(url, name)
            self.refresh_all()
            self.statusBar().showMessage(f"Remote '{name}' connected.", 5000)
        except GitError as exc:
            self._error(str(exc))

    def fetch(self) -> None:
        if not self.git:
            return
        token, username = self._github_auth()
        self._run_background(
            lambda: self.git.fetch(token=token, username=username),
            on_success=lambda msg: self._network_done(str(msg)),
            busy="Fetching remote changes…",
        )

    def pull(self) -> None:
        if not self.git:
            return
        token, username = self._github_auth()

        def task() -> str:
            self.git.fetch(token=token, username=username)
            return self.git.pull_ff_only(token=token, username=username)

        self._run_background(task, on_success=lambda msg: self._network_done(str(msg)), busy="Pulling changes…")

    def push(self) -> None:
        if not self.git:
            return
        info = self.git.repo_info()
        if not info.remote_name:
            self.connect_remote()
            return
        if info.ahead <= 0 and info.upstream:
            answer = QMessageBox.question(self, "Push", "No local commits are ahead of the remote. Run push anyway?")
            if answer != QMessageBox.Yes:
                return
        token, username = self._github_auth()
        self._run_background(
            lambda: self.git.push(token=token, username=username),
            on_success=lambda msg: self._network_done(str(msg)),
            busy="Pushing commits…",
        )

    def _network_done(self, message: str) -> None:
        self.refresh_all()
        first_line = message.splitlines()[0] if message else "Done"
        self.statusBar().showMessage(first_line, 6000)

    def open_remote_in_browser(self) -> None:
        if not self.git:
            return
        url = self.git.remote_url("origin")
        if not url:
            self._error("No origin remote is configured.")
            return
        QDesktopServices.openUrl(QUrl(self._remote_to_web_url(url)))

    @staticmethod
    def _remote_to_web_url(url: str) -> str:
        value = url.strip()
        if value.startswith("git@github.com:"):
            value = "https://github.com/" + value[len("git@github.com:"):]
        elif value.startswith("ssh://git@github.com/"):
            value = "https://github.com/" + value[len("ssh://git@github.com/"):]
        if value.endswith(".git"):
            value = value[:-4]
        return value

    # ---------- Branches / history ----------
    def _branch_menu(self) -> None:
        if not self.git:
            return
        try:
            info = self.git.repo_info()
            branches = self.git.local_branches()
        except GitError as exc:
            self._error(str(exc))
            return
        menu = QMenu(self)
        for branch in branches:
            action = menu.addAction(("✓ " if branch == info.branch else "") + branch)
            action.setData(branch)
        menu.addSeparator()
        new_action = menu.addAction("+ New Branch")
        chosen = menu.exec(self.branch_button.mapToGlobal(self.branch_button.rect().bottomLeft()))
        if not chosen:
            return
        if chosen == new_action:
            dialog = BranchDialog(self)
            if dialog.exec() == dialog.Accepted and dialog.name():
                try:
                    self.git.create_branch(dialog.name(), switch=True)
                    self.refresh_all()
                except GitError as exc:
                    self._error(str(exc))
        else:
            branch = chosen.data()
            if branch and branch != info.branch:
                try:
                    self.git.switch_branch(branch)
                    self.refresh_all()
                except GitError as exc:
                    self._error(str(exc))

    def _populate_history(self) -> None:
        if not self.git:
            return
        self.history_list.clear()
        for commit in self.git.history(120):
            item = QListWidgetItem(f"{commit.short_sha}   {commit.subject}\n{commit.author} • {commit.relative_date}")
            item.setToolTip(commit.sha)
            self.history_list.addItem(item)
        if self.history_list.count() == 0:
            self.history_list.addItem("No commits yet.")

    def _tab_changed(self, index: int) -> None:
        if index == 1:
            self._populate_history()

    # ---------- Background work ----------
    def _run_background(self, fn, *, on_success, busy: str) -> None:
        self._set_busy(True, busy)
        worker = FunctionWorker(fn)
        worker.signals.success.connect(on_success)
        worker.signals.error.connect(self._error)
        worker.signals.finished.connect(lambda: self._set_busy(False, "Ready"))
        self.pool.start(worker)

    def _set_busy(self, busy: bool, message: str) -> None:
        self.statusBar().showMessage(message)
        for button in (self.refresh_button, self.fetch_button, self.pull_button, self.push_button):
            button.setEnabled(not busy and self.git is not None)

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, "RepoFlow", message)
        self.statusBar().showMessage(message, 7000)
