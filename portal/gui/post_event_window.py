"""
Post & Event window.

Flow:
  1. User fills in Title, Date, Description, Image.
  2. "Create Post" runs in a background thread.
  3. Result shown in the log.
"""
import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.post_event_action import PostEventAction

# Pillow is used for clipboard grab and thumbnail preview.
try:
    from PIL import Image, ImageTk, ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


class PostEventWindow(tk.Toplevel):
    def __init__(self, parent, action: PostEventAction, env='staging'):
        super().__init__(parent)
        self.title(f"Post & Event — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action  = action
        self.env     = env

        self._image_path  = None   # path to the image file to upload
        self._image_temp  = False  # True if the file is a temp file (clipboard paste)
        self._thumb_photo = None   # kept alive to prevent GC

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(480, 480)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        pad = {"padx": 8, "pady": 4}

        # --- Details section ---
        details = ttk.LabelFrame(self, text="Event Details", padding=8)
        details.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        details.columnconfigure(1, weight=1)

        # Title
        ttk.Label(details, text="Title:").grid(row=0, column=0, sticky="e", **pad)
        self._title_var = tk.StringVar()
        ttk.Entry(details, textvariable=self._title_var).grid(
            row=0, column=1, columnspan=2, sticky="ew", **pad)

        # Date
        ttk.Label(details, text="Date:").grid(row=1, column=0, sticky="e", **pad)
        self._date_var = tk.StringVar()
        ttk.Entry(details, textvariable=self._date_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", **pad)

        # Description
        ttk.Label(details, text="Description:").grid(row=2, column=0, sticky="ne", **pad)
        self._desc_text = tk.Text(details, height=4, wrap="word", font=("Segoe UI", 9))
        self._desc_text.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)

        # Image — path entry + buttons
        ttk.Label(details, text="Image:").grid(row=3, column=0, sticky="ne", **pad)

        img_frame = ttk.Frame(details)
        img_frame.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)
        img_frame.columnconfigure(0, weight=1)

        self._img_path_var = tk.StringVar(value="No image selected")
        ttk.Entry(img_frame, textvariable=self._img_path_var,
                  state="readonly").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(img_frame, text="Browse…",
                   command=self._browse_image).grid(row=0, column=1)

        paste_btn = ttk.Button(img_frame, text="Paste from clipboard",
                               command=self._paste_image,
                               state="normal" if _PIL_AVAILABLE else "disabled")
        paste_btn.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        if not _PIL_AVAILABLE:
            ttk.Label(img_frame, text="(Install Pillow to enable clipboard paste)",
                      foreground="gray", font=("Segoe UI", 8)).grid(
                row=2, column=0, columnspan=2, sticky="w")

        # Thumbnail
        self._thumb_label = ttk.Label(details, text="")
        self._thumb_label.grid(row=4, column=1, sticky="w", padx=8, pady=(0, 4))

        # --- Log area ---
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
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
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 12))
        bottom.columnconfigure(0, weight=1)

        self._status_var = tk.StringVar(value="Fill in the details and click Create Post.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=0, sticky="w")

        btn_row = ttk.Frame(bottom)
        btn_row.grid(row=0, column=1, sticky="e")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._create_btn = ttk.Button(btn_row, text="Create Post", command=self._on_create)
        self._create_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Defaults / persistence
    # ------------------------------------------------------------------

    def _load_defaults(self):
        title = dm.get('post_event', 'title')
        if title:
            self._title_var.set(title)

        date = dm.get('post_event', 'date')
        if date:
            self._date_var.set(date)

        desc = dm.get('post_event', 'description')
        if desc:
            self._desc_text.insert("1.0", desc)

        image_path = dm.get('post_event', 'image_path')
        if image_path and os.path.exists(image_path):
            self._set_image(image_path, is_temp=False)

    def _save_defaults(self, title, date, description, image_path):
        dm.set_default('post_event', 'title',       title)
        dm.set_default('post_event', 'date',        date)
        dm.set_default('post_event', 'description', description)
        if image_path and not self._image_temp:
            dm.set_default('post_event', 'image_path', image_path)

    # ------------------------------------------------------------------
    # Image selection
    # ------------------------------------------------------------------

    def _browse_image(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._set_image(path, is_temp=False)

    def _paste_image(self):
        if not _PIL_AVAILABLE:
            return
        img = ImageGrab.grabclipboard()
        if img is None:
            messagebox.showwarning("Nothing on clipboard",
                                   "No image found on the clipboard.", parent=self)
            return
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(tmp.name, 'PNG')
        tmp.close()
        self._set_image(tmp.name, is_temp=True)

    def _set_image(self, path: str, is_temp: bool):
        # Clean up previous temp file if any.
        if self._image_temp and self._image_path and os.path.exists(self._image_path):
            try:
                os.unlink(self._image_path)
            except OSError:
                pass

        self._image_path = path
        self._image_temp = is_temp
        label = "Pasted image" if is_temp else os.path.basename(path)
        self._img_path_var.set(label)
        self._update_thumbnail(path)

    def _update_thumbnail(self, path: str):
        if not _PIL_AVAILABLE:
            return
        try:
            img = Image.open(path)
            img.thumbnail((160, 100))
            self._thumb_photo = ImageTk.PhotoImage(img)
            self._thumb_label.configure(image=self._thumb_photo, text="")
        except Exception:
            self._thumb_label.configure(image="", text="(preview unavailable)")

    # ------------------------------------------------------------------
    # Create post
    # ------------------------------------------------------------------

    def _on_create(self):
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Enter a title.", parent=self)
            return

        date = self._date_var.get().strip()
        if not date:
            messagebox.showwarning("Missing date", "Enter a date.", parent=self)
            return

        description = self._desc_text.get("1.0", tk.END).strip()
        if not description:
            messagebox.showwarning("Missing description",
                                   "Enter a description.", parent=self)
            return

        if not self._image_path:
            messagebox.showwarning("Missing image",
                                   "Select or paste an image.", parent=self)
            return

        self._save_defaults(title, date, description, self._image_path)
        self._create_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Creating post…")
        self._log_write(f"Title:       {title}\n")
        self._log_write(f"Date:        {date}\n")
        self._log_write(f"Description: {description[:60]}{'…' if len(description) > 60 else ''}\n")
        self._log_write(f"Image:       {self._img_path_var.get()}\n\n")

        threading.Thread(
            target=self._run_create,
            args=(title, date, description, self._image_path),
            daemon=True,
        ).start()

    def _run_create(self, title, date, description, image_path):
        result = self.action.run(
            title=title, date=date, description=description,
            image_path=image_path, env=self.env,
        )
        self.after(0, self._finish_create, result)

    def _finish_create(self, result):
        if result.success:
            self._log_write(f"Done. {result.message}\n")
            if result.data:
                self._log_write(f"Preview URL: {result.data}\n")
            self._status_var.set("Post created as draft.")
        else:
            self._log_write(f"Error: {result.message}\n")
            self._status_var.set("Failed.")
        self._create_btn.configure(state="normal")

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
        x = parent.winfo_rootx() + 80
        y = parent.winfo_rooty() + 60
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        w = self.winfo_width()
        h = self.winfo_height()
        x = max(40, min(x, screen_w - w - 20))
        y = max(40, min(y, screen_h - h - 40))
        self.geometry(f"+{x}+{y}")

    def destroy(self):
        # Clean up any temp image file created from clipboard paste.
        if self._image_temp and self._image_path and os.path.exists(self._image_path):
            try:
                os.unlink(self._image_path)
            except OSError:
                pass
        super().destroy()
