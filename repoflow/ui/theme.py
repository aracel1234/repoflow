APP_STYLE = r"""
QMainWindow, QWidget {
    background: #14171c;
    color: #e8eaed;
    font-family: Inter, "Noto Sans", sans-serif;
    font-size: 13px;
}
QFrame#sidebar {
    background: #101318;
    border-right: 1px solid #252a33;
}
QFrame#header, QFrame#commitPanel {
    background: #171b21;
    border: 1px solid #252a33;
    border-radius: 10px;
}
QLabel#title { font-size: 20px; font-weight: 700; }
QLabel#muted { color: #9aa3ad; }
QLabel#statusGood { color: #7bd88f; font-weight: 600; }
QLabel#statusWarn { color: #f6c177; font-weight: 600; }
QPushButton {
    background: #242a33;
    border: 1px solid #343b46;
    border-radius: 7px;
    padding: 7px 12px;
}
QPushButton:hover { background: #2d3540; }
QPushButton:pressed { background: #1f252d; }
QPushButton:disabled { color: #69717b; background: #1b1f25; }
QPushButton#primary {
    background: #4c7dff;
    border-color: #5b89ff;
    color: white;
    font-weight: 600;
}
QPushButton#primary:hover { background: #5b89ff; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background: #101318;
    border: 1px solid #303641;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #4c7dff;
}
QListWidget, QTreeWidget {
    background: #111419;
    border: 1px solid #252a33;
    border-radius: 8px;
    outline: none;
}
QListWidget::item, QTreeWidget::item { padding: 6px; }
QListWidget::item:selected, QTreeWidget::item:selected { background: #283449; }
QHeaderView::section {
    background: #171b21;
    color: #aeb6c0;
    border: none;
    border-bottom: 1px solid #303641;
    padding: 7px;
}
QTabWidget::pane { border: 0; }
QTabBar::tab {
    background: transparent;
    padding: 8px 14px;
    color: #9aa3ad;
}
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #4c7dff;
}
QSplitter::handle { background: #252a33; width: 1px; height: 1px; }
QStatusBar { background: #101318; color: #9aa3ad; }
QMenu { background: #171b21; border: 1px solid #303641; }
QMenu::item:selected { background: #283449; }
"""
