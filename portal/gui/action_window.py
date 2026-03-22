"""
Members List action window.
Shows editable path fields (pre-filled from defaults) and a log area.
Runs the pipeline in a background thread to keep the UI responsive.

Production flow: generate PDF → open for review → confirm → upload
Staging flow:    generate PDF → upload immediately
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class MembersListWindow(tk.Toplevel):
    def __init__(self, parent, action, env='staging'):
        super().__init__(parent)
        self.title(f"Members List — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env = env

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(560, 420)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # --- Fields frame ---
        fields = ttk.LabelFrame(self, text="Paths", padding=8)
        fields.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        fields.columnconfigure(1, weight=1)

        pad = {"padx": 6, "pady": 3}

        def path_row(parent, row, label, attr):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="e", **pad)
            entry = ttk.Entry(parent)
            entry.grid(row=row, column=1, sticky="ew", **pad)
            ttk.Button(parent, text="…", width=2,
                       command=lambda e=entry: self._browse(e)).grid(row=row, column=2, **pad)
            setattr(self, attr, entry)

        path_row(fields, 0, "Raw CSV:",       '_raw_csv')
        path_row(fields, 1, "Processed CSV:", '_processed_csv')
        path_row(fields, 2, "PDF output:",    '_pdf')

        # SFTP remote path — no file browser (not a local path)
        ttk.Label(fields, text="SFTP remote path:").grid(row=3, column=0, sticky="e", **pad)
        self._sftp_remote = ttk.Entry(fields)
        self._sftp_remote.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)

        # --- Log area ---
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=10, state="disabled",
                            font=("Consolas", 9), bg="#f8f8f8", relief="flat")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # --- Bottom bar ---
        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        bottom.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(bottom, textvariable=self._status_var, foreground="gray").grid(
            row=0, column=0, sticky="w")

        self._run_btn = ttk.Button(bottom, text="Run", command=self._on_run)
        self._run_btn.grid(row=0, column=1)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def _load_defaults(self):
        defaults = self.action.get_defaults(self.env)
        self._raw_csv.insert(0,       defaults.get('raw_csv_path', ''))
        self._processed_csv.insert(0, defaults.get('processed_csv_path', ''))
        self._pdf.insert(0,           defaults.get('pdf_path', ''))
        self._sftp_remote.insert(0,   defaults.get('sftp_remote_path', ''))

    def _browse(self, entry):
        path = filedialog.asksaveasfilename(parent=self)
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    # ------------------------------------------------------------------
    # Run — Phase 1: Generate
    # ------------------------------------------------------------------

    def _on_run(self):
        raw_csv       = self._raw_csv.get().strip()
        processed_csv = self._processed_csv.get().strip()
        pdf           = self._pdf.get().strip()
        sftp_remote   = self._sftp_remote.get().strip()

        if not all([raw_csv, processed_csv, pdf, sftp_remote]):
            self._log_write("All path fields are required.\n")
            return

        self.action.save_defaults(raw_csv, processed_csv, pdf, sftp_remote, self.env)

        self._run_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Running…")

        threading.Thread(
            target=self._generate_worker,
            args=(raw_csv, processed_csv, pdf, sftp_remote),
            daemon=True
        ).start()

    def _generate_worker(self, raw_csv, processed_csv, pdf, sftp_remote):
        def progress(step, total, msg):
            self.after(0, self._log_write, f"[{step}/{total}] {msg}\n")

        result = self.action.run_generate(
            raw_csv_path=raw_csv,
            processed_csv_path=processed_csv,
            pdf_path=pdf,
            progress_callback=progress,
            env=self.env,
        )

        self.after(0, self._on_generate_done, result, pdf, sftp_remote)

    def _on_generate_done(self, result, pdf, sftp_remote):
        for line in result.details:
            if not line.startswith("["):
                self._log_write(line + "\n")

        if not result.success:
            self._status_var.set("Error.")
            self._log_write(f"\nError: {result.message}\n")
            self._run_btn.configure(text="Run", command=self._on_run, state="normal")
            if "401" in result.message:
                self._log_write("Opening credentials — please update and try again.\n")
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set("Credentials updated."))
            return

        # PDF ready — staging uploads immediately; production asks first
        if self.env == 'production':
            self._ask_upload_production(pdf, sftp_remote)
        else:
            self._status_var.set("PDF ready. Uploading…")
            self._start_upload(pdf, sftp_remote)

    # ------------------------------------------------------------------
    # Production confirmation
    # ------------------------------------------------------------------

    def _ask_upload_production(self, pdf, sftp_remote):
        self._status_var.set("PDF ready — review before uploading.")
        self._log_write("\nPDF generated. Please review it before uploading to production.\n")

        # Open the PDF in the default viewer
        try:
            os.startfile(pdf)
        except Exception as e:
            self._log_write(f"  (Could not open PDF automatically: {e})\n")

        # Replace Run button with Upload / Skip pair
        self._run_btn.grid_remove()

        btn_frame = ttk.Frame(self.nametowidget(self._run_btn.winfo_parent()))
        btn_frame.grid(row=0, column=1)
        self._confirm_frame = btn_frame

        ttk.Button(
            btn_frame, text="Upload to Production",
            command=lambda: self._confirm_upload(pdf, sftp_remote, btn_frame)
        ).pack(side="left", padx=(0, 4))

        ttk.Button(
            btn_frame, text="Skip Upload",
            command=lambda: self._skip_upload(btn_frame)
        ).pack(side="left")

    def _confirm_upload(self, pdf, sftp_remote, btn_frame):
        btn_frame.destroy()
        self._run_btn.grid()
        self._run_btn.configure(state="disabled")
        self._status_var.set("Uploading…")
        self._start_upload(pdf, sftp_remote)

    def _skip_upload(self, btn_frame):
        btn_frame.destroy()
        self._run_btn.grid()
        self._log_write("Upload skipped. PDF saved locally.\n")
        self._status_var.set("Done (not uploaded).")
        self._run_btn.configure(text="Done", command=self.destroy, state="normal")

    # ------------------------------------------------------------------
    # Run — Phase 2: Upload
    # ------------------------------------------------------------------

    def _start_upload(self, pdf, sftp_remote):
        threading.Thread(
            target=self._upload_worker,
            args=(pdf, sftp_remote),
            daemon=True
        ).start()

    def _upload_worker(self, pdf, sftp_remote):
        def progress(step, total, msg):
            self.after(0, self._log_write, f"[upload] {msg}\n")

        result = self.action.run_upload(
            pdf_path=pdf,
            sftp_remote_path=sftp_remote,
            progress_callback=progress,
            env=self.env,
        )

        self.after(0, self._on_upload_done, result)

    def _on_upload_done(self, result):
        for line in result.details:
            if not line.startswith("["):
                self._log_write(line + "\n")

        if result.success:
            self._status_var.set("Done.")
            self._log_write("\nDone.\n")
            self._run_btn.configure(text="Done", command=self.destroy, state="normal")
        else:
            self._status_var.set("Upload failed.")
            self._log_write(f"\nUpload error: {result.message}\n")
            self._run_btn.configure(text="Run", command=self._on_run, state="normal")

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
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
