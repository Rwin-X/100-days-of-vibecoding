#!/usr/bin/env python3
"""
Vedit — a modal text editor with vim-style editing and a modern,
themeable UI. Cross-platform (Linux, Windows, macOS).

Author: black8arch / devforge
"""

import sys
import os
import re

from PyQt6.QtCore import Qt, QDir, QModelIndex
from PyQt6.QtGui import QAction, QKeySequence, QFileSystemModel, QIcon, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QFileDialog, QMessageBox, QTreeView,
    QSplitter, QMenu, QMenuBar, QStatusBar, QInputDialog
)

from theme import THEMES, DEFAULT_THEME, build_qss
from modal_editor import ModalEditor, Mode
from syntax import PygmentsHighlighter
import commands as exc


APP_NAME = "Vedit"

MODE_NAMES = {
    Mode.NORMAL: "NORMAL",
    Mode.INSERT: "INSERT",
    Mode.VISUAL: "VISUAL",
    Mode.VISUAL_LINE: "V-LINE",
    Mode.REPLACE: "REPLACE",
}


class EditorTab(QWidget):
    """One open buffer: the modal editor + its highlighter + file path."""

    def __init__(self, theme: dict, filepath: str | None = None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.encoding = "utf-8"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.editor = ModalEditor(theme)
        self.highlighter = PygmentsHighlighter(self.editor.document(), theme, filepath or "", editor=self.editor)
        layout.addWidget(self.editor)

        if filepath and os.path.exists(filepath):
            self._load_file(filepath)

    def _load_file(self, filepath: str):
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            try:
                text = raw.decode("utf-8")
                self.encoding = "utf-8"
            except UnicodeDecodeError:
                import chardet
                detected = chardet.detect(raw)
                enc = detected.get("encoding") or "latin-1"
                text = raw.decode(enc, errors="replace")
                self.encoding = enc
            self.editor.setPlainText(text)
            self.filepath = filepath
            self.highlighter.set_filepath(filepath)
            self.editor.mark_clean()
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Could not open file:\n{e}")

    def save(self, as_path: str | None = None) -> bool:
        target = as_path or self.filepath
        if not target:
            return False
        try:
            with open(target, "w", encoding=self.encoding, newline="") as f:
                f.write(self.editor.toPlainText())
            self.filepath = target
            self.highlighter.set_filepath(target)  # may re-lex and touch the doc
            self.editor.mark_clean()  # so clear dirty AFTER any rehighlight side effect
            return True
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Could not save file:\n{e}")
            return False

    def display_name(self) -> str:
        if self.filepath:
            return os.path.basename(self.filepath)
        return "[No Name]"

    def apply_theme(self, theme: dict):
        self.editor.apply_theme(theme)
        self.highlighter.set_theme(theme)


class CommandBar(QWidget):
    """The bottom command line, shared for ':' commands and '/' search."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input = QLineEdit()
        self.input.setObjectName("CommandLine")
        layout.addWidget(self.input)
        self.hide()

    def start(self, prefix: str, on_submit, on_cancel=None):
        self.input.setText(prefix)
        self.show()
        self.input.setFocus()
        self.input.selectAll() if False else self.input.end(False)

        try:
            self.input.returnPressed.disconnect()
        except TypeError:
            pass

        def handle_submit():
            text = self.input.text()
            self.hide()
            on_submit(text)

        self.input.returnPressed.connect(handle_submit)
        self._on_cancel = on_cancel

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            if self._on_cancel:
                self._on_cancel()
            return
        super().keyPressEvent(event)


class VeditWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 820)

        self.theme_name = DEFAULT_THEME
        self.theme = THEMES[self.theme_name]

        self._build_ui()
        self._apply_theme()
        self.new_tab()

    # ---------------------------------------------------------------- UI --
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.currentPath())
        self.tree = QTreeView()
        self.tree.setObjectName("Sidebar")
        self.tree.setModel(self.file_model)
        self.tree.setRootIndex(self.file_model.index(QDir.currentPath()))
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self._open_from_tree)
        self.tree.setMinimumWidth(180)
        self.tree.setMaximumWidth(320)
        splitter.addWidget(self.tree)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        right_layout.addWidget(self.tabs, 1)

        self.command_bar = CommandBar()
        right_layout.addWidget(self.command_bar)

        self.status_bar = self._build_status_bar()
        right_layout.addWidget(self.status_bar)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 1000])

        root.addWidget(splitter)
        self.setCentralWidget(central)

        self._build_menu()

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(28)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 2, 10, 2)

        self.mode_label = QLabel("NORMAL")
        self.mode_label.setObjectName("ModeLabel")
        layout.addWidget(self.mode_label)

        self.file_label = QLabel("[No Name]")
        self.file_label.setObjectName("FileLabel")
        layout.addWidget(self.file_label)

        layout.addStretch(1)

        self.theme_label = QLabel(self.theme_name)
        self.theme_label.setObjectName("PosLabel")
        layout.addWidget(self.theme_label)

        self.pos_label = QLabel("1:1")
        self.pos_label.setObjectName("PosLabel")
        layout.addWidget(self.pos_label)

        return bar

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        new_action = QAction("New Tab", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(lambda: self.new_tab())
        file_menu.addAction(new_action)

        open_action = QAction("Open…", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_dialog)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(lambda: self.current_tab().save() if self.current_tab() else None)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As…", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_as_dialog)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        open_folder_action = QAction("Open Folder…", self)
        open_folder_action.triggered.connect(self._open_folder_dialog)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        theme_menu = menubar.addMenu("&Theme")
        for name in THEMES:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self._set_theme(n))
            theme_menu.addAction(action)

        help_menu = menubar.addMenu("&Help")
        keys_action = QAction("Keybindings", self)
        keys_action.triggered.connect(self._show_keybindings)
        help_menu.addAction(keys_action)

    # ------------------------------------------------------------ theme --
    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.theme))
        for i in range(self.tabs.count()):
            self.tabs.widget(i).apply_theme(self.theme)
        self._update_mode_label(Mode.NORMAL)

    def _set_theme(self, name: str):
        self.theme_name = name
        self.theme = THEMES[name]
        self._apply_theme()
        self.theme_label.setText(name)

    # ------------------------------------------------------------- tabs --
    def new_tab(self, filepath: str | None = None):
        tab = EditorTab(self.theme, filepath)
        tab.editor.modeChanged.connect(self._update_mode_label)
        tab.editor.commandRequested.connect(self._start_command)
        tab.editor.searchRequested.connect(self._start_search)
        tab.editor.dirtyChanged.connect(lambda dirty: self._update_tab_title(tab))
        tab.editor.cursorPositionChanged.connect(self._update_position_label)

        index = self.tabs.addTab(tab, tab.display_name())
        self.tabs.setCurrentIndex(index)
        tab.editor.setFocus()
        self._update_tab_title(tab)
        return tab

    def current_tab(self) -> EditorTab | None:
        return self.tabs.currentWidget()

    def _on_tab_changed(self, index):
        tab = self.current_tab()
        if tab:
            self._update_mode_label(tab.editor.mode)
            self.file_label.setText(tab.filepath or "[No Name]")
            self._update_position_label()
            tab.editor.setFocus()

    def _update_tab_title(self, tab: EditorTab):
        index = self.tabs.indexOf(tab)
        if index < 0:
            return
        name = tab.display_name()
        if tab.editor.is_dirty():
            name += " \u25CF"
        self.tabs.setTabText(index, name)
        if tab is self.current_tab():
            self.file_label.setText(tab.filepath or "[No Name]")

    def _close_tab(self, index):
        tab = self.tabs.widget(index)
        if tab and tab.editor.is_dirty():
            reply = QMessageBox.question(
                self, APP_NAME,
                f"{tab.display_name()} has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not tab.save():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_tab()

    # -------------------------------------------------------- file open --
    def _open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.new_tab(path)

    def _open_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder")
        if folder:
            self.file_model.setRootPath(folder)
            self.tree.setRootIndex(self.file_model.index(folder))

    def _open_from_tree(self, index: QModelIndex):
        path = self.file_model.filePath(index)
        if os.path.isfile(path):
            self.new_tab(path)

    def _save_as_dialog(self):
        tab = self.current_tab()
        if not tab:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save As")
        if path:
            tab.save(as_path=path)
            self._update_tab_title(tab)

    # ---------------------------------------------------------- status --
    def _update_mode_label(self, mode: Mode):
        self.mode_label.setText(MODE_NAMES.get(mode, "NORMAL"))
        color_key = {
            Mode.NORMAL: "mode_normal",
            Mode.INSERT: "mode_insert",
            Mode.VISUAL: "mode_visual",
            Mode.VISUAL_LINE: "mode_visual",
            Mode.REPLACE: "mode_replace",
        }.get(mode, "mode_normal")
        color = self.theme.get(color_key, self.theme["accent"])
        self.mode_label.setStyleSheet(
            f"background-color: {color}; color: {self.theme['bg']}; "
            f"font-size: 11px; font-weight: 700; padding: 2px 12px; border-radius: 3px;"
        )

    def _update_position_label(self):
        tab = self.current_tab()
        if not tab:
            return
        cur = tab.editor.textCursor()
        line = cur.blockNumber() + 1
        col = cur.positionInBlock() + 1
        total = tab.editor.document().blockCount()
        self.pos_label.setText(f"{line}:{col}  ({total} lines)")

    # -------------------------------------------------------- commands --
    def _start_command(self, prefix: str):
        tab = self.current_tab()
        if not tab:
            return
        self.command_bar.start(
            ":" + prefix,
            on_submit=self._run_command,
            on_cancel=lambda: tab.editor.setFocus(),
        )

    def _run_command(self, raw: str):
        tab = self.current_tab()
        if tab:
            tab.editor.setFocus()
        if not raw.startswith(":"):
            return
        raw = raw[1:]
        if not raw:
            return

        parsed = exc.parse(raw)

        if parsed.name == "goto":
            self._cmd_goto(parsed.range_spec)
            return
        if parsed.name in ("w", "write"):
            self._cmd_write(parsed.args, force=parsed.force)
            return
        if parsed.name in ("q", "quit"):
            self._cmd_quit(force=parsed.force)
            return
        if parsed.name in ("wq", "x"):
            self._cmd_write("", force=parsed.force)
            self._cmd_quit(force=True)
            return
        if parsed.name == "qa":
            self._cmd_quit_all(force=parsed.force)
            return
        if parsed.name == "wqa":
            self._cmd_write("", force=True)
            self._cmd_quit_all(force=True)
            return
        if parsed.name in ("e", "edit"):
            if parsed.args:
                self.new_tab(parsed.args.strip())
            return
        if parsed.name == "tabnew":
            self.new_tab(parsed.args.strip() or None)
            return
        if parsed.name == "bn":
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % max(1, self.tabs.count()))
            return
        if parsed.name == "bp":
            self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % max(1, self.tabs.count()))
            return
        if parsed.name == "theme":
            name = parsed.args.strip()
            matches = [t for t in THEMES if t.lower() == name.lower()]
            if matches:
                self._set_theme(matches[0])
            return
        if parsed.name == "substitute":
            self._cmd_substitute(parsed.args, parsed.range_spec)
            return
        if parsed.name.startswith("set"):
            return  # accepted, no-op (line numbers always on, etc.)

    def _cmd_goto(self, range_spec: str):
        tab = self.current_tab()
        if not tab or not range_spec.isdigit():
            return
        line = max(1, int(range_spec))
        from PyQt6.QtGui import QTextCursor
        block = tab.editor.document().findBlockByNumber(line - 1)
        if block.isValid():
            cur = tab.editor.textCursor()
            cur.setPosition(block.position())
            tab.editor.setTextCursor(cur)

    def _cmd_write(self, args: str, force: bool):
        tab = self.current_tab()
        if not tab:
            return
        target = args.strip() or None
        if not target and not tab.filepath:
            self._save_as_dialog()
            return
        tab.save(as_path=target)
        self._update_tab_title(tab)

    def _cmd_quit(self, force: bool):
        tab = self.current_tab()
        if not tab:
            return
        index = self.tabs.indexOf(tab)
        if tab.editor.is_dirty() and not force:
            reply = QMessageBox.question(
                self, APP_NAME,
                f"{tab.display_name()} has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not tab.save():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.close()

    def _cmd_quit_all(self, force: bool):
        if not force:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab.editor.is_dirty():
                    reply = QMessageBox.question(
                        self, APP_NAME,
                        "Some tabs have unsaved changes. Quit anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    break
        self.close()

    def _cmd_substitute(self, args: str, range_spec: str):
        tab = self.current_tab()
        if not tab:
            return
        parsed = exc.parse_substitute(args)
        if not parsed:
            return
        pattern, replacement, flags = parsed
        py_flags = re.MULTILINE
        count = 0 if "g" in flags else 1

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            QMessageBox.warning(self, APP_NAME, f"Invalid pattern: {e}")
            return

        doc = tab.editor.document()
        cur = tab.editor.textCursor()
        cur.beginEditBlock()

        if range_spec in ("%", ""):
            full_text = tab.editor.toPlainText()
            new_text = compiled.sub(replacement, full_text, count=0 if count == 0 else 0) \
                if count == 0 else "\n".join(
                    compiled.sub(replacement, line, count=1) for line in full_text.split("\n")
                )
            if count == 0:
                new_text = "\n".join(
                    compiled.sub(replacement, line, count=0) for line in full_text.split("\n")
                )
            tab.editor.setPlainText(new_text)
        elif range_spec == "'<,'>":
            # operate on current selection's line range if present, else current line
            sel_cur = tab.editor.textCursor()
            if sel_cur.hasSelection():
                start_block = doc.findBlock(min(sel_cur.selectionStart(), sel_cur.selectionEnd()))
                end_block = doc.findBlock(max(sel_cur.selectionStart(), sel_cur.selectionEnd()))
            else:
                start_block = end_block = cur.block()
            b = start_block
            while True:
                text = b.text()
                new_text = compiled.sub(replacement, text, count=0 if count == 0 else 1)
                if new_text != text:
                    line_cur = QTextCursorForBlock(doc, b)
                    line_cur.select(line_cur.SelectionType.LineUnderCursor) if False else None
                    self._replace_block_text(tab.editor, b, new_text)
                    b = doc.findBlock(b.position())
                if b.blockNumber() >= end_block.blockNumber():
                    break
                b = b.next()
        else:
            # current line only
            b = cur.block()
            text = b.text()
            new_text = compiled.sub(replacement, text, count=0 if count == 0 else 1)
            if new_text != text:
                self._replace_block_text(tab.editor, b, new_text)

        cur.endEditBlock()

    @staticmethod
    def _replace_block_text(editor, block, new_text):
        from PyQt6.QtGui import QTextCursor
        c = QTextCursor(block)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        c.insertText(new_text)

    # ---------------------------------------------------------- search --
    def _start_search(self, _pattern: str, forward: bool):
        tab = self.current_tab()
        if not tab:
            return
        prefix = "/" if forward else "?"
        self.command_bar.start(
            prefix,
            on_submit=lambda text: self._run_search(text, forward),
            on_cancel=lambda: tab.editor.setFocus(),
        )

    def _run_search(self, raw: str, forward: bool):
        tab = self.current_tab()
        if tab:
            tab.editor.setFocus()
        if len(raw) < 2:
            return
        pattern = raw[1:]
        if not pattern:
            return
        doc_flags = QApplication.instance()
        from PyQt6.QtGui import QTextDocument
        find_flags = QTextDocument.FindFlag(0) if forward else QTextDocument.FindFlag.FindBackward
        found = tab.editor.find(pattern, find_flags)
        if not found:
            cur = tab.editor.textCursor()
            cur.movePosition(cur.MoveOperation.Start if forward else cur.MoveOperation.End)
            tab.editor.setTextCursor(cur)
            tab.editor.find(pattern, find_flags)

    # ------------------------------------------------------------ help --
    def _show_keybindings(self):
        text = (
            "MODES\n"
            "  i / a / I / A / o / O   enter Insert mode\n"
            "  Esc                     back to Normal mode\n"
            "  v / V                   Visual / Visual Line\n"
            "  R                       Replace mode\n\n"
            "MOTIONS\n"
            "  h j k l   left/down/up/right      w b e   word motions\n"
            "  0 ^ $     line start/first-char/end   gg / G   top / bottom\n\n"
            "EDITING\n"
            "  x X       delete char (fwd/back)   dd / yy / cc   line ops\n"
            "  dw yw cw  operator + motion         p / P   paste after/before\n"
            "  u / Ctrl+R   undo / redo            ~   toggle case\n\n"
            "COMMAND LINE\n"
            "  :w  :q  :wq  :q!  :x     save / quit\n"
            "  :e <file>   :tabnew      open files / tabs\n"
            "  :theme <name>            switch color theme\n"
            "  :%s/pat/rep/g            substitute\n"
            "  / and ?                  search forward / backward\n"
        )
        QMessageBox.information(self, "Vedit Keybindings", text)

    # --------------------------------------------------------- shutdown --
    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if tab.editor.is_dirty():
                self.tabs.setCurrentIndex(i)
                reply = QMessageBox.question(
                    self, APP_NAME,
                    f"{tab.display_name()} has unsaved changes. Quit anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
        event.accept()


def QTextCursorForBlock(doc, block):
    from PyQt6.QtGui import QTextCursor
    return QTextCursor(block)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = VeditWindow()
    window.show()

    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isfile(arg):
                window.new_tab(arg)
        # remove the initial blank tab if we opened real files
        if window.tabs.count() > 1 and window.tabs.widget(0).filepath is None \
                and not window.tabs.widget(0).editor.toPlainText():
            window.tabs.removeTab(0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
