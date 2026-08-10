"""
SimpleCrypt - fast, simple, strong file encryption tool.

  - Cipher:  AES-256-GCM (authenticated, tamper-evident)
  - KDF:     scrypt (memory-hard, brute-force resistant)
  - Modes:   password OR keyfile
  - Batch:   encrypt/decrypt multiple files at once

Run:
    pip install cryptography
    python simplecrypt_gui.py

Requires only the standard library (tkinter) + the `cryptography` package.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import crypto_engine as ce

# ---------------------------------------------------------------------------
# Theme: minimal, dark-blue on white, high contrast, no clutter
# ---------------------------------------------------------------------------
BLUE = "#1E5FB8"       # primary accent
BLUE_DARK = "#123E7A"  # hover/pressed
BLUE_PALE = "#EAF1FB"  # panel background
WHITE = "#FFFFFF"
GRAY_TEXT = "#5A6472"
GRAY_BORDER = "#D5DEEA"
RED = "#C0392B"
GREEN = "#1E8449"
FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_MONO = ("Consolas", 9)


class SimpleCryptApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SimpleCrypt")
        self.geometry("620x560")
        self.minsize(560, 480)
        self.configure(bg=WHITE)

        self.mode = tk.StringVar(value="encrypt")   # encrypt | decrypt
        self.key_mode = tk.StringVar(value="password")  # password | keyfile
        self.files = []          # list of selected file paths
        self.keyfile_path = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value="")     # optional custom output folder

        self._build_style()
        self._build_layout()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=WHITE)
        style.configure("Panel.TFrame", background=BLUE_PALE)
        style.configure("TLabel", background=WHITE, foreground="#1B1F27", font=FONT_UI)
        style.configure("Sub.TLabel", background=WHITE, foreground=GRAY_TEXT, font=FONT_UI)
        style.configure("Panel.TLabel", background=BLUE_PALE, foreground="#1B1F27", font=FONT_UI)
        style.configure("Title.TLabel", background=WHITE, foreground=BLUE_DARK, font=FONT_TITLE)

        style.configure("TRadiobutton", background=WHITE, foreground="#1B1F27", font=FONT_UI)
        style.map("TRadiobutton", background=[("active", WHITE)])

        style.configure(
            "Accent.TButton",
            background=BLUE, foreground=WHITE, font=FONT_UI_BOLD,
            padding=(14, 9), borderwidth=0,
        )
        style.map("Accent.TButton",
                  background=[("active", BLUE_DARK), ("disabled", "#A9BEDD")])

        style.configure(
            "Ghost.TButton",
            background=WHITE, foreground=BLUE, font=FONT_UI,
            padding=(10, 6), borderwidth=1, relief="solid",
        )
        style.map("Ghost.TButton",
                  background=[("active", BLUE_PALE)],
                  bordercolor=[("!disabled", GRAY_BORDER)])

        style.configure("TEntry", fieldbackground=WHITE, padding=6)
        style.configure("Horizontal.TProgressbar", background=BLUE, troughcolor=BLUE_PALE)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)

        # --- Header -----------------------------------------------------
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(header, text="SimpleCrypt", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="AES-256-GCM  ·  scrypt", style="Sub.TLabel").pack(side="right")

        # --- Mode switch (Encrypt / Decrypt) -----------------------------
        mode_frame = ttk.Frame(outer)
        mode_frame.pack(fill="x", pady=(0, 12))
        ttk.Radiobutton(mode_frame, text="Encrypt", value="encrypt",
                         variable=self.mode, command=self._on_mode_change).pack(side="left", padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Decrypt", value="decrypt",
                         variable=self.mode, command=self._on_mode_change).pack(side="left")

        # --- File list panel ---------------------------------------------
        files_panel = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        files_panel.pack(fill="both", expand=True, pady=(0, 12))

        top_row = ttk.Frame(files_panel, style="Panel.TFrame")
        top_row.pack(fill="x")
        ttk.Label(top_row, text="Files", style="Panel.TLabel", font=FONT_UI_BOLD).pack(side="left")
        self.file_count_lbl = ttk.Label(top_row, text="0 selected", style="Panel.TLabel")
        self.file_count_lbl.pack(side="right")

        list_frame = tk.Frame(files_panel, bg=WHITE, highlightbackground=GRAY_BORDER,
                               highlightthickness=1)
        list_frame.pack(fill="both", expand=True, pady=(8, 8))

        self.file_listbox = tk.Listbox(
            list_frame, font=FONT_MONO, bg=WHITE, fg="#1B1F27",
            selectbackground=BLUE, selectforeground=WHITE,
            borderwidth=0, highlightthickness=0, activestyle="none",
        )
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_row = ttk.Frame(files_panel, style="Panel.TFrame")
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Add Files", style="Ghost.TButton",
                   command=self._add_files).pack(side="left")
        ttk.Button(btn_row, text="Remove Selected", style="Ghost.TButton",
                   command=self._remove_selected).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Clear", style="Ghost.TButton",
                   command=self._clear_files).pack(side="left")

        # --- Key panel -----------------------------------------------------
        key_panel = ttk.Frame(outer, style="Panel.TFrame", padding=12)
        key_panel.pack(fill="x", pady=(0, 12))

        key_mode_row = ttk.Frame(key_panel, style="Panel.TFrame")
        key_mode_row.pack(fill="x")
        ttk.Label(key_mode_row, text="Key", style="Panel.TLabel", font=FONT_UI_BOLD).pack(side="left")
        ttk.Radiobutton(key_mode_row, text="Password", value="password",
                         variable=self.key_mode, command=self._on_key_mode_change).pack(side="left", padx=(16, 12))
        ttk.Radiobutton(key_mode_row, text="Key File", value="keyfile",
                         variable=self.key_mode, command=self._on_key_mode_change).pack(side="left")

        # password entry
        self.pw_frame = ttk.Frame(key_panel, style="Panel.TFrame")
        self.pw_frame.pack(fill="x", pady=(8, 0))
        self.pw_entry = ttk.Entry(self.pw_frame, show="•", font=FONT_UI)
        self.pw_entry.pack(side="left", fill="x", expand=True)
        self.show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.pw_frame, text="show", variable=self.show_pw,
                         command=self._toggle_pw_visibility).pack(side="left", padx=(8, 0))

        # keyfile row (hidden unless key_mode == keyfile)
        self.kf_frame = ttk.Frame(key_panel, style="Panel.TFrame")
        self.kf_entry = ttk.Entry(self.kf_frame, textvariable=self.keyfile_path, font=FONT_UI)
        self.kf_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(self.kf_frame, text="Browse", style="Ghost.TButton",
                   command=self._browse_keyfile).pack(side="left", padx=(8, 0))
        ttk.Button(self.kf_frame, text="Generate New Key", style="Ghost.TButton",
                   command=self._generate_keyfile).pack(side="left", padx=(8, 0))

        # --- Output folder (optional) --------------------------------------
        out_row = ttk.Frame(outer)
        out_row.pack(fill="x", pady=(0, 12))
        ttk.Label(out_row, text="Output folder (optional):", style="Sub.TLabel").pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_dir, font=FONT_UI).pack(
            side="left", fill="x", expand=True, padx=8)
        ttk.Button(out_row, text="Browse", style="Ghost.TButton",
                   command=self._browse_output_dir).pack(side="left")

        # --- Action + progress -----------------------------------------------
        self.action_btn = ttk.Button(outer, text="Encrypt Files", style="Accent.TButton",
                                      command=self._run_action)
        self.action_btn.pack(fill="x", pady=(0, 10))

        self.progress = ttk.Progressbar(outer, style="Horizontal.TProgressbar", mode="determinate")
        self.progress.pack(fill="x", pady=(0, 8))

        self.status_lbl = ttk.Label(outer, text="Ready.", style="Sub.TLabel")
        self.status_lbl.pack(fill="x")

        self._on_key_mode_change()

    # ------------------------------------------------------------------
    # UI event handlers
    # ------------------------------------------------------------------
    def _on_mode_change(self):
        is_encrypt = self.mode.get() == "encrypt"
        self.action_btn.configure(text="Encrypt Files" if is_encrypt else "Decrypt Files")
        self._refresh_file_list_display()

    def _on_key_mode_change(self):
        if self.key_mode.get() == "password":
            self.kf_frame.pack_forget()
            self.pw_frame.pack(fill="x", pady=(8, 0))
        else:
            self.pw_frame.pack_forget()
            self.kf_frame.pack(fill="x", pady=(8, 0))

    def _toggle_pw_visibility(self):
        self.pw_entry.configure(show="" if self.show_pw.get() else "•")

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select file(s)")
        if not paths:
            return
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh_file_list_display()

    def _remove_selected(self):
        sel = list(self.file_listbox.curselection())
        for i in reversed(sel):
            del self.files[i]
        self._refresh_file_list_display()

    def _clear_files(self):
        self.files = []
        self._refresh_file_list_display()

    def _refresh_file_list_display(self):
        self.file_listbox.delete(0, tk.END)
        for p in self.files:
            self.file_listbox.insert(tk.END, os.path.basename(p))
        self.file_count_lbl.configure(text=f"{len(self.files)} selected")

    def _browse_keyfile(self):
        path = filedialog.askopenfilename(
            title="Select key file",
            filetypes=[("SimpleCrypt Key", f"*{ce.KEYFILE_EXT}"), ("All files", "*.*")],
        )
        if path:
            self.keyfile_path.set(path)

    def _generate_keyfile(self):
        path = filedialog.asksaveasfilename(
            title="Save new key file",
            defaultextension=ce.KEYFILE_EXT,
            filetypes=[("SimpleCrypt Key", f"*{ce.KEYFILE_EXT}")],
        )
        if not path:
            return
        key = ce.generate_random_key()
        ce.save_keyfile(key, path)
        self.keyfile_path.set(path)
        messagebox.showinfo(
            "Key Generated",
            "A new 256-bit key was generated and saved.\n\n"
            "Keep this file safe — anyone with it can decrypt your files, "
            "and losing it means the data is unrecoverable."
        )

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.output_dir.set(d)

    # ------------------------------------------------------------------
    # Core action
    # ------------------------------------------------------------------
    def _run_action(self):
        if not self.files:
            messagebox.showwarning("No files", "Add at least one file first.")
            return

        password = None
        key_bytes = None

        if self.key_mode.get() == "password":
            password = self.pw_entry.get()
            if not password:
                messagebox.showwarning("No password", "Enter a password.")
                return
        else:
            kf_path = self.keyfile_path.get().strip()
            if not kf_path or not os.path.isfile(kf_path):
                messagebox.showwarning("No key file", "Select or generate a key file.")
                return
            try:
                key_bytes = ce.load_keyfile(kf_path)
            except ce.CryptoError as e:
                messagebox.showerror("Invalid key file", str(e))
                return

        out_dir = self.output_dir.get().strip() or None
        is_encrypt = self.mode.get() == "encrypt"

        self.action_btn.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        self.status_lbl.configure(text="Working...")

        thread = threading.Thread(
            target=self._worker, args=(list(self.files), is_encrypt, password, key_bytes, out_dir),
            daemon=True,
        )
        thread.start()

    def _worker(self, files, is_encrypt, password, key_bytes, out_dir):
        successes, failures = [], []

        for i, path in enumerate(files, start=1):
            base = os.path.basename(path)
            target_dir = out_dir or os.path.dirname(path)
            os.makedirs(target_dir, exist_ok=True)

            if is_encrypt:
                out_name = os.path.basename(ce.default_encrypted_name(path))
            else:
                out_name = os.path.basename(ce.default_decrypted_name(path))

            out_path = os.path.join(target_dir, out_name)

            if is_encrypt:
                result = ce.encrypt_file(path, out_path, password=password, key=key_bytes)
            else:
                result = ce.decrypt_file(path, out_path, password=password, key=key_bytes)

            if result.ok:
                successes.append(base)
            else:
                failures.append((base, result.error))

            self.after(0, self._update_progress, i, base)

        self.after(0, self._finish, successes, failures)

    def _update_progress(self, i, name):
        self.progress.configure(value=i)
        self.status_lbl.configure(text=f"Processing ({i}/{len(self.files)}): {name}")

    def _finish(self, successes, failures):
        self.action_btn.configure(state="normal")

        verb = "encrypted" if self.mode.get() == "encrypt" else "decrypted"
        if failures:
            self.status_lbl.configure(
                text=f"{len(successes)} {verb}, {len(failures)} failed.", foreground=RED)
            detail = "\n".join(f"• {name}: {err}" for name, err in failures)
            messagebox.showerror(
                "Some files failed",
                f"{len(successes)} succeeded, {len(failures)} failed:\n\n{detail}"
            )
        else:
            self.status_lbl.configure(
                text=f"Done — {len(successes)} file(s) {verb} successfully.", foreground=GREEN)

        self.progress.configure(value=0)


if __name__ == "__main__":
    app = SimpleCryptApp()
    app.mainloop()
