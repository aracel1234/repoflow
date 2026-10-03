from __future__ import annotations

from pathlib import Path
import logging

from PySide6.QtCore import Qt, QSignalBlocker, QThreadPool, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from repoflow.core.models import FileKind, GitFile, GitHubRepository, GitHubUser
from repoflow.core.safety import SafetyScanner
from repoflow.core.settings import AppSettings
from repoflow.core.workers import FunctionWorker
from repoflow.services.credential_service import CredentialService
from repoflow.services.git_service import GitError, GitService
from repoflow.services.github_service import GitHubError, GitHubService
logger = logging.getLogger(__name__)


from repoflow.ui.dialogs import (
    BranchDialog,
    BranchManagerDialog,
    CloneDialog,
    ConflictReviewDialog,
    CreateGitHubRepositoryDialog,
    GitHubAccountDialog,
    GitHubRepositoriesDialog,
    GitHubTokenDialog,
    GitIgnoreDialog,
    HunkStageDialog,
    RemoteBranchesDialog,
    RemoteDialog,
    RepositorySafetyDialog,
    SafetyWarningDialog,
    StashManagerDialog,
    SyncDetailsDialog,
    TagManagerDialog,
)


class MainWindow(QMainWindow):
    COL_CHECK = 0
    COL_STATUS = 1
    COL_PATH = 2

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RepoFlow")
        self.resize(1380, 840)
        self.setMinimumSize(1060, 660)

        self.settings = AppSettings()
        self.credentials = CredentialService()
        self.git: GitService | None = None
        self.repo_path: str | None = None
        self.file_rows: dict[str, QTreeWidgetItem] = {}
        self._loading_checks = False
        self._change_refresh_pending = False
        self.pool = QThreadPool.globalInstance()
        # Keep Python-side worker wrappers alive until their Qt work finishes.
        # Without this, queued success/error signals may be lost on some PySide6 runtimes.
        self._active_workers: list[FunctionWorker] = []
        self.github_user: GitHubUser | None = None
        self.github_storage_note = ""
        self._safety_acknowledged_paths: set[str] = set()
        self._current_conflicts: list[GitFile] = []
        self._current_diverged = False
        self._current_operation: str | None = None
        self._can_fetch = False
        self._can_pull = False
        self._can_push = False
        self._is_busy = False
        self._hunk_available = False

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
        sidebar.setFixedWidth(282)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 18, 16, 16)
        side_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_icon = QLabel()
        brand_icon.setObjectName("brandIcon")
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "repoflow.svg"
        if icon_path.exists():
            brand_icon.setPixmap(QIcon(str(icon_path)).pixmap(40, 40))
        brand_icon.setFixedSize(42, 42)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand = QLabel("RepoFlow")
        brand.setObjectName("title")
        subtitle = QLabel("Git, without the terminal")
        subtitle.setObjectName("muted")
        brand_text.addWidget(brand)
        brand_text.addWidget(subtitle)
        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)

        self.repo_list = QListWidget()
        self.repo_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.repo_list.customContextMenuRequested.connect(self._repo_context_menu)
        self.repo_list.itemClicked.connect(self._sidebar_repo_clicked)

        add_button = QPushButton("+ Add Repository")
        add_button.clicked.connect(self._show_add_menu)
        self.github_account_button = QPushButton("Connect GitHub")
        self.github_account_button.clicked.connect(self.show_github_account)

        side_layout.addLayout(brand_row)
        side_layout.addSpacing(8)
        side_layout.addWidget(QLabel("Repositories"))
        side_layout.addWidget(self.repo_list, 1)
        side_layout.addWidget(add_button)
        side_layout.addWidget(self.github_account_button)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 18, 20, 14)
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
        self.activity_progress = QProgressBar()
        self.activity_progress.setObjectName("activityProgress")
        self.activity_progress.setRange(0, 0)
        self.activity_progress.setTextVisible(False)
        self.activity_progress.setFixedWidth(120)
        self.activity_progress.setFixedHeight(10)
        self.activity_progress.hide()
        self.statusBar().addPermanentWidget(self.activity_progress)
        self.statusBar().showMessage("Ready")

    def _build_changes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.sync_label = QLabel("Select a repository to view changes.")
        self.sync_label.setObjectName("syncBadge")

        safety_row = QHBoxLayout()
        safety_row.setContentsMargins(0, 0, 0, 0)
        self.safety_notice = QLabel("")
        self.safety_notice.setObjectName("safetyBanner")
        self.safety_notice.setWordWrap(True)
        self.safety_notice.hide()
        self.safety_button = QPushButton("Review Safety")
        self.safety_button.setObjectName("warningAction")
        self.safety_button.clicked.connect(self._show_repository_safety)
        self.safety_button.hide()
        safety_row.addWidget(self.safety_notice, 1)
        safety_row.addWidget(self.safety_button)

        self.stage_legend = QLabel("Checkbox: ☐ unstaged   ☑ staged   ◩ partially staged")
        self.stage_legend.setObjectName("muted")
        stage_tools = QHBoxLayout()
        stage_tools.setContentsMargins(0, 0, 0, 0)
        stage_tools.addWidget(self.stage_legend)
        stage_tools.addStretch(1)
        self.hunk_button = QPushButton("Stage Selected Hunks…")
        self.hunk_button.setToolTip("Stage only selected text hunks from the currently selected tracked file.")
        self.hunk_button.setEnabled(False)
        self.hunk_button.clicked.connect(self.stage_selected_hunks)
        stage_tools.addWidget(self.hunk_button)

        splitter = QSplitter(Qt.Horizontal)
        self.change_tree = QTreeWidget()
        self.change_tree.setHeaderLabels(["Stage", "Status", "File"])
        self.change_tree.setColumnWidth(self.COL_CHECK, 70)
        self.change_tree.setColumnWidth(self.COL_STATUS, 190)
        self.change_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.change_tree.itemChanged.connect(self._file_check_changed)
        self.change_tree.currentItemChanged.connect(self._file_selected)

        self.diff_view = QPlainTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.diff_view.setObjectName("diffView")
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
        self.commit_push_button = QPushButton("Commit and Push")
        self.commit_push_button.clicked.connect(lambda: self.commit(push_after=True))
        commit_layout.addWidget(self.commit_message, 1)
        commit_layout.addWidget(self.commit_button)
        commit_layout.addWidget(self.commit_push_button)

        layout.addWidget(self.sync_label)
        layout.addLayout(safety_row)
        layout.addLayout(stage_tools)
        layout.addWidget(splitter, 1)
        layout.addWidget(commit_panel)
        return page

    def _build_history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        self.sync_details_button = QPushButton("Sync Details…")
        self.sync_details_button.clicked.connect(self.show_sync_details)
        self.remote_branches_button = QPushButton("Remote Branches…")
        self.remote_branches_button.clicked.connect(self.manage_remote_branches)
        self.tags_button = QPushButton("Tags…")
        self.tags_button.clicked.connect(self.manage_tags)
        self.history_all_branches = QCheckBox("All local branches")
        self.history_all_branches.setToolTip("Include commits reachable from every local branch. Useful when selecting a commit to cherry-pick.")
        self.history_all_branches.toggled.connect(lambda _checked: self._populate_history())
        toolbar.addWidget(self.sync_details_button)
        toolbar.addWidget(self.remote_branches_button)
        toolbar.addWidget(self.tags_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.history_all_branches)

        splitter = QSplitter(Qt.Horizontal)
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._history_selected)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(8)
        self.history_title = QLabel("Select a commit to inspect it.")
        self.history_title.setObjectName("title")
        self.history_meta = QLabel("")
        self.history_meta.setObjectName("muted")
        self.history_meta.setWordWrap(True)
        self.history_detail = QPlainTextEdit()
        self.history_detail.setReadOnly(True)
        self.history_detail.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.history_detail.setObjectName("diffView")

        history_actions = QHBoxLayout()
        self.copy_hash_button = QPushButton("Copy Hash")
        self.copy_hash_button.clicked.connect(self.copy_selected_commit_hash)
        self.open_commit_button = QPushButton("Open on GitHub")
        self.open_commit_button.clicked.connect(self.open_selected_commit_on_github)
        self.revert_button = QPushButton("Revert Commit…")
        self.revert_button.clicked.connect(self.revert_selected_commit)
        self.cherry_pick_button = QPushButton("Cherry-pick Commit…")
        self.cherry_pick_button.clicked.connect(self.cherry_pick_selected_commit)
        for button in (self.copy_hash_button, self.open_commit_button, self.revert_button, self.cherry_pick_button):
            button.setEnabled(False)
            history_actions.addWidget(button)
        history_actions.addStretch(1)

        detail_layout.addWidget(self.history_title)
        detail_layout.addWidget(self.history_meta)
        detail_layout.addWidget(self.history_detail, 1)
        detail_layout.addLayout(history_actions)
        splitter.addWidget(self.history_list)
        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addLayout(toolbar)
        layout.addWidget(splitter, 1)
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
        gitignore_action = QAction("Manage .gitignore…", self)
        gitignore_action.triggered.connect(self.manage_gitignore)
        stash_action = QAction("Stashes…", self)
        stash_action.triggered.connect(self.manage_stashes)
        branch_manager_action = QAction("Manage Branches…", self)
        branch_manager_action.triggered.connect(self.manage_branches)
        remote_branches_action = QAction("Remote Branches…", self)
        remote_branches_action.triggered.connect(self.manage_remote_branches)
        tags_action = QAction("Tags…", self)
        tags_action.triggered.connect(self.manage_tags)
        sync_details_action = QAction("Sync Details…", self)
        sync_details_action.triggered.connect(self.show_sync_details)
        self.abort_operation_action = QAction("Abort Current Git Operation…", self)
        self.abort_operation_action.triggered.connect(self.abort_current_operation)
        self.abort_operation_action.setEnabled(False)
        repo_menu.addAction(gitignore_action)
        repo_menu.addAction(stash_action)
        repo_menu.addAction(branch_manager_action)
        repo_menu.addAction(remote_branches_action)
        repo_menu.addAction(tags_action)
        repo_menu.addAction(sync_details_action)
        repo_menu.addSeparator()
        repo_menu.addAction(self.abort_operation_action)
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
        if dialog.exec() != QDialog.DialogCode.Accepted:
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
        self._safety_acknowledged_paths.clear()
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
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        token, remember = dialog.values()
        if not token:
            self._error("Paste a GitHub Personal Access Token first.")
            return

        logger.info("GitHub authentication requested remember=%s", remember)

        def validate() -> GitHubUser:
            return GitHubService(token).get_user()

        def connected(user: GitHubUser) -> None:
            result = self.credentials.set_token(token, remember=remember)
            self.github_storage_note = result.message
            self.github_user = user
            self.settings.set_github_identity(user.login, user.name)
            self._update_github_button()
            logger.info("GitHub authentication succeeded login=%r", user.login)
            self.statusBar().showMessage(f"Connected to GitHub as @{user.login}. {result.message}", 8000)
            QMessageBox.information(self, "RepoFlow", f"GitHub connected as @{user.login}.\n\n{result.message}")

        def auth_failed(message: str) -> None:
            logger.warning("GitHub authentication failed: %s", message)
            QMessageBox.warning(
                self,
                "GitHub Authentication Failed",
                f"Could not connect this GitHub account.\n\n{message}",
            )
            self.statusBar().showMessage(f"GitHub authentication failed: {message}", 8000)
            self._update_github_button()

        self._run_background(
            validate,
            on_success=connected,
            on_error=auth_failed,
            busy="Connecting to GitHub…",
        )

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
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.selected_repository:
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
        if dialog.exec() != QDialog.DialogCode.Accepted:
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

    # ---------- Safety / ignore rules ----------
    def manage_gitignore(self) -> None:
        if not self.git:
            self._error("Open a repository before editing .gitignore.")
            return
        try:
            dialog = GitIgnoreDialog(self.git.read_gitignore(), self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.git.write_gitignore(dialog.text())
            self.refresh_all()
            self.statusBar().showMessage(".gitignore saved.", 4000)
        except GitError as exc:
            self._error(str(exc))

    def manage_stashes(self) -> None:
        if not self.git:
            self._error("Open a repository before managing stashes.")
            return
        if self._current_conflicts or self._current_operation:
            self._error("Resolve or abort the current Git operation before creating or applying stashes.")
            return
        try:
            dialog = StashManagerDialog(self.git.stash_list(), self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            if dialog.action == "create":
                message = self.git.stash_create(
                    dialog.message(),
                    include_untracked=dialog.include_untracked(),
                )
                self.refresh_all()
                self.statusBar().showMessage(message.splitlines()[0] if message else "Working changes stashed.", 5500)
                return
            ref = dialog.selected_ref()
            if not ref:
                return
            if dialog.action == "apply":
                if self.git.status():
                    answer = QMessageBox.question(
                        self,
                        "Apply Stash",
                        "This repository already has local changes. Applying a stash on top of them can create conflicts. Continue?",
                    )
                    if answer != QMessageBox.Yes:
                        return
                try:
                    message = self.git.stash_apply(ref)
                except GitError:
                    self.refresh_all()
                    raise
                self.refresh_all()
                self.statusBar().showMessage(message.splitlines()[0] if message else f"Applied {ref}.", 5500)
                return
            if dialog.action == "drop":
                answer = QMessageBox.warning(
                    self,
                    "Drop Stash",
                    f"Permanently remove {ref}? This cannot be undone by RepoFlow.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                message = self.git.stash_drop(ref)
                self.statusBar().showMessage(message.splitlines()[0] if message else f"Dropped {ref}.", 5500)
        except GitError as exc:
            self._error(str(exc))

    def manage_branches(self) -> None:
        if not self.git:
            self._error("Open a repository before managing branches.")
            return
        if self._current_conflicts or self._current_operation:
            self._error("Resolve or abort the current Git operation before renaming or deleting branches.")
            return
        try:
            current = self.git.branch()
            dialog = BranchManagerDialog(self.git.local_branches(), current, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            branch = dialog.selected_branch()
            if not branch:
                return
            if dialog.action == "rename":
                new_name, ok = QInputDialog.getText(
                    self,
                    "Rename Branch",
                    f"New name for '{branch}':",
                    text=branch,
                )
                if not ok or not new_name.strip() or new_name.strip() == branch:
                    return
                self.git.rename_branch(branch, new_name.strip())
                self.refresh_all()
                self.statusBar().showMessage(f"Renamed branch '{branch}' to '{new_name.strip()}'.", 5000)
                return
            if dialog.action == "delete":
                if branch == current:
                    self._error("The active branch cannot be deleted. Switch to another branch first.")
                    return
                answer = QMessageBox.question(
                    self,
                    "Delete Local Branch",
                    f"Delete local branch '{branch}'? RepoFlow uses Git's safe delete mode and will refuse if the branch is not fully merged.",
                )
                if answer != QMessageBox.Yes:
                    return
                self.git.delete_branch(branch)
                self.refresh_all()
                self.statusBar().showMessage(f"Deleted local branch '{branch}'.", 5000)
        except GitError as exc:
            self._error(str(exc))

    def manage_remote_branches(self) -> None:
        if not self.git:
            self._error("Open a repository before browsing remote branches.")
            return
        if self._current_conflicts or self._current_operation:
            self._error("Resolve or abort the current Git operation before creating a tracking branch.")
            return
        try:
            if self.git.status():
                self._error("Create a tracking branch only from a clean working tree. Commit or stash local changes first.")
                return
            branches = self.git.remote_branches()
            if not branches:
                self._error("No remote branches are known locally. Connect a remote and run Fetch first.")
                return
            dialog = RemoteBranchesDialog(branches, self)
            if dialog.exec() != QDialog.DialogCode.Accepted or dialog.action != "track":
                return
            remote_branch = dialog.selected_branch()
            local_name = dialog.local_branch_name()
            if not remote_branch:
                return
            self.git.create_tracking_branch(remote_branch, local_name)
            self.refresh_all()
            self.statusBar().showMessage(
                f"Created local branch '{local_name}' tracking '{remote_branch}'.", 6000
            )
        except GitError as exc:
            self._error(str(exc))

    def manage_tags(self) -> None:
        if not self.git:
            self._error("Open a repository before managing tags.")
            return
        try:
            dialog = TagManagerDialog(self.git.tags(), self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            if dialog.action == "create":
                name, message = dialog.new_tag()
                self.git.create_annotated_tag(name, message)
                self.statusBar().showMessage(f"Created local tag '{name}'.", 5000)
                return
            tag = dialog.selected_tag()
            if not tag:
                return
            if dialog.action == "delete":
                answer = QMessageBox.warning(
                    self,
                    "Delete Local Tag",
                    f"Delete local tag '{tag}'? RepoFlow will not delete any remote tag.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return
                self.git.delete_tag(tag)
                self.statusBar().showMessage(f"Deleted local tag '{tag}'.", 5000)
                return
            if dialog.action == "push":
                answer = QMessageBox.question(
                    self,
                    "Push Tag",
                    f"Push tag '{tag}' to the configured remote? This publishes the tag explicitly.",
                )
                if answer != QMessageBox.Yes:
                    return
                token, username = self._github_auth()
                self._run_background(
                    lambda: self.git.push_tag(tag, token=token, username=username),
                    on_success=lambda msg: self._network_done(str(msg), "Tag Push"),
                    busy=f"Pushing tag {tag}…",
                )
        except GitError as exc:
            self._error(str(exc))

    def show_sync_details(self) -> None:
        if not self.git:
            self._error("Open a repository before viewing sync details.")
            return
        try:
            info = self.git.repo_info()
            if not info.upstream:
                self._error("This branch does not have an upstream yet.")
                return
            local_only, remote_only = self.git.sync_commit_lists(100)
            SyncDetailsDialog(info.upstream, local_only, remote_only, self).exec()
        except GitError as exc:
            self._error(str(exc))

    def abort_current_operation(self) -> None:
        if not self.git:
            return
        try:
            state = self.git.operation_state()
            if not state:
                self._error("There is no merge, cherry-pick, or revert operation to abort.")
                return
            answer = QMessageBox.warning(
                self,
                "Abort Git Operation",
                f"Abort the current {state} operation and return to the pre-operation state?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            message = self.git.abort_current_operation()
            self.refresh_all()
            self.statusBar().showMessage(message, 6000)
        except GitError as exc:
            self._error(str(exc))

    def _show_repository_safety(self) -> None:
        if not self.git:
            return
        try:
            info = self.git.repo_info()
        except GitError as exc:
            self._error(str(exc))
            return

        if self._current_conflicts:
            paths = "\n".join(f"• {entry.path}" for entry in self._current_conflicts[:12])
            if len(self._current_conflicts) > 12:
                paths += f"\n• …and {len(self._current_conflicts) - 12} more"
            body = (
                "RepoFlow detected unresolved merge conflicts. Pull and Push are disabled while the index is conflicted.\n\n"
                f"Conflicted files:\n{paths}\n\n"
                "Edit each file to resolve the conflict markers, then stage the resolved file with its checkbox. "
                "When no Conflict rows remain, create the appropriate commit and refresh."
            )
            ConflictReviewDialog(info.root, [entry.path for entry in self._current_conflicts], self).exec()
            return

        if self._current_operation:
            body = (
                f"A {self._current_operation} operation is currently in progress.\n\n"
                "Resolve and stage any conflicted files, then create the appropriate commit to finish the operation, "
                "or choose Repository → Abort Current Git Operation… to return to the pre-operation state. "
                "RepoFlow blocks branch switching and remote sync while this state is active."
            )
            RepositorySafetyDialog(
                "Git Operation in Progress",
                f"Current operation: {self._current_operation}",
                body,
                self,
            ).exec()
            return

        if self._current_diverged:
            body = (
                f"The current branch is {info.ahead} commit(s) ahead and {info.behind} commit(s) behind its upstream.\n\n"
                "RepoFlow deliberately does not choose a merge, rebase, reset, or force-push strategy for you. "
                "Pull and Push remain disabled until the histories are reconciled with the strategy you choose. "
                "After resolving the divergence in a Git tool that supports that workflow, return here and press Refresh."
            )
            RepositorySafetyDialog("Diverged History", "Local and remote histories diverged", body, self).exec()
            return

        RepositorySafetyDialog(
            "Repository Safety",
            "No blocking repository state detected",
            "There are currently no unresolved conflicts or diverged upstream histories blocking RepoFlow sync operations.",
            self,
        ).exec()

    # ---------- Refresh ----------
    def refresh_all(self) -> None:
        if not self.git:
            self._show_empty_state()
            return
        try:
            info = self.git.repo_info()
            files = self.git.status()
            conflicts = [entry for entry in files if entry.conflicted]
            diverged = bool(info.upstream and info.ahead > 0 and info.behind > 0)
            operation = self.git.operation_state()
            self._current_conflicts = conflicts
            self._current_diverged = diverged
            self._current_operation = operation

            self.repo_title.setText(info.name)
            remote = info.remote_url or "Local only"
            upstream = info.upstream or "No upstream"
            self.repo_meta.setText(f"{info.root}   •   {info.branch}   •   {remote}")
            self.branch_button.setText(info.branch)
            self.remote_open_button.setEnabled(bool(info.remote_url) and not self._is_busy)
            self.remote_button.setText("Remote ✓" if info.remote_url else "Connect Remote")

            self._can_fetch = bool(info.remote_name)
            self._can_pull = bool(info.remote_name) and not conflicts and not diverged and not operation
            self._can_push = bool(info.remote_name) and not conflicts and not diverged and not operation
            self._apply_operation_button_state()

            if diverged:
                sync = f"Diverged • ↑ {info.ahead} local   ↓ {info.behind} remote"
            elif info.ahead == 0 and info.behind == 0:
                sync = "Up to date" if info.upstream else "No upstream yet"
            else:
                sync = f"↑ {info.ahead} commit(s) to push   ↓ {info.behind} commit(s) to pull"
            self.sync_label.setText(f"{len(files)} changed file(s)   •   {sync}   •   {upstream}")

            if conflicts:
                operation_note = f" Current operation: {operation}." if operation else ""
                self.safety_notice.setText(
                    f"⚠ {len(conflicts)} unresolved conflict(s). Resolve and stage them before syncing.{operation_note}"
                )
                self.safety_button.setText("Review Conflicts")
                self.safety_notice.show()
                self.safety_button.show()
            elif operation:
                self.safety_notice.setText(
                    f"⚠ A {operation} operation is in progress. Complete it before starting another history operation."
                )
                self.safety_button.setText("Review Safety")
                self.safety_notice.show()
                self.safety_button.show()
            elif diverged:
                self.safety_notice.setText(
                    f"⚠ Local and remote histories diverged (↑ {info.ahead} / ↓ {info.behind}). "
                    "RepoFlow blocks Pull and Push until you choose how to reconcile them."
                )
                self.safety_button.setText("Review Divergence")
                self.safety_notice.show()
                self.safety_button.show()
            else:
                self.safety_notice.hide()
                self.safety_button.hide()

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
        self.safety_notice.hide()
        self.safety_button.hide()
        self._current_conflicts = []
        self._current_diverged = False
        self._current_operation = None
        self._can_fetch = self._can_pull = self._can_push = False
        self._hunk_available = False
        self.hunk_button.setEnabled(False)
        for button in (
            self.branch_button,
            self.refresh_button,
            self.fetch_button,
            self.pull_button,
            self.push_button,
            self.remote_button,
            self.remote_open_button,
            self.commit_button,
            self.commit_push_button,
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
                safety_issues = (
                    []
                    if entry.kind == FileKind.DELETED or not self.repo_path
                    else SafetyScanner.inspect_path(self.repo_path, entry.path)
                )
                if safety_issues:
                    status_text += " · ⚠ Review"
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
                if safety_issues:
                    categories = ", ".join(sorted({issue.title for issue in safety_issues}))
                    tooltip += f" | Safety review: {categories}"
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
            self._hunk_available = False
            self.hunk_button.setEnabled(False)
            self.diff_view.setPlainText("Working tree clean. Nothing to commit.")
        else:
            self._hunk_available = False
            self.hunk_button.setEnabled(False)
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
            entry = self._status_entry_for_path(path)
            # From a partially staged row, checking means "stage the complete
            # current file" while unchecking means "unstage the complete file".
            if state == Qt.Checked:
                if entry and entry.kind != FileKind.DELETED and path not in self._safety_acknowledged_paths:
                    issues = self.git.safety_issues([path])
                    if issues:
                        dialog = SafetyWarningDialog(
                            issues,
                            context="stage",
                            allow_ignore=entry.untracked,
                            parent=self,
                        )
                        if dialog.exec() != QDialog.DialogCode.Accepted:
                            self.statusBar().showMessage(f"Staging cancelled for {path}", 3000)
                            return
                        if dialog.action == "ignore":
                            pattern = SafetyScanner.exact_gitignore_pattern(path)
                            self.git.append_gitignore_patterns([pattern])
                            self.statusBar().showMessage(
                                f"Added {pattern} to .gitignore instead of staging {path}.", 5000
                            )
                            return
                        if dialog.action != "continue":
                            return
                        self._safety_acknowledged_paths.add(path)

                self.git.stage([path])
                self.statusBar().showMessage(f"Staged all current changes in {path}", 2200)
            elif state == Qt.Unchecked:
                self.git.unstage([path])
                self._safety_acknowledged_paths.discard(path)
                self.statusBar().showMessage(f"Unstaged {path}", 2200)
            else:
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
                self._hunk_available = False
                self.hunk_button.setEnabled(False)
                self.diff_view.setPlainText("This file no longer has pending changes.")
                return

            self._hunk_available = bool(self.git.unstaged_hunks(path))
            self.hunk_button.setEnabled(self._hunk_available and not self._is_busy)

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

    def stage_selected_hunks(self) -> None:
        if not self.git:
            return
        item = self.change_tree.currentItem()
        path = item.data(self.COL_PATH, Qt.UserRole) if item else None
        if not path:
            return
        try:
            entry = self._status_entry_for_path(path)
            if not entry:
                self._error("The selected file no longer has pending changes.")
                return
            hunks = self.git.unstaged_hunks(path)
            if not hunks:
                self._error("Hunk staging is available only for tracked text modifications with unstaged hunks.")
                return
            if path not in self._safety_acknowledged_paths and entry.kind != FileKind.DELETED:
                issues = self.git.safety_issues([path])
                if issues:
                    warning = SafetyWarningDialog(issues, context="stage", allow_ignore=False, parent=self)
                    if warning.exec() != QDialog.DialogCode.Accepted or warning.action != "continue":
                        return
                    self._safety_acknowledged_paths.add(path)
            dialog = HunkStageDialog(path, hunks, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            selected = dialog.selected_indexes()
            self.git.stage_hunks(path, selected)
            self.refresh_all()
            self.statusBar().showMessage(
                f"Staged {len(selected)} selected hunk(s) from {path}.",
                5000,
            )
        except GitError as exc:
            self._error(str(exc))

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
            if any(entry.conflicted for entry in staged):
                self._error("Resolve all merge conflicts before committing.")
                return

            candidates = [
                entry.path
                for entry in staged
                if entry.kind != FileKind.DELETED and entry.path not in self._safety_acknowledged_paths
            ]
            issues = self.git.safety_issues(candidates) if candidates else []
            if issues:
                dialog = SafetyWarningDialog(issues, context="commit", allow_ignore=False, parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted or dialog.action != "continue":
                    self.statusBar().showMessage("Commit cancelled during safety review.", 3500)
                    return
                self._safety_acknowledged_paths.update(issue.path for issue in issues)

            output = self.git.commit(message)
            self._safety_acknowledged_paths.clear()
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
        if dialog.exec() != QDialog.DialogCode.Accepted:
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
            on_success=lambda msg: self._network_done(str(msg), "Fetch"),
            busy="Fetching remote changes…",
        )

    def pull(self) -> None:
        if not self.git:
            return
        if self._current_conflicts:
            self._error("Resolve all merge conflicts before pulling.")
            return
        if self._current_operation:
            self._error(f"Finish or abort the current {self._current_operation} operation before pulling.")
            return
        if self._current_diverged:
            self._show_repository_safety()
            return
        token, username = self._github_auth()

        def task() -> str:
            self.git.fetch(token=token, username=username)
            return self.git.pull_ff_only(token=token, username=username)

        self._run_background(task, on_success=lambda msg: self._network_done(str(msg), "Pull"), busy="Pulling changes…")

    def push(self) -> None:
        if not self.git:
            return
        if self._current_conflicts:
            self._error("Resolve all merge conflicts before pushing.")
            return
        if self._current_operation:
            self._error(f"Finish or abort the current {self._current_operation} operation before pushing.")
            return
        if self._current_diverged:
            self._show_repository_safety()
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
            on_success=lambda msg: self._network_done(str(msg), "Push"),
            busy="Pushing commits…",
        )

    def _network_done(self, message: str, operation: str = "Operation") -> None:
        self.refresh_all()
        normalized = (message or "").strip().lower()
        if normalized.startswith("already up to date"):
            friendly = "✓ Already up to date."
        elif operation == "Fetch":
            friendly = "✓ Fetch completed."
        elif operation == "Pull":
            friendly = "✓ Pull completed."
        elif operation == "Push":
            friendly = "✓ Push completed."
        else:
            first_line = message.splitlines()[0] if message else "Done"
            friendly = f"✓ {first_line}"
        self.statusBar().showMessage(friendly, 6500)

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
        manage_action = menu.addAction("Manage Branches…")
        chosen = menu.exec(self.branch_button.mapToGlobal(self.branch_button.rect().bottomLeft()))
        if not chosen:
            return
        if chosen == manage_action:
            self.manage_branches()
            return
        if chosen == new_action:
            dialog = BranchDialog(self)
            result = dialog.exec()
            if result != QDialog.DialogCode.Accepted:
                return

            branch_name = dialog.name()
            if not branch_name:
                self._error("Branch name cannot be empty.")
                return

            try:
                logger.info("Creating and switching branch name=%r", branch_name)
                self.git.create_branch(branch_name, switch=True)
                active = self.git.branch()
                logger.info("Branch created successfully active=%r", active)
                self.statusBar().showMessage(
                    f"Created and switched to branch '{active}'.",
                    5000,
                )
                QTimer.singleShot(0, self.refresh_all)
            except GitError as exc:
                logger.exception("Could not create branch name=%r", branch_name)
                self._error(str(exc))
        else:
            branch = chosen.data()
            if branch and branch != info.branch:
                try:
                    logger.info("Switching branch from=%r to=%r", info.branch, branch)
                    self.git.switch_branch(branch)
                    active = self.git.branch()
                    self.statusBar().showMessage(
                        f"Switched to branch '{active}'.",
                        5000,
                    )
                    QTimer.singleShot(0, self.refresh_all)
                except GitError as exc:
                    logger.exception("Could not switch branch to=%r", branch)
                    self._error(str(exc))

    def _populate_history(self) -> None:
        if not self.git:
            return
        selected_sha = self._selected_history_sha()
        self.history_list.clear()
        selected_item = None
        for commit in self.git.history(120, all_local_branches=self.history_all_branches.isChecked()):
            item = QListWidgetItem(f"{commit.short_sha}   {commit.subject}\n{commit.author} • {commit.relative_date}")
            item.setToolTip(commit.sha)
            item.setData(Qt.UserRole, commit.sha)
            self.history_list.addItem(item)
            if selected_sha == commit.sha:
                selected_item = item
        if self.history_list.count() == 0:
            empty = QListWidgetItem("No commits yet.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.history_list.addItem(empty)
            self._history_selected(None, None)
        elif selected_item:
            self.history_list.setCurrentItem(selected_item)
        else:
            self.history_list.setCurrentRow(0)

    def _selected_history_sha(self) -> str | None:
        item = self.history_list.currentItem() if hasattr(self, "history_list") else None
        value = item.data(Qt.UserRole) if item else None
        return str(value) if value else None

    def _history_selected(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        sha = current.data(Qt.UserRole) if current else None
        available = bool(sha and self.git)
        if not available:
            self.history_title.setText("Select a commit to inspect it.")
            self.history_meta.clear()
            self.history_detail.clear()
            for button in (self.copy_hash_button, self.open_commit_button, self.revert_button, self.cherry_pick_button):
                button.setEnabled(False)
            return
        try:
            detail = self.git.commit_detail(str(sha))
            self.history_title.setText(f"{detail.short_sha}  {detail.subject}")
            body_note = f"\n\n{detail.body}" if detail.body else ""
            self.history_meta.setText(
                f"{detail.author} <{detail.author_email}> • {detail.authored_at} • {len(detail.files)} changed path(s){body_note}"
            )
            files = "\n".join(detail.files) if detail.files else "(no changed paths reported)"
            self.history_detail.setPlainText(f"CHANGED PATHS\n{'─' * 72}\n{files}\n\n{detail.patch}")
            self.copy_hash_button.setEnabled(True)
            info = self.git.repo_info()
            self.open_commit_button.setEnabled(bool(info.remote_url and GitService.is_github_url(info.remote_url)))
            history_safe = not self._is_busy and not self._current_conflicts and not self._current_diverged and not self._current_operation
            self.revert_button.setEnabled(history_safe and detail.parent_count <= 1)
            self.cherry_pick_button.setEnabled(history_safe)
            if detail.parent_count > 1:
                self.revert_button.setToolTip("Merge commits require an explicit mainline choice; RepoFlow does not guess it.")
            else:
                self.revert_button.setToolTip("")
        except GitError as exc:
            self.history_detail.setPlainText(str(exc))
            self.revert_button.setEnabled(False)
            self.cherry_pick_button.setEnabled(False)

    def copy_selected_commit_hash(self) -> None:
        sha = self._selected_history_sha()
        if not sha:
            return
        QApplication.clipboard().setText(sha)
        self.statusBar().showMessage(f"Copied commit {sha[:12]} to clipboard.", 4000)

    def open_selected_commit_on_github(self) -> None:
        if not self.git:
            return
        sha = self._selected_history_sha()
        if not sha:
            return
        url = self.git.remote_url("origin")
        if not url or not GitService.is_github_url(url):
            self._error("Open Commit on GitHub requires a GitHub origin remote.")
            return
        QDesktopServices.openUrl(QUrl(f"{self._remote_to_web_url(url)}/commit/{sha}"))

    def revert_selected_commit(self) -> None:
        if not self.git:
            return
        sha = self._selected_history_sha()
        if not sha:
            return
        try:
            detail = self.git.commit_detail(sha)
            if detail.parent_count > 1:
                self._error("RepoFlow does not guess the mainline parent for merge-commit reverts.")
                return
            answer = QMessageBox.warning(
                self,
                "Revert Commit",
                f"Create a new commit that reverses {detail.short_sha} ({detail.subject})?\n\n"
                "This preserves history and does not reset or rewrite existing commits.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            try:
                message = self.git.revert_commit(sha)
            except GitError:
                self.refresh_all()
                raise
            self.refresh_all()
            self.statusBar().showMessage(message.splitlines()[0] if message else "Revert commit created.", 6000)
        except GitError as exc:
            self._error(str(exc))

    def cherry_pick_selected_commit(self) -> None:
        if not self.git:
            return
        sha = self._selected_history_sha()
        if not sha:
            return
        try:
            detail = self.git.commit_detail(sha)
            answer = QMessageBox.question(
                self,
                "Cherry-pick Commit",
                f"Apply commit {detail.short_sha} ({detail.subject}) onto the current branch?\n\n"
                "RepoFlow will not resolve conflicts automatically.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            try:
                message = self.git.cherry_pick_commit(sha)
            except GitError:
                self.refresh_all()
                raise
            self.refresh_all()
            self.statusBar().showMessage(message.splitlines()[0] if message else "Cherry-pick completed.", 6000)
        except GitError as exc:
            self._error(str(exc))

    def _tab_changed(self, index: int) -> None:
        if index == 1:
            self._populate_history()

    # ---------- Background work ----------
    def _run_background(self, fn, *, on_success, busy: str, on_error=None) -> None:
        self._set_busy(True, busy)
        worker = FunctionWorker(fn)
        self._active_workers.append(worker)
        logger.info("Background task started label=%r active_workers=%d", busy, len(self._active_workers))

        def success(result) -> None:
            logger.info("Background task succeeded label=%r", busy)
            on_success(result)

        def error(message: str) -> None:
            logger.warning("Background task failed label=%r error=%s", busy, message)
            (on_error or self._error)(message)

        def finished() -> None:
            # Do not overwrite the success/error message with "Ready" immediately.
            # The result remains visible for its configured timeout.
            self._set_busy(False, None)
            if worker in self._active_workers:
                self._active_workers.remove(worker)
            logger.info("Background task finished label=%r active_workers=%d", busy, len(self._active_workers))

        worker.signals.success.connect(success)
        worker.signals.error.connect(error)
        worker.signals.finished.connect(finished)
        self.pool.start(worker)

    def _apply_operation_button_state(self) -> None:
        has_repo = self.git is not None
        available = has_repo and not self._is_busy
        self.refresh_button.setEnabled(available)
        self.fetch_button.setEnabled(available and self._can_fetch)
        self.pull_button.setEnabled(available and self._can_pull)
        self.push_button.setEnabled(available and self._can_push)
        self.branch_button.setEnabled(available and not self._current_conflicts and not self._current_operation)
        self.remote_button.setEnabled(available)
        self.commit_button.setEnabled(available)
        self.commit_push_button.setEnabled(
            available and not self._current_conflicts and not self._current_diverged and not self._current_operation
        )
        self.hunk_button.setEnabled(available and self._hunk_available and not self._current_operation)
        if hasattr(self, "abort_operation_action"):
            self.abort_operation_action.setEnabled(available and bool(self._current_operation))
        history_safe = available and not self._current_conflicts and not self._current_diverged and not self._current_operation
        if hasattr(self, "revert_button"):
            selected = bool(self._selected_history_sha())
            self.revert_button.setEnabled(history_safe and selected)
            self.cherry_pick_button.setEnabled(history_safe and selected)
        if hasattr(self, "sync_details_button"):
            self.sync_details_button.setEnabled(available)
            self.remote_branches_button.setEnabled(available and not self._current_conflicts and not self._current_operation)
            self.tags_button.setEnabled(available)

    def _set_busy(self, busy: bool, message: str | None) -> None:
        self._is_busy = busy
        if message is not None:
            self.statusBar().showMessage(message)
        self.activity_progress.setVisible(busy)
        self._apply_operation_button_state()

    def _error(self, message: str) -> None:
        QMessageBox.critical(self, "RepoFlow", message)
        self.statusBar().showMessage(message, 7000)
