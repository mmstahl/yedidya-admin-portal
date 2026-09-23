"""
Approve / Deny Users action window.

Flow:
  1. User picks a CSV file (columns: email, setting)
  2. "Preview" looks up each user → shows current and new status
  3. User confirms → status changes run in a background thread
  4. Per-user results shown in log
"""
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.user_status_action import UserStatusAction, status_label

ACTION_TEXT = {
    'change':  'Will change',
    'skip':    'No change',
    'blocked': "Admin — can't deny",
}


class UserStatusWindow(tk.Toplevel):
    def __init__(self, parent, action: UserStatusAction, env='staging'):
        super().__init__(parent)
        self.title(f"Approve / Deny Users — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env = env
        self._preview_users = []   # list from action.preview()

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(640, 480)

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
                  text="CSV must have 'email' and 'setting' columns. Setting is Approve or Deny.",
                  foreground="gray", font=("Segoe UI", 8)).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=8)

        self._preview_btn = ttk.Button(file_frame, text="Preview",
                                       command=self._on_preview)
        self._preview_btn.grid(row=0, column=3, **pad)

        # --- Preview table ---
        preview_frame = ttk.LabelFrame(self, text="Users found in WordPress", padding=8)
        preview_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        preview_frame.columnconfigure(0, weight=1)

        cols = ("name", "email", "current", "new", "action")
        self._tree = ttk.Treeview(preview_frame, columns=cols, show="headings", height=8)
        for col, text, width in (("name",    "Name",           160),
                                 ("email",   "Email",          200),
                                 ("current", "Current",         80),
                                 ("new",     "New",             80),
                                 ("action",  "Result",         110)):
            self._tree.heading(col, text=text)
            self._tree.column(col, width=width)
        vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="ew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._tree.tag_configure("change",  foreground="#1f5fa8")
        self._tree.tag_configure("skip",    foreground="gray")
        self._tree.tag_configure("blocked", foreground="#c0392b")
        self._tree.tag_configure("missing", foreground="gray")

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
        bottom.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Select a CSV and click Preview.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(bottom)
        btn_frame.grid(row=0, column=1, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._apply_btn = ttk.Button(btn_frame, text="Apply Changes",
                                     command=self._on_apply, state="disabled")
        self._apply_btn.pack(side="right")

    # ------------------------------------------------------------------
    # CSV browse
    # ------------------------------------------------------------------

    def _load_defaults(self):
        saved = dm.get('user_status', 'csv_path')
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
            dm.set_default('user_status', 'csv_path', path)
            self._reset_preview()

    def _reset_preview(self):
        self._preview_users = []
        self._apply_btn.configure(state="disabled")
        for item in self._tree.get_children():
            self._tree.delete(item)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_preview(self):
        path = self._csv_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Please select a CSV file first.", parent=self)
            return
        self._reset_preview()
        self._log_clear()
        self._preview_btn.configure(state="disabled")
        self._status_var.set("Looking up users…")
        threading.Thread(target=self._run_preview, args=(path,), daemon=True).start()

    def _run_preview(self, path):
        users, not_found, invalid, error = self.action.preview(path, env=self.env)
        self.after(0, self._show_preview, users, not_found, invalid, error)

    def _show_preview(self, users, not_found, invalid, error):
        self._preview_btn.configure(state="normal")

        if invalid:
            self._log_write(f"Skipped CSV rows ({len(invalid)}):\n" +
                            "".join(f"  • {r}\n" for r in invalid) + "\n")

        if error:
            self._status_var.set("Could not preview. See the log.")
            self._log_write(f"{error}\n")
            if "401" in error:
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Try preview again."))
            return

        for u in users:
            self._tree.insert("", tk.END, values=(
                u['name'], u['email'],
                status_label(u['current']), status_label(u['target']),
                ACTION_TEXT[u['action']],
            ), tags=(u['action'],))
        for email in not_found:
            self._tree.insert("", tk.END, values=("—", email, "—", "—", "Not found"),
                              tags=("missing",))

        self._preview_users = users
        changes = sum(1 for u in users if u['action'] == 'change')
        skips   = sum(1 for u in users if u['action'] == 'skip')
        blocked = [u for u in users if u['action'] == 'blocked']

        if not_found:
            self._log_write(f"Not found in WordPress ({len(not_found)}): " +
                            ", ".join(not_found) + "\n")
        if blocked:
            self._log_write("Administrators cannot be denied — skipped: " +
                            ", ".join(u['email'] for u in blocked) + "\n")

        parts = [f"{changes} user(s) will change"]
        if skips:
            parts.append(f"{skips} already set")
        if not_found:
            parts.append(f"{len(not_found)} not found")
        self._status_var.set(". ".join(parts) + ".")

        self._apply_btn.configure(state="normal" if changes else "disabled")

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def _on_apply(self):
        to_change = [u for u in self._preview_users if u['action'] == 'change']
        if not to_change:
            return

        approve = sum(1 for u in to_change if u['target'] == 'approved')
        deny    = len(to_change) - approve
        env_note = "\n\n⚠ This is the PRODUCTION site." if self.env == 'production' else ""
        confirmed = messagebox.askyesno(
            "Confirm Changes",
            f"Set {approve} user(s) to Approved and {deny} user(s) to Denied?\n\n"
            "Denied users will not be able to log in. "
            "No emails will be sent to the users." + env_note,
            icon="warning",
            parent=self
        )
        if not confirmed:
            return

        self._apply_btn.configure(state="disabled")
        self._preview_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Updating…")

        threading.Thread(target=self._run_apply, args=(self._preview_users,),
                         daemon=True).start()

    def _run_apply(self, users):
        def progress(current, total, msg):
            self.after(0, self._log_write, f"[{current}/{total}] {msg}\n")

        result = self.action.run(users, progress_callback=progress, env=self.env)
        self.after(0, self._finish_apply, result)

    def _finish_apply(self, result):
        # Rewrite the log so each result sits under its user line
        self._log_clear()
        for line in result.details:
            self._log_write(line + "\n")

        if result.success:
            self._status_var.set(result.message)
            self._log_write(f"\nDone. {result.message}\n")
            self._apply_btn.configure(text="Done", command=self.destroy, state="normal")
        else:
            self._status_var.set("Completed with errors.")
            self._log_write(f"\n{result.message}\n")
            self._preview_btn.configure(state="normal")
            if any("401" in line for line in result.details):
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Click Preview again."))

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
        x = parent.winfo_rootx() + 80
        y = parent.winfo_rooty() + 60
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(40, min(x, screen_w - w - 20))
        y = max(40, min(y, screen_h - h - 40))
        self.geometry(f"+{x}+{y}")
