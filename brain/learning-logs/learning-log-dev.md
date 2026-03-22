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
