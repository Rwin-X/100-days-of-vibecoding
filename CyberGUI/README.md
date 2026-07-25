# CryptVault

A GUI cryptography suite built with PyQt6 — part of the `devforge` collection.

## Setup

```bash
pip install -r requirements.txt
python3 cryptvault.py
```

## Features

**TEXT** — Encrypt/decrypt text or notes, output as Base64, with a SWAP and COPY button.

**FILE** — Encrypt/decrypt any file. Output is a `.cvlt` container that stores the
original filename internally, so it's restored automatically on decrypt. Runs on a
background thread so the UI never freezes on large files.

**HASH** — MD5, SHA-1, SHA-256, SHA-512, and BLAKE2b digests for text or files, plus
a field to paste an expected hash and get an instant match/no-match check.

**PASSWORD GEN** — Configurable random password generator (length, character sets,
ambiguous-character exclusion) with a live entropy-based strength estimate, plus a
diceware-style passphrase generator.

## Cryptography

- **Ciphers:** AES-256-GCM (default), ChaCha20-Poly1305, AES-256-CBC+HMAC-SHA256
- **Key derivation:** Argon2id (default, 64 MiB / t=3 / p=4), scrypt (N=2^17), PBKDF2-HMAC-SHA256 (600k iterations)
- All modes are authenticated — tampering or a wrong password is always detected and
  rejected, never silently produces garbage output.
- Each encrypted blob is self-describing (cipher, KDF, salt, nonce all stored
  alongside the ciphertext), so you only ever need the password to decrypt.

## File format (`.cvlt`)

```
[name_len(2)] [original_filename] [MAGIC "CVLT"] [version(1)] [cipher_id(1)]
[kdf_id(1)] [salt_len(1)] [salt] [nonce_len(1)] [nonce] [tag_len(1)] [tag] [ciphertext]
```
