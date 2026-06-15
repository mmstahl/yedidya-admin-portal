"""
Update Product Prices window.

Flow:
  1. User picks an Excel file
  2. "Preview" parses the file and fetches each product from WooCommerce
     → shows table: Product | ID | Type | Current Price | New Price
  3. User confirms → prices are updated in sequence with progress log
"""
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.update_prices_action import UpdatePricesAction


class UpdatePricesWindow(tk.Toplevel):
    def __init__(self, parent, action: UpdatePricesAction, env='staging'):
        super().__init__(parent)
        self.title(f"Update Product Prices — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env = env
        self._preview_rows = []
        self._preview_done = False

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(660, 520)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        pad = {"padx": 8, "pady": 4}

        # --- File picker ---
        file_frame = ttk.LabelFrame(self, text="Input Excel file", padding=8)
        file_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="Excel file:").grid(row=0, column=0, sticky="e", **pad)
        self._file_path = ttk.Entry(file_frame)
        self._file_path.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(file_frame, text="…", width=2,
                   command=self._browse_file).grid(row=0, column=2, **pad)
        ttk.Label(file_frame,
                  text="Required columns: ID, Regular price, Minimum price.",
                  foreground="gray", font=("Segoe UI", 8)).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=8)

        self._preview_btn = ttk.Button(file_frame, text="Preview",
                                       command=self._on_preview)
        self._preview_btn.grid(row=0, column=3, **pad)

        # --- Preview table ---
        preview_frame = ttk.LabelFrame(self, text="Products to update", padding=8)
        preview_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        preview_frame.columnconfigure(0, weight=1)

        cols = ("name", "id", "type", "current", "new")
        self._tree = ttk.Treeview(preview_frame, columns=cols, show="headings", height=7)
        self._tree.heading("name",    text="Product")
        self._tree.heading("id",      text="ID")
        self._tree.heading("type",    text="Type")
        self._tree.heading("current", text="Current price")
        self._tree.heading("new",     text="New price")
        self._tree.column("name",    width=260)
        self._tree.column("id",      width=60,  anchor="center")
        self._tree.column("type",    width=120, anchor="center")
        self._tree.column("current", width=110, anchor="center")
        self._tree.column("new",     width=110, anchor="center")

        vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="ew")
        vsb.grid(row=0, column=1, sticky="ns")

        # --- Log area ---
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=7, state="disabled",
                            font=("Consolas", 9), bg="#f8f8f8", relief="flat")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Bottom bar ---
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        bottom.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Select an Excel file and click Preview.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=0, sticky="w")

        btn_frame = ttk.Frame(bottom)
        btn_frame.grid(row=0, column=1, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._update_btn = ttk.Button(btn_frame, text="Update prices",
                                      command=self._on_update, state="disabled")
        self._update_btn.pack(side="right")

    # ------------------------------------------------------------------
    # File browse
    # ------------------------------------------------------------------

    def _load_defaults(self):
        saved = dm.get('update_prices', 'file_path')
        if saved:
            self._file_path.insert(0, saved)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if path:
            self._file_path.delete(0, tk.END)
            self._file_path.insert(0, path)
            dm.set_default('update_prices', 'file_path', path)
            self._reset_preview()

    def _reset_preview(self):
        self._preview_done = False
        self._preview_rows = []
        self._update_btn.configure(state="disabled")
        for item in self._tree.get_children():
            self._tree.delete(item)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _on_preview(self):
        path = self._file_path.get().strip()
        if not path:
            messagebox.showwarning("No file", "Please select an Excel file first.", parent=self)
            return
        self._reset_preview()
        self._preview_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Parsing file…")
        threading.Thread(target=self._run_preview, args=(path,), daemon=True).start()

    def _run_preview(self, path):
        rows, error = self.action.parse_excel(path)
        if error:
            self.after(0, self._show_error, error)
            return

        self.after(0, self._status_var.set,
                   f"Fetching {len(rows)} product(s) from WordPress…")

        preview_rows, error = self.action.preview(rows, env=self.env)
        self.after(0, self._show_preview, preview_rows, error)

    def _show_error(self, error):
        self._preview_btn.configure(state="normal")
        self._status_var.set("Validation failed.")
        self._log_write(f"Error: {error}\n")

    def _show_preview(self, preview_rows, error):
        self._preview_btn.configure(state="normal")

        if error:
            self._status_var.set("Could not load products.")
            self._log_write(f"Error: {error}\n")
            if "401" in error:
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Try preview again."))
            return

        type_labels = {'regular': 'Regular', 'min': 'Name Your Price'}
        for prow in preview_rows:
            self._tree.insert("", tk.END, values=(
                prow['name'],
                prow['id'],
                type_labels.get(prow['price_type'], prow['price_type']),
                prow['current_price'],
                prow['new_price'],
            ))

        self._preview_rows = preview_rows
        self._preview_done = True
        self._update_btn.configure(state="normal")

        reg_count = sum(1 for p in preview_rows if p['price_type'] == 'regular')
        min_count = sum(1 for p in preview_rows if p['price_type'] == 'min')
        parts = []
        if reg_count:
            parts.append(f"{reg_count} regular price{'s' if reg_count > 1 else ''}")
        if min_count:
            parts.append(f"{min_count} minimum price{'s' if min_count > 1 else ''}")
        self._status_var.set(f"Ready to update: {', '.join(parts)}.")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def _on_update(self):
        if not self._preview_rows:
            return

        reg_count = sum(1 for p in self._preview_rows if p['price_type'] == 'regular')
        min_count = sum(1 for p in self._preview_rows if p['price_type'] == 'min')
        parts = []
        if reg_count:
            parts.append(f"{reg_count} regular price{'s' if reg_count > 1 else ''}")
        if min_count:
            parts.append(f"{min_count} minimum price{'s' if min_count > 1 else ''}")
        summary = ", ".join(parts)

        confirmed = messagebox.askyesno(
            "Confirm Update",
            f"Update {summary} in {self.env}?\n\nThis will overwrite the current prices.",
            icon="warning" if self.env == 'production' else "question",
            parent=self
        )
        if not confirmed:
            return

        self._update_btn.configure(state="disabled")
        self._preview_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Updating…")

        threading.Thread(target=self._run_update, daemon=True).start()

    def _run_update(self):
        def progress(current, total, msg):
            self.after(0, self._log_write, f"[{current}/{total}] {msg}\n")

        result = self.action.run(
            preview_rows=self._preview_rows,
            env=self.env,
            progress_callback=progress,
        )
        self.after(0, self._finish_update, result)

    def _finish_update(self, result):
        for line in result.details:
            if not line.startswith("["):
                self._log_write(line + "\n")

        if result.success:
            self._status_var.set(result.message)
            self._log_write(f"\nDone. {result.message}\n")
            self._update_btn.configure(text="Done", command=self.destroy, state="normal")
        else:
            self._status_var.set("Completed with errors.")
            self._log_write(f"\n{result.message}\n")
            self._update_btn.configure(state="normal")
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
        x = parent.winfo_rootx() + 80
        y = parent.winfo_rooty() + 60
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(40, min(x, screen_w - w - 20))
        y = max(40, min(y, screen_h - h - 40))
        self.geometry(f"+{x}+{y}")
