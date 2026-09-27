APP_STYLE = r"""
QMainWindow, QWidget {
    background: #0f131a;
    color: #e9edf3;
    font-family: Inter, "Noto Sans", sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background: #0b0f15;
    border-right: 1px solid #232b37;
}
QFrame#header, QFrame#commitPanel {
    background: #151b24;
    border: 1px solid #263142;
    border-radius: 12px;
}
QFrame#header { background: #141a23; }
QLabel#title { font-size: 21px; font-weight: 700; color: #f6f8fb; }
QLabel#muted { color: #8f9bab; }
QLabel#brandIcon { background: transparent; }
QLabel#syncBadge {
    color: #b9c4d3;
    background: #151b24;
    border: 1px solid #263142;
    border-radius: 8px;
    padding: 7px 10px;
}
QLabel#statusGood { color: #79dc93; font-weight: 600; }
QLabel#statusWarn { color: #f2c66d; font-weight: 600; }
QPushButton {
    background: #202936;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 13px;
    color: #e9edf3;
}
QPushButton:hover { background: #293546; border-color: #43536a; }
QPushButton:pressed { background: #1a2330; }
QPushButton:disabled { color: #697586; background: #171d26; border-color: #252e3b; }
QPushButton#primary {
    background: #4c7dff;
    border-color: #6a94ff;
    color: white;
    font-weight: 650;
}
QPushButton#primary:hover { background: #5b89ff; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background: #0c1118;
    border: 1px solid #2b3645;
    border-radius: 8px;
    padding: 8px;
    color: #e9edf3;
    selection-background-color: #4c7dff;
}
QPlainTextEdit#diffView {
    background: #0a0f15;
    font-family: "JetBrains Mono", "Noto Sans Mono", monospace;
    font-size: 12px;
}
QListWidget, QTreeWidget {
    background: #0c1118;
    border: 1px solid #252f3d;
    border-radius: 9px;
    outline: none;
    alternate-background-color: #101720;
}
QListWidget::item, QTreeWidget::item { padding: 7px; border-radius: 5px; }
QListWidget::item:hover, QTreeWidget::item:hover { background: #172131; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #22324a; color: #ffffff; }
QHeaderView::section {
    background: #141a23;
    color: #aeb8c6;
    border: none;
    border-bottom: 1px solid #2b3645;
    padding: 8px;
    font-weight: 600;
}
QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: transparent;
    padding: 9px 15px;
    color: #8f9bab;
}
QTabBar::tab:hover { color: #cbd5e1; }
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #5b89ff;
    font-weight: 600;
}
QSplitter::handle { background: #263142; width: 1px; height: 1px; }
QStatusBar {
    background: #0b0f15;
    color: #a8b3c2;
    border-top: 1px solid #202938;
    padding: 2px 8px;
}
QProgressBar#activityProgress {
    background: #18202b;
    border: 1px solid #2d3a4d;
    border-radius: 5px;
}
QProgressBar#activityProgress::chunk {
    background: #4c7dff;
    border-radius: 4px;
}
QMenu {
    background: #151b24;
    border: 1px solid #303c4e;
    padding: 5px;
}
QMenu::item { padding: 7px 24px 7px 12px; border-radius: 5px; }
QMenu::item:selected { background: #22324a; }
QToolTip {
    background: #202936;
    color: #f8fafc;
    border: 1px solid #3a4658;
    padding: 5px;
}
QScrollBar:vertical {
    background: #0c1118;
    width: 11px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

# Stage 3 safety surfaces.
APP_STYLE += r"""
QLabel#safetyBanner {
    color: #ffd68a;
    background: #2a2114;
    border: 1px solid #6b4d1f;
    border-radius: 9px;
    padding: 9px 11px;
    font-weight: 600;
}
QPushButton#warningAction {
    background: #3a2c16;
    border-color: #8a6427;
    color: #ffd68a;
    font-weight: 650;
}
QPushButton#warningAction:hover { background: #49371b; }
QPushButton#dangerAction {
    background: #7f2934;
    border-color: #b44959;
    color: #ffffff;
    font-weight: 650;
}
QPushButton#dangerAction:hover { background: #953441; }
QPlainTextEdit#safetyDetails, QPlainTextEdit#gitignoreEditor {
    background: #0a0f15;
    font-family: "JetBrains Mono", "Noto Sans Mono", monospace;
    font-size: 12px;
}
"""
