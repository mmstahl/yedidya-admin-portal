# Release Notes — Yedidya Admin Portal

---

## v1.3.4 — 2026-05-12

### Fixed
- **Root cause of `find_post` always returning empty**: the search request included `?status=any&context=edit`. WordPress.com staging silently returns `HTTP 200 []` (empty array) when `context=edit` is requested by a credential that lacks `edit_others_posts` — no 403, no error, just zero results. Removed both `status=any` and `context=edit` from `find_post`. Published posts are all that's needed for title-check and delete, and `rendered` titles are sufficient for matching.

---

## v1.3.3 — 2026-05-12

### Diagnostic
- Added detailed logging to `find_post` (and the title-check flow) so every search attempt is visible in the window's log panel:
  - Original vs cleaned title (shows if invisible Unicode chars were stripped)
  - Full URL + params for each search pass
  - HTTP status code and result count
  - Each returned post's ID, raw title, and whether it matched
  - Which pass (with/without `?lang=`) succeeded or failed

---

## v1.3.2 — 2026-05-12

### Fixed
- **`find_post` still failing for existing posts** — three compounding causes, all fixed:
  1. *Unicode format characters*: browsers embed invisible RTL marks (U+200F etc.) in copied Hebrew text. WordPress never stores these. Added `_clean_title()` helper that strips all Unicode category-Cf characters before searching and comparing.
  2. *WPML lang filter too strict*: when a post isn't registered in WPML's language table, `?lang=he` silently returns 0 results. `find_post` now tries with `?lang=` first, then retries without it as a fallback.
  3. *Comparison now strips Cf chars from both sides* (input AND the stored raw/rendered title).

### New
- **Pre-populate fields from existing post**: when a title-check finds an existing post, the portal now fetches the post from WordPress and:
  - Shows the post's current image as a thumbnail (labeled "existing post image").
  - Pre-ticks the post's current categories on the matching side.
  - Does not override a new image or categories the user has already selected in this session.
- Added `fetch_post(post_id, env)` to `PostEventAction`.
- Added `_cat_id_to_name` mapping populated alongside `_cat_vars` during the category fetch, enabling ID→name resolution for pre-population.

---

## v1.3.1 — 2026-05-12

### Fixed
- **Delete post: "No post found with title"** when deleting a post that was not created in the current session.
  - Root cause 1: The delete flow was ignoring the post ID already resolved by the background title-check (`_existing_post_id`), forcing an unnecessary second `find_post()` call that could fail.
  - Root cause 2: `find_post()` searched with `per_page=20`. WordPress ranks results by recency, so older posts could fall outside the first 20 results and never be matched.
  - Fix: `_on_delete()` now passes already-known post IDs to the delete thread; `find_post()` uses `per_page=100` and matches against both `raw` and `rendered` titles.

---

## v1.3.0 — 2026-05-12

### New
- Version number introduced. Displayed in the status bar (bottom-right, gray). Stored in `portal/version.py`.

### Changed
- Status bar is now a two-label frame: status message on the left, version on the right.

### Post Event (bilingual flow)
- Replaced tabbed Hebrew/English layout with side-by-side parallel layout.
- Hebrew and English fields are displayed together, aligned row-by-row.
- New "Create → Duplicate → Update" bilingual flow: create Hebrew post, WPML-duplicate it, update the English copy.
- Per-side "Update existing post" checkbox with automatic title lookup.
- Categories are now loaded dynamically from WordPress (via `yedidya/v1/category-pairs` endpoint) instead of a hardcoded list.
- Categories from both languages are aligned by WPML translation group (trid).
- Fixed: POST requests no longer silently redirect to GET (WordPress trailing-slash 301 redirect). Added `_post()` helper that follows redirects while preserving POST method.
- Fixed: WPML translation linking now uses custom PHP endpoint (`yedidya/v1/duplicate-post`) instead of the standard WP REST API (which ignores `icl_translation_of`).
- Fixed: English category IDs now resolved from Hebrew via `wpml_object_id` filter on the PHP side.
- Fixed: Caption field uses `wrap='word'` (no scrollbar); description field uses `wrap='none'` + horizontal scrollbar.

### PHP Plugin
- New file: `post-event.php` — registers `POST /wp-json/yedidya/v1/duplicate-post` and `GET /wp-json/yedidya/v1/category-pairs`.
- `duplicate-post`: creates a WPML-linked translation using `wpml_set_element_language_details`. Translates category IDs via `wpml_object_id`. Returns warnings for categories with no translation.
- `category-pairs`: returns all categories grouped by WPML trid, sorted by Hebrew name. Uses direct `$wpdb` SQL to bypass WPML's `get_terms()` language filter.
- All PHP functions now wrapped in `function_exists()` guards (reversed prior "no guards" decision after a live site crash from duplicate definitions).
- Added `db-extract.php` to the output folder (was on server but not tracked locally).
