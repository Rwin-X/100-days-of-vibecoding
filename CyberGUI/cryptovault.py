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
import json
import base64
import hashlib
import secrets
import string
import struct
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QPlainTextEdit,
    QComboBox, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QCheckBox, QSpinBox, QGroupBox, QFrame, QSlider, QSizePolicy,
    QToolButton, QStackedWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon, QClipboard, QAction

from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Protocol.KDF import PBKDF2, scrypt as scrypt_kdf
from Crypto.Hash import SHA256, SHA512
from Crypto.Random import get_random_bytes

from argon2.low_level import hash_secret_raw, Type as Argon2Type


# ──────────────────────────────────────────────────────────────────────
#  Theme — phosphor terminal aesthetic (devforge house style)
# ──────────────────────────────────────────────────────────────────────

BG_DARK      = "#0a0f0d"
BG_PANEL     = "#0f1613"
BG_INPUT     = "#0d1512"
FG_GREEN     = "#39ff8f"
FG_GREEN_DIM = "#1f8a53"
FG_CYAN      = "#3ee6e6"
FG_TEXT      = "#c9f7dd"
FG_MUTED     = "#5a7d6b"
BORDER       = "#1c3327"
DANGER       = "#ff5c5c"
WARN         = "#ffcc66"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {FG_TEXT};
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
}}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {BG_PANEL};
    top: -1px;
}}

QTabBar::tab {{
    background-color: {BG_DARK};
    color: {FG_MUTED};
    border: 1px solid {BORDER};
    padding: 8px 18px;
    margin-right: 2px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QTabBar::tab:selected {{
    background-color: {BG_PANEL};
    color: {FG_GREEN};
    border-bottom: 2px solid {FG_GREEN};
}}

QTabBar::tab:hover:!selected {{
    color: {FG_CYAN};
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 2px;
    margin-top: 12px;
    padding-top: 14px;
    color: {FG_CYAN};
    font-weight: bold;
    letter-spacing: 1px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {FG_CYAN};
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    color: {FG_GREEN};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 6px;
    selection-background-color: {FG_GREEN_DIM};
    selection-color: {BG_DARK};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {FG_GREEN};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    color: {FG_MUTED};
    background-color: {BG_DARK};
}}

QPushButton {{
    background-color: transparent;
    color: {FG_GREEN};
    border: 1px solid {FG_GREEN_DIM};
    border-radius: 2px;
    padding: 8px 16px;
    font-weight: bold;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    background-color: {FG_GREEN_DIM};
    color: {BG_DARK};
    border: 1px solid {FG_GREEN};
}}

QPushButton:pressed {{
    background-color: {FG_GREEN};
    color: {BG_DARK};
}}

QPushButton:disabled {{
    color: {FG_MUTED};
    border: 1px solid {BORDER};
}}

QPushButton#dangerBtn {{
    border: 1px solid {DANGER};
    color: {DANGER};
}}
QPushButton#dangerBtn:hover {{
    background-color: {DANGER};
    color: {BG_DARK};
}}

QPushButton#primaryBtn {{
    background-color: {FG_GREEN_DIM};
    color: {BG_DARK};
    border: 1px solid {FG_GREEN};
}}
QPushButton#primaryBtn:hover {{
    background-color: {FG_GREEN};
}}

QComboBox {{
    background-color: {BG_INPUT};
    color: {FG_GREEN};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 6px;
}}
QComboBox:hover {{ border: 1px solid {FG_GREEN}; }}
QComboBox QAbstractItemView {{
    background-color: {BG_INPUT};
    color: {FG_GREEN};
    selection-background-color: {FG_GREEN_DIM};
    selection-color: {BG_DARK};
    border: 1px solid {FG_GREEN_DIM};
}}

QSpinBox {{
    background-color: {BG_INPUT};
    color: {FG_GREEN};
    border: 1px solid {BORDER};
    padding: 4px;
}}

QCheckBox {{ color: {FG_TEXT}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {FG_GREEN_DIM};
    background-color: {BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {FG_GREEN};
    border: 1px solid {FG_GREEN};
}}

QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 2px;
    text-align: center;
    color: {FG_TEXT};
    background-color: {BG_INPUT};
    height: 16px;
}}
QProgressBar::chunk {{
    background-color: {FG_GREEN_DIM};
}}

QLabel#header {{
    color: {FG_GREEN};
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 4px;
}}
QLabel#subheader {{
    color: {FG_MUTED};
    font-size: 11px;
    letter-spacing: 2px;
}}
QLabel#fieldLabel {{
    color: {FG_CYAN};
    font-weight: bold;
    letter-spacing: 1px;
}}
QLabel#statusOk {{ color: {FG_GREEN}; font-weight: bold; }}
QLabel#statusErr {{ color: {DANGER}; font-weight: bold; }}
QLabel#statusWarn {{ color: {WARN}; font-weight: bold; }}
QLabel#muted {{ color: {FG_MUTED}; }}

QFrame#divider {{
    background-color: {BORDER};
    max-height: 1px;
}}

QSlider::groove:horizontal {{
    background: {BORDER};
    height: 4px;
}}
QSlider::handle:horizontal {{
    background: {FG_GREEN};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}

QScrollBar:vertical {{
    background: {BG_DARK};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {FG_GREEN_DIM};
}}
"""


# ──────────────────────────────────────────────────────────────────────
#  Crypto backend
# ──────────────────────────────────────────────────────────────────────

MAGIC = b"CVLT"          # file format magic bytes
FORMAT_VERSION = 2

KDF_ARGON2 = "argon2id"
KDF_PBKDF2 = "pbkdf2"
KDF_SCRYPT = "scrypt"

CIPHER_AES_GCM = "AES-256-GCM"
CIPHER_AES_CBC = "AES-256-CBC"
CIPHER_CHACHA  = "ChaCha20-Poly1305"

KDF_IDS = {KDF_ARGON2: 1, KDF_PBKDF2: 2, KDF_SCRYPT: 3}
KDF_NAMES = {v: k for k, v in KDF_IDS.items()}

CIPHER_IDS = {CIPHER_AES_GCM: 1, CIPHER_AES_CBC: 2, CIPHER_CHACHA: 3}
CIPHER_NAMES = {v: k for k, v in CIPHER_IDS.items()}


class CryptoError(Exception):
    pass


def derive_key(password: bytes, salt: bytes, kdf: str, key_len: int = 32) -> bytes:
    """Derive a symmetric key from a password using the chosen KDF."""
    if kdf == KDF_ARGON2:
        return hash_secret_raw(
            secret=password,
            salt=salt,
            time_cost=3,
            memory_cost=65536,   # 64 MiB
            parallelism=4,
            hash_len=key_len,
            type=Argon2Type.ID,
        )
    elif kdf == KDF_PBKDF2:
        return PBKDF2(password, salt, dkLen=key_len, count=600_000, hmac_hash_module=SHA256)
    elif kdf == KDF_SCRYPT:
        return scrypt_kdf(password, salt, key_len=key_len, N=2**17, r=8, p=1)
    else:
        raise CryptoError(f"Unknown KDF: {kdf}")


def encrypt_bytes(plaintext: bytes, password: str, cipher_name: str, kdf_name: str,
                   aad: bytes = b"") -> bytes:
    """
    Encrypt plaintext, returning a self-describing binary blob:

    MAGIC(4) | VERSION(1) | CIPHER_ID(1) | KDF_ID(1) | SALT_LEN(1) | SALT |
    NONCE_LEN(1) | NONCE | TAG(16) | CIPHERTEXT
    """
    salt = get_random_bytes(16)
    key = derive_key(password.encode("utf-8"), salt, kdf_name)

    if cipher_name == CIPHER_AES_GCM:
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        if aad:
            cipher.update(aad)
        ct, tag = cipher.encrypt_and_digest(plaintext)

    elif cipher_name == CIPHER_AES_CBC:
        nonce = get_random_bytes(16)  # IV
        pad_len = 16 - (len(plaintext) % 16)
        padded = plaintext + bytes([pad_len]) * pad_len
        cipher = AES.new(key, AES.MODE_CBC, iv=nonce)
        ct = cipher.encrypt(padded)
        # authenticate via HMAC-SHA256 over IV+CT, stored as "tag"
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

    blob = bytearray()
    blob += MAGIC
    blob += bytes([FORMAT_VERSION])
    blob += bytes([CIPHER_IDS[cipher_name]])
    blob += bytes([KDF_IDS[kdf_name]])
    blob += bytes([len(salt)])
    blob += salt
    blob += bytes([len(nonce)])
    blob += nonce
    blob += tag  # always 16 or 32 bytes depending on scheme; length-prefix it
    blob_tag_len = len(tag)
    # re-pack with tag length prefix for forward compatibility
    out = bytearray()
    out += MAGIC
    out += bytes([FORMAT_VERSION])
    out += bytes([CIPHER_IDS[cipher_name]])
    out += bytes([KDF_IDS[kdf_name]])
    out += bytes([len(salt)])
    out += salt
    out += bytes([len(nonce)])
    out += nonce
    out += bytes([blob_tag_len])
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
    elif algo == "sha-1" or algo == "sha1":
        h = hashlib.sha1(data)
    elif algo == "sha-256" or algo == "sha256":
        h = hashlib.sha256(data)
    elif algo == "sha-512" or algo == "sha512":
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
    """Very rough entropy-based strength estimate. Returns (label, style_id)."""
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
        return f"WEAK ({bits:.0f} bits)", "statusErr"
    elif bits < 65:
        return f"FAIR ({bits:.0f} bits)", "statusWarn"
    elif bits < 90:
        return f"STRONG ({bits:.0f} bits)", "statusOk"
    else:
        return f"VERY STRONG ({bits:.0f} bits)", "statusOk"


# ──────────────────────────────────────────────────────────────────────
#  Background worker for file operations (keeps UI responsive)
# ──────────────────────────────────────────────────────────────────────

class FileCryptoWorker(QThread):
    finished_ok = pyqtSignal(str, float)   # output path, elapsed seconds
    failed = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, mode, in_path, out_path, password, cipher_name, kdf_name):
        super().__init__()
        self.mode = mode  # "encrypt" | "decrypt"
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
                # store original filename length + name right after AAD marker
                # we embed AAD length in the blob itself for retrieval on decrypt:
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

def make_password_field() -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText("Enter password...")
    return field


def make_reveal_button(target: QLineEdit) -> QToolButton:
    btn = QToolButton()
    btn.setText("SHOW")
    btn.setCheckable(True)
    btn.setStyleSheet(f"""
        QToolButton {{
            color: {FG_MUTED}; border: 1px solid {BORDER};
            padding: 4px 8px; font-size: 10px;
        }}
        QToolButton:checked {{ color: {FG_GREEN}; border: 1px solid {FG_GREEN_DIM}; }}
    """)

    def toggle():
        if btn.isChecked():
            target.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("HIDE")
        else:
            target.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("SHOW")

    btn.clicked.connect(toggle)
    return btn


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("divider")
    f.setFrameShape(QFrame.Shape.HLine)
    return f


# ──────────────────────────────────────────────────────────────────────
#  Tab 1 — Text Encrypt / Decrypt
# ──────────────────────────────────────────────────────────────────────

class TextCryptoTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Options row
        opts_group = QGroupBox("PARAMETERS")
        opts_layout = QGridLayout(opts_group)

        opts_layout.addWidget(QLabel("Cipher:", objectName="fieldLabel"), 0, 0)
        self.cipher_combo = QComboBox()
        self.cipher_combo.addItems([CIPHER_AES_GCM, CIPHER_CHACHA, CIPHER_AES_CBC])
        opts_layout.addWidget(self.cipher_combo, 0, 1)

        opts_layout.addWidget(QLabel("KDF:", objectName="fieldLabel"), 0, 2)
        self.kdf_combo = QComboBox()
        self.kdf_combo.addItems([KDF_ARGON2, KDF_SCRYPT, KDF_PBKDF2])
        opts_layout.addWidget(self.kdf_combo, 0, 3)

        opts_layout.addWidget(QLabel("Password:", objectName="fieldLabel"), 1, 0)
        self.password_field = make_password_field()
        opts_layout.addWidget(self.password_field, 1, 1, 1, 2)
        opts_layout.addWidget(make_reveal_button(self.password_field), 1, 3)

        layout.addWidget(opts_group)

        # Input
        layout.addWidget(QLabel("INPUT", objectName="fieldLabel"))
        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText("Type or paste plaintext here to encrypt,\nor ciphertext (Base64) here to decrypt...")
        self.input_text.setMinimumHeight(140)
        layout.addWidget(self.input_text)

        # Buttons
        btn_row = QHBoxLayout()
        self.encrypt_btn = QPushButton("ENCRYPT ▼")
        self.encrypt_btn.setObjectName("primaryBtn")
        self.decrypt_btn = QPushButton("DECRYPT ▲")
        self.clear_btn = QPushButton("CLEAR")
        self.swap_btn = QPushButton("⇅ SWAP")
        btn_row.addWidget(self.encrypt_btn)
        btn_row.addWidget(self.decrypt_btn)
        btn_row.addWidget(self.swap_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

        # Output
        out_label_row = QHBoxLayout()
        out_label_row.addWidget(QLabel("OUTPUT", objectName="fieldLabel"))
        out_label_row.addStretch()
        self.copy_btn = QPushButton("COPY")
        out_label_row.addWidget(self.copy_btn)
        layout.addLayout(out_label_row)

        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(140)
        layout.addWidget(self.output_text)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Wire up
        self.encrypt_btn.clicked.connect(self.do_encrypt)
        self.decrypt_btn.clicked.connect(self.do_decrypt)
        self.clear_btn.clicked.connect(self.do_clear)
        self.swap_btn.clicked.connect(self.do_swap)
        self.copy_btn.clicked.connect(self.do_copy)

    def set_status(self, text, kind="statusOk"):
        self.status_label.setText(text)
        self.status_label.setObjectName(kind)
        self.status_label.setStyleSheet(self.status_label.styleSheet())
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def do_encrypt(self):
        password = self.password_field.text()
        plaintext = self.input_text.toPlainText()
        if not password:
            self.set_status("⚠ Password required.", "statusErr")
            return
        if not plaintext:
            self.set_status("⚠ Input is empty.", "statusErr")
            return
        try:
            blob = encrypt_bytes(
                plaintext.encode("utf-8"), password,
                self.cipher_combo.currentText(), self.kdf_combo.currentText()
            )
            b64 = base64.b64encode(blob).decode("ascii")
            self.output_text.setPlainText(b64)
            self.set_status(f"✓ Encrypted with {self.cipher_combo.currentText()} "
                             f"/ {self.kdf_combo.currentText()} — {len(blob)} bytes.", "statusOk")
        except Exception as e:
            self.set_status(f"✗ Encryption failed: {e}", "statusErr")

    def do_decrypt(self):
        password = self.password_field.text()
        ciphertext_b64 = self.input_text.toPlainText().strip()
        if not password:
            self.set_status("⚠ Password required.", "statusErr")
            return
        if not ciphertext_b64:
            self.set_status("⚠ Input is empty.", "statusErr")
            return
        try:
            blob = base64.b64decode(ciphertext_b64)
        except Exception:
            self.set_status("✗ Input is not valid Base64.", "statusErr")
            return
        try:
            pt = decrypt_bytes(blob, password)
            self.output_text.setPlainText(pt.decode("utf-8", errors="replace"))
            self.set_status("✓ Decrypted successfully.", "statusOk")
        except CryptoError as e:
            self.set_status(f"✗ {e}", "statusErr")
        except Exception as e:
            self.set_status(f"✗ Decryption failed: {e}", "statusErr")

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
            self.set_status("✓ Copied to clipboard.", "statusOk")


# ──────────────────────────────────────────────────────────────────────
#  Tab 2 — File Encrypt / Decrypt
# ──────────────────────────────────────────────────────────────────────

class FileCryptoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        file_group = QGroupBox("SOURCE FILE")
        file_layout = QHBoxLayout(file_group)
        self.file_path_field = QLineEdit()
        self.file_path_field.setReadOnly(True)
        self.file_path_field.setPlaceholderText("No file selected...")
        browse_btn = QPushButton("BROWSE...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path_field)
        file_layout.addWidget(browse_btn)
        layout.addWidget(file_group)

        opts_group = QGroupBox("PARAMETERS")
        opts_layout = QGridLayout(opts_group)
        opts_layout.addWidget(QLabel("Cipher:", objectName="fieldLabel"), 0, 0)
        self.cipher_combo = QComboBox()
        self.cipher_combo.addItems([CIPHER_AES_GCM, CIPHER_CHACHA, CIPHER_AES_CBC])
        opts_layout.addWidget(self.cipher_combo, 0, 1)

        opts_layout.addWidget(QLabel("KDF:", objectName="fieldLabel"), 0, 2)
        self.kdf_combo = QComboBox()
        self.kdf_combo.addItems([KDF_ARGON2, KDF_SCRYPT, KDF_PBKDF2])
        opts_layout.addWidget(self.kdf_combo, 0, 3)

        opts_layout.addWidget(QLabel("Password:", objectName="fieldLabel"), 1, 0)
        self.password_field = make_password_field()
        opts_layout.addWidget(self.password_field, 1, 1, 1, 2)
        opts_layout.addWidget(make_reveal_button(self.password_field), 1, 3)

        opts_layout.addWidget(QLabel("Confirm:", objectName="fieldLabel"), 2, 0)
        self.confirm_field = make_password_field()
        opts_layout.addWidget(self.confirm_field, 2, 1, 1, 2)
        opts_layout.addWidget(make_reveal_button(self.confirm_field), 2, 3)

        layout.addWidget(opts_group)

        btn_row = QHBoxLayout()
        self.encrypt_btn = QPushButton("ENCRYPT FILE")
        self.encrypt_btn.setObjectName("primaryBtn")
        self.decrypt_btn = QPushButton("DECRYPT FILE")
        btn_row.addWidget(self.encrypt_btn)
        btn_row.addWidget(self.decrypt_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Select a file to begin.")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addWidget(divider())
        note = QLabel(
            "Encrypted files are saved with a .cvlt extension and store the\n"
            "original filename internally so it's restored automatically on decrypt."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
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
            self.set_status(f"Loaded: {os.path.basename(path)} "
                             f"({os.path.getsize(path):,} bytes)")

    def start_job(self, mode):
        in_path = self.file_path_field.text()
        password = self.password_field.text()

        if not in_path or not os.path.isfile(in_path):
            self.set_status("⚠ Select a valid file first.", "statusErr")
            return
        if not password:
            self.set_status("⚠ Password required.", "statusErr")
            return

        if mode == "encrypt":
            if password != self.confirm_field.text():
                self.set_status("⚠ Passwords do not match.", "statusErr")
                return
            default_out = in_path + ".cvlt"
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Save Encrypted File As", default_out, "CryptVault File (*.cvlt)")
        else:
            base = in_path[:-5] if in_path.endswith(".cvlt") else in_path + ".decrypted"
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Save Decrypted File As", base)

        if not out_path:
            return

        self.set_controls_enabled(False)
        self.progress.setValue(0)
        self.set_status("Working...", "muted")

        self.worker = FileCryptoWorker(
            mode, in_path, out_path, password,
            self.cipher_combo.currentText(), self.kdf_combo.currentText()
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
        self.set_status(f"✓ {verb} → {out_path}  ({elapsed:.2f}s)", "statusOk")

    def on_failure(self, message):
        self.set_controls_enabled(True)
        self.progress.setValue(0)
        self.set_status(f"✗ {message}", "statusErr")


# ──────────────────────────────────────────────────────────────────────
#  Tab 3 — Hashing / Checksums
# ──────────────────────────────────────────────────────────────────────

class HashTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Source:", objectName="fieldLabel"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Text Input", "File"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Type text to hash...")
        self.text_input.setMinimumHeight(120)
        layout.addWidget(self.text_input)

        file_row = QHBoxLayout()
        self.file_path_field = QLineEdit()
        self.file_path_field.setReadOnly(True)
        self.file_path_field.setPlaceholderText("No file selected...")
        self.browse_btn = QPushButton("BROWSE...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(self.file_path_field)
        file_row.addWidget(self.browse_btn)
        self.file_path_field.setVisible(False)
        self.browse_btn.setVisible(False)
        layout.addLayout(file_row)

        compute_row = QHBoxLayout()
        self.compute_btn = QPushButton("COMPUTE HASHES")
        self.compute_btn.setObjectName("primaryBtn")
        compute_row.addWidget(self.compute_btn)
        compute_row.addStretch()
        layout.addLayout(compute_row)

        layout.addWidget(divider())

        results_group = QGroupBox("DIGESTS")
        grid = QGridLayout(results_group)
        self.hash_fields = {}
        for row, algo in enumerate(["MD5", "SHA-1", "SHA-256", "SHA-512", "BLAKE2b"]):
            grid.addWidget(QLabel(algo + ":", objectName="fieldLabel"), row, 0)
            field = QLineEdit()
            field.setReadOnly(True)
            grid.addWidget(field, row, 1)
            copy_btn = QPushButton("COPY")
            copy_btn.setFixedWidth(70)
            copy_btn.clicked.connect(lambda _, f=field: self.copy_field(f))
            grid.addWidget(copy_btn, row, 2)
            self.hash_fields[algo] = field
        layout.addWidget(results_group)

        layout.addWidget(divider())
        verify_group = QGroupBox("VERIFY AGAINST EXPECTED HASH")
        v_layout = QHBoxLayout(verify_group)
        self.verify_field = QLineEdit()
        self.verify_field.setPlaceholderText("Paste an expected hash to compare...")
        self.verify_result = QLabel("")
        v_layout.addWidget(self.verify_field)
        v_layout.addWidget(self.verify_result)
        self.verify_field.textChanged.connect(self.check_verify)
        layout.addWidget(verify_group)

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
        if self.mode_combo.currentText() == "Text Input":
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
        if match:
            self.verify_result.setText("✓ MATCH")
            self.verify_result.setObjectName("statusOk")
        else:
            self.verify_result.setText("✗ NO MATCH")
            self.verify_result.setObjectName("statusErr")
        self.verify_result.style().unpolish(self.verify_result)
        self.verify_result.style().polish(self.verify_result)


# ──────────────────────────────────────────────────────────────────────
#  Tab 4 — Password Generator
# ──────────────────────────────────────────────────────────────────────

class PasswordGenTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        self.result_field = QLineEdit()
        self.result_field.setReadOnly(True)
        self.result_field.setStyleSheet(f"font-size: 16px; padding: 12px; color: {FG_GREEN};")
        layout.addWidget(self.result_field)

        strength_row = QHBoxLayout()
        strength_row.addWidget(QLabel("Strength:", objectName="fieldLabel"))
        self.strength_label = QLabel("—")
        strength_row.addWidget(self.strength_label)
        strength_row.addStretch()
        copy_btn = QPushButton("COPY")
        copy_btn.clicked.connect(self.copy_password)
        strength_row.addWidget(copy_btn)
        layout.addLayout(strength_row)

        layout.addWidget(divider())

        opts_group = QGroupBox("OPTIONS")
        grid = QGridLayout(opts_group)

        grid.addWidget(QLabel("Length:", objectName="fieldLabel"), 0, 0)
        self.length_spin = QSpinBox()
        self.length_spin.setRange(4, 128)
        self.length_spin.setValue(20)
        grid.addWidget(self.length_spin, 0, 1)

        self.upper_check = QCheckBox("Uppercase (A-Z)")
        self.upper_check.setChecked(True)
        self.lower_check = QCheckBox("Lowercase (a-z)")
        self.lower_check.setChecked(True)
        self.digit_check = QCheckBox("Digits (0-9)")
        self.digit_check.setChecked(True)
        self.symbol_check = QCheckBox("Symbols (!@#$...)")
        self.symbol_check.setChecked(True)
        self.ambig_check = QCheckBox("Exclude ambiguous characters (l, 1, I, O, 0)")

        grid.addWidget(self.upper_check, 1, 0)
        grid.addWidget(self.lower_check, 1, 1)
        grid.addWidget(self.digit_check, 2, 0)
        grid.addWidget(self.symbol_check, 2, 1)
        grid.addWidget(self.ambig_check, 3, 0, 1, 2)

        layout.addWidget(opts_group)

        gen_row = QHBoxLayout()
        gen_btn = QPushButton("GENERATE")
        gen_btn.setObjectName("primaryBtn")
        gen_btn.clicked.connect(self.generate)
        gen_row.addWidget(gen_btn)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        layout.addWidget(divider())

        # Passphrase mode
        pp_group = QGroupBox("DICEWARE-STYLE PASSPHRASE")
        pp_layout = QHBoxLayout(pp_group)
        pp_layout.addWidget(QLabel("Words:", objectName="fieldLabel"))
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(3, 12)
        self.word_count_spin.setValue(5)
        pp_layout.addWidget(self.word_count_spin)
        pp_gen_btn = QPushButton("GENERATE PASSPHRASE")
        pp_gen_btn.clicked.connect(self.generate_passphrase)
        pp_layout.addWidget(pp_gen_btn)
        pp_layout.addStretch()
        layout.addWidget(pp_group)

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CryptVault — devforge")
        self.resize(760, 700)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setStyleSheet(f"background-color: {BG_PANEL}; border-bottom: 1px solid {BORDER};")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(2)
        title = QLabel("CRYPTVAULT")
        title.setObjectName("header")
        subtitle = QLabel("AES-256-GCM · ChaCha20-Poly1305 · Argon2id · SHA-2 // black8arch/devforge")
        subtitle.setObjectName("subheader")
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        outer.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(TextCryptoTab(), "TEXT")
        tabs.addTab(FileCryptoTab(), "FILE")
        tabs.addTab(HashTab(), "HASH")
        tabs.addTab(PasswordGenTab(), "PASSWORD GEN")
        outer.addWidget(tabs)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = CryptVaultWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
