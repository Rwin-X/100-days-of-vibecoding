"""
Syntax highlighting for Vedit, using Pygments' lexers for token
classification and mapping tokens onto the active theme's syntax colors.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from pygments.lexers import get_lexer_for_filename, guess_lexer, TextLexer
from pygments.util import ClassNotFound
from pygments.token import (
    Token, Keyword, Name, String, Comment, Number, Operator, Punctuation,
    Literal, Generic
)


def _lexer_for(filepath: str, sample_text: str):
    if filepath:
        try:
            return get_lexer_for_filename(filepath, stripnl=False)
        except ClassNotFound:
            pass
    if sample_text.strip():
        try:
            return guess_lexer(sample_text)
        except ClassNotFound:
            pass
    return TextLexer(stripnl=False)


class PygmentsHighlighter(QSyntaxHighlighter):
    def __init__(self, document, theme: dict, filepath: str = "", editor=None):
        super().__init__(document)
        self.theme = theme
        self.filepath = filepath
        self.editor = editor  # optional: the QPlainTextEdit, used to
        # suppress false-dirty textChanged signals during rehighlight
        self._lexer = None
        self._formats = {}
        self._build_formats()
        self.set_filepath(filepath)

    def set_theme(self, theme: dict):
        self.theme = theme
        self._build_formats()
        self._rehighlight_quietly()

    def set_filepath(self, filepath: str):
        self.filepath = filepath
        sample = self.document().toPlainText()[:2000]
        self._lexer = _lexer_for(filepath, sample)
        self._rehighlight_quietly()

    def _rehighlight_quietly(self):
        """Rehighlight without letting it appear as a document edit.

        QSyntaxHighlighter.rehighlight() touches block formatting, which
        makes QPlainTextEdit's textChanged fire even though no actual text
        changed. That would incorrectly mark a just-saved/just-loaded
        buffer as dirty, so we block the editor's signals for the duration.
        """
        blocked = False
        if self.editor is not None:
            blocked = self.editor.blockSignals(True)
        try:
            self.rehighlight()
        finally:
            if self.editor is not None:
                self.editor.blockSignals(blocked)

    def _build_formats(self):
        colors = self.theme["syntax"]

        def fmt(color_key, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(colors.get(color_key, self.theme["fg"])))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            if italic:
                f.setFontItalic(True)
            return f

        self._formats = {
            Keyword: fmt("keyword", bold=True),
            Keyword.Constant: fmt("constant"),
            Keyword.Declaration: fmt("keyword", bold=True),
            Keyword.Namespace: fmt("keyword", bold=True),
            Name.Builtin: fmt("builtin"),
            Name.Builtin.Pseudo: fmt("builtin"),
            Name.Function: fmt("function"),
            Name.Class: fmt("class", bold=True),
            Name.Decorator: fmt("function"),
            Name.Tag: fmt("tag"),
            Name.Attribute: fmt("attribute"),
            Name.Exception: fmt("class"),
            Name.Constant: fmt("constant"),
            String: fmt("string"),
            String.Doc: fmt("comment", italic=True),
            Comment: fmt("comment", italic=True),
            Comment.Preproc: fmt("keyword"),
            Number: fmt("number"),
            Operator: fmt("operator"),
            Operator.Word: fmt("keyword", bold=True),
            Punctuation: fmt("operator"),
            Generic.Deleted: fmt("keyword"),
            Generic.Inserted: fmt("string"),
        }

    def _lookup(self, token_type) -> QTextCharFormat | None:
        t = token_type
        while t is not None:
            if t in self._formats:
                return self._formats[t]
            t = t.parent
        return None

    def highlightBlock(self, text: str):
        """Lex just this block's text in isolation.

        Pygments lexers aren't built for incremental per-line state
        tracking, so this re-lexes each line independently. This gets
        single-line constructs (keywords, strings, numbers, comments)
        right, which covers the common case; constructs that span
        multiple lines (e.g. unterminated triple-quoted strings) may
        not highlight perfectly across the boundary.
        """
        if self._lexer is None:
            return
        try:
            tokens = self._lexer.get_tokens(text)
        except Exception:
            return

        pos = 0
        for token_type, value in tokens:
            length = len(value)
            if not value or value == "\n":
                pos += length
                continue
            fmt = self._lookup(token_type)
            if fmt is not None and length > 0:
                self.setFormat(pos, min(length, len(text) - pos), fmt)
            pos += length
