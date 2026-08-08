"""
QR Live — minimal desktop QR code generator.

Type text on the left, see the QR code update live on the right.
"""

import sys
import io

import qrcode
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QTextEdit,
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

BG = "#0b0b0c"
PANEL = "#111113"
BORDER = "#232326"
TEXT = "#ededee"
MUTED = "#7a7a80"

QR_BOX_SIZE = 260
QR_IMAGE_SIZE = 220


class QRLive(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QR Live")
        self.resize(760, 480)
        self.setStyleSheet(f"background-color: {BG};")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- left panel: text input ----
        left = QWidget()
        left.setStyleSheet(f"border-right: 1px solid {BORDER};")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(40, 40, 40, 40)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        label = QLabel("TEXT")
        label.setStyleSheet(f"color: {MUTED}; letter-spacing: 2px;")
        label.setFont(QFont("JetBrains Mono", 10))
        left_layout.addWidget(label)
        left_layout.addSpacing(10)

        self.input = QTextEdit()
        self.input.setPlaceholderText("Type your text here...")
        self.input.setFont(QFont("JetBrains Mono", 11))
        self.input.setFixedHeight(220)
        self.input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 16px;
            }}
            QTextEdit:focus {{
                border: 1px solid #3a3a3f;
            }}
        """)
        self.input.textChanged.connect(self.render_qr)
        left_layout.addWidget(self.input)

        root.addWidget(left, 1)

        # ---- right panel: QR code ----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_box = QLabel("QR CODE")
        self.qr_box.setFixedSize(QR_BOX_SIZE, QR_BOX_SIZE)
        self.qr_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_box.setFont(QFont("JetBrains Mono", 10))
        self._set_empty_style()
        right_layout.addWidget(self.qr_box)

        self.meta = QLabel("")
        self.meta.setStyleSheet(f"color: {MUTED}; margin-top: 14px;")
        self.meta.setFont(QFont("JetBrains Mono", 9))
        self.meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.meta)

        root.addWidget(right, 1)

    def _set_empty_style(self):
        self.qr_box.setText("QR CODE")
        self.qr_box.setPixmap(QPixmap())
        self.qr_box.setStyleSheet(f"""
            background-color: {PANEL};
            color: {MUTED};
            border: 1px dashed {BORDER};
            border-radius: 8px;
        """)

    def render_qr(self):
        text = self.input.toPlainText()

        if not text.strip():
            self._set_empty_style()
            self.meta.setText("")
            return

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buf.getvalue())
        pixmap = pixmap.scaled(
            QR_IMAGE_SIZE,
            QR_IMAGE_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.qr_box.setStyleSheet("background-color: #ffffff; border-radius: 8px;")
        self.qr_box.setPixmap(pixmap)
        self.meta.setText(f"{len(text)} chars")


def main():
    app = QApplication(sys.argv)
    window = QRLive()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
