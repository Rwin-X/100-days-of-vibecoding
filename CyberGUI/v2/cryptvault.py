#!/usr/bin/env python3
"""
CryptVault - A GUI Cryptography Suite
======================================
Text and file encryption/decryption, password-based key derivation,
hashing utilities, and a password generator, all in one desktop app.

Ciphers:    AES-256-GCM, AES-256-CBC, ChaCha20-Poly1305
KDF:        Argon2id (default), PBKDF2-HMAC-SHA256, scrypt
Hashing:    MD5, SHA-1, SHA-256, SHA-512, BLAKE2b

Author: black8arch / devforge
"""

import sys
import os
import base64
import hashlib
import secrets
import string
import struct
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QComboBox, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QCheckBox, QSpinBox, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Protocol.KDF import PBKDF2, scrypt as scrypt_kdf
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

from argon2.low_level import hash_secret_raw, Type as Argon2Type


# ──────────────────────────────────────────────────────────────────────
#  Theme — minimal, with a dark / light (white) mode toggle
# ──────────────────────────────────────────────────────────────────────

THEMES = {
    "dark": dict(
        bg="#0b0f0d", panel="#0f1613", input_bg="#121a16",
        text="#dcefe4", accent="#39ff8f", accent_dim="#1f8a53",
        muted="#6b8578", border="#1d2c24", danger="#ff6b6b",
    ),
    "light": dict(
        bg="#ffffff", panel="#f6f8f7", input_bg="#ffffff",
        text="#1a231e", accent="#178a4c", accent_dim="#e4f3ea",
        muted="#7a8c82", border="#e1e6e3", danger="#d43d3d",
    ),
}


def build_stylesheet(mode: str) -> str:
    c = THEMES[mode]
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
}}

QTabWidget::pane {{
    border: none;
    border-top: 1px solid {c['border']};
    background-color: {c['bg']};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {c['muted']};
    border: none;
    padding: 10px 16px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    color: {c['accent']};
    border-bottom: 2px solid {c['accent']};
}}

QLineEdit, QPlainTextEdit {{
    background-color: {c['input_bg']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 7px;
    selection-background-color: {c['accent']};
    selection-color: {c['bg']};
}}

QLineEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {c['accent']};
}}

QLineEdit:read-only {{
    color: {c['muted']};
}}

QPushButton {{
    background-color: transparent;
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 8px 14px;
    font-weight: 600;
}}

QPushButton:hover {{
    border: 1px solid {c['accent']};
    color: {c['accent']};
}}

QPushButton:pressed {{
    background-color: {c['accent_dim']};
}}

QPushButton:disabled {{
    color: {c['muted']};
    border: 1px solid {c['border']};
}}

QPushButton#primaryBtn {{
    background-color: {c['accent']};
    color: {'#08110d' if mode == 'dark' else '#ffffff'};
    border: 1px solid {c['accent']};
}}
QPushButton#primaryBtn:hover {{
    background-color: {c['accent']};
    opacity: 0.9;
}}

QPushButton#flatBtn {{
    border: none;
    color: {c['muted']};
    padding: 6px 10px;
}}
QPushButton#flatBtn:hover {{
    color: {c['accent']};
    border: none;
}}

QToolButton {{
    color: {c['muted']};
    border: none;
    padding: 4px 8px;
    font-size: 10px;
}}
QToolButton:checked {{ color: {c['accent']}; }}
QToolButton:hover {{ color: {c['accent']}; }}

QComboBox {{
    background-color: {c['input_bg']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 6px;
}}
QComboBox:hover {{ border: 1px solid {c['accent']}; }}
QComboBox QAbstractItemView {{
    background-color: {c['panel']};
    color: {c['text']};
    selection-background-color: {c['accent']};
    selection-color: {c['bg']};
    border: 1px solid {c['border']};
}}

QSpinBox {{
    background-color: {c['input_bg']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 4px;
}}

QCheckBox {{ color: {c['text']}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {c['border']};
    border-radius: 3px;
    background-color: {c['input_bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border: 1px solid {c['accent']};
}}

QProgressBar {{
    border: 1px solid {c['border']};
    border-radius: 4px;
    text-align: center;
    color: {c['text']};
    background-color: {c['input_bg']};
    height: 6px;
}}
QProgressBar::chunk {{
    background-color: {c['accent']};
    border-radius: 4px;
}}

QLabel#header {{ color: {c['text']}; font-size: 16px; font-weight: 700; }}
QLabel#subheader {{ color: {c['muted']}; font-size: 10px; }}
QLabel#fieldLabel {{ color: {c['muted']}; font-size: 10.5px; font-weight: 600; }}
QLabel#statusOk {{ color: {c['accent']}; }}
QLabel#statusErr {{ color: {c['danger']}; }}
QLabel#muted {{ color: {c['muted']}; }}
QLabel#resultBig {{ color: {c['accent']}; font-size: 15px; }}

QFrame#divider {{ background-color: {c['border']}; max-height: 1px; }}

QScrollBar:vertical {{ background: transparent; width: 8px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {c['accent_dim']}; }}
"""


# ──────────────────────────────────────────────────────────────────────
#  Crypto backend (unchanged logic — battle-tested)
# ──────────────────────────────────────────────────────────────────────

MAGIC = b"CVLT"
FORMAT_VERSION = 2

KDF_ARGON2 = "argon2id"
KDF_PBKDF2 = "pbkdf2"
KDF_SCRYPT = "scrypt"

CIPHER_AES_GCM = "AES-256-GCM"
CIPHER_AES_CBC = "AES-256-CBC"
CIPHER_CHACHA = "ChaCha20-Poly1305"

KDF_IDS = {KDF_ARGON2: 1, KDF_PBKDF2: 2, KDF_SCRYPT: 3}
KDF_NAMES = {v: k for k, v in KDF_IDS.items()}

CIPHER_IDS = {CIPHER_AES_GCM: 1, CIPHER_AES_CBC: 2, CIPHER_CHACHA: 3}
CIPHER_NAMES = {v: k for k, v in CIPHER_IDS.items()}


class CryptoError(Exception):
    pass


def derive_key(password: bytes, salt: bytes, kdf: str, key_len: int = 32) -> bytes:
    if kdf == KDF_ARGON2:
        return hash_secret_raw(
            secret=password, salt=salt, time_cost=3, memory_cost=65536,
            parallelism=4, hash_len=key_len, type=Argon2Type.ID,
        )
    elif kdf == KDF_PBKDF2:
        return PBKDF2(password, salt, dkLen=key_len, count=600_000, hmac_hash_module=SHA256)
    elif kdf == KDF_SCRYPT:
        return scrypt_kdf(password, salt, key_len=key_len, N=2**17, r=8, p=1)
    else:
        raise CryptoError(f"Unknown KDF: {kdf}")


def encrypt_bytes(plaintext: bytes, password: str, cipher_name: str, kdf_name: str,
                   aad: bytes = b"") -> bytes:
    salt = get_random_bytes(16)
    key = derive_key(password.encode("utf-8"), salt, kdf_name)

    if cipher_name == CIPHER_AES_GCM:
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        ct, tag = cipher.encrypt_and_digest(plaintext)

    elif cipher_name == CIPHER_AES_CBC:
        nonce = get_random_bytes(16)
        pad_len = 16 - (len(plaintext) % 16)
        padded = plaintext + bytes([pad_len]) * pad_len
        cipher = AES.new(key, AES.MODE_CBC, iv=nonce)
        ct = cipher.encrypt(padded)
        import hmac as _hmac
        tag = _hmac.new(key, nonce + ct, hashlib.sha256).digest()

    elif cipher_name == CIPHER_CHACHA:
        nonce = get_random_bytes(12)
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        if aad:
            cipher.update(aad)
        ct, tag = cipher.encrypt_and_digest(plaintext)

    else:
        raise CryptoError(f"Unknown cipher: {cipher_name}")

    out = bytearray()
    out += MAGIC
    out += bytes([FORMAT_VERSION])
    out += bytes([CIPHER_IDS[cipher_name]])
    out += bytes([KDF_IDS[kdf_name]])
    out += bytes([len(salt)])
    out += salt
    out += bytes([len(nonce)])
    out += nonce
    out += bytes([len(tag)])
    out += tag
    out += ct
    return bytes(out)


def decrypt_bytes(blob: bytes, password: str, aad: bytes = b"") -> bytes:
    if blob[:4] != MAGIC:
        raise CryptoError("Not a CryptVault file (bad magic bytes).")
    pos = 4
    version = blob[pos]; pos += 1
    if version != FORMAT_VERSION:
        raise CryptoError(f"Unsupported format version: {version}")
    cipher_id = blob[pos]; pos += 1
    kdf_id = blob[pos]; pos += 1
    salt_len = blob[pos]; pos += 1
    salt = blob[pos:pos+salt_len]; pos += salt_len
    nonce_len = blob[pos]; pos += 1
    nonce = blob[pos:pos+nonce_len]; pos += nonce_len
    tag_len = blob[pos]; pos += 1
    tag = blob[pos:pos+tag_len]; pos += tag_len
    ct = blob[pos:]

    cipher_name = CIPHER_NAMES.get(cipher_id)
    kdf_name = KDF_NAMES.get(kdf_id)
    if cipher_name is None or kdf_name is None:
        raise CryptoError("Unrecognized cipher/KDF identifier in file.")

    key = derive_key(password.encode("utf-8"), bytes(salt), kdf_name)

    try:
        if cipher_name == CIPHER_AES_GCM:
            cipher = AES.new(key, AES.MODE_GCM, nonce=bytes(nonce))
            if aad:
                cipher.update(aad)
            pt = cipher.decrypt_and_verify(bytes(ct), bytes(tag))

        elif cipher_name == CIPHER_AES_CBC:
            import hmac as _hmac
            expected_tag = _hmac.new(key, bytes(nonce) + bytes(ct), hashlib.sha256).digest()
            if not _hmac.compare_digest(expected_tag, bytes(tag)):
                raise CryptoError("Authentication failed — wrong password or corrupted data.")
            cipher = AES.new(key, AES.MODE_CBC, iv=bytes(nonce))
            padded = cipher.decrypt(bytes(ct))
            pad_len = padded[-1]
            if pad_len < 1 or pad_len > 16:
                raise CryptoError("Authentication failed — wrong password or corrupted data.")
            pt = padded[:-pad_len]

        elif cipher_name == CIPHER_CHACHA:
            cipher = ChaCha20_Poly1305.new(key=key, nonce=bytes(nonce))
            if aad:
                cipher.update(aad)
            pt = cipher.decrypt_and_verify(bytes(ct), bytes(tag))

        else:
            raise CryptoError(f"Unknown cipher id: {cipher_id}")

    except CryptoError:
        raise
    except ValueError:
        raise CryptoError("Authentication failed — wrong password or corrupted data.")

    return pt


def compute_hash(data: bytes, algo: str) -> str:
    algo = algo.lower()
    if algo == "md5":
        h = hashlib.md5(data)
    elif algo in ("sha-1", "sha1"):
        h = hashlib.sha1(data)
    elif algo in ("sha-256", "sha256"):
        h = hashlib.sha256(data)
    elif algo in ("sha-512", "sha512"):
        h = hashlib.sha512(data)
    elif algo == "blake2b":
        h = hashlib.blake2b(data)
    else:
        raise CryptoError(f"Unknown hash algorithm: {algo}")
    return h.hexdigest()


def generate_password(length: int, use_upper: bool, use_lower: bool,
                       use_digits: bool, use_symbols: bool,
                       exclude_ambiguous: bool = False) -> str:
    pool = ""
    if use_upper:
        pool += string.ascii_uppercase
    if use_lower:
        pool += string.ascii_lowercase
    if use_digits:
        pool += string.digits
    if use_symbols:
        pool += "!@#$%^&*()-_=+[]{};:,.<>?/~"
    if not pool:
        raise CryptoError("Select at least one character set.")
    if exclude_ambiguous:
        for ch in "il1LoO0|":
            pool = pool.replace(ch, "")
    return "".join(secrets.choice(pool) for _ in range(length))


def estimate_strength(password: str) -> tuple[str, str]:
    if not password:
        return "—", "muted"
    pool = 0
    if any(c.islower() for c in password):
        pool += 26
    if any(c.isupper() for c in password):
        pool += 26
    if any(c.isdigit() for c in password):
        pool += 10
    if any(not c.isalnum() for c in password):
        pool += 32
    if pool == 0:
        pool = 1
    import math
    bits = len(password) * math.log2(pool)
    if bits < 40:
        return f"Weak · {bits:.0f} bits", "statusErr"
    elif bits < 65:
        return f"Fair · {bits:.0f} bits", "statusErr"
    elif bits < 90:
        return f"Strong · {bits:.0f} bits", "statusOk"
    else:
        return f"Very strong · {bits:.0f} bits", "statusOk"


# ──────────────────────────────────────────────────────────────────────
#  Background worker for file operations
# ──────────────────────────────────────────────────────────────────────

class FileCryptoWorker(QThread):
    finished_ok = pyqtSignal(str, float)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, mode, in_path, out_path, password, cipher_name, kdf_name):
        super().__init__()
        self.mode = mode
        self.in_path = in_path
        self.out_path = out_path
        self.password = password
        self.cipher_name = cipher_name
        self.kdf_name = kdf_name

    def run(self):
        try:
            t0 = time.time()
            self.progress.emit(10)
            with open(self.in_path, "rb") as f:
                data = f.read()
            self.progress.emit(40)

            if self.mode == "encrypt":
                original_name = os.path.basename(self.in_path).encode("utf-8")
                aad = struct.pack(">H", len(original_name)) + original_name
                blob = encrypt_bytes(data, self.password, self.cipher_name, self.kdf_name, aad=aad)
                full = struct.pack(">H", len(original_name)) + original_name + blob
                self.progress.emit(80)
                with open(self.out_path, "wb") as f:
                    f.write(full)
            else:
                name_len = struct.unpack(">H", data[:2])[0]
                original_name = data[2:2+name_len]
                blob = data[2+name_len:]
                aad = struct.pack(">H", len(original_name)) + original_name
                pt = decrypt_bytes(blob, self.password, aad=aad)
                self.progress.emit(80)
                with open(self.out_path, "wb") as f:
                    f.write(pt)

            self.progress.emit(100)
            elapsed = time.time() - t0
            self.finished_ok.emit(self.out_path, elapsed)
        except CryptoError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"Unexpected error: {e}")


# ──────────────────────────────────────────────────────────────────────
#  UI helpers
# ──────────────────────────────────────────────────────────────────────

def make_password_field(placeholder="Password") -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    return field


def make_reveal_button(target: QLineEdit) -> QToolButton:
    btn = QToolButton()
    btn.setText("show")
    btn.setCheckable(True)

    def toggle():
        if btn.isChecked():
            target.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("hide")
        else:
            target.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("show")

    btn.clicked.connect(toggle)
    return btn


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


def field_label(text: str) -> QLabel:
    return QLabel(text, objectName="fieldLabel")


class AdvancedRow(QWidget):
    """Collapsed-by-default cipher/KDF picker to keep the default view minimal."""

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self.toggle_btn = QPushButton("Advanced ▾")
        self.toggle_btn.setObjectName("flatBtn")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._on_toggle)
        outer.addWidget(self.toggle_btn)

        self.panel = QWidget()
        row = QHBoxLayout(self.panel)
        row.setContentsMargins(0, 2, 0, 4)
        row.addWidget(field_label("Cipher"))
        self.cipher_combo = QComboBox()
        self.cipher_combo.addItems([CIPHER_AES_GCM, CIPHER_CHACHA, CIPHER_AES_CBC])
        row.addWidget(self.cipher_combo)
        row.addSpacing(12)
        row.addWidget(field_label("KDF"))
        self.kdf_combo = QComboBox()
        self.kdf_combo.addItems([KDF_ARGON2, KDF_SCRYPT, KDF_PBKDF2])
        row.addWidget(self.kdf_combo)
        row.addStretch()
        self.panel.setVisible(False)
        outer.addWidget(self.panel)

    def _on_toggle(self):
        expanded = self.toggle_btn.isChecked()
        self.panel.setVisible(expanded)
        self.toggle_btn.setText("Advanced ▴" if expanded else "Advanced ▾")

    @property
    def cipher(self):
        return self.cipher_combo.currentText()

    @property
    def kdf(self):
        return self.kdf_combo.currentText()


# ──────────────────────────────────────────────────────────────────────
#  Tab 1 — Text
# ──────────────────────────────────────────────────────────────────────

class TextCryptoTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 18)

        pw_row = QHBoxLayout()
        self.password_field = make_password_field()
        pw_row.addWidget(self.password_field)
        pw_row.addWidget(make_reveal_button(self.password_field))
        layout.addLayout(pw_row)

        self.advanced = AdvancedRow()
        layout.addWidget(self.advanced)

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText("Plaintext to encrypt, or Base64 ciphertext to decrypt...")
        self.input_text.setMinimumHeight(130)
        layout.addWidget(self.input_text)

        btn_row = QHBoxLayout()
        self.encrypt_btn = QPushButton("Encrypt")
        self.encrypt_btn.setObjectName("primaryBtn")
        self.decrypt_btn = QPushButton("Decrypt")
        self.swap_btn = QPushButton("Swap")
        self.swap_btn.setObjectName("flatBtn")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("flatBtn")
        btn_row.addWidget(self.encrypt_btn)
        btn_row.addWidget(self.decrypt_btn)
        btn_row.addWidget(self.swap_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(130)
        self.output_text.setPlaceholderText("Output appears here")
        layout.addWidget(self.output_text)

        out_row = QHBoxLayout()
        self.status_label = QLabel("")
        out_row.addWidget(self.status_label)
        out_row.addStretch()
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("flatBtn")
        out_row.addWidget(self.copy_btn)
        layout.addLayout(out_row)

        self.encrypt_btn.clicked.connect(self.do_encrypt)
        self.decrypt_btn.clicked.connect(self.do_decrypt)
        self.clear_btn.clicked.connect(self.do_clear)
        self.swap_btn.clicked.connect(self.do_swap)
        self.copy_btn.clicked.connect(self.do_copy)

    def set_status(self, text, kind="statusOk"):
        self.status_label.setText(text)
        self.status_label.setObjectName(kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def do_encrypt(self):
        password = self.password_field.text()
        plaintext = self.input_text.toPlainText()
        if not password:
            self.set_status("Password required.", "statusErr")
            return
        if not plaintext:
            self.set_status("Input is empty.", "statusErr")
            return
        try:
            blob = encrypt_bytes(plaintext.encode("utf-8"), password,
                                  self.advanced.cipher, self.advanced.kdf)
            b64 = base64.b64encode(blob).decode("ascii")
            self.output_text.setPlainText(b64)
            self.set_status(f"Encrypted · {self.advanced.cipher}", "statusOk")
        except Exception as e:
            self.set_status(f"Encryption failed: {e}", "statusErr")

    def do_decrypt(self):
        password = self.password_field.text()
        ciphertext_b64 = self.input_text.toPlainText().strip()
        if not password:
            self.set_status("Password required.", "statusErr")
            return
        if not ciphertext_b64:
            self.set_status("Input is empty.", "statusErr")
            return
        try:
            blob = base64.b64decode(ciphertext_b64)
        except Exception:
            self.set_status("Input is not valid Base64.", "statusErr")
            return
        try:
            pt = decrypt_bytes(blob, password)
            self.output_text.setPlainText(pt.decode("utf-8", errors="replace"))
            self.set_status("Decrypted.", "statusOk")
        except CryptoError as e:
            self.set_status(str(e), "statusErr")
        except Exception as e:
            self.set_status(f"Decryption failed: {e}", "statusErr")

    def do_clear(self):
        self.input_text.clear()
        self.output_text.clear()
        self.set_status("")

    def do_swap(self):
        i, o = self.input_text.toPlainText(), self.output_text.toPlainText()
        self.input_text.setPlainText(o)
        self.output_text.setPlainText(i)

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.set_status("Copied.", "statusOk")


# ──────────────────────────────────────────────────────────────────────
#  Tab 2 — File
# ──────────────────────────────────────────────────────────────────────

class FileCryptoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 18)

        file_row = QHBoxLayout()
        self.file_path_field = QLineEdit()
        self.file_path_field.setReadOnly(True)
        self.file_path_field.setPlaceholderText("No file selected")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(self.file_path_field)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        pw_row = QHBoxLayout()
        self.password_field = make_password_field()
        pw_row.addWidget(self.password_field)
        pw_row.addWidget(make_reveal_button(self.password_field))
        layout.addLayout(pw_row)

        self.confirm_field = make_password_field("Confirm password (encrypt only)")
        layout.addWidget(self.confirm_field)

        self.advanced = AdvancedRow()
        layout.addWidget(self.advanced)

        btn_row = QHBoxLayout()
        self.encrypt_btn = QPushButton("Encrypt file")
        self.encrypt_btn.setObjectName("primaryBtn")
        self.decrypt_btn = QPushButton("Decrypt file")
        btn_row.addWidget(self.encrypt_btn)
        btn_row.addWidget(self.decrypt_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Select a file to begin.")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.encrypt_btn.clicked.connect(lambda: self.start_job("encrypt"))
        self.decrypt_btn.clicked.connect(lambda: self.start_job("decrypt"))

    def set_status(self, text, kind="muted"):
        self.status_label.setText(text)
        self.status_label.setObjectName(kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            self.file_path_field.setText(path)
            self.set_status(f"{os.path.basename(path)} · {os.path.getsize(path):,} bytes")

    def start_job(self, mode):
        in_path = self.file_path_field.text()
        password = self.password_field.text()

        if not in_path or not os.path.isfile(in_path):
            self.set_status("Select a valid file first.", "statusErr")
            return
        if not password:
            self.set_status("Password required.", "statusErr")
            return

        if mode == "encrypt":
            if password != self.confirm_field.text():
                self.set_status("Passwords do not match.", "statusErr")
                return
            default_out = in_path + ".cvlt"
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Save Encrypted File As", default_out, "CryptVault File (*.cvlt)")
        else:
            base = in_path[:-5] if in_path.endswith(".cvlt") else in_path + ".decrypted"
            out_path, _ = QFileDialog.getSaveFileName(self, "Save Decrypted File As", base)

        if not out_path:
            return

        self.set_controls_enabled(False)
        self.progress.setValue(0)
        self.set_status("Working...", "muted")

        self.worker = FileCryptoWorker(
            mode, in_path, out_path, password, self.advanced.cipher, self.advanced.kdf
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished_ok.connect(lambda p, t: self.on_success(mode, p, t))
        self.worker.failed.connect(self.on_failure)
        self.worker.start()

    def set_controls_enabled(self, enabled):
        self.encrypt_btn.setEnabled(enabled)
        self.decrypt_btn.setEnabled(enabled)

    def on_success(self, mode, out_path, elapsed):
        self.set_controls_enabled(True)
        verb = "Encrypted" if mode == "encrypt" else "Decrypted"
        self.set_status(f"{verb} → {out_path} · {elapsed:.2f}s", "statusOk")

    def on_failure(self, message):
        self.set_controls_enabled(True)
        self.progress.setValue(0)
        self.set_status(message, "statusErr")


# ──────────────────────────────────────────────────────────────────────
#  Tab 3 — Hash
# ──────────────────────────────────────────────────────────────────────

class HashTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 18)

        mode_row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Text", "File"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        self.compute_btn = QPushButton("Compute")
        self.compute_btn.setObjectName("primaryBtn")
        mode_row.addWidget(self.compute_btn)
        layout.addLayout(mode_row)

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Text to hash...")
        self.text_input.setMinimumHeight(100)
        layout.addWidget(self.text_input)

        file_row = QHBoxLayout()
        self.file_path_field = QLineEdit()
        self.file_path_field.setReadOnly(True)
        self.file_path_field.setPlaceholderText("No file selected")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(self.file_path_field)
        file_row.addWidget(self.browse_btn)
        self.file_path_field.setVisible(False)
        self.browse_btn.setVisible(False)
        layout.addLayout(file_row)

        layout.addWidget(divider())

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        self.hash_fields = {}
        for row, algo in enumerate(["MD5", "SHA-1", "SHA-256", "SHA-512", "BLAKE2b"]):
            grid.addWidget(field_label(algo), row, 0)
            field = QLineEdit()
            field.setReadOnly(True)
            grid.addWidget(field, row, 1)
            copy_btn = QPushButton("Copy")
            copy_btn.setObjectName("flatBtn")
            copy_btn.setFixedWidth(56)
            copy_btn.clicked.connect(lambda _, f=field: self.copy_field(f))
            grid.addWidget(copy_btn, row, 2)
            self.hash_fields[algo] = field
        layout.addLayout(grid)

        layout.addWidget(divider())

        verify_row = QHBoxLayout()
        self.verify_field = QLineEdit()
        self.verify_field.setPlaceholderText("Paste a hash to verify against")
        self.verify_result = QLabel("")
        verify_row.addWidget(self.verify_field)
        verify_row.addWidget(self.verify_result)
        self.verify_field.textChanged.connect(self.check_verify)
        layout.addLayout(verify_row)

        layout.addStretch()
        self.compute_btn.clicked.connect(self.compute)

    def on_mode_changed(self, text):
        is_file = (text == "File")
        self.text_input.setVisible(not is_file)
        self.file_path_field.setVisible(is_file)
        self.browse_btn.setVisible(is_file)

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Hash")
        if path:
            self.file_path_field.setText(path)

    def copy_field(self, field):
        if field.text():
            QApplication.clipboard().setText(field.text())

    def compute(self):
        if self.mode_combo.currentText() == "Text":
            data = self.text_input.toPlainText().encode("utf-8")
        else:
            path = self.file_path_field.text()
            if not path or not os.path.isfile(path):
                QMessageBox.warning(self, "No File", "Select a valid file first.")
                return
            with open(path, "rb") as f:
                data = f.read()

        for algo, field in self.hash_fields.items():
            field.setText(compute_hash(data, algo))
        self.check_verify()

    def check_verify(self):
        expected = self.verify_field.text().strip().lower()
        if not expected:
            self.verify_result.setText("")
            return
        match = any(field.text().lower() == expected for field in self.hash_fields.values())
        self.verify_result.setText("Match" if match else "No match")
        self.verify_result.setObjectName("statusOk" if match else "statusErr")
        self.verify_result.style().unpolish(self.verify_result)
        self.verify_result.style().polish(self.verify_result)


# ──────────────────────────────────────────────────────────────────────
#  Tab 4 — Password generator
# ──────────────────────────────────────────────────────────────────────

class PasswordGenTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 18)

        self.result_field = QLineEdit()
        self.result_field.setReadOnly(True)
        self.result_field.setObjectName("resultBig")
        layout.addWidget(self.result_field)

        strength_row = QHBoxLayout()
        self.strength_label = QLabel("—")
        strength_row.addWidget(self.strength_label)
        strength_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("flatBtn")
        copy_btn.clicked.connect(self.copy_password)
        strength_row.addWidget(copy_btn)
        layout.addLayout(strength_row)

        layout.addWidget(divider())

        len_row = QHBoxLayout()
        len_row.addWidget(field_label("Length"))
        self.length_spin = QSpinBox()
        self.length_spin.setRange(4, 128)
        self.length_spin.setValue(20)
        len_row.addWidget(self.length_spin)
        len_row.addStretch()
        layout.addLayout(len_row)

        check_row = QHBoxLayout()
        self.upper_check = QCheckBox("A-Z")
        self.upper_check.setChecked(True)
        self.lower_check = QCheckBox("a-z")
        self.lower_check.setChecked(True)
        self.digit_check = QCheckBox("0-9")
        self.digit_check.setChecked(True)
        self.symbol_check = QCheckBox("Symbols")
        self.symbol_check.setChecked(True)
        for w in (self.upper_check, self.lower_check, self.digit_check, self.symbol_check):
            check_row.addWidget(w)
        check_row.addStretch()
        layout.addLayout(check_row)

        self.ambig_check = QCheckBox("Exclude ambiguous characters (l, 1, I, O, 0)")
        layout.addWidget(self.ambig_check)

        gen_row = QHBoxLayout()
        gen_btn = QPushButton("Generate")
        gen_btn.setObjectName("primaryBtn")
        gen_btn.clicked.connect(self.generate)
        gen_row.addWidget(gen_btn)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        layout.addWidget(divider())

        pp_row = QHBoxLayout()
        pp_row.addWidget(field_label("Passphrase"))
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(3, 12)
        self.word_count_spin.setValue(5)
        pp_row.addWidget(self.word_count_spin)
        pp_row.addWidget(field_label("words"))
        pp_gen_btn = QPushButton("Generate")
        pp_gen_btn.clicked.connect(self.generate_passphrase)
        pp_row.addWidget(pp_gen_btn)
        pp_row.addStretch()
        layout.addLayout(pp_row)

        layout.addStretch()
        self.generate()

    def generate(self):
        try:
            pw = generate_password(
                self.length_spin.value(),
                self.upper_check.isChecked(),
                self.lower_check.isChecked(),
                self.digit_check.isChecked(),
                self.symbol_check.isChecked(),
                self.ambig_check.isChecked(),
            )
        except CryptoError as e:
            QMessageBox.warning(self, "Invalid Options", str(e))
            return
        self.result_field.setText(pw)
        self.update_strength(pw)

    def generate_passphrase(self):
        words = [
            "anchor", "basalt", "cinder", "delta", "ember", "falcon", "granite", "harbor",
            "ionize", "jasper", "kernel", "lumen", "magnet", "nebula", "onyx", "photon",
            "quartz", "raster", "shadow", "tundra", "umbra", "vertex", "willow", "xenon",
            "yonder", "zephyr", "cobalt", "dagger", "ferrite", "glacier", "helix", "ivory"
        ]
        n = self.word_count_spin.value()
        chosen = [secrets.choice(words) for _ in range(n)]
        chosen[secrets.randbelow(n)] = chosen[secrets.randbelow(n)].capitalize()
        pp = "-".join(chosen) + str(secrets.randbelow(100))
        self.result_field.setText(pp)
        self.update_strength(pp)

    def update_strength(self, pw):
        label, style_id = estimate_strength(pw)
        self.strength_label.setText(label)
        self.strength_label.setObjectName(style_id)
        self.strength_label.style().unpolish(self.strength_label)
        self.strength_label.style().polish(self.strength_label)

    def copy_password(self):
        if self.result_field.text():
            QApplication.clipboard().setText(self.result_field.text())


# ──────────────────────────────────────────────────────────────────────
#  Main window
# ──────────────────────────────────────────────────────────────────────

class CryptVaultWindow(QMainWindow):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.mode = "dark"
        self.setWindowTitle("CryptVault")
        self.resize(680, 640)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 14, 20, 14)
        title = QLabel("CryptVault")
        title.setObjectName("header")
        h_layout.addWidget(title)
        h_layout.addStretch()
        self.theme_btn = QPushButton("Light")
        self.theme_btn.setObjectName("flatBtn")
        self.theme_btn.clicked.connect(self.toggle_theme)
        h_layout.addWidget(self.theme_btn)
        outer.addWidget(header)
        outer.addWidget(divider())

        tabs = QTabWidget()
        tabs.addTab(TextCryptoTab(), "Text")
        tabs.addTab(FileCryptoTab(), "File")
        tabs.addTab(HashTab(), "Hash")
        tabs.addTab(PasswordGenTab(), "Password")
        outer.addWidget(tabs)

        self.apply_theme()

    def toggle_theme(self):
        self.mode = "light" if self.mode == "dark" else "dark"
        self.apply_theme()

    def apply_theme(self):
        self.app.setStyleSheet(build_stylesheet(self.mode))
        self.theme_btn.setText("Light" if self.mode == "dark" else "Dark")


def main():
    app = QApplication(sys.argv)
    window = CryptVaultWindow(app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
