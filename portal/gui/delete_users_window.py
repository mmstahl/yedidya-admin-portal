"""
Delete Users action window.

Flow:
  1. User picks a CSV file
  2. "Preview" looks up each email → shows matched / not-found table
  3. User selects delete mode (standard / GDPR checkbox)
  4. User confirms → pipeline runs in background thread
  5. Per-user results shown in log
"""
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.delete_users_action import DeleteUsersAction


class DeleteUsersWindow(tk.Toplevel):
    def __init__(self, parent, action: DeleteUsersAction, env='staging'):
        super().__init__(parent)
        self.title(f"Delete Users — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env = env
        self._preview_users    = []   # list of {email, id, display_name} — WP account found
        self._not_found_emails = []   # emails from CSV with no WP account
        self._preview_done     = False

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(560, 480)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        pad = {"padx": 8, "pady": 4}

        # --- CSV picker ---
        file_frame = ttk.LabelFrame(self, text="Input CSV", padding=8)
        file_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="CSV file:").grid(row=0, column=0, sticky="e", **pad)
        self._csv_path = ttk.Entry(file_frame)
        self._csv_path.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(file_frame, text="…", width=2,
                   command=self._browse_csv).grid(row=0, column=2, **pad)
        ttk.Label(file_frame,
                  text="CSV must have an 'email' column (or email as the first column).",
                  foreground="gray", font=("Segoe UI", 8)).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=8)

        self._preview_btn = ttk.Button(file_frame, text="Preview",
                                       command=self._on_preview)
        self._preview_btn.grid(row=0, column=3, **pad)

        # --- Preview table ---
        preview_frame = ttk.LabelFrame(self, text="Users found in WordPress", padding=8)
        preview_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        preview_frame.columnconfigure(0, weight=1)

        cols = ("name", "email", "status")
        self._tree = ttk.Treeview(preview_frame, columns=cols, show="headings", height=6)
        self._tree.heading("name",   text="Name")
        self._tree.heading("email",  text="Email")
        self._tree.heading("status", text="Status")
        self._tree.column("name",   width=180)
        self._tree.column("email",  width=220)
        self._tree.column("status", width=100)
        vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="ew")
        vsb.grid(row=0, column=1, sticky="ns")

        # --- Log area ---
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=8, state="disabled",
                            font=("Consolas", 9), bg="#f8f8f8", relief="flat")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Bottom bar ---
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        bottom.columnconfigure(1, weight=1)

        # GDPR checkbox
        self._gdpr_var = tk.BooleanVar(value=False)
        self._gdpr_cb = ttk.Checkbutton(
            bottom, text="GDPR erase (also deletes payment history)",
            variable=self._gdpr_var,
            command=self._on_gdpr_toggle
        )
        self._gdpr_cb.grid(row=0, column=0, sticky="w")

        # Status + action buttons
        self._status_var = tk.StringVar(value="Select a CSV and click Preview.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=1, column=0, sticky="w")

        btn_frame = ttk.Frame(bottom)
        btn_frame.grid(row=1, column=1, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._delete_btn = ttk.Button(btn_frame, text="Delete",
                                      command=self._on_delete, state="disabled")
        self._delete_btn.pack(side="right")

    # ------------------------------------------------------------------
    # CSV browse
    # ------------------------------------------------------------------

    def _load_defaults(self):
        saved = dm.get('delete_users', 'csv_path')
        if saved:
            self._csv_path.insert(0, saved)

    def _browse_csv(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self._csv_path.delete(0, tk.END)
            self._csv_path.insert(0, path)
            dm.set_default('delete_users', 'csv_path', path)
            self._reset_preview()

    def _reset_preview(self):
        self._preview_done     = False
        self._preview_users    = []
        self._not_found_emails = []
        self._delete_btn.configure(state="disabled")
        for item in self._tree.get_children():
            self._tree.delete(item)

    def _refresh_delete_btn(self):
        """Enable Delete if there is something actionable given the current mode."""
        has_found     = bool(self._preview_users)
        has_not_found = bool(self._not_found_emails)
        gdpr          = self._gdpr_var.get()
        if has_found or (gdpr and has_not_found):
            self._delete_btn.configure(state="normal")
        else:
            self._delete_btn.configure(state="disabled")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_preview(self):
        path = self._csv_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Please select a CSV file first.", parent=self)
            return
        self._reset_preview()
        self._preview_btn.configure(state="disabled")
        self._status_var.set("Looking up users…")
        threading.Thread(target=self._run_preview, args=(path,), daemon=True).start()

    def _run_preview(self, path):
        found, not_found, error = self.action.preview(path, env=self.env)
        self.after(0, self._show_preview, found, not_found, error)

    def _show_preview(self, found, not_found, warning):
        self._preview_btn.configure(state="normal")

        # A hard stop — no results at all and a 401/403
        if warning and not found and not not_found:
            self._status_var.set("Error during preview.")
            self._log_write(f"Error: {warning}\n")
            if "401" in warning:
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Try preview again."))
            return

        # Per-user warnings — show them but continue to display results
        if warning:
            self._log_write(f"{warning}\n\n")

        for user in found:
            self._tree.insert("", tk.END, values=(
                user['display_name'], user['email'], "Will be deleted"
            ), tags=("found",))
        for email in not_found:
            self._tree.insert("", tk.END, values=("—", email, "Not found"),
                              tags=("missing",))

        self._tree.tag_configure("found",   foreground="#c0392b")
        self._tree.tag_configure("missing", foreground="gray")

        self._preview_users    = found
        self._not_found_emails = not_found
        self._preview_done     = True
        self._refresh_delete_btn()

        if found and not_found:
            self._status_var.set(
                f"{len(found)} user(s) found. {len(not_found)} not found in WordPress.")
        elif found:
            self._status_var.set(f"{len(found)} user(s) will be deleted.")
        elif not_found:
            self._status_var.set(
                f"No active WP accounts found. {len(not_found)} email(s) may still have "
                f"WooCommerce data — enable GDPR Erase to clean up.")

        if not_found:
            self._log_write(f"Not found in WordPress ({len(not_found)}): " +
                            ", ".join(not_found) + "\n")

    # ------------------------------------------------------------------
    # GDPR toggle
    # ------------------------------------------------------------------

    def _on_gdpr_toggle(self):
        if self._gdpr_var.get():
            confirmed = messagebox.askyesno(
                "GDPR Erase — Warning",
                "This will delete the history of the user's payments to Yedidya "
                "across the years.\n\nAre you sure you want to do that?",
                icon="warning",
                parent=self
            )
            if not confirmed:
                self._gdpr_var.set(False)
        self._refresh_delete_btn()

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _on_delete(self):
        gdpr = self._gdpr_var.get()

        # Build the full list of users to process
        users_to_run = list(self._preview_users)
        if gdpr:
            # Add not-found emails as WooCommerce-only targets (no WP account to delete)
            for email in self._not_found_emails:
                users_to_run.append({
                    'email': email,
                    'id': None,
                    'display_name': '(no WP account)',
                })

        if not users_to_run:
            return

        mode = "GDPR erase" if gdpr else "standard delete"
        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Process {len(users_to_run)} email(s) using {mode}?\n\n"
            "This cannot be undone.",
            icon="warning",
            parent=self
        )
        if not confirmed:
            return

        self._delete_btn.configure(state="disabled")
        self._preview_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Deleting…")

        threading.Thread(
            target=self._run_delete,
            args=(users_to_run, gdpr),
            daemon=True
        ).start()

    def _run_delete(self, users, gdpr):
        def progress(current, total, msg):
            self.after(0, self._log_write, f"[{current}/{total}] {msg}\n")

        result = self.action.run(
            users_to_delete=users,
            gdpr_mode=gdpr,
            progress_callback=progress,
            env=self.env,
        )
        self.after(0, self._finish_delete, result)

    def _finish_delete(self, result):
        for line in result.details:
            if not line.startswith("["):
                self._log_write(line + "\n")

        if result.success:
            self._status_var.set(result.message)
            self._log_write(f"\nDone. {result.message}\n")
            self._delete_btn.configure(text="Done", command=self.destroy, state="normal")
        else:
            self._status_var.set("Completed with errors.")
            self._log_write(f"\n{result.message}\n")
            self._delete_btn.configure(state="normal")
            self._preview_btn.configure(state="normal")
            if any("401" in line for line in result.details):
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Try again."))

    # ------------------------------------------------------------------
    # Log helpers
    # ------------------------------------------------------------------

    def _log_write(self, text):
        self._log.configure(state="normal")
        self._log.insert(tk.END, text)
        self._log.see(tk.END)
        self._log.configure(state="disabled")

    def _log_clear(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", tk.END)
        self._log.configure(state="disabled")

    def _center(self, parent):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        # Offset from parent top-left so both windows are visible
        x = parent.winfo_rootx() + 80
        y = parent.winfo_rooty() + 60
        # Clamp so the window stays fully on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(40, min(x, screen_w - w - 20))
        y = max(40, min(y, screen_h - h - 40))
        self.geometry(f"+{x}+{y}")
