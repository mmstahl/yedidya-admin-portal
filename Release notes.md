# Release Notes — Yedidya Admin Portal

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
