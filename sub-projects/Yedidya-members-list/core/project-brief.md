# Project Brief

## What This Is

Automation pipeline for generating and publishing a member list for the Yedidya community. The system pulls member data from WordPress, processes it through two existing Python scripts (CSV transformation + PDF generation), and uploads the resulting PDF back to WordPress — all triggered by a single command.

## Goals

- **Primary:** A working manual trigger that runs the full pipeline end-to-end
- **Secondary (stretch):** Event-driven trigger — auto-run when a new member registers in WordPress

## Audience

The user. This is an internal tool, not a product.

## Code Location

`D:\OneDrive - ITCB\Support\UtilInstalls\MemberList-Generator`

## Where Things Stand

### Existing scripts

**`pre_process.py`**
- Input: `members data raw.csv` (hardcoded path)
- Filters by privacy flags (`contact_list_privacy_setting == Yes`, `privacy_approval == approve`)
- Normalizes data, swaps male/female order (wife listed first), adds Hebrew cross-reference rows for different last names, sorts alphabetically, adds Hebrew letter section markers
- Output: `pre-processing output.csv` (hardcoded path)

**`MemberList Generator.py`**
- Input: `pre-processing output.csv` (hardcoded path)
- Generates an A4 PDF with Hebrew RTL text using reportlab + arabic_reshaper + python-bidi
- Custom fonts: Alef-Regular.ttf, Alef-Bold.ttf (must be in same directory)
- Output: `members_list_2026.pdf` (hardcoded path)

Both scripts currently use hardcoded relative paths and must be run from the project directory.

### WordPress data structure
The raw CSV has these columns: `user_login, user_email, first_name, last_name, partnerfirst, partnerlast, partneremail, cellphone1, partnerphone, homephone, home_address, yourgender, partnergender, contact_list_privacy_setting, privacy_approval` — all stored as WordPress user meta fields.

### What's missing
- Pulling member data from WordPress via the REST API (or WP-CLI) → saves as `members data raw.csv`
- An orchestration script that calls both scripts in sequence
- Uploading the final PDF to the correct location in WordPress
- (Future) A trigger that fires when a new member registers

## Done Looks Like

The full pipeline runs with a single command. Input: nothing (it pulls its own data). Output: a PDF published to WordPress.

## Constraints

- Runs on Windows
- CLI is fine — no UI needed
- No over-engineering: the simplest thing that works
- Every non-trivial decision gets explained before implementation

## Out of Scope (for now)

- Visual design
- Automatic event-driven triggering (manual first)
- Any user-facing UI
