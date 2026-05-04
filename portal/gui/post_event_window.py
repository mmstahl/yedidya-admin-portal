"""
Post & Event window — bilingual (Hebrew + English).

Flow:
  1. User picks a template — fields shown/hidden accordingly.
  2. User fills Hebrew fields; English fields auto-populate on first FocusOut of each
     Hebrew field. Once an English field is manually edited it is no longer overwritten.
     Auto-copy fires only once per field per session.
  3. User selects categories via checkboxes — separate per language, persisted across
     invocations.
  4. "Create Post" / "Update Post" runs two API calls: Hebrew then English.
     English is skipped if its title is empty.
  5. Result shown in the log; window stays open for consecutive runs.
  6. "Delete Post" deletes both language versions by their respective titles.
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
        self.action = action
        self.env    = env

        # Per-language image state
        self._image_path     = {'he': None, 'en': None}
        self._image_temp     = {'he': False, 'en': False}
        self._thumb_photo    = {'he': None, 'en': None}
        self._image_user_set = {'he': False, 'en': False}  # True only if user picked image this session

        # Per-language field-row pairs for show/hide and thumb labels
        self._field_rows = {'he': {}, 'en': {}}
        self._thumb_rows = {'he': None, 'en': None}

        # Per-language category BooleanVars — source of truth regardless of tab visibility
        self._cat_vars = {
            lang: {cat: tk.BooleanVar() for cat in CATEGORIES}
            for lang in ('he', 'en')
        }

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(520, 640)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # log expands

        # ── Details ────────────────────────────────────────────────────
        details = ttk.LabelFrame(self, text="Event Details", padding=8)
        details.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        details.columnconfigure(0, weight=1)

        # Template (shared, above language tabs)
        tpl_row = ttk.Frame(details)
        tpl_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        tpl_row.columnconfigure(1, weight=1)
        ttk.Label(tpl_row, text="Template:").grid(row=0, column=0, sticky="e", padx=(0, 8))
        self._template_var = tk.StringVar()
        self._template_cb = ttk.Combobox(
            tpl_row, textvariable=self._template_var,
            values=list(TEMPLATES.keys()), state="readonly", width=30,
        )
        self._template_cb.grid(row=0, column=1, sticky="w")
        self._template_cb.bind("<<ComboboxSelected>>", self._on_template_change)

        ttk.Button(tpl_row, text="Show template info",
                   command=self._on_show_template_info,
                   ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        # Language notebook
        self._notebook = ttk.Notebook(details)
        self._notebook.grid(row=1, column=0, sticky="ew")

        he_tab = ttk.Frame(self._notebook, padding=4)
        en_tab = ttk.Frame(self._notebook, padding=4)
        self._notebook.add(he_tab, text="Hebrew (עברית)")
        self._notebook.add(en_tab, text="English")

        self._build_lang_tab(he_tab, 'he')
        self._build_lang_tab(en_tab, 'en')

        # ── Log ────────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=15, state="disabled",
                            font=("Consolas", 9), bg="#f8f8f8", relief="flat")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # ── Bottom bar ─────────────────────────────────────────────────
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

    def _build_lang_tab(self, parent, lang):
        parent.columnconfigure(1, weight=1)
        pad = {"padx": 8, "pady": 3}

        # Title
        ttk.Label(parent, text="Title:").grid(row=0, column=0, sticky="e", **pad)
        title_var = tk.StringVar()
        title_entry = ttk.Entry(parent, textvariable=title_var,
                                justify='right' if lang == 'he' else 'left')
        title_entry.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        if lang == 'he':
            self._title_he_var   = title_var
            self._title_he_entry = title_entry
            title_var.trace_add('write', self._on_title_edited)
            title_entry.bind("<FocusOut>", lambda _: self._check_title_exists())
        else:
            self._title_en_var   = title_var
            self._title_en_entry = title_entry

        # Date
        lbl_date = ttk.Label(parent, text="Date:")
        lbl_date.grid(row=1, column=0, sticky="e", **pad)
        date_var = tk.StringVar()
        date_entry = ttk.Entry(parent, textvariable=date_var,
                               justify='right' if lang == 'he' else 'left')
        date_entry.grid(row=1, column=1, columnspan=2, sticky="ew", **pad)
        self._field_rows[lang]['date'] = (lbl_date, date_entry)
        if lang == 'he':
            self._date_he_var   = date_var
            self._date_he_entry = date_entry
        else:
            self._date_en_var = date_var

        # Description
        lbl_desc = ttk.Label(parent, text="Description:")
        lbl_desc.grid(row=2, column=0, sticky="ne", **pad)
        if lang == 'he':
            desc_text, desc_grid_widget = self._make_rtl_text(parent, height=4, row=2, pad=pad)
            self._desc_he_text = desc_text
        else:
            desc_text = tk.Text(parent, height=4, wrap="word", font=("Segoe UI", 9))
            desc_text.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)
            desc_grid_widget = desc_text
            self._desc_en_text = desc_text
        self._field_rows[lang]['description'] = (lbl_desc, desc_grid_widget)

        # Image
        lbl_img = ttk.Label(parent, text="Image:")
        lbl_img.grid(row=3, column=0, sticky="ne", **pad)
        img_frame = ttk.Frame(parent)
        img_frame.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)
        img_frame.columnconfigure(0, weight=1)

        img_path_var = tk.StringVar(value="No image selected")
        ttk.Entry(img_frame, textvariable=img_path_var,
                  state="readonly").grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(img_frame, text="Browse…",
                   command=lambda l=lang: self._browse_image(l)).grid(row=0, column=1)
        ttk.Button(img_frame, text="Paste from clipboard",
                   command=lambda l=lang: self._paste_image(l),
                   state="normal" if _PIL_AVAILABLE else "disabled",
                   ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        thumb_label = ttk.Label(parent)
        thumb_label.grid(row=4, column=1, sticky="w", padx=8, pady=(0, 3))

        self._field_rows[lang]['image'] = (lbl_img, img_frame)
        self._thumb_rows[lang] = thumb_label
        if lang == 'he':
            self._img_path_var_he = img_path_var
            self._thumb_label_he  = thumb_label
        else:
            self._img_path_var_en = img_path_var
            self._thumb_label_en  = thumb_label

        # Caption
        lbl_cap = ttk.Label(parent, text="Caption:")
        lbl_cap.grid(row=5, column=0, sticky="ne", **pad)
        if lang == 'he':
            cap_text, cap_grid_widget = self._make_rtl_text(parent, height=3, row=5, pad=pad)
            self._caption_he_text = cap_text
        else:
            cap_text = tk.Text(parent, height=3, wrap="word", font=("Segoe UI", 9))
            cap_text.grid(row=5, column=1, columnspan=2, sticky="ew", **pad)
            cap_grid_widget = cap_text
            self._caption_en_text = cap_text
        self._field_rows[lang]['caption'] = (lbl_cap, cap_grid_widget)

        # Categories — Checkbuttons backed by BooleanVars (persist across tab switches)
        ttk.Label(parent, text="Categories:").grid(row=6, column=0, sticky="ne", **pad)
        cat_frame = ttk.Frame(parent)
        cat_frame.grid(row=6, column=1, columnspan=2, sticky="ew", **pad)
        for cat in CATEGORIES:
            ttk.Checkbutton(
                cat_frame, text=cat, variable=self._cat_vars[lang][cat],
            ).pack(anchor='w')

    def _make_rtl_text(self, parent, height, row, pad):
        """Create a no-wrap RTL Text widget inside a scrollable frame.

        Returns (text_widget, frame) where frame is what should be gridded
        and stored in _field_rows for show/hide, and text_widget is the
        actual tk.Text used for reading/writing content.

        Using wrap='none' eliminates the BiDi wrap confusion:
        Hebrew characters render right-to-left within one long line and the
        viewport scrolls horizontally to follow the cursor.  This avoids the
        "text teleports to position 0" symptom that wrap='char'/'word' causes
        with RTL text in tkinter.
        """
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, columnspan=2, sticky="ew", **pad)
        frame.columnconfigure(0, weight=1)

        text = tk.Text(frame, height=height, wrap='none', font=("Segoe UI", 9))
        xsb  = ttk.Scrollbar(frame, orient='horizontal', command=text.xview)
        text.configure(xscrollcommand=xsb.set)
        text.grid(row=0, column=0, sticky='ew')
        xsb.grid(row=1, column=0, sticky='ew')

        self._configure_rtl_text(text)
        return text, frame

    @staticmethod
    def _configure_rtl_text(widget):
        """Apply a right-justified paragraph tag on every keystroke/click."""
        widget.tag_configure('rtl', justify='right')

        def _apply(*_):
            widget.tag_add('rtl', '1.0', 'end')

        widget.bind('<KeyRelease>',    _apply)
        widget.bind('<ButtonRelease>', _apply)

    # ------------------------------------------------------------------
    # Category helpers
    # ------------------------------------------------------------------

    def _get_categories(self, lang):
        return [cat for cat in CATEGORIES if self._cat_vars[lang][cat].get()]

    def _set_categories(self, lang, selected):
        selected_set = set(selected)
        for cat, var in self._cat_vars[lang].items():
            var.set(cat in selected_set)

    # ------------------------------------------------------------------
    # Template selection
    # ------------------------------------------------------------------

    def _on_template_change(self, *_):
        template = self._template_var.get()
        fields   = TEMPLATES.get(template, {}).get('fields', [])

        for lang in ('he', 'en'):
            for name, (lbl, widget) in self._field_rows[lang].items():
                if name in fields:
                    lbl.grid()
                    widget.grid()
                else:
                    lbl.grid_remove()
                    widget.grid_remove()
            if 'image' in fields:
                self._thumb_rows[lang].grid()
            else:
                self._thumb_rows[lang].grid_remove()

    # ------------------------------------------------------------------
    # Title → button label
    # ------------------------------------------------------------------

    def _on_title_edited(self, *_):
        self._create_btn.configure(text="Create Post")

    def _check_title_exists(self):
        title = self._title_he_var.get().strip()
        if not title:
            return
        threading.Thread(
            target=self._run_check_title, args=(title,), daemon=True,
        ).start()

    def _run_check_title(self, title):
        result = self.action.find_post(title=title, env=self.env, lang='he')
        exists = result.success and result.data is not None
        self.after(0, self._update_create_btn_label, exists)

    def _update_create_btn_label(self, exists):
        try:
            self._create_btn.configure(text="Update Post" if exists else "Create Post")
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Show template info (helps user find the WordPress post for editing)
    # ------------------------------------------------------------------

    def _on_show_template_info(self):
        template = self._template_var.get()
        if not template:
            messagebox.showwarning("No template", "Select a template first.", parent=self)
            return
        self._status_var.set(f"Looking up template '{template}'…")
        threading.Thread(
            target=self._run_show_template_info, args=(template,), daemon=True,
        ).start()

    def _run_show_template_info(self, template):
        result = self.action.find_template(template, env=self.env)
        self.after(0, self._finish_show_template_info, template, result)

    def _finish_show_template_info(self, template, result):
        self._status_var.set("Ready.")
        if not result.success:
            messagebox.showerror("Template not found", result.message, parent=self)
            return
        d = result.data or {}
        kind = "Page" if d.get('post_type') == 'pages' else "Post"
        msg = (
            f"Slug:    {template}\n"
            f"Title:   {d.get('title', '(no title)')}\n"
            f"Type:    {kind}\n"
            f"Status:  {d.get('status', '')}\n"
            f"ID:      {d.get('id', 0)}\n\n"
            f"Public URL:\n{d.get('link', '')}\n\n"
            f"Edit in WordPress admin:\n{d.get('edit_link', '')}"
        )
        messagebox.showinfo(f"Template: {template}", msg, parent=self)

    # ------------------------------------------------------------------
    # Defaults / persistence
    # ------------------------------------------------------------------

    def _load_defaults(self):
        template = dm.get('post_event', 'template')
        if template and template in TEMPLATES:
            self._template_var.set(template)
        elif TEMPLATES:
            self._template_var.set(next(iter(TEMPLATES)))
        self._on_template_change()

        for lang in ('he', 'en'):
            title = dm.get('post_event', f'title_{lang}')
            if title:
                (self._title_he_var if lang == 'he' else self._title_en_var).set(title)

            date = dm.get('post_event', f'date_{lang}')
            if date:
                (self._date_he_var if lang == 'he' else self._date_en_var).set(date)

            desc = dm.get('post_event', f'description_{lang}')
            if desc:
                w = self._desc_he_text if lang == 'he' else self._desc_en_text
                w.insert("1.0", desc)

            caption = dm.get('post_event', f'caption_{lang}')
            if caption:
                w = self._caption_he_text if lang == 'he' else self._caption_en_text
                w.insert("1.0", caption)

            image_path = dm.get('post_event', f'image_path_{lang}')
            if image_path and os.path.exists(image_path):
                self._set_image(image_path, is_temp=False, lang=lang)

            saved_cats = dm.get('post_event', f'categories_{lang}')
            if saved_cats:
                self._set_categories(lang, saved_cats.split('|'))

        if dm.get('post_event', 'title_he'):
            self.after(200, self._check_title_exists)

    def _save_defaults(self, template, lang_data):
        dm.set_default('post_event', 'template', template)
        for lang in ('he', 'en'):
            d = lang_data[lang]
            dm.set_default('post_event', f'title_{lang}',       d.get('title', ''))
            dm.set_default('post_event', f'date_{lang}',        d.get('date', ''))
            dm.set_default('post_event', f'description_{lang}', d.get('description', ''))
            dm.set_default('post_event', f'caption_{lang}',     d.get('caption', ''))
            dm.set_default('post_event', f'categories_{lang}',  '|'.join(d.get('categories', [])))
            if d.get('image_path') and not self._image_temp[lang]:
                dm.set_default('post_event', f'image_path_{lang}', d['image_path'])

    # ------------------------------------------------------------------
    # Image selection
    # ------------------------------------------------------------------

    def _browse_image(self, lang):
        path = filedialog.askopenfilename(
            parent=self, title="Select image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                       ("All files", "*.*")],
        )
        if path:
            filename = os.path.basename(path)
            try:
                filename.encode('ascii')
            except UnicodeEncodeError:
                messagebox.showwarning(
                    "Non-English filename",
                    f'The filename "{filename}" contains non-English characters.\n\n'
                    "Please rename the file using English characters only and try again.",
                    parent=self,
                )
                return
            self._set_image(path, is_temp=False, lang=lang)
            self._image_user_set[lang] = True

    def _paste_image(self, lang):
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
        self._set_image(tmp.name, is_temp=True, lang=lang)
        self._image_user_set[lang] = True

    def _set_image(self, path, is_temp, lang):
        old = self._image_path[lang]
        if self._image_temp[lang] and old and os.path.exists(old):
            try:
                os.unlink(old)
            except OSError:
                pass
        self._image_path[lang] = path
        self._image_temp[lang] = is_temp
        label = "Pasted image" if is_temp else os.path.basename(path)
        if lang == 'he':
            self._img_path_var_he.set(label)
            self._update_thumbnail(path, self._thumb_label_he, 'he')
        else:
            self._img_path_var_en.set(label)
            self._update_thumbnail(path, self._thumb_label_en, 'en')

    def _update_thumbnail(self, path, label_widget, lang):
        if not _PIL_AVAILABLE:
            return
        try:
            img = Image.open(path)
            img.thumbnail((160, 100))
            photo = ImageTk.PhotoImage(img)
            self._thumb_photo[lang] = photo
            label_widget.configure(image=photo, text="")
        except Exception:
            label_widget.configure(image="", text="(preview unavailable)")

    # ------------------------------------------------------------------
    # Create / Update post
    # ------------------------------------------------------------------

    def _collect_lang(self, lang, fields):
        """Gather user input for ONE language tab.  Validates only when this
        language has a non-empty title (i.e. the user wants this post saved).

        Returns (data_dict, error_message_or_None).  The data_dict is always
        shape-complete so it can be passed straight into action.run() and into
        _save_defaults regardless of validation outcome.
        """
        title_var   = self._title_he_var   if lang == 'he' else self._title_en_var
        date_var    = self._date_he_var    if lang == 'he' else self._date_en_var
        desc_widget = self._desc_he_text   if lang == 'he' else self._desc_en_text
        cap_widget  = self._caption_he_text if lang == 'he' else self._caption_en_text
        label       = "Hebrew" if lang == 'he' else "English"

        title = title_var.get().strip()
        date  = date_var.get().strip() if 'date' in fields else ''
        desc  = desc_widget.get("1.0", tk.END).strip() if 'description' in fields else ''
        cap   = cap_widget.get("1.0", tk.END).strip() if 'caption' in fields else ''
        # Always pass the loaded image_path; run() decides whether to upload
        # (using is_new_image as the hint) or to reuse the existing post's image.
        image_path = self._image_path[lang] if 'image' in fields else None

        data = {
            'title':        title,
            'date':         date,
            'description':  desc,
            'image_path':   image_path or '',
            'caption':      cap,
            'categories':   self._get_categories(lang),
            'is_new_image': self._image_user_set[lang],
        }

        # Validation only fires when this language is actually being saved.
        if not title:
            return data, None
        if 'date' in fields and not date:
            return data, f"Enter a date ({label} tab)."
        if 'description' in fields and not desc:
            return data, f"Enter a description ({label} tab)."

        return data, None

    def _on_create(self):
        template = self._template_var.get()
        if not template:
            messagebox.showwarning("No template", "Select a template.", parent=self)
            return

        fields = TEMPLATES[template].get('fields', [])

        # Collect both languages through the same helper.  Each language is an
        # independent unit — no cross-language fallbacks.
        lang_data = {}
        for lang in ('he', 'en'):
            data, err = self._collect_lang(lang, fields)
            if err:
                messagebox.showwarning("Invalid input", err, parent=self)
                return
            lang_data[lang] = data

        # Hebrew is the primary language: a Hebrew title is always required.
        if not lang_data['he']['title']:
            messagebox.showwarning("Missing title", "Enter a Hebrew title.", parent=self)
            return

        # English is optional; if its title is set it must differ from Hebrew.
        if lang_data['en']['title'] and lang_data['he']['title'] == lang_data['en']['title']:
            messagebox.showerror(
                "Duplicate title",
                "The Hebrew and English titles are identical.\n\n"
                "Please ensure the Title of the Hebrew and English posts are different.",
                parent=self,
            )
            return

        self._save_defaults(template, lang_data)
        self._create_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._log_clear()
        self._status_var.set("Saving post…")

        self._log_write(f"Template: {template}\n")
        for lang, label in (('he', 'Hebrew'), ('en', 'English')):
            d = lang_data[lang]
            if not d['title']:
                continue
            self._log_write(f"\n[{label}]\n")
            self._log_write(f"  Title: {d['title']}\n")
            if d['date']:
                self._log_write(f"  Date:  {d['date']}\n")
            if d['description']:
                s = d['description']
                self._log_write(f"  Desc:  {s[:60]}{'…' if len(s) > 60 else ''}\n")
            if d['image_path']:
                lbl = "Pasted image" if self._image_temp[lang] else os.path.basename(d['image_path'])
                self._log_write(f"  Image: {lbl}\n")
            if d['caption']:
                s = d['caption']
                self._log_write(f"  Caption: {s[:60]}{'…' if len(s) > 60 else ''}\n")
            if d['categories']:
                self._log_write(f"  Categories: {', '.join(d['categories'])}\n")
        self._log_write("\n")

        threading.Thread(
            target=self._run_create,
            args=(template, lang_data),
            daemon=True,
        ).start()

    def _run_create(self, template, lang_data):
        """Process each language as an independent post.  Same code path,
        same parameters, just called twice with different lang values."""
        results = {}
        for lang in ('he', 'en'):
            d = lang_data[lang]
            if not d['title']:
                results[lang] = None
                continue
            results[lang] = self.action.run(
                template=template,
                title=d['title'],
                categories=d['categories'],
                date=d['date'],
                description=d['description'],
                image_path=d['image_path'],
                is_new_image=d['is_new_image'],
                caption=d['caption'],
                lang=lang,
                env=self.env,
            )
        self.after(0, self._finish_create, results)

    def _finish_create(self, results):
        overall_ok = True
        for lang, label in (('he', 'Hebrew'), ('en', 'English')):
            result = results.get(lang)
            if result is None:
                self._log_write(f"[{label}] Skipped (no title).\n")
                continue
            if result.success:
                self._log_write(f"[{label}] Done. {result.message}\n")
                if result.data:
                    self._log_write(f"[{label}] URL: {result.data}\n")
            else:
                overall_ok = False
                self._log_write(f"[{label}] Error: {result.message}\n")
                if "401" in result.message:
                    from portal.gui.credentials_dialog import CredentialsDialog
                    CredentialsDialog(self, on_save=lambda: self._status_var.set(
                        "Credentials updated. Try again."))
        self._status_var.set("Post saved." if overall_ok else "One or more errors — see log.")
        if overall_ok:
            self._create_btn.configure(text="Update Post")
            # Image was just saved to WordPress. Clear the "user set this session" flags so
            # the next update doesn't re-upload the same image — Option C will reuse the
            # media already embedded in the post.
            self._image_user_set = {'he': False, 'en': False}
        self._create_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Delete post
    # ------------------------------------------------------------------

    def _on_delete(self):
        title_he = self._title_he_var.get().strip()
        title_en = self._title_en_var.get().strip()
        if not title_he and not title_en:
            messagebox.showwarning("No title",
                                   "Enter at least one title to identify the post.",
                                   parent=self)
            return

        choice, delete_image = self._delete_confirm_dialog(title_he, title_en)
        if choice is None:
            return
        if choice == 'he':
            title_en = ''
        elif choice == 'en':
            title_he = ''

        self._create_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._status_var.set("Deleting…")

        threading.Thread(
            target=self._run_delete_both,
            args=(title_he, title_en, delete_image),
            daemon=True,
        ).start()

    def _delete_confirm_dialog(self, title_he, title_en):
        """Show a custom delete-confirmation dialog.
        Returns (choice, delete_image) where choice is 'both'/'he'/'en'/None."""
        dlg = tk.Toplevel(self)
        dlg.title("Delete post")
        dlg.grab_set()
        dlg.resizable(False, False)

        msg = "The following posts will be permanently deleted.\nSelect which to delete:\n"
        if title_he:
            msg += f'\n  Hebrew:  "{title_he}"'
        if title_en:
            msg += f'\n  English: "{title_en}"'
        msg += "\n\nThis cannot be undone."
        ttk.Label(dlg, text=msg, justify="left", padding=(16, 12)).pack()

        delete_image_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            dlg, text="Also delete the associated image",
            variable=delete_image_var,
        ).pack(anchor='w', padx=20, pady=(0, 8))

        result = tk.StringVar(value='cancel')

        btn_frame = ttk.Frame(dlg, padding=(12, 0, 12, 12))
        btn_frame.pack()
        ttk.Button(btn_frame, text="Delete both",
                   command=lambda: (result.set('both'), dlg.destroy())).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Delete only Hebrew",
                   command=lambda: (result.set('he'), dlg.destroy())).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Delete only English",
                   command=lambda: (result.set('en'), dlg.destroy())).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel",
                   command=dlg.destroy).pack(side="left", padx=4)

        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - dlg.winfo_width())  // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")
        self.wait_window(dlg)
        if result.get() == 'cancel':
            return None, False
        return result.get(), delete_image_var.get()

    def _run_delete_both(self, title_he, title_en, delete_image):
        results = {}
        for lang, title in (('he', title_he), ('en', title_en)):
            if not title:
                results[lang] = {'post': None, 'media': None}
                continue

            find = self.action.find_post(title=title, env=self.env, lang=lang)
            if not find.success:
                results[lang] = {'post': find, 'media': None}
                continue

            post_id = find.data
            if post_id is None:
                results[lang] = {'post': None, 'media': None}
                continue

            # Fetch media ID before deleting the post (while content is still accessible)
            media_id = self.action.get_post_media_id(post_id, env=self.env) if delete_image else 0

            post_result = self.action.delete(post_id=post_id, env=self.env)

            media_result = None
            if delete_image and media_id and post_result.success:
                media_result = self.action.delete_media(media_id=media_id, env=self.env)

            results[lang] = {'post': post_result, 'media': media_result}

        self.after(0, self._finish_delete, results, title_he, title_en)

    def _finish_delete(self, results, title_he, title_en):
        overall_ok = True
        for lang, label, title in (('he', 'Hebrew', title_he), ('en', 'English', title_en)):
            r           = results.get(lang, {})
            post_result = r.get('post')
            media_result = r.get('media')

            if post_result is None and not title:
                continue
            if post_result is None:
                self._log_write(f"[{label}] No post found with title '{title}'.\n")
            elif post_result.success:
                self._log_write(f"[{label}] {post_result.message}\n")
                if media_result is not None:
                    if media_result.success:
                        self._log_write(f"[{label}] {media_result.message}\n")
                    else:
                        overall_ok = False
                        self._log_write(f"[{label}] Image error: {media_result.message}\n")
            else:
                overall_ok = False
                self._log_write(f"[{label}] Error: {post_result.message}\n")

        self._status_var.set("Deleted." if overall_ok else "Delete had errors — see log.")
        if overall_ok:
            self._create_btn.configure(text="Create Post")
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
        for lang in ('he', 'en'):
            path = self._image_path[lang]
            if self._image_temp[lang] and path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        super().destroy()
