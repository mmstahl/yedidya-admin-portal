# Technical Spec — Member List Pipeline

## Overview

Five files to create. Two are already written (`pre_process.py`, `MemberList Generator.py`) — they stay untouched. Three are new.

```
run.py                        ← single entry point (new)
fetch_members.py              ← pulls data from WordPress (new)
yedidya-member-export.php     ← WordPress plugin (new)
.env                          ← credentials, not committed (new, from .env.example)
.env.example                  ← template (new)
requirements.txt              ← Python dependencies (new)
```

---

## File: `yedidya-member-export.php`

A minimal WordPress plugin. Registers one REST endpoint that returns all members with their meta fields.

**Endpoint:** `GET /wp-json/yedidya/v1/members`
**Auth:** WordPress Application Password (HTTP Basic Auth). Requires `edit_users` capability (admin only).
**Response:** JSON array of user objects.

Each object contains:
```json
{
  "user_login": "...",
  "user_email": "...",
  "first_name": "...",
  "last_name": "...",
  "partnerfirst": "...",
  "partnerlast": "...",
  "partneremail": "...",
  "cellphone1": "...",
  "partnerphone": "...",
  "homephone": "...",
  "home_address": "...",
  "yourgender": "...",
  "partnergender": "...",
  "contact_list_privacy_setting": "...",
  "privacy_approval": "..."
}
```

Missing meta values return `""` (empty string, not null).

**Installation:** Upload to `/wp-content/plugins/yedidya-member-export/` and activate in WP admin.

---

## File: `fetch_members.py`

Calls the WordPress endpoint and saves the result as `members data raw.csv`.

**Steps:**
1. Load `.env` → read `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`
2. GET `{WP_URL}/wp-json/yedidya/v1/members` with Basic Auth
3. Handle pagination: WP REST API returns max 100 per page. Script loops through all pages until empty.
4. Write result to `members data raw.csv` with columns in exact order matching `pre_process.py`

**Output on success:** `✓ Fetched {n} members from WordPress`
**Output on failure:** `Error: Could not fetch members ({status code} — {message})`

---

## File: `run.py`

Single entry point. Runs the four steps in sequence. Stops on any failure.

```
Step 1: Fetch members from WordPress   → calls fetch_members.py logic
Step 2: Pre-process CSV                → runs pre_process.py via subprocess
Step 3: Generate PDF                   → runs "MemberList Generator.py" via subprocess
Step 4: Upload PDF via SFTP            → uploads members_list.pdf to server
```

**CLI output pattern:**
```
[1/4] Fetching members from WordPress...
✓ Fetched 187 members
[2/4] Pre-processing CSV...
✓ Processed 203 entries
[3/4] Generating PDF...
✓ PDF generated: members_list.pdf
[4/4] Uploading to server...
✓ Uploaded to /srv/htdocs/wp-content/uploads/members_list.pdf

Done.
```

**On failure (example):**
```
[1/4] Fetching members from WordPress...
Error: 401 Unauthorized — check WP_USER and WP_APP_PASSWORD in .env
```
Then exits with code 1.

**SFTP:** Uses `paramiko`. Connects to `SFTP_HOST` with `SFTP_USER` / `SFTP_PASSWORD`. Uploads `members_list.pdf` to `SFTP_REMOTE_PATH`, overwriting the existing file.

---

## File: `.env.example`

```
WP_URL=https://your-site.com
WP_USER=your-admin-username
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

SFTP_HOST=your-server-hostname
SFTP_USER=your-sftp-username
SFTP_PASSWORD=your-sftp-password
SFTP_REMOTE_PATH=/srv/htdocs/wp-content/uploads/members_list.pdf
```

Note: Application Passwords are generated in WP Admin → Users → Profile → Application Passwords. Copy the value exactly including spaces.

---

## File: `requirements.txt`

```
pandas
numpy
reportlab
arabic-reshaper
python-bidi
requests
paramiko
python-dotenv
```

---

## Setup sequence (for the user)

1. Copy `.env.example` → `.env`, fill in all values
2. Install Python deps: `pip install -r requirements.txt`
3. Upload `yedidya-member-export.php` to `/wp-content/plugins/yedidya-member-export/` via SFTP
4. Activate plugin in WP Admin → Plugins
5. Generate Application Password: WP Admin → Users → Your Profile → scroll to "Application Passwords" → name it "Member List Script" → copy the generated password → paste into `.env`
6. Run: `python run.py`

---

## What stays unchanged

- `pre_process.py` — not modified
- `MemberList Generator.py` — updated by user to output `members_list.pdf` directly (no rename step needed)
- All font files and existing assets — not touched
