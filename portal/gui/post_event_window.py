"""
Post & Event window — bilingual (Hebrew + English), side-by-side.

Layout:
  - Top: template selector
  - Middle: two columns side by side (Hebrew on the left, English on the right).
    Each column has its own title, "Update existing post" checkbox, date,
    description, image, caption, and category checkboxes.
  - Bottom: log + status + Save / Delete / Cancel buttons.

Save flow:
  - Both sides are NEW (titles don't match any existing post):
      1. Create the Hebrew post.
      2. Duplicate it to English via the WPML endpoint
         (yedidya/v1/duplicate-post) — both posts get linked as translations.
      3. Update the English duplicate with the English-side fields
         (overwrites the duplicated Hebrew content with the user's English
         content, while preserving the translation link).
  - Either side already exists (matched title or "Update existing post"
    checked): each side is processed independently — its own update or
    create call. No re-duplication.

"Update existing post" checkbox (per side):
  - Disabled by default.
  - Becomes enabled when the title-check confirms a post with that title
    exists on the site.
  - When the user checks it, the post_id is "locked in" — even if the user
    then edits the title, the system updates that specific post (renames
    it) instead of creating a new one. Useful when you want to fix a
    typo in a published post's title.
"""
import os
import tempfile
import threading
import tkinter as tk
import requests
from tkinter import ttk, filedialog, messagebox

import defaults_manager as dm
from portal.actions.base_action import ActionResult
from portal.actions.post_event_action import PostEventAction, TEMPLATES

try:
    from PIL import Image, ImageTk, ImageGrab
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

class PostEventWindow(tk.Toplevel):
    def __init__(self, parent, action: PostEventAction, env='staging',
                 verbose_var=None):
        super().__init__(parent)
        self.title(f"Post/Update Event — {env.capitalize()}")
        self.resizable(True, True)
        self.grab_set()
        self.action = action
        self.env    = env

        # Use the shared verbose var from MainWindow (so the checkbox state
        # is set before this window opens and starts its background checks).
        # Fall back to a local var if not provided (e.g. in tests).
        self._verbose_var = verbose_var if verbose_var is not None \
            else tk.BooleanVar(value=False)

        # Counter for in-flight title-checks; used to update the status bar.
        self._pending_checks = 0

        # Per-language image state
        self._image_path     = {'he': None, 'en': None}
        self._image_temp     = {'he': False, 'en': False}
        self._thumb_photo    = {'he': None, 'en': None}
        self._image_user_set = {'he': False, 'en': False}  # user explicitly picked image this session

        # Per-language field-row pairs for show/hide and thumb labels
        self._field_rows = {'he': {}, 'en': {}}
        self._thumb_rows = {'he': None, 'en': None}

        # Per-language category BooleanVars — populated dynamically once the
        # background fetch from WordPress returns.  Until then, each side's
        # dict is empty and a "Loading…" placeholder is shown.
        # _cat_vars[lang]            : {name: BooleanVar(), ...}
        # _cat_id_to_name[lang]      : {wp_category_id: name} — for pre-population
        # _cat_frame[lang]           : the parent ttk.Frame holding the checkboxes
        # _pending_default_cats[lang]: names from saved defaults waiting to be
        #                              applied once the real list arrives
        self._cat_vars            = {'he': {}, 'en': {}}
        self._cat_id_to_name      = {'he': {}, 'en': {}}
        self._cat_frame           = {'he': None, 'en': None}
        self._pending_default_cats = {'he': [], 'en': []}

        # Existence / "update existing post" state, per language.
        # _existing_post_id[lang]  : ID found by background title-check (None if none)
        # _locked_post_id[lang]    : ID locked in when user checked the checkbox.
        #                            Set to existing_post_id at the moment of checking.
        # _update_existing_var[..] : the BooleanVar the Checkbutton is bound to.
        # _update_existing_cb[..]  : the Checkbutton widget itself (so we can enable/disable it).
        # _locked_id_label_var[..] : StringVar for the "(post #1234)" hint shown next to the box.
        self._existing_post_id    = {'he': None, 'en': None}
        self._locked_post_id      = {'he': None, 'en': None}
        self._update_existing_var = {'he': tk.BooleanVar(), 'en': tk.BooleanVar()}
        self._update_existing_cb  = {'he': None, 'en': None}
        self._locked_id_label_var = {'he': tk.StringVar(value=''),
                                     'en': tk.StringVar(value='')}

        self._build()
        self._load_defaults()
        self._center(parent)
        self.minsize(1000, 760)
        # Kick off the WordPress category fetch.  Each side's column shows a
        # "Loading categories…" placeholder until this completes.
        self._fetch_categories_async()

    # ==================================================================
    # Layout
    # ==================================================================

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # log expands

        # ── Details ────────────────────────────────────────────────────
        details = ttk.LabelFrame(self, text="Event Details", padding=8)
        details.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))
        details.columnconfigure(0, weight=1)

        # Template (shared, above the two language columns)
        tpl_row = ttk.Frame(details)
        tpl_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
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

        # Side-by-side language panels
        cols = ttk.Frame(details)
        cols.grid(row=1, column=0, sticky="nsew")
        cols.columnconfigure(0, weight=1, uniform="lang")
        cols.columnconfigure(1, weight=1, uniform="lang")

        he_panel = ttk.LabelFrame(cols, text="Hebrew (עברית)", padding=6)
        he_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        en_panel = ttk.LabelFrame(cols, text="English",         padding=6)
        en_panel.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self._build_lang_panel(he_panel, 'he')
        self._build_lang_panel(en_panel, 'en')

        # ── Log ────────────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="Log", padding=8)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self._log = tk.Text(log_frame, height=12, state="disabled",
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

        self._status_var = tk.StringVar(value="Initialising…")
        ttk.Label(bottom, textvariable=self._status_var,
                  foreground="gray").grid(row=0, column=1, sticky="w", padx=(12, 0))

        btn_row = ttk.Frame(bottom)
        btn_row.grid(row=0, column=2, sticky="e")
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(4, 0))
        self._save_btn = ttk.Button(btn_row, text="Save", command=self._on_save)
        self._save_btn.pack(side="right")

    def _build_lang_panel(self, parent, lang):
        """Build one language column (mirrored layout for Hebrew and English)."""
        parent.columnconfigure(1, weight=1)
        pad = {"padx": 6, "pady": 3}
        is_he = (lang == 'he')

        # ── Title ────────────────────────────────────────────────────
        ttk.Label(parent, text="Title:").grid(row=0, column=0, sticky="e", **pad)
        title_var = tk.StringVar()
        title_entry = ttk.Entry(parent, textvariable=title_var,
                                justify='right' if is_he else 'left')
        title_entry.grid(row=0, column=1, sticky="ew", **pad)
        title_var.trace_add('write', lambda *_, l=lang: self._on_title_edited(l))
        title_entry.bind("<FocusOut>", lambda _, l=lang: self._check_title_exists(l))
        if is_he:
            self._title_he_var, self._title_he_entry = title_var, title_entry
        else:
            self._title_en_var, self._title_en_entry = title_var, title_entry

        # ── "Update existing post" checkbox + locked-id hint ─────────
        ue_row = ttk.Frame(parent)
        ue_row.grid(row=1, column=1, sticky="w", padx=6, pady=(0, 4))
        cb = ttk.Checkbutton(
            ue_row, text="Update existing post (rename allowed)",
            variable=self._update_existing_var[lang], state='disabled',
            command=lambda l=lang: self._on_update_existing_toggled(l),
        )
        cb.pack(side="left")
        self._update_existing_cb[lang] = cb
        ttk.Label(ue_row, textvariable=self._locked_id_label_var[lang],
                  foreground="gray").pack(side="left", padx=(8, 0))

        # ── Date ─────────────────────────────────────────────────────
        lbl_date = ttk.Label(parent, text="Date:")
        lbl_date.grid(row=2, column=0, sticky="e", **pad)
        date_var   = tk.StringVar()
        date_entry = ttk.Entry(parent, textvariable=date_var,
                               justify='right' if is_he else 'left')
        date_entry.grid(row=2, column=1, sticky="ew", **pad)
        self._field_rows[lang]['date'] = (lbl_date, date_entry)
        if is_he:
            self._date_he_var, self._date_he_entry = date_var, date_entry
        else:
            self._date_en_var = date_var

        # ── Description ──────────────────────────────────────────────
        lbl_desc = ttk.Label(parent, text="Description:")
        lbl_desc.grid(row=3, column=0, sticky="ne", **pad)
        if is_he:
            desc_text, desc_grid = self._make_rtl_text(parent, height=4, row=3, pad=pad)
            self._desc_he_text = desc_text
        else:
            desc_text = tk.Text(parent, height=4, wrap="word", font=("Segoe UI", 9))
            desc_text.grid(row=3, column=1, sticky="ew", **pad)
            desc_grid = desc_text
            self._desc_en_text = desc_text
        self._field_rows[lang]['description'] = (lbl_desc, desc_grid)

        # ── Image ────────────────────────────────────────────────────
        lbl_img = ttk.Label(parent, text="Image:")
        lbl_img.grid(row=4, column=0, sticky="ne", **pad)
        img_frame = ttk.Frame(parent)
        img_frame.grid(row=4, column=1, sticky="ew", **pad)
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
        thumb_label.grid(row=5, column=1, sticky="w", padx=6, pady=(0, 3))

        self._field_rows[lang]['image'] = (lbl_img, img_frame)
        self._thumb_rows[lang] = thumb_label
        if is_he:
            self._img_path_var_he, self._thumb_label_he = img_path_var, thumb_label
        else:
            self._img_path_var_en, self._thumb_label_en = img_path_var, thumb_label

        # ── Caption ──────────────────────────────────────────────────
        # Captions are short, so we use wrap='word' (no horizontal scrollbar)
        # for both languages.  The "text teleport" bug that drove the
        # wrap='none' decision (see decisions.md 2026-04-25) only affects
        # long text — descriptions still use the RTL-with-scrollbar helper.
        lbl_cap = ttk.Label(parent, text="Caption:")
        lbl_cap.grid(row=6, column=0, sticky="ne", **pad)
        cap_text = tk.Text(parent, height=3, wrap="word", font=("Segoe UI", 9))
        cap_text.grid(row=6, column=1, sticky="ew", **pad)
        cap_grid = cap_text
        if is_he:
            self._configure_rtl_text(cap_text)
            self._caption_he_text = cap_text
        else:
            self._caption_en_text = cap_text
        self._field_rows[lang]['caption'] = (lbl_cap, cap_grid)

        # ── Categories (populated dynamically) ───────────────────────
        ttk.Label(parent, text="Categories:").grid(row=7, column=0, sticky="ne", **pad)
        cat_frame = ttk.Frame(parent)
        cat_frame.grid(row=7, column=1, sticky="ew", **pad)
        ttk.Label(cat_frame, text="Loading categories…",
                  foreground="gray").pack(anchor='w')
        self._cat_frame[lang] = cat_frame

    def _make_rtl_text(self, parent, height, row, pad):
        """RTL no-wrap Text in a scrollable frame.  See decisions.md
        (2026-04-25 — Hebrew RTL text) for why wrap='none'."""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=1, sticky="ew", **pad)
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
        widget.tag_configure('rtl', justify='right')
        def _apply(*_):
            widget.tag_add('rtl', '1.0', 'end')
        widget.bind('<KeyRelease>',    _apply)
        widget.bind('<ButtonRelease>', _apply)

    # ==================================================================
    # Categories helpers
    # ==================================================================

    def _get_categories(self, lang):
        """Return the names of the currently-selected categories for this
        language.  Iterates over self._cat_vars in insertion order (the order
        WordPress returned them in)."""
        return [name for name, var in self._cat_vars[lang].items() if var.get()]

    def _set_categories(self, lang, selected):
        """Set the selected categories for this language.

        If the dynamic category list hasn't loaded yet (the fetch is still in
        flight), stash the desired names in _pending_default_cats — they get
        applied automatically once the fetch completes.  Names not in the
        real list are silently dropped, since they no longer exist on the site.
        """
        if not self._cat_vars[lang]:
            self._pending_default_cats[lang] = list(selected)
            return
        sset = set(selected)
        for name, var in self._cat_vars[lang].items():
            var.set(name in sset)

    # ==================================================================
    # Categories fetch (background)
    # ==================================================================

    def _fetch_categories_async(self):
        threading.Thread(target=self._run_fetch_categories, daemon=True).start()

    def _run_fetch_categories(self):
        result = self.action.list_category_pairs(env=self.env)
        self.after(0, self._finish_fetch_categories, result)

    def _finish_fetch_categories(self, result):
        """Replace each side's 'Loading…' placeholder with checkboxes.
        Both sides are rendered together row-by-row from the trid-grouped
        result, so row N on the Hebrew column maps to row N on the English
        column (same translation group)."""
        try:
            # Clear placeholders on both sides
            for lang in ('he', 'en'):
                frame = self._cat_frame[lang]
                if frame is None:
                    continue
                for child in frame.winfo_children():
                    child.destroy()
                self._cat_vars[lang]       = {}
                self._cat_id_to_name[lang] = {}

            if not result or not result.success:
                err = (result.message if result else 'no response')
                for lang in ('he', 'en'):
                    frame = self._cat_frame[lang]
                    if frame:
                        ttk.Label(
                            frame,
                            text=f"⚠ Failed to load categories:\n{err}",
                            foreground="#b00020", wraplength=240,
                            justify="left",
                        ).pack(anchor='w')
                return

            pairs = result.data or []
            if not pairs:
                for lang in ('he', 'en'):
                    frame = self._cat_frame[lang]
                    if frame:
                        ttk.Label(frame, text="(no categories on the site)",
                                  foreground="gray").pack(anchor='w')
                return

            # Render each pair as one row in both columns.  Using a
            # Checkbutton on every row (real or disabled-placeholder)
            # keeps vertical heights identical, so the two columns
            # stay perfectly aligned.
            for pair in pairs:
                for lang in ('he', 'en'):
                    cat = pair.get(lang)
                    frame = self._cat_frame[lang]
                    if cat:
                        name = cat.get('name', '')
                        cat_id = cat.get('id')
                        var = tk.BooleanVar()
                        self._cat_vars[lang][name] = var
                        if cat_id:
                            self._cat_id_to_name[lang][cat_id] = name
                        ttk.Checkbutton(
                            frame, text=name, variable=var,
                        ).pack(anchor='w')
                    else:
                        # Placeholder so the row exists on this side too.
                        ttk.Checkbutton(
                            frame, text="(no translation)",
                            variable=tk.BooleanVar(), state='disabled',
                        ).pack(anchor='w')

            # Apply any defaults that were waiting for the list to arrive.
            for lang in ('he', 'en'):
                pending = self._pending_default_cats.get(lang, [])
                if pending:
                    sset = set(pending)
                    for name, var in self._cat_vars[lang].items():
                        if name in sset:
                            var.set(True)
                    self._pending_default_cats[lang] = []
        except tk.TclError:
            # Window closed before the fetch came back.
            pass

    # ==================================================================
    # Template
    # ==================================================================

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

    # ==================================================================
    # Title-edited / title-check / update-existing checkbox
    # ==================================================================

    def _on_title_edited(self, lang):
        """Called on every keystroke in a title field.  Resets the existence
        cache so the checkbox can't claim 'I match an existing post' until
        the next FocusOut-triggered title-check completes."""
        # Don't disturb a locked checkbox — the user has explicitly committed
        # to updating that specific post.  But do clear the no-lock state.
        if not self._update_existing_var[lang].get():
            self._existing_post_id[lang] = None
            self._refresh_update_existing_state(lang)

    def _check_title_exists(self, lang):
        title_var = self._title_he_var if lang == 'he' else self._title_en_var
        title = title_var.get().strip()
        if not title:
            self._existing_post_id[lang] = None
            self._refresh_update_existing_state(lang)
            return
        label = "Hebrew" if lang == 'he' else "English"
        self._pending_checks += 1
        self._status_var.set(f"Checking for existing {label} post…")
        threading.Thread(
            target=self._run_check_title, args=(lang, title), daemon=True,
        ).start()

    def _run_check_title(self, lang, title):
        label    = 'Hebrew' if lang == 'he' else 'English'
        verbose  = self._verbose_var.get()
        def _cb(msg):
            self.after(0, self._log_write, f"[{label} title-check] {msg}")
        result = self.action.find_post(
            title=title, env=self.env, lang=lang,
            log_cb=_cb, verbose_cb=(_cb if verbose else None),
        )
        post_id = result.data if (result.success and result.data is not None) else None
        self.after(0, self._apply_title_check_result, lang, title, post_id)

    def _apply_title_check_result(self, lang, checked_title, post_id):
        try:
            self._pending_checks = max(0, self._pending_checks - 1)
            # Make sure the title hasn't changed since this check was kicked off.
            current = (self._title_he_var if lang == 'he' else self._title_en_var).get().strip()
            if current != checked_title:
                if self._pending_checks == 0:
                    self._status_var.set("Ready.")
                return
            self._existing_post_id[lang] = post_id
            self._refresh_update_existing_state(lang)
            if self._pending_checks == 0:
                self._status_var.set(
                    f"Existing post found (#{post_id})." if post_id else "Ready."
                )
            # Pre-populate image thumbnail and categories from the existing post.
            if post_id is not None:
                threading.Thread(
                    target=self._run_load_existing_post,
                    args=(lang, post_id),
                    daemon=True,
                ).start()
        except tk.TclError:
            # Window closed before the thread came back.
            pass

    def _run_load_existing_post(self, lang, post_id):
        """Background: fetch image URL + category IDs for an existing post."""
        result = self.action.fetch_post(post_id, env=self.env)
        self.after(0, self._apply_existing_post_fields, lang, post_id, result)

    def _apply_existing_post_fields(self, lang, post_id, result):
        """Main thread: pre-populate image thumbnail and category checkboxes."""
        try:
            # Guard: the user may have edited the title since the fetch started.
            if self._existing_post_id[lang] != post_id:
                return
            if not result.success or not result.data:
                return
            data = result.data

            # ── Categories ────────────────────────────────────────────
            # Map WordPress category IDs → names using the cached lookup,
            # then tick the matching checkboxes.
            cat_ids = set(data.get('categories', []))
            for cat_id in cat_ids:
                name = self._cat_id_to_name[lang].get(cat_id)
                if name and name in self._cat_vars[lang]:
                    self._cat_vars[lang][name].set(True)

            # ── Image thumbnail ───────────────────────────────────────
            # Show what image the existing post already has.  This is
            # purely visual — _image_path stays None so that saving without
            # a new image still uses Option C (reuse the existing media).
            media_url = data.get('media_url', '')
            if media_url and not self._image_path[lang]:
                threading.Thread(
                    target=self._run_fetch_thumbnail,
                    args=(lang, post_id, media_url),
                    daemon=True,
                ).start()
        except tk.TclError:
            pass

    def _run_fetch_thumbnail(self, lang, post_id, url):
        """Background: download the image bytes for thumbnail display."""
        try:
            import io as _io
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            self.after(0, self._apply_thumbnail_from_bytes, lang, post_id, resp.content)
        except Exception:
            pass  # thumbnail is purely cosmetic — silent failure is fine

    def _apply_thumbnail_from_bytes(self, lang, post_id, data):
        """Main thread: render downloaded image bytes as a thumbnail."""
        if not _PIL_AVAILABLE:
            return
        try:
            import io as _io
            # Guard: stale result if the post has changed.
            if self._existing_post_id[lang] != post_id:
                return
            # Don't override a thumbnail the user explicitly set this session.
            if self._image_path[lang]:
                return
            img   = Image.open(_io.BytesIO(data))
            img.thumbnail((140, 90))
            photo = ImageTk.PhotoImage(img)
            self._thumb_photo[lang] = photo
            label = self._thumb_label_he if lang == 'he' else self._thumb_label_en
            label.configure(image=photo, text='')
            path_var = self._img_path_var_he if lang == 'he' else self._img_path_var_en
            path_var.set('(existing post image)')
        except Exception:
            pass

    def _refresh_update_existing_state(self, lang):
        """Enable/disable the checkbox and refresh the (#1234) hint label
        based on current state.  Called whenever existence or lock state
        changes."""
        cb         = self._update_existing_cb[lang]
        is_checked = self._update_existing_var[lang].get()
        existing   = self._existing_post_id[lang]
        locked     = self._locked_post_id[lang]

        # Enable when either:
        #   - the title currently matches an existing post (so the user
        #     can opt-in to "I want to rename this one"), OR
        #   - the box is already checked (locked) — must remain enabled
        #     so the user can uncheck it.
        if existing is not None or is_checked:
            cb.configure(state='normal')
        else:
            cb.configure(state='disabled')

        # Hint text next to the checkbox
        if is_checked and locked:
            self._locked_id_label_var[lang].set(f"→ post #{locked}")
        elif existing is not None:
            self._locked_id_label_var[lang].set(f"(existing post #{existing})")
        else:
            self._locked_id_label_var[lang].set('')

    def _on_update_existing_toggled(self, lang):
        """User clicked the checkbox.  Lock or unlock the target post_id."""
        if self._update_existing_var[lang].get():
            # Just checked.  Lock in whatever existing post matches now.
            if self._existing_post_id[lang] is None:
                # Should not be reachable (the checkbox is disabled when
                # nothing matches) — undo the check defensively.
                self._update_existing_var[lang].set(False)
            else:
                self._locked_post_id[lang] = self._existing_post_id[lang]
        else:
            # Just unchecked.
            self._locked_post_id[lang] = None
        self._refresh_update_existing_state(lang)

    # ==================================================================
    # Defaults / persistence
    # ==================================================================

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

        # Kick off title-checks for any pre-loaded titles so the
        # "Update existing post" checkboxes get enabled where applicable.
        for lang in ('he', 'en'):
            self.after(200, self._check_title_exists, lang)

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

    # ==================================================================
    # Image selection
    # ==================================================================

    def _browse_image(self, lang):
        path = filedialog.askopenfilename(
            parent=self, title="Select image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.webp"),
                       ("All files", "*.*")],
        )
        if not path:
            return
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
            img.thumbnail((140, 90))
            photo = ImageTk.PhotoImage(img)
            self._thumb_photo[lang] = photo
            label_widget.configure(image=photo, text="")
        except Exception:
            label_widget.configure(image="", text="(preview unavailable)")

    # ==================================================================
    # Save flow
    # ==================================================================

    def _collect_lang(self, lang, fields):
        """Gather user input for ONE language column.  Validates only when
        this language has a non-empty title (i.e. the user wants this post
        saved).  Returns (data_dict, error_message_or_None)."""
        title_var   = self._title_he_var   if lang == 'he' else self._title_en_var
        date_var    = self._date_he_var    if lang == 'he' else self._date_en_var
        desc_widget = self._desc_he_text   if lang == 'he' else self._desc_en_text
        cap_widget  = self._caption_he_text if lang == 'he' else self._caption_en_text
        label       = "Hebrew" if lang == 'he' else "English"

        title = title_var.get().strip()
        date  = date_var.get().strip() if 'date' in fields else ''
        desc  = desc_widget.get("1.0", tk.END).strip() if 'description' in fields else ''
        cap   = cap_widget.get("1.0", tk.END).strip() if 'caption' in fields else ''
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

        if not title:
            return data, None
        if 'date' in fields and not date:
            return data, f"Enter a date ({label} side)."
        if 'description' in fields and not desc:
            return data, f"Enter a description ({label} side)."
        return data, None

    def _save_mode(self, lang):
        """Decide what kind of save this language needs.

        Returns (mode, target_id):
          ('update', post_id) — checkbox locked, OR title matches existing
          ('create', None)    — nothing to update, will create a new post
        """
        if self._update_existing_var[lang].get() and self._locked_post_id[lang]:
            return 'update', self._locked_post_id[lang]
        if self._existing_post_id[lang]:
            return 'update', self._existing_post_id[lang]
        return 'create', None

    def _on_save(self):
        template = self._template_var.get()
        if not template:
            messagebox.showwarning("No template", "Select a template.", parent=self)
            return

        fields = TEMPLATES[template].get('fields', [])

        he_data, he_err = self._collect_lang('he', fields)
        if he_err:
            messagebox.showwarning("Invalid input", he_err, parent=self); return
        en_data, en_err = self._collect_lang('en', fields)
        if en_err:
            messagebox.showwarning("Invalid input", en_err, parent=self); return

        if not he_data['title'] and not en_data['title']:
            messagebox.showwarning("Nothing to save",
                                   "Enter at least one title.", parent=self)
            return

        # Refuse identical titles when both sides will create new posts.
        # WordPress would happily create them but Hebrew search wouldn't be
        # able to disambiguate, and WPML translation linkage would be wrong.
        he_mode, he_target = self._save_mode('he')
        en_mode, en_target = self._save_mode('en')
        if (he_data['title'] and en_data['title']
                and he_data['title'] == en_data['title']
                and (he_mode == 'create' or en_mode == 'create')):
            messagebox.showerror(
                "Duplicate title",
                "The Hebrew and English titles are identical.\n\n"
                "Please ensure the Title of the Hebrew and English posts are different.",
                parent=self,
            )
            return

        self._save_defaults(template, {'he': he_data, 'en': en_data})
        self._save_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._log_clear()
        self._log_intro(template, he_data, en_data, he_mode, en_mode, he_target, en_target)

        # Pick the flow:
        bilingual_create = (
            he_data['title'] and en_data['title']
            and he_mode == 'create' and en_mode == 'create'
        )
        if bilingual_create:
            self._status_var.set("Bilingual create flow…")
            threading.Thread(
                target=self._run_bilingual_create,
                args=(template, he_data, en_data),
                daemon=True,
            ).start()
        else:
            self._status_var.set("Saving…")
            threading.Thread(
                target=self._run_independent,
                args=(template, he_data, he_mode, he_target,
                      en_data, en_mode, en_target),
                daemon=True,
            ).start()

    # ──────────────────────────────────────────────────────────────────
    # Bilingual create (Hebrew → duplicate → update English)
    # ──────────────────────────────────────────────────────────────────

    def _run_bilingual_create(self, template, he_data, en_data):
        """Both sides are new.  Three steps:
            1. Create the Hebrew post.
            2. Duplicate it to English (WPML link).
            3. Overwrite the English duplicate with the English-side fields.
        Wrapped in try/except so any uncaught exception still re-enables the UI.
        """
        def _set_status(msg):
            self.after(0, self._status_var.set, msg)

        results = {'he': None, 'en': None}
        try:
            # Step 1: Hebrew create
            results['he'] = self.action.run(
                template=template,
                title=he_data['title'],
                categories=he_data['categories'],
                date=he_data['date'],
                description=he_data['description'],
                image_path=he_data['image_path'],
                is_new_image=he_data['is_new_image'],
                caption=he_data['caption'],
                lang='he',
                env=self.env,
                progress_cb=lambda m: _set_status(f"Hebrew: {m}"),
            )
            he_result = results['he']
            if not he_result.success or not isinstance(he_result.data, dict):
                self.after(0, self._finish_save, template, results,
                           {'he': he_data, 'en': en_data},
                           {'he': None, 'en': None})
                return

            he_id      = he_result.data.get('id', 0)
            he_created = he_result.data.get('created', False)

            if not (he_id and he_created):
                # Hebrew was actually an UPDATE (e.g. title-check came back
                # late and the user clicked Save while is-existing wasn't
                # yet known).  Don't risk a duplicate translation; bail out.
                self.after(0, self._finish_save, template, results,
                           {'he': he_data, 'en': en_data},
                           {'he': None, 'en': None})
                return

            # Step 2: WPML duplicate
            _set_status("Duplicating Hebrew → English (WPML)…")
            dup_result = self.action.duplicate_to_lang(he_id, 'en', env=self.env)
            if not dup_result.success or not isinstance(dup_result.data, dict):
                results['en'] = dup_result
                self.after(0, self._finish_save, template, results,
                           {'he': he_data, 'en': en_data},
                           {'he': he_id, 'en': None})
                return

            en_id = dup_result.data.get('id', 0)

            # Step 3: Update the English duplicate with the English-side fields
            _set_status("Updating English content…")
            results['en'] = self.action.run(
                template=template,
                title=en_data['title'],
                categories=en_data['categories'],
                date=en_data['date'],
                description=en_data['description'],
                image_path=en_data['image_path'],
                is_new_image=en_data['is_new_image'],
                caption=en_data['caption'],
                lang='en',
                env=self.env,
                existing_id=en_id,                  # force update of THIS post
                progress_cb=lambda m: _set_status(f"English: {m}"),
            )
            self.after(0, self._finish_save, template, results,
                       {'he': he_data, 'en': en_data},
                       {'he': he_id, 'en': en_id})

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            for k in ('he', 'en'):
                if results[k] is None:
                    results[k] = ActionResult(
                        False, f"Unexpected error: {exc}\n\nTraceback:\n{tb}"
                    )
            self.after(0, self._finish_save, template, results,
                       {'he': he_data, 'en': en_data}, {'he': None, 'en': None})

    # ──────────────────────────────────────────────────────────────────
    # Independent save (each side processed separately)
    # ──────────────────────────────────────────────────────────────────

    def _run_independent(self, template,
                         he_data, he_mode, he_target,
                         en_data, en_mode, en_target):
        """Each side is processed independently — used whenever at least one
        side is updating an existing post (no WPML duplication needed)."""
        def _set_status(msg):
            self.after(0, self._status_var.set, msg)

        results  = {'he': None, 'en': None}
        ids_used = {'he': he_target, 'en': en_target}
        labels   = {'he': 'Hebrew', 'en': 'English'}
        plan     = (
            ('he', he_data, he_mode, he_target),
            ('en', en_data, en_mode, en_target),
        )

        try:
            for lang, data, mode, target in plan:
                if not data['title']:
                    continue
                _set_status(f"{labels[lang]}: {mode}…")
                results[lang] = self.action.run(
                    template=template,
                    title=data['title'],
                    categories=data['categories'],
                    date=data['date'],
                    description=data['description'],
                    image_path=data['image_path'],
                    is_new_image=data['is_new_image'],
                    caption=data['caption'],
                    lang=lang,
                    env=self.env,
                    existing_id=target,
                    progress_cb=lambda m, l=lang: _set_status(
                        f"{labels[l]}: {m}"
                    ),
                )
                if results[lang].success and isinstance(results[lang].data, dict):
                    ids_used[lang] = results[lang].data.get('id', target)

            self.after(0, self._finish_save, template, results,
                       {'he': he_data, 'en': en_data}, ids_used)

        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            for k in ('he', 'en'):
                if results[k] is None and (he_data if k == 'he' else en_data)['title']:
                    results[k] = ActionResult(
                        False, f"Unexpected error: {exc}\n\nTraceback:\n{tb}"
                    )
            self.after(0, self._finish_save, template, results,
                       {'he': he_data, 'en': en_data}, ids_used)

    # ──────────────────────────────────────────────────────────────────
    # Finish (both flows funnel into here)
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _link_from_result(result):
        if result and result.success and isinstance(result.data, dict):
            return result.data.get('link', '') or ''
        return ''

    def _log_intro(self, template, he_data, en_data, he_mode, en_mode, he_target, en_target):
        self._log_write(f"Template: {template}\n")
        for lang, label, data, mode, target in (
            ('he', 'Hebrew',  he_data, he_mode, he_target),
            ('en', 'English', en_data, en_mode, en_target),
        ):
            if not data['title']:
                continue
            verb = ("update post #%d" % target) if mode == 'update' else "create new post"
            self._log_write(f"\n[{label}] Plan: {verb}\n")
            self._log_write(f"  Title: {data['title']}\n")
            if data['date']:
                self._log_write(f"  Date:  {data['date']}\n")
            if data['description']:
                s = data['description']
                self._log_write(f"  Desc:  {s[:60]}{'…' if len(s) > 60 else ''}\n")
            if data['image_path']:
                lbl = "Pasted image" if self._image_temp[lang] else os.path.basename(data['image_path'])
                self._log_write(f"  Image: {lbl}\n")
            if data['caption']:
                s = data['caption']
                self._log_write(f"  Caption: {s[:60]}{'…' if len(s) > 60 else ''}\n")
            if data['categories']:
                self._log_write(f"  Categories: {', '.join(data['categories'])}\n")
        self._log_write("\n")

    def _finish_save(self, template, results, lang_data, ids_used):
        try:
            overall_ok = True
            for lang, label in (('he', 'Hebrew'), ('en', 'English')):
                r = results.get(lang)
                if r is None:
                    if lang_data[lang]['title']:
                        # We had work to do but didn't get a result — usually
                        # because an earlier step failed and we bailed.
                        self._log_write(f"[{label}] Skipped.\n")
                    continue
                if r.success:
                    self._log_write(f"[{label}] Done. {r.message}\n")
                    link = self._link_from_result(r)
                    if link:
                        self._log_write(f"[{label}] URL: {link}\n")
                else:
                    overall_ok = False
                    self._log_write(f"[{label}] Error: {r.message}\n")
                    if "401" in (r.message or ''):
                        from portal.gui.credentials_dialog import CredentialsDialog
                        CredentialsDialog(self, on_save=lambda: self._status_var.set(
                            "Credentials updated. Try again."))

            self._status_var.set("Saved." if overall_ok else "One or more errors — see log.")

            if overall_ok:
                # Both posts now exist on the site.  Mark them as "existing"
                # so the next click on Save will update (not duplicate).
                for lang in ('he', 'en'):
                    new_id = ids_used.get(lang)
                    if new_id:
                        self._existing_post_id[lang] = new_id
                        # Leave _locked_post_id alone unless the user had it
                        # locked already — but if not locked, the title-match
                        # path will handle the next save.
                    self._refresh_update_existing_state(lang)
                # Image was just saved.  Reset the per-session "user picked"
                # flags so the next update reuses the post's existing media
                # (Option C) instead of re-uploading.
                self._image_user_set = {'he': False, 'en': False}

        except tk.TclError:
            pass
        finally:
            try:
                self._save_btn.configure(state="normal")
                self._delete_btn.configure(state="normal")
            except tk.TclError:
                pass

    # ==================================================================
    # Delete post
    # ==================================================================

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

        # Use any post IDs already known from the title-check or locked checkbox
        # so we skip a redundant find_post() call (which can fail for older posts
        # due to WordPress search ranking — see decisions / bug fix 2026-05-12).
        known_ids = {
            lang: self._locked_post_id[lang] or self._existing_post_id[lang]
            for lang in ('he', 'en')
        }

        self._save_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._status_var.set("Deleting…")
        threading.Thread(
            target=self._run_delete_both,
            args=(title_he, title_en, delete_image, known_ids),
            daemon=True,
        ).start()

    def _delete_confirm_dialog(self, title_he, title_en):
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

    def _run_delete_both(self, title_he, title_en, delete_image, known_ids=None):
        known_ids = known_ids or {}
        results = {}
        for lang, title in (('he', title_he), ('en', title_en)):
            label = 'Hebrew' if lang == 'he' else 'English'
            if not title:
                results[lang] = {'post': None, 'media': None}
                continue
            # Prefer the ID already resolved by the title-check; only call
            # find_post() when we genuinely don't know the ID yet.
            post_id = known_ids.get(lang)
            if post_id is not None:
                self.after(0, self._log_write,
                           f"[{label}] Using cached post ID {post_id} (from title-check).\n")
            else:
                self.after(0, self._log_write,
                           f"[{label}] No cached ID — searching by title…\n")
                verbose = self._verbose_var.get()
                def _cb(msg, l=label):
                    self.after(0, self._log_write, f"[{l}] {msg}")
                find = self.action.find_post(
                    title=title, env=self.env, lang=lang,
                    log_cb=_cb, verbose_cb=(_cb if verbose else None),
                )
                if not find.success:
                    results[lang] = {'post': find, 'media': None}
                    continue
                post_id = find.data
            if post_id is None:
                results[lang] = {'post': None, 'media': None}
                continue
            media_id = self.action.get_post_media_id(post_id, env=self.env) if delete_image else 0
            post_result  = self.action.delete(post_id=post_id, env=self.env)
            media_result = None
            if delete_image and media_id and post_result.success:
                media_result = self.action.delete_media(media_id=media_id, env=self.env)
            results[lang] = {'post': post_result, 'media': media_result}
        self.after(0, self._finish_delete, results, title_he, title_en)

    def _finish_delete(self, results, title_he, title_en):
        overall_ok = True
        for lang, label, title in (('he', 'Hebrew', title_he), ('en', 'English', title_en)):
            r            = results.get(lang, {})
            post_result  = r.get('post')
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
        # The posts (and possibly the locked IDs) are gone — clear state.
        for lang in ('he', 'en'):
            self._existing_post_id[lang] = None
            self._locked_post_id[lang]   = None
            self._update_existing_var[lang].set(False)
            self._refresh_update_existing_state(lang)
        self._save_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    # ==================================================================
    # Log helpers
    # ==================================================================

    def _log_write(self, text):
        # Guard: background threads schedule self.after(0, _log_write, ...)
        # which can fire after the window has been destroyed (e.g. user clicked
        # Cancel while a title-check was still in flight).  Silently ignore.
        try:
            self._log.configure(state="normal")
            self._log.insert(tk.END, text)
            self._log.see(tk.END)
            self._log.configure(state="disabled")
        except tk.TclError:
            pass

    def _log_clear(self):
        try:
            self._log.configure(state="normal")
            self._log.delete("1.0", tk.END)
            self._log.configure(state="disabled")
        except tk.TclError:
            pass

    def _center(self, parent):
        self.update_idletasks()
        x = max(40, min(parent.winfo_rootx() + 40,
                        self.winfo_screenwidth()  - self.winfo_width()  - 20))
        y = max(40, min(parent.winfo_rooty() + 40,
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
