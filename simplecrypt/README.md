# SimpleCrypt

Fast, minimal file encryption tool. Strong crypto under a clean GUI.

## Crypto

| Component     | Choice                                      |
|----------------|----------------------------------------------|
| Cipher         | AES-256-GCM (authenticated — detects tampering) |
| KDF            | scrypt (N=2^15, r=8, p=1) — memory-hard, brute-force resistant |
| Key modes      | Password-derived, or random 256-bit key file (`.scekey`) |
| Container      | `.sce` — magic bytes + mode + salt + nonce + ciphertext+tag |

Every encrypted file is authenticated: a wrong password/key or a modified
file is detected and rejected, never silently corrupted.

## Setup

```bash
pip install cryptography
python simplecrypt_gui.py
```

Requires Python 3.9+. GUI is pure `tkinter` (standard library) — the only
external dependency is `cryptography`.

## Usage

1. Choose **Encrypt** or **Decrypt**.
2. **Add Files** — supports multiple files at once (batch).
3. Choose key mode:
   - **Password** — type any passphrase (used with scrypt to derive the key).
   - **Key File** — use **Generate New Key** to create a random 256-bit
     `.scekey` file, or **Browse** to reuse an existing one.
4. (Optional) pick an output folder — otherwise files are written next to
   the originals.
5. Run. Encrypted files get a `.sce` suffix; decrypting strips it back off.

## Files

```
crypto_engine.py     # pure crypto logic, no UI dependencies, unit-tested
simplecrypt_gui.py    # tkinter GUI
```

`crypto_engine.py` has no GUI dependency and can be reused standalone (CLI,
scripts, other tools) — import `encrypt_file` / `decrypt_file` directly.

## Notes

- Keep `.scekey` files as safe as the data they protect — losing one makes
  encrypted files unrecoverable, and anyone who has it can decrypt.
- Passwords are never stored; only used transiently to derive the key.
