"""
CRYPTOLOCK - Minimal AES-256-GCM File Encryption Tool
Single-purpose, fast, no-frills GUI encryptor.
"""

import sys
import os
import secrets
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# --- Constants -------------------------------------------------------------

SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32          # AES-256
KDF_ITERATIONS = 480_000
MAGIC = b"CLK1"        # file format tag
EXT = ".clk"

BG = "#0a0e0a"
FG = "#00ff9c"
FG_DIM = "#0a7a52"
ACCENT = "#00ff9c"
ERROR = "#ff4d4d"
FONT_FAMILY = "JetBrains Mono"


# --- Crypto core -------------------------------------------------------------

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_file(path: Path, password: str) -> Path:
    data = path.read_bytes()
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    key = derive_key(password, salt)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)

    out_path = path.with_suffix(path.suffix + EXT)
    out_path.write_bytes(MAGIC + salt + nonce + ciphertext)
    return out_path


def decrypt_file(path: Path, password: str) -> Path:
    blob = path.read_bytes()
    if blob[:4] != MAGIC:
        raise ValueError("Not a valid CLK file")

    salt = blob[4:4 + SALT_SIZE]
    nonce = blob[4 + SALT_SIZE:4 + SALT_SIZE + NONCE_SIZE]
    ciphertext = blob[4 + SALT_SIZE + NONCE_SIZE:]

    key = derive_key(password, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    if path.suffix == EXT:
        out_path = path.with_suffix("")
    else:
        out_path = path.with_name(path.stem + ".dec" + path.suffix)
    out_path.write_bytes(plaintext)
    return out_path


# --- UI -------------------------------------------------------------

class CryptoLock(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_path: Path | None = None
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("CRYPTOLOCK")
        self.setFixedSize(420, 300)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {BG};
                color: {FG};
                font-family: '{FONT_FAMILY}';
            }}
            QLineEdit {{
                background-color: #0f140f;
                border: 1px solid {FG_DIM};
                border-radius: 3px;
                padding: 8px;
                color: {FG};
                font-family: '{FONT_FAMILY}';
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid {FG_DIM};
                border-radius: 3px;
                padding: 10px;
                color: {FG};
                font-family: '{FONT_FAMILY}';
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                border: 1px solid {ACCENT};
                background-color: #0f1f17;
            }}
            QPushButton:pressed {{
                background-color: #142a1f;
            }}
            QPushButton:disabled {{
                color: {FG_DIM};
                border: 1px solid #1a2a20;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("CRYPTOLOCK")
        title.setFont(QFont(FONT_FAMILY, 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT}; letter-spacing: 3px;")
        layout.addWidget(title)

        subtitle = QLabel("AES-256-GCM // single file")
        subtitle.setStyleSheet(f"color: {FG_DIM}; font-size: 10px;")
        layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {FG_DIM}; max-height: 1px; border: none;")
        layout.addWidget(sep)

        # File select row
        file_row = QHBoxLayout()
        self.file_label = QLabel("no file selected")
        self.file_label.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        self.file_label.setWordWrap(True)
        browse_btn = QPushButton("BROWSE")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Password field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.encrypt_btn = QPushButton("ENCRYPT")
        self.encrypt_btn.clicked.connect(self.do_encrypt)
        self.decrypt_btn = QPushButton("DECRYPT")
        self.decrypt_btn.clicked.connect(self.do_decrypt)
        btn_row.addWidget(self.encrypt_btn)
        btn_row.addWidget(self.decrypt_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    # --- actions ---

    def browse_file(self):
        path_str, _ = QFileDialog.getOpenFileName(self, "Select file")
        if path_str:
            self.selected_path = Path(path_str)
            self.file_label.setText(self.selected_path.name)
            self.file_label.setStyleSheet(f"color: {FG}; font-size: 11px;")

    def set_status(self, msg: str, error: bool = False):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(f"color: {ERROR if error else ACCENT}; font-size: 11px;")

    def do_encrypt(self):
        if not self._validate():
            return
        try:
            out = encrypt_file(self.selected_path, self.password_input.text())
            self.set_status(f"encrypted -> {out.name}")
        except Exception as e:
            self.set_status(f"error: {e}", error=True)

    def do_decrypt(self):
        if not self._validate():
            return
        try:
            out = decrypt_file(self.selected_path, self.password_input.text())
            self.set_status(f"decrypted -> {out.name}")
        except Exception as e:
            self.set_status(f"error: wrong password or corrupt file", error=True)

    def _validate(self) -> bool:
        if self.selected_path is None:
            self.set_status("error: no file selected", error=True)
            return False
        if not self.password_input.text():
            self.set_status("error: password required", error=True)
            return False
        return True


def main():
    app = QApplication(sys.argv)
    window = CryptoLock()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
