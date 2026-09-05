"""
Modal editing engine for Vedit — a QPlainTextEdit subclass that implements
vim-like modal editing: Normal, Insert, Visual, Visual Line, and Replace
modes, with common motions, operators, and text objects.

This is a practical subset of vim's editing model — not a full
reimplementation — chosen to cover the motions and operators people
actually use day to day.
"""

import re
from enum import Enum, auto

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QFont, QKeyEvent, QPainter,
    QTextFormat
)
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


class Mode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()
    VISUAL_LINE = auto()
    REPLACE = auto()


WORD_RE = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]+")


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class ModalEditor(QPlainTextEdit):
    """A QPlainTextEdit with vim-like modal editing layered on top."""

    modeChanged = pyqtSignal(object)          # Mode
    commandRequested = pyqtSignal(str)        # raw text typed after ':'
    searchRequested = pyqtSignal(str, bool)   # pattern, forward?
    statusMessage = pyqtSignal(str)
    dirtyChanged = pyqtSignal(bool)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.mode = Mode.NORMAL
        self._pending_count = ""
        self._pending_op = None          # 'd', 'c', 'y' waiting for a motion
        self._pending_g = False
        self._pending_replace_char = False
        self._visual_anchor = None
        self._last_find = None           # (char, direction, till) for ; and ,
        self._clipboard_text = ""
        self._clipboard_is_line = False
        self._undo_dirty_baseline = 0
        self._is_dirty = False

        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabChangesFocus(False)
        self.setCursorWidth(0)  # we draw our own cursor to reflect mode

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)

        self._update_line_number_area_width(0)
        self._highlight_current_line()
        self._apply_font()
        self.set_mode(Mode.NORMAL)

    # ------------------------------------------------------ appearance --
    def _apply_font(self):
        font = QFont("JetBrains Mono", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        if not font.exactMatch():
            font = QFont("Consolas", 12)
            font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def apply_theme(self, theme: dict):
        self.theme = theme
        pal = self.palette()
        from PyQt6.QtGui import QPalette
        pal.setColor(QPalette.ColorRole.Base, QColor(theme["bg"]))
        pal.setColor(QPalette.ColorRole.Text, QColor(theme["fg"]))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(theme["selection"]))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(theme["fg"]))
        self.setPalette(pal)
        self._highlight_current_line()
        self.line_number_area.update()
        self.viewport().update()

    # ---------------------------------------------------------- dirty --
    def _on_text_changed(self):
        was_dirty = self._is_dirty
        self._is_dirty = True
        if not was_dirty:
            self.dirtyChanged.emit(True)

    def mark_clean(self):
        self._is_dirty = False
        self.dirtyChanged.emit(False)

    def is_dirty(self) -> bool:
        return self._is_dirty

    # ------------------------------------------------------------ mode --
    def set_mode(self, mode: Mode):
        prev = self.mode
        self.mode = mode
        if mode == Mode.NORMAL:
            self.setCursorWidth(0)
            self._pending_count = ""
            self._pending_op = None
            self._pending_g = False
            if prev in (Mode.VISUAL, Mode.VISUAL_LINE):
                cur = self.textCursor()
                cur.clearSelection()
                self.setTextCursor(cur)
        elif mode == Mode.INSERT:
            self.setCursorWidth(2)
        elif mode == Mode.REPLACE:
            self.setCursorWidth(2)
        elif mode in (Mode.VISUAL, Mode.VISUAL_LINE):
            self.setCursorWidth(0)
            if prev not in (Mode.VISUAL, Mode.VISUAL_LINE):
                self._visual_anchor = self.textCursor().position()
        self.modeChanged.emit(mode)
        self.viewport().update()

    def enter_insert(self, after: bool = False, end_of_line: bool = False,
                      new_line_below: bool = False, new_line_above: bool = False):
        cur = self.textCursor()
        if new_line_below:
            cur.movePosition(QTextCursor.MoveOperation.EndOfLine)
            cur.insertText("\n")
        elif new_line_above:
            cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cur.insertText("\n")
            cur.movePosition(QTextCursor.MoveOperation.Up)
        elif end_of_line:
            cur.movePosition(QTextCursor.MoveOperation.EndOfLine)
        elif after:
            if not self._at_end_of_line(cur):
                cur.movePosition(QTextCursor.MoveOperation.Right)
        self.setTextCursor(cur)
        self.set_mode(Mode.INSERT)

    # ---------------------------------------------------------- helpers --
    def _at_end_of_line(self, cur: QTextCursor) -> bool:
        test = QTextCursor(cur)
        test.movePosition(QTextCursor.MoveOperation.EndOfLine)
        return cur.position() == test.position()

    def _clamp_to_line(self, cur: QTextCursor):
        """In Normal mode the cursor should never sit past the last char of a line."""
        block = cur.block()
        text = block.text()
        col = cur.positionInBlock()
        if text and col >= len(text):
            cur.setPosition(block.position() + max(0, len(text) - 1))
        return cur

    def _current_line_text(self) -> str:
        return self.textCursor().block().text()

    # ------------------------------------------------------------ paint --
    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 14 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_area_width(self, _=0):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        from PyQt6.QtCore import QRect
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self.theme["bg_alt"]))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        current_line = self.textCursor().blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                color = (
                    QColor(self.theme["gutter_fg_active"])
                    if block_number == current_line
                    else QColor(self.theme["gutter_fg"])
                )
                painter.setPen(color)
                painter.drawText(
                    0, int(top), self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number,
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def _highlight_current_line(self):
        extra_selections = []
        if self.mode not in (Mode.VISUAL, Mode.VISUAL_LINE) and not self.textCursor().hasSelection():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(self.theme["cursor_line"]))
            sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra_selections.append(sel)
        self.setExtraSelections(extra_selections)

    def paintEvent(self, event):
        super().paintEvent(event)
        # Draw a block/underline cursor to reflect the current mode, since
        # we disabled the native thin caret in Normal/Visual modes.
        if self.mode in (Mode.NORMAL, Mode.VISUAL, Mode.VISUAL_LINE):
            cur = self.textCursor()
            rect = self.cursorRect(cur)
            painter = QPainter(self.viewport())
            color = QColor(self.theme["fg"])
            color.setAlpha(160)
            char_width = self.fontMetrics().horizontalAdvance("W")
            painter.fillRect(rect.left(), rect.top(), char_width, rect.height(), color)
            painter.end()

    # -------------------------------------------------------------- key --
    def keyPressEvent(self, event: QKeyEvent):
        if self.mode == Mode.INSERT:
            self._handle_insert_key(event)
        elif self.mode == Mode.REPLACE:
            self._handle_replace_key(event)
        elif self.mode in (Mode.VISUAL, Mode.VISUAL_LINE):
            self._handle_visual_key(event)
        else:
            self._handle_normal_key(event)

    # ----------------------------------------------------- insert mode --
    def _handle_insert_key(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            cur = self.textCursor()
            if not self._at_end_of_line(cur) and cur.positionInBlock() > 0:
                cur.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(cur)
            self.set_mode(Mode.NORMAL)
            return
        super().keyPressEvent(event)

    # ---------------------------------------------------- replace mode --
    def _handle_replace_key(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            self.set_mode(Mode.NORMAL)
            return
        text = event.text()
        if text and text.isprintable():
            cur = self.textCursor()
            cur.beginEditBlock()
            if not self._at_end_of_line(cur):
                cur.deleteChar()
            cur.insertText(text)
            cur.endEditBlock()
            self.setTextCursor(cur)
            return
        if event.key() == Qt.Key.Key_Backspace:
            cur = self.textCursor()
            cur.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cur)
            return
        super().keyPressEvent(event)

    # ----------------------------------------------------- visual mode --
    def _handle_visual_key(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Escape:
            self.set_mode(Mode.NORMAL)
            return

        cur = self.textCursor()

        motion_made = self._try_motion(cur, key, text)
        if motion_made:
            anchor = self._visual_anchor
            cur.setPosition(anchor, QTextCursor.MoveMode.MoveAnchor)
            cur.setPosition(self._pending_new_pos, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cur)
            return

        if text == "v":
            self.set_mode(Mode.NORMAL if self.mode == Mode.VISUAL else Mode.VISUAL)
            return
        if text == "V":
            self.set_mode(Mode.NORMAL if self.mode == Mode.VISUAL_LINE else Mode.VISUAL_LINE)
            return

        if text in ("d", "x"):
            self._visual_delete(yank=False)
            return
        if text == "y":
            self._visual_delete(yank=True, restore_cursor=True)
            return
        if text == "c":
            self._visual_delete(yank=False)
            self.set_mode(Mode.INSERT)
            return
        if text == "u":
            self._visual_case(lower=True)
            return
        if text == "U":
            self._visual_case(lower=False)
            return
        if text == ":":
            self.commandRequested.emit("'<,'>")
            return
        # ignore anything else silently in visual mode

    def _visual_selection_bounds(self):
        cur = self.textCursor()
        start = min(self._visual_anchor, cur.position())
        end = max(self._visual_anchor, cur.position())
        return start, end

    def _visual_delete(self, yank: bool, restore_cursor: bool = False):
        cur = self.textCursor()
        if self.mode == Mode.VISUAL_LINE:
            start_block = self.document().findBlock(min(self._visual_anchor, cur.position()))
            end_block = self.document().findBlock(max(self._visual_anchor, cur.position()))
            sel = QTextCursor(self.document())
            sel.setPosition(start_block.position())
            sel.setPosition(end_block.position() + end_block.length() - 1, QTextCursor.MoveMode.KeepAnchor)
            if end_block.next().isValid():
                sel.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            text = sel.selectedText()
            self._clipboard_text = text.replace("\u2029", "\n")
            self._clipboard_is_line = True
            if not yank:
                sel.removeSelectedText()
        else:
            start, end = self._visual_selection_bounds()
            sel = QTextCursor(self.document())
            sel.setPosition(start)
            sel.setPosition(end + 1, QTextCursor.MoveMode.KeepAnchor)
            text = sel.selectedText()
            self._clipboard_text = text.replace("\u2029", "\n")
            self._clipboard_is_line = False
            if not yank:
                sel.removeSelectedText()

        if restore_cursor:
            new_cur = self.textCursor()
            new_cur.setPosition(min(self._visual_anchor, cur.position()))
            self.setTextCursor(new_cur)
        self.set_mode(Mode.NORMAL)

    def _visual_case(self, lower: bool):
        start, end = self._visual_selection_bounds()
        sel = QTextCursor(self.document())
        sel.setPosition(start)
        sel.setPosition(end + 1, QTextCursor.MoveMode.KeepAnchor)
        text = sel.selectedText()
        new_text = text.lower() if lower else text.upper()
        sel.beginEditBlock()
        sel.insertText(new_text)
        sel.endEditBlock()
        self.set_mode(Mode.NORMAL)

    # ------------------------------------------------------ normal mode --
    def _handle_normal_key(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        if key == Qt.Key.Key_Escape:
            self._pending_count = ""
            self._pending_op = None
            self._pending_g = False
            return

        # count prefix (digits, but not a leading 0)
        if text.isdigit() and not (text == "0" and not self._pending_count):
            self._pending_count += text
            return

        count = int(self._pending_count) if self._pending_count else 1

        if text == ":":
            self._pending_count = ""
            self.commandRequested.emit("")
            return

        if text == "/":
            self._pending_count = ""
            self.searchRequested.emit("", True)
            return

        if text == "?":
            self._pending_count = ""
            self.searchRequested.emit("", False)
            return

        if text == "u":
            for _ in range(count):
                self.undo()
            self._pending_count = ""
            return

        if event.key() == Qt.Key.Key_R and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            for _ in range(count):
                self.redo()
            self._pending_count = ""
            return

        if self._pending_g:
            self._pending_g = False
            if text == "g":
                cur = self.textCursor()
                cur.movePosition(QTextCursor.MoveOperation.Start)
                self.setTextCursor(cur)
            self._pending_count = ""
            return

        if text == "g":
            self._pending_g = True
            return

        if self._pending_op:
            self._handle_operator_motion(text, key, count)
            return

        cur = self.textCursor()

        # ---- operators awaiting a motion ----
        if text in ("d", "c", "y") and not self._pending_op:
            self._pending_op = text
            self._pending_op_count = count
            self._pending_count = ""
            return

        # ---- simple edits ----
        if text == "x":
            cur.beginEditBlock()
            for _ in range(count):
                if not self._at_end_of_line(cur):
                    cur.deleteChar()
            cur.endEditBlock()
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        if text == "X":
            cur.beginEditBlock()
            for _ in range(count):
                cur.deletePreviousChar()
            cur.endEditBlock()
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        if text == "D":
            cur.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            self._clipboard_text = cur.selectedText()
            self._clipboard_is_line = False
            cur.removeSelectedText()
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        if text == "C":
            cur.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            cur.removeSelectedText()
            self.setTextCursor(cur)
            self.set_mode(Mode.INSERT)
            self._pending_count = ""
            return

        if text == "p":
            self._paste(after=True, count=count)
            self._pending_count = ""
            return
        if text == "P":
            self._paste(after=False, count=count)
            self._pending_count = ""
            return

        if text == "~":
            cur.beginEditBlock()
            for _ in range(count):
                if self._at_end_of_line(cur):
                    break
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                ch = cur.selectedText()
                cur.insertText(ch.lower() if ch.isupper() else ch.upper())
            cur.endEditBlock()
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        if text == "J":
            cur.beginEditBlock()
            for _ in range(max(1, count - 1)):
                cur.movePosition(QTextCursor.MoveOperation.EndOfLine)
                cur.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                cur.insertText(" ")
                cur.movePosition(QTextCursor.MoveOperation.Left)
            cur.endEditBlock()
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        # ---- entering insert mode ----
        if text == "i":
            self.enter_insert()
            self._pending_count = ""
            return
        if text == "a":
            self.enter_insert(after=True)
            self._pending_count = ""
            return
        if text == "I":
            cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
            self.setTextCursor(cur)
            self.enter_insert()
            self._pending_count = ""
            return
        if text == "A":
            self.enter_insert(end_of_line=True)
            self._pending_count = ""
            return
        if text == "o":
            self.enter_insert(new_line_below=True)
            self._pending_count = ""
            return
        if text == "O":
            self.enter_insert(new_line_above=True)
            self._pending_count = ""
            return
        if text == "R":
            self.set_mode(Mode.REPLACE)
            self._pending_count = ""
            return

        # ---- visual mode ----
        if text == "v":
            self.set_mode(Mode.VISUAL)
            self._pending_count = ""
            return
        if text == "V":
            self.set_mode(Mode.VISUAL_LINE)
            self._pending_count = ""
            return

        # ---- motions (move cursor only) ----
        moved = self._try_motion(cur, key, text, count=count)
        if moved:
            cur.setPosition(self._pending_new_pos)
            cur = self._clamp_to_line(cur)
            self.setTextCursor(cur)
            self._pending_count = ""
            return

        self._pending_count = ""

    # ---------------------------------------------------------- motions --
    def _try_motion(self, cur: QTextCursor, key, text, count: int = 1) -> bool:
        """Compute a motion target position into self._pending_new_pos.
        Returns True if `text`/`key` was recognized as a motion."""
        c = QTextCursor(cur)
        c.clearSelection()  # motions always compute from a collapsed cursor;
        # visual-mode selection is reconstructed separately from _visual_anchor

        if key == Qt.Key.Key_Left or text == "h":
            for _ in range(count):
                if not c.atBlockStart():
                    c.movePosition(QTextCursor.MoveOperation.Left)
        elif key == Qt.Key.Key_Right or text == "l":
            for _ in range(count):
                if not self._at_end_of_line(c):
                    c.movePosition(QTextCursor.MoveOperation.Right)
        elif key == Qt.Key.Key_Down or text == "j":
            c.movePosition(QTextCursor.MoveOperation.Down, n=count)
        elif key == Qt.Key.Key_Up or text == "k":
            c.movePosition(QTextCursor.MoveOperation.Up, n=count)
        elif text == "0":
            c.movePosition(QTextCursor.MoveOperation.StartOfLine)
        elif text == "$":
            c.movePosition(QTextCursor.MoveOperation.EndOfLine)
            if not c.atBlockStart():
                c.movePosition(QTextCursor.MoveOperation.Left)
        elif text == "^":
            c.movePosition(QTextCursor.MoveOperation.StartOfLine)
            line = c.block().text()
            stripped = len(line) - len(line.lstrip())
            c.movePosition(QTextCursor.MoveOperation.Right, n=stripped)
        elif text == "w":
            for _ in range(count):
                c = self._word_forward(c)
        elif text == "b":
            for _ in range(count):
                c = self._word_backward(c)
        elif text == "e":
            for _ in range(count):
                c = self._word_end(c)
        elif text == "G":
            c.movePosition(QTextCursor.MoveOperation.End)
        elif key == Qt.Key.Key_Home:
            c.movePosition(QTextCursor.MoveOperation.StartOfLine)
        elif key == Qt.Key.Key_End:
            c.movePosition(QTextCursor.MoveOperation.EndOfLine)
        elif key in (Qt.Key.Key_PageDown,):
            c.movePosition(QTextCursor.MoveOperation.Down, n=20)
        elif key in (Qt.Key.Key_PageUp,):
            c.movePosition(QTextCursor.MoveOperation.Up, n=20)
        else:
            return False

        self._pending_new_pos = c.position()
        return True

    def _word_forward(self, c: QTextCursor) -> QTextCursor:
        text = self.toPlainText()
        pos = c.position()
        n = len(text)
        if pos >= n:
            return c
        if pos < n and not text[pos].isspace():
            cls = self._char_class(text[pos])
            while pos < n and self._char_class(text[pos]) == cls and not text[pos].isspace():
                pos += 1
        while pos < n and text[pos].isspace():
            pos += 1
        c.setPosition(min(pos, n))
        return c

    def _word_backward(self, c: QTextCursor) -> QTextCursor:
        text = self.toPlainText()
        pos = c.position()
        if pos == 0:
            return c
        pos -= 1
        while pos > 0 and text[pos].isspace():
            pos -= 1
        if pos > 0:
            cls = self._char_class(text[pos])
            while pos > 0 and self._char_class(text[pos - 1]) == cls and not text[pos - 1].isspace():
                pos -= 1
        c.setPosition(max(0, pos))
        return c

    def _word_end(self, c: QTextCursor) -> QTextCursor:
        text = self.toPlainText()
        pos = c.position()
        n = len(text)
        if pos < n - 1:
            pos += 1
        while pos < n and text[pos].isspace():
            pos += 1
        if pos < n:
            cls = self._char_class(text[pos])
            while pos + 1 < n and self._char_class(text[pos + 1]) == cls and not text[pos + 1].isspace():
                pos += 1
        c.setPosition(min(pos, max(0, n - 1)))
        return c

    @staticmethod
    def _char_class(ch: str) -> str:
        if ch.isalnum() or ch == "_":
            return "word"
        return "punct"

    # --------------------------------------------------- operator+motion --
    def _handle_operator_motion(self, text, key, count):
        op = self._pending_op
        op_count = getattr(self, "_pending_op_count", 1) * count

        cur = self.textCursor()
        start = cur.position()

        # doubled operator = whole line ("dd", "yy", "cc")
        if text == op:
            self._apply_linewise_operator(op, op_count)
            self._pending_op = None
            self._pending_count = ""
            return

        # G (and gg, handled separately) are linewise motions when used
        # as an operator target: "dG" deletes whole lines to the end of
        # the document, not just up to the last character.
        if text == "G":
            last_block_number = self.document().blockCount() - 1
            lines_to_cover = last_block_number - cur.blockNumber() + 1
            self._apply_linewise_operator(op, lines_to_cover)
            self._pending_op = None
            self._pending_count = ""
            return

        moved = self._try_motion(cur, key, text, count=op_count)
        if not moved:
            self._pending_op = None
            self._pending_count = ""
            return

        end = self._pending_new_pos

        # vim special-case: "cw"/"cW" on a non-blank char behaves like "ce"
        # (changes to the end of the word, not consuming trailing whitespace)
        if op == "c" and text == "w":
            doc_text = self.toPlainText()
            if start < len(doc_text) and not doc_text[start].isspace():
                e = QTextCursor(cur)
                e = self._word_end(QTextCursor(cur))
                end = e.position() + 1  # word-end motion is inclusive

        lo, hi = min(start, end), max(start, end)

        # inclusive motions (e, $) extend by one char, approximating vim
        if text in ("e", "$"):
            hi = min(hi + 1, len(self.toPlainText()))

        sel = QTextCursor(self.document())
        sel.setPosition(lo)
        sel.setPosition(hi, QTextCursor.MoveMode.KeepAnchor)
        cut_text = sel.selectedText()

        sel.beginEditBlock()
        if op in ("d", "c"):
            self._clipboard_text = cut_text
            self._clipboard_is_line = False
            sel.removeSelectedText()
        elif op == "y":
            self._clipboard_text = cut_text
            self._clipboard_is_line = False
            sel.setPosition(lo)
        sel.endEditBlock()
        self.setTextCursor(sel)

        self._pending_op = None
        self._pending_count = ""

        if op == "c":
            self.set_mode(Mode.INSERT)

    def _apply_linewise_operator(self, op, count):
        cur = self.textCursor()
        start_block = cur.block()
        start_pos = start_block.position()
        original_line_number = start_block.blockNumber()
        original_col = cur.positionInBlock()

        end_block = start_block
        for _ in range(count - 1):
            if end_block.next().isValid():
                end_block = end_block.next()

        end_pos = end_block.position() + end_block.length() - 1
        is_last_block = not end_block.next().isValid()
        has_preceding_block = start_block.previous().isValid()
        # For delete/yank, deleting through the true end of a multi-line
        # document should absorb the separator preceding start_block
        # rather than try to include one after end_block (there isn't
        # one), or a phantom empty trailing block is left behind. Change
        # ("c") keeps the original framing since it re-inserts a fresh
        # line to type into anyway.
        absorb_preceding = is_last_block and has_preceding_block and op != "c"

        sel = QTextCursor(self.document())
        if absorb_preceding:
            prev_block = start_block.previous()
            sel.setPosition(prev_block.position() + prev_block.length() - 1)
            sel.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
            trailing_separator_consumed = False
        else:
            sel.setPosition(start_pos)
            trailing_separator_consumed = not is_last_block
            sel.setPosition(
                end_pos + (1 if trailing_separator_consumed else 0),
                QTextCursor.MoveMode.KeepAnchor,
            )
        text = sel.selectedText()
        # normalize: the "absorb preceding separator" branch picks up a
        # leading paragraph separator that isn't part of the yanked/cut
        # lines themselves — strip it back off before it reaches the
        # clipboard or gets counted as content.
        if absorb_preceding and text.startswith("\u2029"):
            text = text[1:]

        sel.beginEditBlock()
        if op in ("d", "c"):
            self._clipboard_text = text.replace("\u2029", "\n")
            self._clipboard_is_line = True
            sel.removeSelectedText()
            if op == "c" and trailing_separator_consumed:
                # The deleted range swallowed the separator that used to
                # give our line its own block, so there's nothing left to
                # type into until we insert one back.
                sel.insertText("\n")
                sel.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(sel)
        elif op == "y":
            self._clipboard_text = text.replace("\u2029", "\n")
            self._clipboard_is_line = True
            # yanking must not move the cursor
            restore = QTextCursor(self.document())
            restore_block = self.document().findBlockByNumber(min(original_line_number, self.document().blockCount() - 1))
            restore.setPosition(restore_block.position() + min(original_col, max(0, restore_block.length() - 1)))
            self.setTextCursor(restore)
        sel.endEditBlock()

        if op == "c":
            self.set_mode(Mode.INSERT)

    def _paste(self, after: bool, count: int):
        if not self._clipboard_text:
            return
        cur = self.textCursor()
        cur.beginEditBlock()
        if self._clipboard_is_line:
            text = self._clipboard_text
            if not text.endswith("\n"):
                text += "\n"
            payload = text * count

            if after:
                cur.movePosition(QTextCursor.MoveOperation.EndOfLine)
                if cur.atEnd():
                    # last line of the document has no trailing newline of
                    # its own yet, so paste "\n" + lines, minus the final
                    # newline (so we don't leave an extra blank line)
                    cur.insertText("\n" + payload.rstrip("\n"))
                else:
                    cur.movePosition(QTextCursor.MoveOperation.Right)
                    cur.insertText(payload)
            else:
                cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
                cur.insertText(payload)
        else:
            if after and not self._at_end_of_line(cur):
                cur.movePosition(QTextCursor.MoveOperation.Right)
            for _ in range(count):
                cur.insertText(self._clipboard_text)
        cur.endEditBlock()
        self.setTextCursor(cur)
