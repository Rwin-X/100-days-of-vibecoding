"""
crypto_engine.py
-----------------
Core cryptographic engine for SimpleCrypt.

Design:
  - Cipher:        AES-256-GCM (authenticated encryption; tamper-evident)
  - KDF:           scrypt (memory-hard, resists GPU/ASIC brute force)
  - File format:   custom ".sce" container (SimpleCrypt Encrypted)
  - Key modes:     password-derived, OR random 256-bit keyfile (.scekey)

Container layout (".sce" file):
  MAGIC   (4 bytes)   = b"SCE1"
  MODE    (1 byte)    = 0x01 (password) or 0x02 (keyfile)
  SALT    (16 bytes)  = scrypt salt (all zero if keyfile mode)
  NONCE   (12 bytes)  = AES-GCM nonce
  CIPHERTEXT (rest)   = AES-GCM(plaintext) + 16-byte auth tag (appended by AESGCM)

Everything is written/read in binary; no plaintext metadata (like original
filename) is stored in the header to avoid leaking info — original filename
is preserved by simply stripping the .sce extension on decrypt, or the user
can rename freely since content integrity is verified by the GCM tag.
"""

import os
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidTag

MAGIC = b"SCE1"
MODE_PASSWORD = 0x01
MODE_KEYFILE = 0x02

SALT_LEN = 16
NONCE_LEN = 12
KEY_LEN = 32  # 256-bit

# scrypt cost parameters — tuned for interactive use (~0.3-0.6s on modern CPU)
# while still being expensive enough to meaningfully slow brute force.
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1

FILE_EXT = ".sce"
KEYFILE_EXT = ".scekey"


class CryptoError(Exception):
    """Raised for any encryption/decryption failure (wrong password, corrupt file, etc.)."""
    pass


@dataclass
class EncryptResult:
    output_path: str
    ok: bool
    error: str = ""


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from a password using scrypt (memory-hard KDF)."""
    kdf = Scrypt(salt=salt, length=KEY_LEN, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(password.encode("utf-8"))


def generate_random_key() -> bytes:
    """Generate a cryptographically secure random 256-bit key (for keyfile mode)."""
    return secrets.token_bytes(KEY_LEN)


def save_keyfile(key: bytes, path: str) -> None:
    """Write a raw 256-bit key to a .scekey file."""
    with open(path, "wb") as f:
        f.write(key)


def load_keyfile(path: str) -> bytes:
    """Load a raw 256-bit key from a .scekey file."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != KEY_LEN:
        raise CryptoError("Invalid key file (unexpected length).")
    return data


def encrypt_file(input_path: str, output_path: str, *,
                  password: str = None, key: bytes = None) -> EncryptResult:
    """
    Encrypt a single file. Supply either `password` (scrypt-derived key)
    or `key` (raw 32-byte key, e.g. from a keyfile) — not both.
    """
    try:
        if bool(password) == bool(key):
            raise CryptoError("Provide exactly one of: password or key.")

        with open(input_path, "rb") as f:
            plaintext = f.read()

        nonce = secrets.token_bytes(NONCE_LEN)

        if password:
            salt = secrets.token_bytes(SALT_LEN)
            derived_key = derive_key_from_password(password, salt)
            mode = MODE_PASSWORD
        else:
            salt = b"\x00" * SALT_LEN
            derived_key = key
            mode = MODE_KEYFILE

        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        with open(output_path, "wb") as f:
            f.write(MAGIC)
            f.write(bytes([mode]))
            f.write(salt)
            f.write(nonce)
            f.write(ciphertext)

        return EncryptResult(output_path=output_path, ok=True)

    except Exception as e:
        return EncryptResult(output_path=output_path, ok=False, error=str(e))


def decrypt_file(input_path: str, output_path: str, *,
                  password: str = None, key: bytes = None) -> EncryptResult:
    """
    Decrypt a .sce file. Supply either `password` or `key` matching how
    the file was originally encrypted.
    """
    try:
        with open(input_path, "rb") as f:
            data = f.read()

        if len(data) < len(MAGIC) + 1 + SALT_LEN + NONCE_LEN:
            raise CryptoError("File is too short or not a valid .sce container.")

        if data[:4] != MAGIC:
            raise CryptoError("Not a valid SimpleCrypt (.sce) file.")

        offset = 4
        mode = data[offset]
        offset += 1
        salt = data[offset:offset + SALT_LEN]
        offset += SALT_LEN
        nonce = data[offset:offset + NONCE_LEN]
        offset += NONCE_LEN
        ciphertext = data[offset:]

        if mode == MODE_PASSWORD:
            if not password:
                raise CryptoError("This file was encrypted with a password.")
            derived_key = derive_key_from_password(password, salt)
        elif mode == MODE_KEYFILE:
            if not key:
                raise CryptoError("This file was encrypted with a key file.")
            derived_key = key
        else:
            raise CryptoError("Unknown encryption mode in file header.")

        aesgcm = AESGCM(derived_key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except InvalidTag:
            raise CryptoError("Wrong password/key, or the file is corrupted/tampered.")

        with open(output_path, "wb") as f:
            f.write(plaintext)

        return EncryptResult(output_path=output_path, ok=True)

    except Exception as e:
        return EncryptResult(output_path=output_path, ok=False, error=str(e))


def default_encrypted_name(path: str) -> str:
    return path + FILE_EXT


def default_decrypted_name(path: str) -> str:
    if path.endswith(FILE_EXT):
        return path[: -len(FILE_EXT)]
    return path + ".decrypted"
