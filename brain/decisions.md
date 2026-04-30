# Decisions

Standing decisions and choices. Updated by the Chief of Staff after noteworthy decisions.

---

## 2026-03-19 — Added `dev` as a specialist agent

**Decision:** Add a Python developer (`dev`) to the base team of 4.

**Why:** The project is fundamentally a coding project — a distributable desktop portal in Python. The base team (Martha, designer, writer, gatekeeper) has no coding capability. A dev agent is a clear must-have.

**Alternatives rejected:** Adding a `frontend-dev` (as in the sub-project) was considered but rejected — the UI is intentionally minimal ("basic page with fields, dropdowns, buttons, nothing fancy") and doesn't warrant a dedicated frontend specialist.

---

## 2026-03-22 — Staging/Production environments

**Decision:** Portal always defaults to Staging on startup, regardless of last-used environment. Production requires an explicit switch.

**Why:** Prevents accidental production runs. The main window shows a red ⚠ PRODUCTION label when production is active as an additional visual warning.

**Alternatives rejected:** Persisting last-used environment as default — too risky for a destructive tool.

---

## 2026-03-22 — Members List: production requires PDF review before upload

**Decision:** In production mode, the portal generates the PDF, opens it for the user to review, then asks for explicit confirmation before uploading via SFTP. In staging, upload happens automatically.

**Why:** Production is the live site. An incorrect members list going live is a meaningful risk.

---

## 2026-03-22 — GDPR erase: delete WooCommerce orders, not anonymize

**Decision:** GDPR erase deletes WooCommerce orders (`$order->delete(true)`) rather than anonymizing them.

**Why:** The user explicitly wants full erasure of payment history for GDPR compliance. WooCommerce's built-in erasure only anonymizes.

**Alternatives rejected:** Using `WC_Privacy_Erasers` built-in (anonymizes, doesn't delete) — rejected because the user wants full deletion, not masked data.

---

## 2026-04-19 — No function_exists guards in portal PHP files

**Decision:** Do not wrap functions in `function_exists()` guards in `gdpr-erase.php`, `member-export.php`, or other portal sub-files.

**Why:** Guards silently hide duplicate function conflicts. Without them, a redeclaration causes an immediate PHP fatal, making the conflict obvious and forcing it to be resolved properly.

**How to handle conflicts:** If a function is already defined by another active plugin, deactivate or delete that standalone plugin rather than adding guards. The portal plugin is the canonical home for this functionality.

---

## 2026-04-22 — Bilingual post creation: Option C implemented, Option B deferred

**Decision:** Implemented Option C — separate Hebrew and English content fields in the portal UI, two independent API calls (one per language) with `lang=he` / `lang=en`.

**Option B (deferred):** Link the two posts as WPML translations by passing `icl_translation_of=<he_post_id>` in the English post creation call. Return point: `post_event_action.py › run()` step 6 (create/update post). The `lang` param is already wired through. Missing piece: thread the Hebrew post ID from the first call's result into the second call, and add it to `post_body` as `icl_translation_of`. Exact WPML REST API field name needs testing (`icl_translation_of` is most likely).

**Why deferred:** Option B requires knowing the exact WPML parameter name for translation linking and testing it. Option C gives the user bilingual posts immediately with minimal risk.

---

## 2026-04-25 — Image deduplication: Option C (reuse ID from post content)

**Decision:** When updating a post without selecting a new image, reuse the media item already embedded in the existing post's Gutenberg block. Do not search by filename or filesize.

**How it works:** `run()` calls `find_post()` before the image step. If the post exists and `image_path=''`, it fetches the post's raw content, extracts the media ID via `re.search(r'<!-- wp:image \{"id":(\d+)', raw)`, then calls `GET /wp-json/wp/v2/media/{id}` to get the current URL. The `_image_user_set` flag (per language) tracks whether the user explicitly picked a new image this session; it is reset to `False` after every successful save.

**Alternatives rejected:**
- Filename matching — WordPress renames uploads (e.g., `english.jpg` → `english-7.jpg`) whenever a file with the same base name exists, even in trash. Filename matching never finds the existing file.
- Filesize comparison — unreliable; WordPress may re-encode images on upload.

---

## 2026-04-25 — Hebrew RTL text: wrap='none' + scrollbar

**Decision:** Hebrew `tk.Text` fields (description, caption) use `wrap='none'` with a horizontal scrollbar, and a `justify='right'` tag applied on every keystroke. Hebrew `ttk.Entry` fields (title, date) use `justify='right'`.

**Why:** tkinter has no Unicode BiDi engine. With `wrap='word'` or `wrap='char'`, the LTR wrap logic causes Hebrew text to "teleport" to position 0 of the next line when a line fills up. `wrap='none'` eliminates wrapping entirely — text scrolls horizontally, cursor always stays in the correct position relative to typed characters. Known remaining limitation: clicking in the middle of Hebrew text positions the cursor inaccurately (LTR mouse-to-index mapping vs RTL visual layout). This is a hard tkinter ceiling with no workaround.

**Alternatives rejected:** `wrap='char'` — still caused the teleport bug. RFC 5987 Hebrew filenames in HTTP headers — WordPress.com staging returns 400; solution is to validate filenames are ASCII in the GUI.

---

## 2026-04-25 — Post/Update Event: no Hebrew→English auto-sync

**Decision:** Each language tab (Hebrew, English) is fully independent. No automatic copying of Hebrew field values into English fields.

**Why:** Initially implemented auto-sync (copy Hebrew to English on first FocusOut per field). Removed at user's explicit request — the user wants to write each language independently.

---

## 2026-03-22 — GDPR plugin: standalone, no WooCommerce core modifications

**Decision:** GDPR erasure is implemented as a standalone plugin (`yedidya-gdpr-erase`) that calls WooCommerce classes. WooCommerce files are never modified.

**Why:** WooCommerce updates would overwrite any changes to core files. A standalone plugin survives updates safely.
