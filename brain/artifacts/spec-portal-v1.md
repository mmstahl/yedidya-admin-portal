# Architecture Spec: Yedidya Admin Portal v1

**Version:** 1.1
**Date:** 2026-03-19
**Status:** Approved
**Author:** Dev Agent

---

## Executive Summary

The Yedidya Admin Portal is a local Windows desktop application that wraps WordPress admin actions in a simple GUI. It manages credentials via Windows Credential Manager, persists user-editable defaults for file paths, and is distributed as a `.exe`.

**First milestone:** Credentials management + Members List action (including SFTP upload).

---

## 1. Tech Choices

| Decision | Choice | Why |
|----------|--------|-----|
| GUI framework | Tkinter | Built-in Python, zero extra dependencies, sufficient for internal tool |
| Credential storage | Windows Credential Manager via `keyring` | Encrypted, native Windows, no plaintext files |
| Persistent defaults | JSON config file (`config.json`) | Simple, readable, non-sensitive (file paths only) |
| Sub-project integration | Import as module (sub-project stays in place) | Each sub-project remains independently runnable |
| Distribution | PyInstaller `.exe` | No Python required on admin machines |
| v1 scope | Generate + SFTP upload | Full pipeline end-to-end |

---

## 2. Sub-Project Structure & Integration

### Principle

Each sub-project stays in its own folder (on OneDrive for backup) and remains **independently runnable**. The portal imports from it — no code duplication.

```
D:\OneDrive - ITCB\Support\UtilInstalls\
└── MemberList-Generator\           ← Sub-project stays here (OneDrive-backed)
    ├── run.py                      ← Standalone entry point (updated)
    ├── fetch_members.py            ← Refactored: callable functions
    ├── pre_process.py              ← Refactored: callable functions
    ├── MemberList Generator.py     ← Refactored: callable functions
    └── upload.py                   ← New: SFTP upload function

D:\[portal repo]\
└── portal/                         ← Portal application
    ├── main.py
    ├── gui/
    ├── actions/
    ├── credentials/
    └── config/
```

### OneDrive Location & Distribution

The sub-project lives in OneDrive on the **developer's machine**. This is fine for distribution:
- The portal imports the sub-project at development time
- PyInstaller follows those imports at **build time** and bundles the sub-project code into the `.exe`
- Distributed admins get a self-contained `.exe` — they don't need OneDrive or the sub-project files
- OneDrive continues to back up the source code as usual

### Two Modes for Each Sub-Project

**Standalone mode (`run.py`):**
- Gets credentials from Windows Credential Manager
- Prompts for file paths, showing current defaults
- User can accept defaults (Enter) or type new paths
- On new entry, saves as new default for next time
- Runs the full pipeline

**Portal mode:**
- Portal imports the same functions directly
- Passes credentials and paths programmatically (no prompts)
- Displays paths in editable GUI fields pre-filled with stored defaults
- On Run: saves any changed paths as new defaults

Both modes read/write the same defaults store (`config.json`).

---

## 3. Portal Module Structure

```
portal/
├── main.py                         ← Entry point
├── gui/
│   ├── __init__.py
│   ├── main_window.py              ← Main window (action list)
│   ├── credentials_dialog.py       ← First-run / settings
│   └── action_result_dialog.py     ← Output display
├── actions/
│   ├── __init__.py
│   ├── base_action.py              ← Abstract base class + ActionResult
│   └── members_list_action.py      ← Wraps sub-project pipeline
├── credentials/
│   ├── __init__.py
│   └── credential_manager.py       ← Keyring wrapper
├── config/
│   ├── __init__.py
│   └── defaults_manager.py         ← Read/write config.json
├── assets/
│   └── fonts/
│       ├── Alef-Regular.ttf        ← Bundled Hebrew font (fixed)
│       └── Alef-Bold.ttf
└── requirements.txt
```

---

## 4. Persistent Defaults

### Storage

Non-sensitive defaults (file paths, SFTP details) are stored in `config.json` alongside the portal. Example:

```json
{
  "members_list": {
    "raw_csv_path": "C:/Users/admin/OneDrive/MemberList-Generator/members data raw.csv",
    "output_pdf_path": "C:/Users/admin/OneDrive/MemberList-Generator/members_list_2026.pdf",
    "sftp_host": "yedidya.org.il",
    "sftp_path": "/wp-content/uploads/members/"
  }
}
```

### Behavior

- **Portal:** Fields pre-filled from `config.json` on startup. On Run, saves any changed values before executing.
- **Standalone `run.py`:** Same `config.json` — prompts show current value in brackets, e.g.:
  ```
  Raw CSV path [C:/Users/.../members data raw.csv]:
  ```
  User presses Enter to accept, or types a new path (which becomes the new default).

### DefaultsManager API

```python
class DefaultsManager:
    def get(self, action: str, key: str) -> str
    def set(self, action: str, key: str, value: str) -> None
    def get_all(self, action: str) -> dict
```

---

## 5. Credential Flow

### Windows Credential Manager

Three credentials stored (all via `keyring`):
- WordPress admin URL
- WordPress admin username
- WordPress admin password (application password)
- SFTP username
- SFTP password

### First Run
1. `credential_manager.has_credentials()` → False
2. Show Credentials Dialog
3. User enters WP URL, username, app password + SFTP host, username, password
4. Saved to Windows Credential Manager
5. Main window appears

### Subsequent Runs
1. `has_credentials()` → True
2. Credentials retrieved silently
3. Main window appears immediately

### Settings
- "Settings" button → update or clear any credential set

---

## 6. Members List Action: Full Pipeline

### Steps

1. **Fetch** members from WordPress REST API → `raw.csv`
2. **Pre-process** CSV (filter, normalize, sort) → `processed.csv`
3. **Generate PDF** (Hebrew RTL, A4) → `members_list.pdf`
4. **Upload** PDF via SFTP to WordPress server

### Portal UI for This Action

```
┌─────────────────────────────────────────────────┐
│ Members List                                     │
├─────────────────────────────────────────────────┤
│ Raw CSV output path:                            │
│ [C:/Users/.../members data raw.csv          ]   │
│                                                  │
│ PDF output path:                                │
│ [C:/Users/.../members_list_2026.pdf         ]   │
│                                                  │
│ SFTP upload path:                               │
│ [/wp-content/uploads/members/               ]   │
│                                                  │
│                              [Run]               │
└─────────────────────────────────────────────────┘
```

Any edited field is saved as the new default before the action runs.

**Fonts:** Alef-Regular.ttf and Alef-Bold.ttf — fixed, bundled with the app, not user-configurable.

### Refactoring Required

Each pipeline function becomes callable with explicit parameters:

| File | Refactor |
|------|----------|
| `fetch_members.py` | `fetch_members(wp_url, wp_user, wp_password, output_path)` → returns member count. Remove `getpass`/dotenv. |
| `pre_process.py` | `pre_process(input_path, output_path)` → returns row count. Remove hardcoded paths. |
| `MemberList Generator.py` | `generate_pdf(input_path, output_path, fonts_dir)` → None. Remove hardcoded paths. |
| `upload.py` *(new)* | `upload_sftp(local_path, sftp_host, sftp_user, sftp_password, remote_path)` → None. |
| `run.py` | Updated: gets credentials from WCM, uses DefaultsManager for paths, prompts with defaults. |

Hardcoded values in original scripts become the **seed defaults** in `config.json` — not removed, just moved.

---

## 7. Main Window Layout

```
┌─────────────────────────────────────────┐
│ Yedidya Admin Portal                ⚙️  │
├─────────────────────────────────────────┤
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Members List                    [Go] │ │
│ │ Generate and upload member list     │ │
│ └─────────────────────────────────────┘ │
│                                         │
├─────────────────────────────────────────┤
│ Status: Ready                           │
└─────────────────────────────────────────┘
```

Clicking [Go] expands or opens the action panel with its editable fields.

---

## 8. Error Messages

| Situation | Message |
|-----------|---------|
| 401 Unauthorized | "Could not connect to WordPress. Check your username and app password in Settings." |
| 403 Forbidden | "Your WordPress account doesn't have admin access." |
| Timeout | "Connection timed out. Check your internet connection and try again." |
| SFTP failure | "Could not upload to the server. Check your SFTP credentials in Settings." |
| No credentials | "Please enter your credentials in Settings." |
| File not found | "Could not find [path]. Check the path in the fields above." |

---

## 9. Distribution

### Build
```bash
pyinstaller --onefile --noconsole --name YedidyaPortal portal/main.py
```
Sub-project code is bundled in via PyInstaller's path hooks.

### Share
- Zip: `YedidyaPortal.exe` + `config.json` (pre-seeded with default paths) + `README.txt`
- Each admin extracts, runs, enters credentials once on first run

---

## 10. Dependencies

```
keyring>=24.0.0
pywin32>=300
pandas>=1.3.0
reportlab>=3.6.0
arabic-reshaper>=0.3.0
python-bidi>=0.4.2
requests>=2.25.0
paramiko>=2.8.0        # SFTP upload
```

---

## 11. Out of Scope (v1)

- Delete Users action
- Upload Document action
- Scheduled / event-driven runs
