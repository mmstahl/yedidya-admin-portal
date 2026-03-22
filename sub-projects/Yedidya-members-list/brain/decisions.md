# Decisions

Standing decisions and choices. Updated by the Chief of Staff after noteworthy decisions.

---

## 2026-03-12 — Working language

All communication in English. (User preference, stated at session start.)

## 2026-03-12 — WordPress environment

- Platform: WordPress.com Business plan (staging: staging-9e0a-kehilatyedidya.wpcomstaging.com)
- WordPress version: 6.9.4
- User has SFTP credentials and admin access
- Application Passwords supported (WP 5.6+)

## 2026-03-12 — WordPress data integration approach

- Custom REST endpoint via a small plugin (not functions.php — user preference)
- Authenticated with Application Passwords
- PDF upload via SFTP using paramiko

## 2026-03-13 — Password handling

- Passwords entered interactively via `getpass` (hidden input) — not stored anywhere
- Non-sensitive config (URLs, usernames, paths) stays in `.env.staging` / `.env.production`

## 2026-03-13 — Multi-environment support

- Two env files: `.env.staging`, `.env.production`
- `run.py` takes `--site` flag (`staging` or `production`), default is `staging`
- Usage: `python run.py` (staging) or `python run.py --site production`

## 2026-03-12 — PDF filename

- Final filename: `members_list.pdf` (year-agnostic, overwrites same file each run)
- `MemberList Generator.py` updated by user to output `members_list.pdf` directly — no rename step needed in `run.py`
