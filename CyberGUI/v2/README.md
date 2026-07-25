# CryptVault

A minimal GUI cryptography suite built with PyQt6 — part of the `devforge` collection.

## Setup

```bash
pip install -r requirements.txt
python3 cryptvault.py
```

## Theme

Dark by default. Click **Light** in the top-right corner to switch to a white theme, and
**Dark** to switch back. Toggling is instant and applies to every tab.

## Features

**Text** — Encrypt/decrypt text to/from Base64, with Swap and Copy.

**File** — Encrypt/decrypt any file into a `.cvlt` container (original filename preserved
internally, restored automatically on decrypt). Runs on a background thread so large files
never freeze the UI.

**Hash** — MD5, SHA-1, SHA-256, SHA-512, BLAKE2b for text or files, plus an instant
match-checker against a pasted hash.

**Password** — Configurable random password generator with a live strength estimate, plus
a diceware-style passphrase generator.

Cipher and KDF choice are tucked behind an **Advanced** toggle on the Text and File tabs
(collapsed by default) — AES-256-GCM + Argon2id is used unless you open it and pick
something else.

## Cryptography

- **Ciphers:** AES-256-GCM (default), ChaCha20-Poly1305, AES-256-CBC+HMAC-SHA256
- **Key derivation:** Argon2id (default, 64 MiB / t=3 / p=4), scrypt (N=2^17), PBKDF2-HMAC-SHA256 (600k iterations)
- All modes are authenticated — tampering or a wrong password is always detected and
  rejected, never silently produces garbage output.
- Each encrypted blob is self-describing (cipher, KDF, salt, nonce stored alongside the
  ciphertext), so you only ever need the password to decrypt.

## File format (`.cvlt`)

```
[name_len(2)] [original_filename] [MAGIC "CVLT"] [version(1)] [cipher_id(1)]
[kdf_id(1)] [salt_len(1)] [salt] [nonce_len(1)] [nonce] [tag_len(1)] [tag] [ciphertext]
```
