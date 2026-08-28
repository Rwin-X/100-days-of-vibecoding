#!/usr/bin/env python3
"""
HashForge — Hash Identifier & Generator
devforge suite

Minimal, dependency-free GUI tool:
  - Identify:  paste a hash -> get candidate algorithm(s) by length/charset
  - Generate:  type text -> get its hash under every supported algorithm

No third-party dependencies. Pure stdlib (tkinter, hashlib, zlib, re).
"""

import re
import zlib
import hashlib
import tkinter as tk
from tkinter import ttk, font

# ---------------------------------------------------------------------------
# Theme — dark cyberpunk, phosphor green/cyan, high density
# ---------------------------------------------------------------------------

BG        = "#0a0e0c"
BG_PANEL  = "#0f1512"
BG_INPUT  = "#0d1210"
FG        = "#8fffc0"      # phosphor green (primary text)
FG_DIM    = "#4d6b5c"       # dim green (labels / secondary)
ACCENT    = "#00e5ff"      # cyan accent
ACCENT_DIM= "#0a5a66"
WARN      = "#ff8a3d"       # amber for uncertain/multi-match
BORDER    = "#1c2a22"
SELECT_BG = "#123028"

MONO = ("JetBrains Mono", 10)
MONO_BOLD = ("JetBrains Mono", 10, "bold")
MONO_SMALL = ("JetBrains Mono", 9)
MONO_TITLE = ("JetBrains Mono", 13, "bold")

# ---------------------------------------------------------------------------
# Hash identification data
# ---------------------------------------------------------------------------
# Each entry: name -> (hex length, description)
# Multiple algorithms can share a length; identification returns all candidates.

HEX_RE = re.compile(r'^[0-9a-fA-F]+$')
BASE64_RE = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')

HASH_BY_HEX_LENGTH = {
    8:   [("CRC32", "checksum, not cryptographic")],
    16:  [("MD5 (half / truncated)", "unusual — verify source")],
    32:  [("MD5", "128-bit, broken for security use")],
    40:  [("SHA-1", "160-bit, broken for security use"),
          ("RIPEMD-160", "160-bit, used in Bitcoin addresses")],
    56:  [("SHA-224", "224-bit"),
          ("SHA3-224", "224-bit, Keccak-based"),
          ("SHA-512/224", "224-bit, truncated SHA-512")],
    64:  [("SHA-256", "256-bit, widely used (Bitcoin, TLS, etc.)"),
          ("SHA3-256", "256-bit, Keccak-based"),
          ("SHA-512/256", "256-bit, truncated SHA-512"),
          ("BLAKE2s-256", "256-bit, fast, used in some VPNs"),
          ("BLAKE2b-256", "256-bit variant"),
          ("Keccak-256", "256-bit, used in Ethereum")],
    96:  [("SHA-384", "384-bit"),
          ("SHA3-384", "384-bit, Keccak-based")],
    128: [("SHA-512", "512-bit"),
          ("SHA3-512", "512-bit, Keccak-based"),
          ("BLAKE2b-512", "512-bit, fast, modern")],
}

# bcrypt / crypt-style hashes are not raw hex — detect by prefix pattern
PREFIX_PATTERNS = [
    (re.compile(r'^\$2[abxy]?\$\d{2}\$'), "bcrypt", "adaptive, salted — not a raw digest"),
    (re.compile(r'^\$argon2(id|i|d)\$'), "Argon2", "modern password hash, salted + memory-hard"),
    (re.compile(r'^\$6\$'), "SHA-512 crypt (Unix)", "glibc crypt(3), salted"),
    (re.compile(r'^\$5\$'), "SHA-256 crypt (Unix)", "glibc crypt(3), salted"),
    (re.compile(r'^\$1\$'), "MD5 crypt (Unix)", "legacy glibc crypt(3), salted"),
    (re.compile(r'^\$y\$'), "yescrypt (Unix)", "modern glibc crypt(3), salted"),
    (re.compile(r'^\$apr1\$'), "Apache MD5 (apr1)", "Apache htpasswd variant"),
]


def identify_hash(raw: str):
    """Return (kind, list_of_(name, note), extra_info) for a given hash string."""
    s = raw.strip()
    if not s:
        return None

    # 1. Salted / KDF-style prefixed formats
    for pattern, name, note in PREFIX_PATTERNS:
        if pattern.match(s):
            return ("prefixed", [(name, note)], f"format-tagged, length {len(s)}")

    # 2. Plain hex digest — match by length
    if HEX_RE.match(s):
        length = len(s)
        if length in HASH_BY_HEX_LENGTH:
            return ("hex", HASH_BY_HEX_LENGTH[length], f"{length} hex chars = {length*4}-bit digest")
        else:
            return ("hex_unknown", [], f"{length} hex chars = {length*4}-bit digest (no common match)")

    # 3. Base64-looking digest (common for SHA-256 base64, etc.)
    if BASE64_RE.match(s) and len(s) >= 20:
        stripped = s.rstrip('=')
        # rough decoded byte length estimate
        decoded_len = (len(stripped) * 3) // 4
        guesses = []
        length_map = {16: "MD5", 20: "SHA-1", 28: "SHA-224", 32: "SHA-256",
                      48: "SHA-384", 64: "SHA-512"}
        if decoded_len in length_map:
            guesses = [(length_map[decoded_len] + " (base64-encoded)", "decoded byte length match")]
        return ("base64", guesses, f"base64-like, ~{decoded_len} decoded bytes")

    return ("unrecognized", [], "not hex, not base64, no known prefix")


# ---------------------------------------------------------------------------
# Hash generation
# ---------------------------------------------------------------------------

GENERATORS = [
    ("MD5",         lambda b: hashlib.md5(b).hexdigest()),
    ("SHA-1",       lambda b: hashlib.sha1(b).hexdigest()),
    ("SHA-224",     lambda b: hashlib.sha224(b).hexdigest()),
    ("SHA-256",     lambda b: hashlib.sha256(b).hexdigest()),
    ("SHA-384",     lambda b: hashlib.sha384(b).hexdigest()),
    ("SHA-512",     lambda b: hashlib.sha512(b).hexdigest()),
    ("SHA-512/224", lambda b: hashlib.new('sha512_224', b).hexdigest()),
    ("SHA-512/256", lambda b: hashlib.new('sha512_256', b).hexdigest()),
    ("SHA3-224",    lambda b: hashlib.sha3_224(b).hexdigest()),
    ("SHA3-256",    lambda b: hashlib.sha3_256(b).hexdigest()),
    ("SHA3-384",    lambda b: hashlib.sha3_384(b).hexdigest()),
    ("SHA3-512",    lambda b: hashlib.sha3_512(b).hexdigest()),
    ("BLAKE2b-512", lambda b: hashlib.blake2b(b).hexdigest()),
    ("BLAKE2s-256", lambda b: hashlib.blake2s(b).hexdigest()),
    ("SHAKE-128 (32B)", lambda b: hashlib.shake_128(b).hexdigest(32)),
    ("SHAKE-256 (64B)", lambda b: hashlib.shake_256(b).hexdigest(64)),
    ("CRC32",       lambda b: format(zlib.crc32(b) & 0xffffffff, '08x')),
]

# Optional: RIPEMD-160 / Keccak-256 via OpenSSL backend if available
def _try_openssl(name):
    try:
        h = hashlib.new(name)
        return lambda b, n=name: hashlib.new(n, b).hexdigest()
    except Exception:
        return None

_ripemd = _try_openssl('ripemd160')
if _ripemd:
    GENERATORS.append(("RIPEMD-160", _ripemd))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class HashForgeApp:
    def __init__(self, root):
        self.root = root
        root.title("HASHFORGE // devforge")
        root.configure(bg=BG)
        root.geometry("880x640")
        root.minsize(720, 520)

        self._check_font()
        self._build_style()
        self._build_layout()

    def _check_font(self):
        global MONO, MONO_BOLD, MONO_SMALL, MONO_TITLE
        available = set(font.families())
        if "JetBrains Mono" not in available:
            fallback = "Consolas" if "Consolas" in available else "Courier New"
            MONO = (fallback, 10)
            MONO_BOLD = (fallback, 10, "bold")
            MONO_SMALL = (fallback, 9)
            MONO_TITLE = (fallback, 13, "bold")

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=FG_DIM,
                         padding=(18, 8), font=MONO_BOLD, borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_INPUT)],
                  foreground=[("selected", ACCENT)])

        style.configure("Vertical.TScrollbar", background=BG_PANEL, troughcolor=BG,
                         bordercolor=BG, arrowcolor=FG_DIM, darkcolor=BG_PANEL,
                         lightcolor=BG_PANEL)

    def _build_layout(self):
        # Header
        header = tk.Frame(self.root, bg=BG, height=52)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(header, text="HASHFORGE", bg=BG, fg=ACCENT, font=MONO_TITLE
                  ).pack(side="left", padx=(18, 6), pady=10)
        tk.Label(header, text="hash identifier // multi-algorithm generator", bg=BG,
                  fg=FG_DIM, font=MONO_SMALL).pack(side="left", pady=10)

        sep = tk.Frame(self.root, bg=BORDER, height=1)
        sep.pack(fill="x")

        # Notebook (tabs)
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        identify_tab = tk.Frame(nb, bg=BG)
        generate_tab = tk.Frame(nb, bg=BG)
        nb.add(identify_tab, text="  IDENTIFY  ")
        nb.add(generate_tab, text="  GENERATE  ")

        self._build_identify_tab(identify_tab)
        self._build_generate_tab(generate_tab)

        # Status bar
        self.status = tk.StringVar(value="ready.")
        status_bar = tk.Frame(self.root, bg=BG_PANEL, height=26)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        tk.Label(status_bar, textvariable=self.status, bg=BG_PANEL, fg=FG_DIM,
                  font=MONO_SMALL, anchor="w").pack(fill="both", padx=12)

    # ---------------- IDENTIFY TAB ----------------

    def _build_identify_tab(self, parent):
        pad = tk.Frame(parent, bg=BG)
        pad.pack(fill="both", expand=True, padx=18, pady=16)

        tk.Label(pad, text="INPUT HASH", bg=BG, fg=FG_DIM, font=MONO_SMALL, anchor="w"
                  ).pack(fill="x")

        self.id_entry = tk.Entry(pad, bg=BG_INPUT, fg=FG, insertbackground=ACCENT,
                                   font=MONO, relief="flat", highlightthickness=1,
                                   highlightbackground=BORDER, highlightcolor=ACCENT)
        self.id_entry.pack(fill="x", ipady=8, pady=(4, 10))
        self.id_entry.bind("<KeyRelease>", lambda e: self._on_identify())
        self.id_entry.focus_set()

        btn_row = tk.Frame(pad, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._make_button(btn_row, "CLEAR", self._clear_identify).pack(side="left")
        self._make_button(btn_row, "PASTE", self._paste_identify).pack(side="left", padx=(8, 0))

        # Results area
        tk.Label(pad, text="CANDIDATES", bg=BG, fg=FG_DIM, font=MONO_SMALL, anchor="w"
                  ).pack(fill="x", pady=(4, 4))

        result_frame = tk.Frame(pad, bg=BG_PANEL, highlightthickness=1,
                                  highlightbackground=BORDER)
        result_frame.pack(fill="both", expand=True)

        self.result_text = tk.Text(result_frame, bg=BG_PANEL, fg=FG, font=MONO,
                                     relief="flat", wrap="word", state="disabled",
                                     padx=14, pady=12, highlightthickness=0)
        self.result_text.pack(fill="both", expand=True)

        # tags for coloring
        self.result_text.tag_configure("name", foreground=ACCENT, font=MONO_BOLD)
        self.result_text.tag_configure("note", foreground=FG_DIM, font=MONO_SMALL)
        self.result_text.tag_configure("meta", foreground=WARN, font=MONO_SMALL)
        self.result_text.tag_configure("empty", foreground=FG_DIM, font=MONO)

        self._render_identify_placeholder()

    def _render_identify_placeholder(self):
        self._set_result_text([("paste or type a hash above.\n\n", "empty"),
                                 ("length + charset determine candidates.\n", "empty"),
                                 ("multiple algorithms may share output length —\n", "empty"),
                                 ("treat results as candidates, not certainty.", "empty")])

    def _set_result_text(self, segments):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        for text, tag in segments:
            self.result_text.insert("end", text, tag)
        self.result_text.configure(state="disabled")

    def _on_identify(self):
        raw = self.id_entry.get()
        if not raw.strip():
            self._render_identify_placeholder()
            self.status.set("ready.")
            return

        kind, candidates, meta = identify_hash(raw)

        segments = [(f"input length: {len(raw.strip())} chars\n", "meta"),
                    (f"{meta}\n\n", "meta")]

        if kind == "unrecognized":
            segments.append(("no match — not valid hex, not base64-shaped,\n"
                              "and no recognized salted-hash prefix.\n", "empty"))
            self.status.set("no candidates found.")
        elif not candidates:
            segments.append(("no common algorithm produces this exact length.\n"
                              "could be a non-standard digest, truncated hash,\n"
                              "or an HMAC / keyed variant.\n", "empty"))
            self.status.set("no common-length match.")
        else:
            for name, note in candidates:
                segments.append((f"▸ {name}\n", "name"))
                segments.append((f"   {note}\n\n", "note"))
            plural = "candidate" if len(candidates) == 1 else "candidates"
            self.status.set(f"{len(candidates)} {plural} found.")

        self._set_result_text(segments)

    def _clear_identify(self):
        self.id_entry.delete(0, "end")
        self._render_identify_placeholder()
        self.status.set("ready.")

    def _paste_identify(self):
        try:
            clip = self.root.clipboard_get()
            self.id_entry.delete(0, "end")
            self.id_entry.insert(0, clip.strip())
            self._on_identify()
        except tk.TclError:
            self.status.set("clipboard empty.")

    # ---------------- GENERATE TAB ----------------

    def _build_generate_tab(self, parent):
        pad = tk.Frame(parent, bg=BG)
        pad.pack(fill="both", expand=True, padx=18, pady=16)

        tk.Label(pad, text="INPUT TEXT", bg=BG, fg=FG_DIM, font=MONO_SMALL, anchor="w"
                  ).pack(fill="x")

        self.gen_entry = tk.Entry(pad, bg=BG_INPUT, fg=FG, insertbackground=ACCENT,
                                    font=MONO, relief="flat", highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT)
        self.gen_entry.pack(fill="x", ipady=8, pady=(4, 10))
        self.gen_entry.bind("<KeyRelease>", lambda e: self._on_generate())

        btn_row = tk.Frame(pad, bg=BG)
        btn_row.pack(fill="x", pady=(0, 12))
        self._make_button(btn_row, "CLEAR", self._clear_generate).pack(side="left")
        self._make_button(btn_row, "COPY ALL", self._copy_all_hashes).pack(side="left", padx=(8, 0))

        tk.Label(pad, text=f"DIGESTS  ({len(GENERATORS)} algorithms)", bg=BG, fg=FG_DIM,
                  font=MONO_SMALL, anchor="w").pack(fill="x", pady=(4, 4))

        # Scrollable results
        outer = tk.Frame(pad, bg=BG_PANEL, highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.gen_inner = tk.Frame(canvas, bg=BG_PANEL)

        self.gen_inner.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.gen_inner, anchor="nw", width=0)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _resize(e):
            canvas.itemconfig(canvas.find_all()[0], width=e.width)
        canvas.bind("<Configure>", _resize)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # mousewheel support
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.gen_rows = {}
        self._build_generate_rows()

    def _build_generate_rows(self):
        for name, _ in GENERATORS:
            row = tk.Frame(self.gen_inner, bg=BG_PANEL)
            row.pack(fill="x", padx=12, pady=4)

            label = tk.Label(row, text=name, bg=BG_PANEL, fg=ACCENT, font=MONO_BOLD,
                               width=16, anchor="w")
            label.pack(side="left")

            value_var = tk.StringVar(value="—")
            value_entry = tk.Entry(row, textvariable=value_var, bg=BG_INPUT, fg=FG,
                                     font=MONO_SMALL, relief="flat", state="readonly",
                                     readonlybackground=BG_INPUT,
                                     highlightthickness=1, highlightbackground=BORDER)
            value_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(8, 8))

            copy_btn = tk.Label(row, text="⧉", bg=BG_PANEL, fg=FG_DIM, font=MONO_BOLD,
                                  cursor="hand2", padx=6)
            copy_btn.pack(side="right")
            copy_btn.bind("<Button-1>", lambda e, v=value_var: self._copy_value(v))
            copy_btn.bind("<Enter>", lambda e, w=copy_btn: w.configure(fg=ACCENT))
            copy_btn.bind("<Leave>", lambda e, w=copy_btn: w.configure(fg=FG_DIM))

            self.gen_rows[name] = value_var

    def _on_generate(self):
        text = self.gen_entry.get()
        if not text:
            for var in self.gen_rows.values():
                var.set("—")
            self.status.set("ready.")
            return

        data = text.encode("utf-8")
        for name, fn in GENERATORS:
            try:
                self.gen_rows[name].set(fn(data))
            except Exception as e:
                self.gen_rows[name].set(f"(unavailable: {e})")
        self.status.set(f"{len(data)} bytes hashed across {len(GENERATORS)} algorithms.")

    def _clear_generate(self):
        self.gen_entry.delete(0, "end")
        self._on_generate()

    def _copy_value(self, var):
        val = var.get()
        if val and val != "—":
            self.root.clipboard_clear()
            self.root.clipboard_append(val)
            self.status.set("copied to clipboard.")

    def _copy_all_hashes(self):
        lines = [f"{name}: {var.get()}" for name, var in self.gen_rows.items()
                  if var.get() != "—"]
        if lines:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(lines))
            self.status.set(f"copied {len(lines)} digests to clipboard.")
        else:
            self.status.set("nothing to copy — enter text first.")

    # ---------------- shared widgets ----------------

    def _make_button(self, parent, text, command):
        btn = tk.Label(parent, text=text, bg=BG_PANEL, fg=FG, font=MONO_BOLD,
                         cursor="hand2", padx=14, pady=6,
                         highlightthickness=1, highlightbackground=BORDER)
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.configure(bg=SELECT_BG, fg=ACCENT))
        btn.bind("<Leave>", lambda e: btn.configure(bg=BG_PANEL, fg=FG))
        return btn


def main():
    root = tk.Tk()
    app = HashForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
