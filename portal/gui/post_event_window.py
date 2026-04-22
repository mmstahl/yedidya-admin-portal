"""
Post & Event window.

Flow:
  1. User picks a template — fields shown/hidden accordingly.
  2. User fills in Title plus the template-specific fields.
  3. User selects one or more categories (not remembered between invocations).
  4. "Create Post" / "Update Post" runs in a background thread.
  5. Result shown in the log; window stays open for consecutive runs.
  6. "Delete Post" looks up the post by title, confirms, then deletes permanently.
"""
import os
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.post_event_action import PostEventAction, TEMPLATES

try:
    from PIL import Image, ImageTk, ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

CATEGORIES = [
    'אירועים',
    'אירועים קרובים',
    'גיוס כספים',
    'השבוע בידידיה',
    'ידיעות ידידיה',
    'ללא קטגוריה',
    'עדכוני שבעה',
    'Upcoming Events',
    'מידע נוסף',
]


class PostEventWindow(tk.Toplevel):
    def __init__(self, parent, action: PostEventAction, env='staging'):
        super().__init__(parent)
        self.title(f"Post/Update Event — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action  = action
        self.env     = env

        self._image_path  = None
        self._image_temp  = False
        self._thumb_photo = None
        self._field_rows  = {}   # name → (label_widget, content_widget)

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(500, 560)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        pad = {"padx": 8, "pady": 4}

        # ── Details section ────────────────────────────────────────────────
        details = ttk.LabelFrame(self, text="Event Details", padding=8)
        details.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        details.columnconfigure(1, weight=1)

        # Template
        ttk.Label(details, text="Template:").grid(row=0, column=0, sticky="e", **pad)
        self._template_var = tk.StringVar()
        self._template_cb = ttk.Combobox(
            details, textvariable=self._template_var,
            values=list(TEMPLATES.keys()), state="readonly", width=30,
        )
        self._template_cb.grid(row=0, column=1, columnspan=2, sticky="w", **pad)
        self._template_cb.bind("<<ComboboxSelected>>", self._on_template_change)

        # Title (always visible)
        ttk.Label(details, text="Title:").grid(row=1, column=0, sticky="e", **pad)
        self._title_var = tk.StringVar()
        self._title_var.trace_add('write', self._on_title_edited)
        self._title_entry = ttk.Entry(details, textvariable=self._title_var)
        self._title_entry.grid(row=1, column=1, columnspan=2, sticky="ew", **pad)
        self._title_entry.bind("<FocusOut>", lambda _: self._check_title_exists())

        # Date (optional)
        lbl_date = ttk.Label(details, text="Date:")
        lbl_date.grid(row=2, column=0, sticky="e", **pad)
        self._date_var = tk.StringVar()
        entry_date = ttk.Entry(details, textvariable=self._date_var)
        entry_date.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)
        self._field_rows['date'] = (lbl_date, entry_date)

        # Description (optional)
        lbl_desc = ttk.Label(details, text="Description:")
        lbl_desc.grid(row=3, column=0, sticky="ne", **pad)
        self._desc_text = tk.Text(details, height=4, wrap="word", font=("Segoe UI", 9))
        self._desc_text.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)
        self._field_rows['description'] = (lbl_desc, self._desc_text)

        # Image (optional)
        lbl_img = ttk.Label(details, text="Image:")
        lbl_img.grid(row=4, column=0, sticky="ne", **pad)

        img_frame = ttk.Frame(details)
        img_frame.grid(row=4, column=1, columnspan=2, sticky="ew", **pad)
        img_frame.columnconfigure(0, weight=1)

        self._img_path_var = tk.StringVar(value="No image selected")
        ttk.Entry(img_frame, textvariable=self._img_path_var,
                  state="readonly").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(img_frame, text="Browse…",
                   command=self._browse_image).grid(row=0, column=1)
        ttk.Button(img_frame, text="Paste from clipboard",
                   command=self._paste_image,
                   state="normal" if _PIL_AVAILABLE else "disabled",
                   ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self._thumb_label = ttk.Label(details)
        self._thumb_label.grid(row=5, column=1, sticky="w", padx=8, pady=(0, 4))
        self._field_rows['image'] = (lbl_img, img_frame)
        self._thumb_row = self._thumb_label

        # ── Category section ───────────────────────────────────────────────
        cat_frame = ttk.LabelFrame(self, text="Category", padding=8)
        cat_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        cat_frame.columnconfigure(0, weight=1)
        cat_frame.rowconfigure(0, weight=1)

        self._cat_listbox = tk.Listbox(
            cat_frame, selectmode=tk.MULTIPLE,
            height=len(CATEGORIES), font=("Segoe UI", 10),  # auto-sizes to list length
            activestyle="none",
        )
        for cat in CATEGORIES:
            self._cat_listbox.insert(tk.END, cat)
        self._cat_listbox.grid(row=0, column=0, sticky="nsew")

        # ── Log area ───────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=6, state="disabled",
                            font=("Consolas", 9), bg="#f8f8f8", relief="flat")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # ── Bottom bar ─────────────────────────────────────────────────────
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        bottom.columnconfigure(1, weight=1)

        self._delete_btn = ttk.Button(bottom, text="Delete Post", command=self._on_delete)
        self._delete_btn.grid(row=0, column=0, sticky="w")

        self._status_var = tk.StringVar(value="Select a template and fill in the details.")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=1, sticky="w", padx=(12, 0))

        btn_row = ttk.Frame(bottom)
        btn_row.grid(row=0, column=2, sticky="e")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._create_btn = ttk.Button(btn_row, text="Create Post", command=self._on_create)
        self._create_btn.pack(side="right")

    # ------------------------------------------------------------------
    # Template selection
    # ------------------------------------------------------------------

    def _on_template_change(self, *_):
        template = self._template_var.get()
        fields   = TEMPLATES.get(template, {}).get('fields', [])

        for name, (lbl, widget) in self._field_rows.items():
            if name in fields:
                lbl.grid()
                widget.grid()
            else:
                lbl.grid_remove()
                widget.grid_remove()

        if 'image' in fields:
            self._thumb_row.grid()
        else:
            self._thumb_row.grid_remove()

    # ------------------------------------------------------------------
    # Title → button label
    # ------------------------------------------------------------------

    def _on_title_edited(self, *_):
        """Reset button label as soon as the user starts editing the title."""
        self._create_btn.configure(text="Create Post")

    def _check_title_exists(self):
        """On focus-out: ask WP whether a post with this title already exists."""
        title = self._title_var.get().strip()
        if not title:
            return
        threading.Thread(
            target=self._run_check_title, args=(title,), daemon=True,
        ).start()

    def _run_check_title(self, title):
        result = self.action.find_post(title=title, env=self.env)
        exists = result.success and result.data is not None
        self.after(0, self._update_create_btn_label, exists)

    def _update_create_btn_label(self, exists):
        self._create_btn.configure(text="Update Post" if exists else "Create Post")

    # ------------------------------------------------------------------
    # Defaults / persistence  (categories intentionally excluded)
    # ------------------------------------------------------------------

    def _load_defaults(self):
        template = dm.get('post_event', 'template')
        if template and template in TEMPLATES:
            self._template_var.set(template)
        elif TEMPLATES:
            self._template_var.set(next(iter(TEMPLATES)))
        self._on_template_change()

        title = dm.get('post_event', 'title')
        if title:
            self._title_var.set(title)
            self.after(200, self._check_title_exists)

        date = dm.get('post_event', 'date')
        if date:
            self._date_var.set(date)

        desc = dm.get('post_event', 'description')
        if desc:
            self._desc_text.insert("1.0", desc)

        image_path = dm.get('post_event', 'image_path')
        if image_path and os.path.exists(image_path):
            self._set_image(image_path, is_temp=False)

    def _save_defaults(self, template, title, date, description, image_path):
        dm.set_default('post_event', 'template',    template)
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
            parent=self, title="Select image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                       ("All files", "*.*")],
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

    def _set_image(self, path, is_temp):
        if self._image_temp and self._image_path and os.path.exists(self._image_path):
            try:
                os.unlink(self._image_path)
            except OSError:
                pass
        self._image_path = path
        self._image_temp = is_temp
        self._img_path_var.set("Pasted image" if is_temp else os.path.basename(path))
        self._update_thumbnail(path)

    def _update_thumbnail(self, path):
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
    # Create / Update post
    # ------------------------------------------------------------------

    def _on_create(self):
        template = self._template_var.get()
        if not template:
            messagebox.showwarning("No template", "Select a template.", parent=self)
            return

        fields = TEMPLATES[template].get('fields', [])

        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Enter a title.", parent=self)
            return

        date = self._date_var.get().strip() if 'date' in fields else ''
        if 'date' in fields and not date:
            messagebox.showwarning("Missing date", "Enter a date.", parent=self)
            return

        description = self._desc_text.get("1.0", tk.END).strip() if 'description' in fields else ''
        if 'description' in fields and not description:
            messagebox.showwarning("Missing description", "Enter a description.", parent=self)
            return

        image_path = self._image_path if 'image' in fields else ''
        if 'image' in fields and not image_path:
            messagebox.showwarning("Missing image", "Select or paste an image.", parent=self)
            return

        categories = [CATEGORIES[i] for i in self._cat_listbox.curselection()]

        self._save_defaults(template, title, date, description, image_path)
        self._create_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Saving post…")
        self._log_write(f"Template:    {template}\n")
        self._log_write(f"Title:       {title}\n")
        if date:
            self._log_write(f"Date:        {date}\n")
        if description:
            self._log_write(f"Description: {description[:60]}{'…' if len(description) > 60 else ''}\n")
        if image_path:
            self._log_write(f"Image:       {self._img_path_var.get()}\n")
        if categories:
            self._log_write(f"Categories:  {', '.join(categories)}\n")
        self._log_write("\n")

        threading.Thread(
            target=self._run_create,
            args=(template, title, categories, date, description, image_path),
            daemon=True,
        ).start()

    def _run_create(self, template, title, categories, date, description, image_path):
        result = self.action.run(
            template=template, title=title, categories=categories,
            date=date, description=description, image_path=image_path,
            env=self.env,
        )
        self.after(0, self._finish_create, result)

    def _finish_create(self, result):
        if result.success:
            self._log_write(f"Done. {result.message}\n")
            if result.data:
                self._log_write(f"URL: {result.data}\n")
            self._status_var.set("Post saved.")
            self._create_btn.configure(text="Update Post")
        else:
            self._log_write(f"Error: {result.message}\n")
            self._status_var.set("Failed.")
            if "401" in result.message:
                from portal.gui.credentials_dialog import CredentialsDialog
                CredentialsDialog(self, on_save=lambda: self._status_var.set(
                    "Credentials updated. Try again."))
        self._create_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Delete post
    # ------------------------------------------------------------------

    def _on_delete(self):
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("No title", "Enter a title to identify the post.", parent=self)
            return

        self._create_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._status_var.set("Looking up post…")

        threading.Thread(
            target=self._run_find_for_delete, args=(title,), daemon=True,
        ).start()

    def _run_find_for_delete(self, title):
        result = self.action.find_post(title=title, env=self.env)
        self.after(0, self._confirm_delete, title, result)

    def _confirm_delete(self, title, find_result):
        if not find_result.success:
            self._log_write(f"Error: {find_result.message}\n")
            self._status_var.set("Failed.")
            self._create_btn.configure(state="normal")
            self._delete_btn.configure(state="normal")
            return

        post_id = find_result.data
        if post_id is None:
            self._log_write(f"No post found with title '{title}'.\n")
            self._status_var.set("Post not found.")
            self._create_btn.configure(state="normal")
            self._delete_btn.configure(state="normal")
            return

        if not messagebox.askyesno(
            "Delete post",
            f'Permanently delete "{title}"?\n\nThis cannot be undone.',
            parent=self,
        ):
            self._status_var.set("Cancelled.")
            self._create_btn.configure(state="normal")
            self._delete_btn.configure(state="normal")
            return

        self._status_var.set("Deleting…")
        threading.Thread(
            target=self._run_delete, args=(post_id,), daemon=True,
        ).start()

    def _run_delete(self, post_id):
        result = self.action.delete(post_id=post_id, env=self.env)
        self.after(0, self._finish_delete, result)

    def _finish_delete(self, result):
        if result.success:
            self._log_write(f"Done. {result.message}\n")
            self._status_var.set("Post deleted.")
            self._create_btn.configure(text="Create Post")
        else:
            self._log_write(f"Error: {result.message}\n")
            self._status_var.set("Failed.")
        self._create_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

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
        x = max(40, min(parent.winfo_rootx() + 80,
                        self.winfo_screenwidth()  - self.winfo_width()  - 20))
        y = max(40, min(parent.winfo_rooty() + 60,
                        self.winfo_screenheight() - self.winfo_height() - 40))
        self.geometry(f"+{x}+{y}")

    def destroy(self):
        if self._image_temp and self._image_path and os.path.exists(self._image_path):
            try:
                os.unlink(self._image_path)
            except OSError:
                pass
        super().destroy()
