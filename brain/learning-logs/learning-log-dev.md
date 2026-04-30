# Learning Log — Dev

*Updated by the dev agent after completing tasks. Captures decisions, surprises, and things to carry forward.*

---

## 2026-03-22 — Portal v1 build + Delete Users action

**What worked:**
- Splitting `run()` into `run_generate()` + `run_upload()` (for production review gate) was clean — the GUI's two-phase thread model handled it well.
- Per-environment credential keys (`staging.wp_url`, `production.wp_url`) in keyring is simple and unambiguous. Works well.
- Storing SFTP remote path per-env in `config.json` (`staging_sftp_remote_path` / `production_sftp_remote_path`) while keeping local paths shared — correct separation.
- GDPR erasure via a standalone plugin calling `wc_get_orders()` + `wp_delete_user()` — no WooCommerce core files touched, survives WC updates.

**What failed / bugs caught:**
- `GDPR_ERASE_ENDPOINT` was missing the `/wp-json/` prefix → 404 HTML response. Pattern: always verify full REST API URL including `/wp-json/` when constructing endpoints.
- `ActionResult.__init__()` didn't accept a `data=` kwarg — caused a crash after PDF generation. Keep `ActionResult` signature consistent with how actions use it.
- `SyntaxWarning: invalid escape sequence` in `defaults_manager.py` docstring — backslash in a plain string. Use raw strings (`r"""..."""`) or forward slashes in docstring paths.

**Patterns to repeat:**
- Credential dialog: offset from parent window (+40, +40) so both are visible on first run.
- Production environment: always show a visible warning label (red ⚠ PRODUCTION) in the main window — prevents accidental production runs.
- GDPR erase should always be safe to run even if the WP account was already deleted — match by email, skip user deletion gracefully.

---

## 2026-04-25 — Post/Update Event: bilingual UI + image dedup + Hebrew RTL

**What worked:**
- `BooleanVar`-backed `Checkbutton` widgets for category selection — state persists across notebook tab switches regardless of widget visibility. `Listbox.selection_set()` on hidden tabs is unreliable on Windows; never use it.
- `_image_user_set` flag pattern: set `True` only when user explicitly picks an image via Browse or Paste this session; reset to `False` after each successful save. Controls whether `run()` uploads a new image or reuses the one already in the post (Option C).
- Option C image deduplication: instead of searching by filename/filesize (both unreliable — see failures below), fetch the existing post's raw Gutenberg content and extract the media ID via `re.search(r'<!-- wp:image \{"id":(\d+)', raw)`, then `GET /wp-json/wp/v2/media/{id}` to get the URL. Clean and exact.
- Moving `find_post()` to before the image step in `run()` — required so Option C knows whether a post exists before deciding whether to upload or reuse.
- `wrap='none'` + horizontal scrollbar for Hebrew `tk.Text` fields — eliminates the "text teleports to position 0" wrap confusion caused by tkinter's LTR wrap logic applied to RTL text. `justify='right'` tag applied on `<KeyRelease>` keeps visual alignment correct.
- `justify='right'` on Hebrew `ttk.Entry` (title, date) — fixes cursor/delete mismatch for RTL characters.
- Background thread calling `find_post` for title-check: wrap the UI callback in `try/except tk.TclError` — the window may be destroyed before the thread finishes, causing a TclError on widget configure.
- `re.subn(..., count=1)` with `new_block` as the replacement string — the replacement string must not contain backslashes that look like regex back-references. WordPress image block content is safe, but be aware.

**What failed / bugs caught:**
- **WordPress renames uploads**: uploading `english.jpg` when `english.jpg` already exists (even in trash) creates `english-7.jpg`. Filename-based dedup never works. Filesize comparison also unreliable (WordPress may re-encode). Abandoned both; Option C (ID from existing post content) is the correct approach.
- **`Listbox.selection_set()` on hidden notebook tabs**: completely unreliable on Windows — selections silently drop when the tab is hidden. Multiple fix attempts all failed. Only cure: replace Listbox with `BooleanVar` + `Checkbutton`.
- **`_image_user_set` not reset after save**: if the user picks an image and saves, then saves again without touching the image, the flag is still `True` so the image gets re-uploaded. Fix: reset both flags to `False` in `_finish_create` on success.
- **`is_update` detection via button label**: fragile — depends on a background thread completing before the user clicks. If the thread is slow, button still says "Create Post" and the create-branch logic runs (re-uploading images). Acceptable for now but worth noting.
- **RFC 5987 filename encoding in `Content-Disposition` header**: attempted to support Hebrew filenames via `filename*=UTF-8''<percent-encoded>` — WordPress.com staging returns 400. Solution: validate filename is ASCII at the Browse step in the GUI and reject non-ASCII filenames with a clear message.
- **Auto-sync (Hebrew → English) complexity**: implemented, then removed per user request. The `_synced` set + `_syncing_now` flag + `_setup_english_edit_protection` approach worked correctly but added significant complexity. Removing it was simpler.
- **Image duplication (both languages uploading same file)**: when Hebrew image was auto-synced to English, both `run()` calls got the same path and both uploaded. Removed by not auto-syncing images and making each language tab fully independent.

**Patterns to repeat:**
- For any WordPress media operation: always work with media IDs, never filenames.
- For tkinter category/selection state that must survive tab switches: use `BooleanVar` + `Checkbutton`, not `Listbox`.
- For Hebrew text input in tkinter: `justify='right'` on Entry, `wrap='none'` + scrollbar + `justify='right'` tag on Text. Accept that click-to-cursor in mid-text is a hard tkinter limit (no BiDi engine).
- Reset session-tracking flags (`_image_user_set`) after each successful save operation.
- When deleting a WordPress post and its image: fetch media ID from post content *before* deleting the post, then delete media after.
