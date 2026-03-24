"""
Credentials dialog — shown on first run and from the main window.
Two tabs: Staging and Production. Saves independently to Windows Credential Manager.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from portal.credentials import credential_manager as cm
from portal.config.settings import CREDENTIAL_SEEDS


class CredentialsDialog(tk.Toplevel):
    def __init__(self, parent, on_save=None, initial_tab='staging'):
        super().__init__(parent)
        self.title("Credentials")
        self.resizable(False, False)
        self.grab_set()
        self.on_save = on_save

        self._entries = {}        # env -> {field: Entry}
        self._show_var = tk.BooleanVar(value=False)

        self._build(initial_tab)
        self._load_existing()
        self._position(parent)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self, initial_tab):
        pad = {"padx": 10, "pady": 4}

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        for env in ('staging', 'production'):
            tab = ttk.Frame(self._notebook, padding=4)
            self._notebook.add(tab, text=env.capitalize())
            self._entries[env] = self._build_tab(tab, env, pad)

        # Select initial tab
        idx = 0 if initial_tab == 'staging' else 1
        self._notebook.select(idx)

        # Show passwords toggle
        ttk.Checkbutton(self, text="Show passwords", variable=self._show_var,
                        command=self._toggle_visibility).pack(anchor="w", padx=14, pady=(2, 0))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(anchor="e", padx=12, pady=(4, 12))
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="right")

    def _build_tab(self, parent, env, pad):
        """Build credential fields for one environment tab. Returns {field: Entry}."""
        parent.columnconfigure(1, weight=1)
        entries = {}

        # WordPress section
        wp = ttk.LabelFrame(parent, text="WordPress", padding=8)
        wp.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        wp.columnconfigure(1, weight=1)

        for row, (label, key, secret) in enumerate([
            ("Site URL:",            "wp_url",      False),
            ("Username:",            "wp_user",     False),
            ("Application Password:", "wp_password", True),
        ]):
            ttk.Label(wp, text=label).grid(row=row, column=0, sticky="e", **pad)
            e = ttk.Entry(wp, width=38, show=("•" if secret else ""))
            e.grid(row=row, column=1, columnspan=2, sticky="ew", **pad)
            entries[key] = e

        ttk.Label(wp, text="(WP → Users → Profile → Application Passwords)",
                  foreground="gray", font=("Segoe UI", 8)).grid(
            row=3, column=1, columnspan=2, sticky="w", padx=10, pady=(0, 2))

        # SFTP section
        sftp = ttk.LabelFrame(parent, text="SFTP", padding=8)
        sftp.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        sftp.columnconfigure(1, weight=1)

        for row, (label, key, secret) in enumerate([
            ("Host:",     "sftp_host",     False),
            ("Username:", "sftp_user",     False),
            ("Password:", "sftp_password", True),
        ]):
            ttk.Label(sftp, text=label).grid(row=row, column=0, sticky="e", **pad)
            e = ttk.Entry(sftp, width=38, show=("•" if secret else ""))
            e.grid(row=row, column=1, sticky="ew", **pad)
            entries[key] = e

        return entries

    # ------------------------------------------------------------------
    # Show / hide passwords
    # ------------------------------------------------------------------

    def _toggle_visibility(self):
        show = "" if self._show_var.get() else "•"
        for env_entries in self._entries.values():
            for key, entry in env_entries.items():
                if key in ('wp_password', 'sftp_password'):
                    entry.configure(show=show)

    # ------------------------------------------------------------------
    # Placeholder helpers (WP username field)
    # ------------------------------------------------------------------

    _PLACEHOLDER = 'Enter here your Admin login email'

    def _clear_placeholder(self, widget):
        if widget.get() == self._PLACEHOLDER:
            widget.delete(0, 'end')
            widget.configure(foreground='')

    def _restore_placeholder(self, widget):
        if not widget.get().strip():
            widget.insert(0, self._PLACEHOLDER)
            widget.configure(foreground='gray')

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def _load_existing(self):
        for env, entries in self._entries.items():
            stored = cm.get_all(env)
            seeds  = CREDENTIAL_SEEDS.get(env, {})
            for key, entry in entries.items():
                value = stored.get(key) or seeds.get(key, '')
                entry.insert(0, value)
                # WP username: show placeholder when empty
                if key == 'wp_user' and not value:
                    entry.insert(0, 'Enter here your Admin login email')
                    entry.configure(foreground='gray')
                    entry.bind('<FocusIn>',  lambda e, w=entry: self._clear_placeholder(w))
                    entry.bind('<FocusOut>', lambda e, w=entry: self._restore_placeholder(w))

    def _save(self):
        # Validate: at least the active tab must be fully filled
        active_tab  = self._notebook.tab(self._notebook.select(), "text").lower()
        active_creds = {
            k: ('' if e.get().strip() == self._PLACEHOLDER else e.get().strip())
            for k, e in self._entries[active_tab].items()
        }

        if not all(active_creds.values()):
            messagebox.showwarning(
                "Missing fields",
                f"All {active_tab.capitalize()} fields are required.",
                parent=self
            )
            return

        # Save both tabs (save whatever is filled in each)
        for env, entries in self._entries.items():
            creds = {
                k: ('' if e.get().strip() == self._PLACEHOLDER else e.get().strip())
                for k, e in entries.items()
            }
            if all(creds.values()):  # only save if complete
                cm.save(creds, env)

        if self.on_save:
            self.on_save()
        self.destroy()

    # ------------------------------------------------------------------
    # Position
    # ------------------------------------------------------------------

    def _position(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + 40
        y = parent.winfo_rooty() + 40
        self.geometry(f"+{x}+{y}")
