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

## 2026-03-22 — GDPR plugin: standalone, no WooCommerce core modifications

**Decision:** GDPR erasure is implemented as a standalone plugin (`yedidya-gdpr-erase`) that calls WooCommerce classes. WooCommerce files are never modified.

**Why:** WooCommerce updates would overwrite any changes to core files. A standalone plugin survives updates safely.
