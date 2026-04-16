"""
DB Extract action window.

Flow:
  1. User enters (or loads a saved preset of) a comma-delimited field list
  2. User picks an output CSV path
  3. "Extract" runs in a background thread
  4. Result shown in the log

Presets are stored as a JSON object in defaults_manager under
  db_extract / presets   →  {"Preset name": "field1,field2,..."}
  db_extract / csv_path  →  last-used output path
"""
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import defaults_manager as dm
from portal.actions.db_extract_action import DbExtractAction


class DbExtractWindow(tk.Toplevel):
    def __init__(self, parent, action: DbExtractAction, env='staging'):
        super().__init__(parent)
        self.title(f"DB Extract — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env = env

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(520, 420)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        pad = {"padx": 8, "pady": 4}

        # --- Fields section ---
        fields_frame = ttk.LabelFrame(self, text="Fields", padding=8)
        fields_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        fields_frame.columnconfigure(1, weight=1)

        # Preset row
        ttk.Label(fields_frame, text="Preset:").grid(row=0, column=0, sticky="e", **pad)

        self._preset_var = tk.StringVar()
        self._preset_cb = ttk.Combobox(
            fields_frame, textvariable=self._preset_var,
            state="readonly", width=28,
        )
        self._preset_cb.grid(row=0, column=1, sticky="ew", **pad)
        self._preset_cb.bind("<<ComboboxSelected>>", self._on_preset_selected)

        btn_frame = ttk.Frame(fields_frame)
        btn_frame.grid(row=0, column=2, **pad)
        ttk.Button(btn_frame, text="Save",   width=6, command=self._save_preset).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", width=6, command=self._delete_preset).pack(side="left", padx=2)

        # Field list entry
        ttk.Label(fields_frame, text="Fields:").grid(row=1, column=0, sticky="ne", pady=(6, 4), padx=8)
        self._fields_text = tk.Text(fields_frame, height=3, wrap="word",
                                    font=("Consolas", 9))
        self._fields_text.grid(row=1, column=1, columnspan=2, sticky="ew", **pad)

        ttk.Label(
            fields_frame,
            text="Additional fields to extract, comma-separated. "
                 "user_login and user_email are always included as the first two columns. "
                 "Add wp_users columns (e.g. display_name) or usermeta keys (e.g. first_name, cellphone1).",
            foreground="gray", font=("Segoe UI", 8), wraplength=420,
        ).grid(row=2, column=1, columnspan=2, sticky="w", padx=8)

        # --- Output section ---
        output_frame = ttk.LabelFrame(self, text="Output", padding=8)
        output_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="CSV file:").grid(row=0, column=0, sticky="e", **pad)
        self._csv_path = ttk.Entry(output_frame)
        self._csv_path.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(output_frame, text="…", width=2,
                   command=self._browse_csv).grid(row=0, column=2, **pad)

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

        self._status_var = tk.StringVar(value="Enter fields and an output path, then click Extract.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=0, sticky="w")

        btn_row = ttk.Frame(bottom)
        btn_row.grid(row=0, column=1, sticky="e")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._extract_btn = ttk.Button(btn_row, text="Extract", command=self._on_extract)
        self._extract_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Defaults / persistence
    # ------------------------------------------------------------------

    def _load_defaults(self):
        saved_path = dm.get('db_extract', 'csv_path')
        if saved_path:
            self._csv_path.insert(0, saved_path)
        self._refresh_presets()

    def _load_presets(self) -> dict:
        raw = dm.get('db_extract', 'presets')
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _store_presets(self, presets: dict):
        dm.set_default('db_extract', 'presets', json.dumps(presets, ensure_ascii=False))

    def _refresh_presets(self):
        presets = self._load_presets()
        names = sorted(presets.keys())
        self._preset_cb['values'] = names
        if self._preset_var.get() not in names:
            self._preset_var.set('')

    # ------------------------------------------------------------------
    # Preset actions
    # ------------------------------------------------------------------

    def _on_preset_selected(self, _event=None):
        name = self._preset_var.get()
        presets = self._load_presets()
        if name in presets:
            self._fields_text.delete("1.0", tk.END)
            self._fields_text.insert("1.0", presets[name])

    def _save_preset(self):
        fields = self._fields_text.get("1.0", tk.END).strip()
        if not fields:
            messagebox.showwarning("No fields", "Enter a field list before saving.", parent=self)
            return
        name = simpledialog.askstring(
            "Save preset", "Preset name:", parent=self,
            initialvalue=self._preset_var.get() or "",
        )
        if not name or not name.strip():
            return
        name = name.strip()
        presets = self._load_presets()
        presets[name] = fields
        self._store_presets(presets)
        self._refresh_presets()
        self._preset_var.set(name)

    def _delete_preset(self):
        name = self._preset_var.get()
        if not name:
            return
        if not messagebox.askyesno("Delete preset",
                                   f'Delete preset "{name}"?', parent=self):
            return
        presets = self._load_presets()
        presets.pop(name, None)
        self._store_presets(presets)
        self._preset_var.set('')
        self._refresh_presets()

    # ------------------------------------------------------------------
    # CSV path
    # ------------------------------------------------------------------

    def _browse_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self._csv_path.delete(0, tk.END)
            self._csv_path.insert(0, path)
            dm.set_default('db_extract', 'csv_path', path)

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------

    def _on_extract(self):
        fields_raw = self._fields_text.get("1.0", tk.END).strip()
        if not fields_raw:
            messagebox.showwarning("No fields", "Enter at least one field name.", parent=self)
            return

        fields = [f.strip() for f in fields_raw.split(',') if f.strip()]
        if not fields:
            messagebox.showwarning("No fields", "Enter at least one field name.", parent=self)
            return

        csv_path = self._csv_path.get().strip()
        if not csv_path:
            messagebox.showwarning("No output path", "Choose an output CSV file.", parent=self)
            return

        dm.set_default('db_extract', 'csv_path', csv_path)

        self._extract_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Extracting…")
        self._log_write(f"Fields: {', '.join(fields)}\n")
        self._log_write(f"Output: {csv_path}\n\n")

        threading.Thread(
            target=self._run_extract,
            args=(fields, csv_path),
            daemon=True,
        ).start()

    def _run_extract(self, fields, csv_path):
        result = self.action.run(fields=fields, csv_path=csv_path, env=self.env)
        self.after(0, self._finish_extract, result)

    def _finish_extract(self, result):
        if result.success:
            self._log_write(f"Done. {result.message}\n")
            self._status_var.set(result.message)
            self._extract_btn.configure(text="Done", command=self.destroy, state="normal")
        else:
            self._log_write(f"Error: {result.message}\n")
            self._status_var.set("Failed.")
            self._extract_btn.configure(state="normal")
            if "401" in result.message:
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
