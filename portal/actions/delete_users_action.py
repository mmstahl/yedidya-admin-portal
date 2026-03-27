"""
Delete Users action.

Reads a CSV of email addresses, looks up each user in WordPress,
and deletes them. Two modes:
  - Standard: deletes WP user + all their content (posts, etc.)
  - GDPR erase: same + WooCommerce customer data (via custom plugin endpoint)

Deletion always uses "delete all content" (not reassign).
"""
import csv
import requests

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

WP_USERS_ENDPOINT   = '/wp-json/wp/v2/users'
GDPR_ERASE_ENDPOINT = '/wp-json/yedidya/v1/gdpr-erase'


def _auth():
    return (get_cred('wp_url'), get_cred('wp_user'), get_cred('wp_password'))


class DeleteUsersAction(BaseAction):
    name = "Delete Users"
    description = "Delete WordPress users from a CSV list of emails"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preview(self, csv_path, env='staging'):
        """
        Look up each email in the CSV against WordPress.
        Returns (found, not_found, error) where:
          found      = list of {email, id, display_name}
          not_found  = list of emails
          error      = error message string or None
        """
        emails, error = self._read_csv(csv_path)
        if error:
            return [], [], error

        wp_url    = get_cred('wp_url',      env)
        wp_user   = get_cred('wp_user',     env)
        wp_pass   = get_cred('wp_password', env)

        found, not_found, warnings = [], [], []
        for email in emails:
            try:
                result = self._lookup_user(wp_url, wp_user, wp_pass, email)
            except ConnectionError as e:
                # 401/403 — the whole API is broken, stop immediately
                return [], [], str(e)

            if result is None:
                not_found.append(email)
            elif isinstance(result, Exception):
                # Per-user lookup error — log as warning and continue
                warnings.append(f"{email}: {result}")
            else:
                found.append(result)

        # Surface warnings as a combined message (not a hard error)
        warning_msg = None
        if warnings:
            warning_msg = "Warnings:\n" + "\n".join(f"  • {w}" for w in warnings)

        return found, not_found, warning_msg

    def run(self, users_to_delete, gdpr_mode=False,
            progress_callback=None, env='staging') -> ActionResult:
        """
        Delete the given users.
        users_to_delete: list of {email, id, display_name} (from preview())
        gdpr_mode: if True, also erase WooCommerce data via custom endpoint
        progress_callback(current, total, message)
        """
        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        log    = []
        total  = len(users_to_delete)
        errors = 0

        for i, user in enumerate(users_to_delete, 1):
            msg = f"Deleting {user['display_name']} ({user['email']})…"
            log.append(msg)
            if progress_callback:
                progress_callback(i, total, msg)

            if gdpr_mode:
                result_msg, is_error = self._gdpr_erase(wp_url, wp_user, wp_pass, user)
            else:
                result_msg, is_error = self._standard_delete(wp_url, wp_user, wp_pass, user)

            log.append(f"  {'✗ ERROR' if is_error else '✓'} {result_msg}")
            if is_error:
                errors += 1

        if errors == 0:
            return ActionResult(True, f"Deleted {total} user(s).", log)
        elif errors < total:
            return ActionResult(
                False,
                f"Completed with {errors} error(s). {total - errors}/{total} deleted.",
                log
            )
        else:
            return ActionResult(False, "All deletions failed.", log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_csv(self, csv_path):
        """Return (list of emails, error_string_or_None).

        Handles both:
          - CSV with header row  (email, Email, EMAIL, or first column)
          - CSV with no header   (detected when first cell contains '@')
        """
        try:
            with open(csv_path, newline='', encoding='utf-8-sig') as f:
                rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]

            if not rows:
                return [], "CSV contains no email addresses."

            first_cell = rows[0][0].strip() if rows[0] else ''

            if '@' in first_cell:
                # No header — every row is data; email is in the first column
                col_idx   = 0
                data_rows = rows
            else:
                # First row is a header — find the email column
                header    = [c.strip().lower() for c in rows[0]]
                col_idx   = header.index('email') if 'email' in header else 0
                data_rows = rows[1:]

            emails = [
                row[col_idx].strip().lower()
                for row in data_rows
                if len(row) > col_idx and row[col_idx].strip()
            ]

            if not emails:
                return [], "CSV contains no email addresses."
            return emails, None
        except FileNotFoundError:
            return [], f"File not found: {csv_path}"
        except Exception as e:
            return [], str(e)

    def _lookup_user(self, wp_url, wp_user, wp_pass, email):
        """
        Return {email, id, display_name} if found, None if not found,
        or an Exception on error.
        """
        try:
            url = f"{wp_url.rstrip('/')}{WP_USERS_ENDPOINT}"
            resp = requests.get(
                url,
                params={'search': email, 'context': 'edit'},
                auth=(wp_user, wp_pass),
                timeout=15
            )
            if resp.status_code == 401:
                raise ConnectionError("401 Unauthorized — check credentials")
            if resp.status_code == 403:
                raise ConnectionError("403 Forbidden — account lacks admin access")
            resp.raise_for_status()
            users = resp.json()
            # Search can return partial matches; find exact email
            match = next((u for u in users if u.get('email', '').lower() == email), None)
            if not match:
                return None
            return {
                'email':        email,
                'id':           match['id'],
                'display_name': match.get('name', email),
            }
        except ConnectionError:
            raise
        except Exception as e:
            return e

    def _standard_delete(self, wp_url, wp_user, wp_pass, user):
        """Delete WP user + all their content. Returns (message, is_error)."""
        try:
            url = f"{wp_url.rstrip('/')}{WP_USERS_ENDPOINT}/{user['id']}"
            resp = requests.delete(
                url,
                params={'force': 'true', 'reassign': 'false'},
                auth=(wp_user, wp_pass),
                timeout=15
            )
            if resp.status_code == 401:
                raise ConnectionError("401 Unauthorized — check credentials")
            if not resp.ok:
                return f"HTTP {resp.status_code}: {resp.text[:120]}", True
            return "Deleted", False
        except ConnectionError as e:
            return str(e), True
        except Exception as e:
            return str(e), True

    def _gdpr_erase(self, wp_url, wp_user, wp_pass, user):
        """
        Full GDPR erasure via custom plugin endpoint.
        Erases WooCommerce data + deletes WP user + content.
        Returns (message, is_error).
        """
        try:
            url = f"{wp_url.rstrip('/')}{GDPR_ERASE_ENDPOINT}"
            resp = requests.post(
                url,
                json={'email': user['email']},
                auth=(wp_user, wp_pass),
                timeout=30
            )
            if resp.status_code == 401:
                raise ConnectionError("401 Unauthorized — check credentials")
            if not resp.ok:
                return f"HTTP {resp.status_code}: {resp.text[:120]}", True
            data = resp.json()
            warnings = data.get('warnings', [])
            msg = "GDPR erased"
            if warnings:
                msg += " (warnings: " + "; ".join(warnings) + ")"
            return msg, False
        except ConnectionError as e:
            return str(e), True
        except Exception as e:
            return str(e), True
