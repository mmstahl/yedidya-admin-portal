# Test Strategy — Yedidya Admin Portal

**Version:** 1.0
**Date:** 2026-03-22
**Author:** Tester Agent
**Status:** Approved — ready for implementation

---

## 1. Context

- **Product:** Yedidya Admin Portal — local Windows desktop app (Python/Tkinter)
- **Scope:** Portal core + two actions: Members List, Delete Users
- **Release cadence:** Manual — developer builds and distributes `.exe` as needed
- **Environments:** Developer machine (local) / Staging WordPress / Production WordPress
- **Key dependencies:** WordPress REST API, Windows Credential Manager (`keyring`), SFTP (`paramiko`), WooCommerce GDPR plugin (`yedidya-gdpr-erase`)

---

## 2. Quality Goals

| Goal | Target |
|------|--------|
| Core actions succeed on valid input | 100% — no silent failures |
| Auth errors caught and surfaced | 401 must trigger credential update prompt |
| Data integrity | CSV input → PDF output produces correct member count |
| No credentials in plaintext | Zero occurrences in logs, files, or exceptions |
| Destructive operations require confirmation | Delete Users always shows preview before running |
| GDPR erasure removes personal data | Verified by inspecting WooCommerce response |
| Defaults persist correctly | Changed paths saved and reloaded on next run |

---

## 3. Risk Model

| Journey | Failure Modes | Impact | Likelihood | Primary Test Layer |
|---------|---------------|--------|------------|--------------------|
| Credential storage & retrieval | Wrong env keys, keyring unavailable, plaintext leak | High | Low | Unit |
| Members List: fetch from WordPress | 401/403, network timeout, malformed JSON, empty result | High | Medium | Unit + Integration |
| Members List: pre-process CSV | Missing columns, encoding issues, empty file, bad data | High | Medium | Unit |
| Members List: generate PDF | Missing font files, Hebrew RTL corruption, empty dataset | High | Low | Unit |
| Members List: SFTP upload | Auth failure, wrong remote path, connection timeout | Medium | Medium | Unit |
| Members List: production confirmation | User skips review step, upload proceeds without confirmation | High | Low | Unit (behaviour) |
| Delete Users: CSV input | No header, wrong column name, encoding, empty file | High | Medium | Unit |
| Delete Users: preview lookup | Email not found, partial matches, 401, network error | High | Medium | Unit + Integration |
| Delete Users: standard delete | Already-deleted user, 404 handling, reassign parameter | High | Low | Unit |
| Delete Users: GDPR erase | Plugin not active (404), WooCommerce retains data, partial success | High | Medium | Unit + Integration |
| Environment switching | Wrong credentials used for wrong env, defaults bleed across envs | High | Low | Unit |
| Defaults persistence | Paths not saved, wrong env key, config.json corruption | Medium | Low | Unit |

---

## 4. Test Portfolio

### Layer Decisions

This is a **local desktop tool** with no web frontend and no CI server. The test pyramid is adapted accordingly:

```
          /\
         /  \   Manual smoke (run portal, verify happy path)
        /----\
       / Integ \  Pipeline end-to-end with mocked HTTP (no live WP)
      /----------\
     /    Unit    \  All logic, all error paths, all boundary cases
    /--------------\
```

**GUI layer is excluded** — Tkinter windows are not unit-tested. Logic tested at the action and module layer.

---

### Unit Tests (`tests/`)

Fast, offline, no real credentials or network. Mock at every external boundary.

#### `test_credential_manager.py`
- `get()` returns stored value for the correct env key
- `get()` returns empty string when key absent
- `save()` writes to the correct namespaced key (`staging.wp_url`, `production.wp_url`, etc.)
- `has_credentials()` returns False when any field missing
- `has_credentials()` returns True only when all six fields present
- `clear()` removes all keys for the given env
- Staging credentials do not bleed into production keys

#### `test_defaults_manager.py`
- `get()` returns seed default when config.json absent
- `set_default()` writes value and persists to disk
- Changed value is returned on next `get()`
- `staging_sftp_remote_path` and `production_sftp_remote_path` stored independently
- `portal.environment` seed default is `'staging'`
- Corrupted config.json falls back to seed defaults without crashing

#### `test_members_list_action.py`
- `run_generate()` calls fetch → pre-process → generate in order
- `run_generate()` returns `ActionResult(success=True)` with `data=pdf_path` on success
- `run_generate()` returns `ActionResult(success=False)` on 401 from fetch step
- `run_generate()` returns `ActionResult(success=False)` on network timeout
- `run_generate()` surfaces warning when member count is zero
- `upload()` calls SFTP with correct host, user, password, remote path
- `upload()` returns error result on SFTP auth failure
- `get_defaults()` returns env-specific SFTP remote path
- `save_defaults()` persists local paths and env-specific SFTP path

#### `test_delete_users_action.py`
- `_read_csv()` accepts column named `email`, `Email`, or `EMAIL`
- `_read_csv()` accepts first column when no `email` column found
- `_read_csv()` skips header row correctly
- `_read_csv()` skips blank rows
- `_read_csv()` returns error on missing file
- `_read_csv()` returns error on empty file
- `_lookup_user()` returns user dict on exact email match
- `_lookup_user()` returns None when email not in results (partial match guard)
- `_lookup_user()` raises `ConnectionError` on 401
- `preview()` returns correct found/not_found/error lists
- `_standard_delete()` sends DELETE with `force=true&reassign=false`
- `_standard_delete()` returns `("Deleted", False)` on 200
- `_standard_delete()` returns error message on non-2xx
- `_gdpr_erase()` POSTs to `/wp-json/yedidya/v1/gdpr-erase` with email
- `_gdpr_erase()` returns success with warnings extracted from response
- `_gdpr_erase()` returns error on 404 (plugin not active)
- `run()` with `gdpr_mode=False` calls `_standard_delete`, not `_gdpr_erase`
- `run()` with `gdpr_mode=True` calls `_gdpr_erase`, not `_standard_delete`
- `run()` reports per-user results including warnings
- `run()` returns partial-success result when some users fail

#### `pipeline/test_fetch_members.py`
- `fetch_members()` calls the correct WP REST API endpoint
- Returns CSV file at `output_path` on success
- Returns member count matching records fetched
- Raises `ConnectionError` on 401
- Raises `ConnectionError` on 403
- Raises `TimeoutError` on request timeout
- Handles paginated response (multiple pages merged)

#### `pipeline/test_pre_process.py`
- Output CSV contains only expected columns
- Rows are sorted correctly
- Malformed rows produce a warning, not a crash
- Empty input file returns error result
- Output row count returned accurately

#### `pipeline/test_generate_pdf.py`
- PDF file created at `output_path` on success
- Font files loaded from `fonts_dir` (using test fixture fonts)
- Hebrew text in member names does not corrupt the PDF (RTL check)
- Empty member list produces a warning result, not a crash

---

### Integration Tests (`tests/integration/`)

Test the full pipeline end-to-end, but with mocked HTTP (no live WordPress).

#### `test_members_list_pipeline.py`
- Full pipeline: mocked WP fetch → real pre-process → real PDF generation → mocked SFTP
- Output PDF exists and is non-empty
- Member count in ActionResult matches rows in input fixture
- Any intermediate file failure stops the pipeline and returns a clear error

#### `test_delete_users_pipeline.py`
- preview() + run() sequence with mocked WP API
- Standard delete: all users in fixture deleted, results reported per user
- GDPR erase: mocked GDPR endpoint called for each user, warnings surfaced
- Mixed result (some found, some not): partial-success ActionResult returned

---

### Smoke Tests (Manual Checklist)

Run manually before any distribution of a new `.exe`. Not automated.

**Portal startup:**
- [ ] First run: credentials dialog appears offset from main window (both visible)
- [ ] Staging is selected by default
- [ ] All fields pre-filled with stored defaults

**Members List (Staging):**
- [ ] Run generates PDF at specified path
- [ ] SFTP uploads file to staging server
- [ ] Changed path saved as new default on next launch
- [ ] 401 mid-run opens credentials dialog automatically

**Members List (Production):**
- [ ] PDF generated, confirmation dialog appears with "Open PDF" option
- [ ] Upload proceeds only after confirmation
- [ ] Cancelling upload leaves PDF locally, reports "upload skipped"

**Delete Users:**
- [ ] CSV with header row: preview shows correct matched users
- [ ] CSV with unknown emails: not-found listed separately
- [ ] Confirmation required before any deletion runs
- [ ] Standard delete: user removed from WP, WC customer record gone
- [ ] GDPR checkbox: warning dialog appears before proceeding
- [ ] GDPR erase: personal data anonymised in WC orders, warnings reported
- [ ] Already-deleted user: preview returns "not found" cleanly, Run still available

---

## 5. Mocking Strategy

| Dependency | Mock approach |
|------------|--------------|
| WordPress REST API | `responses` library — register expected URLs and return fixture JSON |
| `keyring` | `unittest.mock.patch('keyring.get_password')` and `set_password` |
| `paramiko.SSHClient` | `pytest-mock` — mock `connect()`, `open_sftp()`, `put()` |
| File system (input CSVs) | `tmp_path` pytest fixture — write fixture CSV, pass path to function |
| Font files | `tests/fixtures/fonts/` — copy of Alef fonts checked into test fixtures |
| PDF output | Verify file exists and `os.path.getsize() > 0`; full content not asserted |

---

## 6. Test Data & Fixtures

| Fixture | Contents | Used by |
|---------|----------|---------|
| `fixtures/members_raw.csv` | 10 realistic member rows, Hebrew names, valid emails | fetch, pre-process, pipeline |
| `fixtures/members_empty.csv` | Header row only | edge case tests |
| `fixtures/members_bad_encoding.csv` | Mixed encoding rows | pre-process robustness |
| `fixtures/delete_list.csv` | 5 emails: 3 exist in WP mock, 2 do not | delete preview + run |
| `fixtures/delete_list_no_header.csv` | Same 5 emails, no header | CSV parsing test |
| `fixtures/wp_users_response.json` | Mock WP `/wp/v2/users` response | lookup tests |
| `fixtures/gdpr_response.json` | Mock GDPR erase success response with Hebrew warnings | GDPR tests |
| `fixtures/fonts/` | Alef-Regular.ttf, Alef-Bold.ttf | PDF generation tests |

---

## 7. What Is Not Tested (and Why)

| Area | Reason |
|------|--------|
| Tkinter GUI windows | Not unit-testable; covered by manual smoke tests |
| Live WordPress API | Requires credentials and network; mocked in all automated tests |
| Live SFTP | Requires server access; mocked in all automated tests |
| PHP plugin internals | PHP tested on the WP server, not in this Python test suite |
| PyInstaller `.exe` build | Manual build and smoke test before distribution |
| WooCommerce order retention rules | External WC behaviour; documented, not asserted |

---

## 8. Running the Tests

```bash
# Install test dependencies
pip install pytest pytest-mock responses

# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=portal --cov=D:/OneDrive\ -\ ITCB/Support/UtilInstalls/MemberList-Generator

# Run a specific module
pytest tests/test_delete_users_action.py -v
```

---

## 9. Definition of Done (per feature)

Before any code change is considered complete:
- All existing tests pass
- New behaviour has at least one direct test
- Any new error path has a test asserting the correct `ActionResult`
- Manual smoke checklist item checked off if the change touches the GUI

---

## 10. Future Tests (Out of Scope for v1)

- Contract tests against WordPress REST API schema (if API version changes become a risk)
- Performance test: PDF generation time with 500+ members
- Security: credential never appears in exception tracebacks
