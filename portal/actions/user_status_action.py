"""
Approve / Deny Users action.

Reads a CSV with two columns — "email" and "setting" (Approve / Deny) —
and sets each user's New User Approve status in WordPress.

Uses the custom plugin endpoints (yedidya-admin-portal/user-status.php).
Status is changed silently: New User Approve's emails are NOT sent.
Users already in the requested state are skipped.
"""
import csv
import requests

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

LOOKUP_ENDPOINT = '/wp-json/yedidya/v1/user-status/lookup'
SET_ENDPOINT    = '/wp-json/yedidya/v1/user-status'
LOOKUP_CHUNK    = 100

SETTING_VALUES = {
    'approve':  'approved',
    'approved': 'approved',
    'deny':     'denied',
    'denied':   'denied',
}

STATUS_LABELS = {
    'approved': 'Approved',
    'denied':   'Denied',
    'pending':  'Pending',
}

PLUGIN_OUTDATED_MSG = (
    "This WordPress site does not have the approve/deny feature yet. "
    "Upload the latest Yedidya Admin Portal plugin (with user-status.php) and try again."
)


def status_label(status):
    return STATUS_LABELS.get(status, status or '—')


class UserStatusAction(BaseAction):
    name = "Approve / Deny Users"
    description = "Set users to Approved or Denied from a CSV (email, setting)"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preview(self, csv_path, env='staging'):
        """
        Read the CSV and look up each user's current status.
        Returns (users, not_found, invalid, error) where:
          users     = list of {email, id, name, current, target, action}
                      action is 'change', 'skip' (already in that state)
                      or 'blocked' (administrators cannot be denied)
          not_found = list of emails with no WordPress account
          invalid   = list of "row N: reason" strings
          error     = error message string or None (hard stop)
        """
        targets, invalid, error = self._read_csv(csv_path)
        if error:
            return [], [], invalid, error

        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        emails = list(targets)
        users, not_found = [], []
        try:
            for i in range(0, len(emails), LOOKUP_CHUNK):
                found, missing = self._lookup(wp_url, wp_user, wp_pass,
                                              emails[i:i + LOOKUP_CHUNK])
                users.extend(found)
                not_found.extend(missing)
        except ConnectionError as e:
            return [], [], invalid, str(e)

        result = []
        for u in users:
            target = targets.get(u['email'].lower())
            if target is None:
                continue
            if u['status'] == target:
                action = 'skip'
            elif target == 'denied' and 'administrator' in u.get('roles', []):
                action = 'blocked'
            else:
                action = 'change'
            result.append({
                'email':   u['email'],
                'id':      u['id'],
                'name':    u.get('name') or u['email'],
                'current': u['status'],
                'target':  target,
                'action':  action,
            })

        return result, not_found, invalid, None

    def run(self, users, progress_callback=None, env='staging') -> ActionResult:
        """
        Set the status of each user whose action is 'change'.
        users: list from preview()
        progress_callback(current, total, message)
        """
        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        to_change = [u for u in users if u['action'] == 'change']
        log    = []
        total  = len(to_change)
        errors = 0

        for i, user in enumerate(to_change, 1):
            msg = (f"{user['name']} ({user['email']}): "
                   f"{status_label(user['current'])} → {status_label(user['target'])}")
            log.append(msg)
            if progress_callback:
                progress_callback(i, total, msg)

            result_msg, is_error = self._set_status(wp_url, wp_user, wp_pass,
                                                    user['email'], user['target'])
            log.append(f"  {'✗ ERROR' if is_error else '✓'} {result_msg}")
            if is_error:
                errors += 1

        if errors == 0:
            return ActionResult(True, f"Updated {total} user(s).", log)
        elif errors < total:
            return ActionResult(
                False,
                f"Completed with {errors} error(s). {total - errors}/{total} updated.",
                log
            )
        else:
            return ActionResult(False, "All updates failed.", log)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_csv(self, csv_path):
        """
        Return (targets, invalid, error) where:
          targets = {email_lower: 'approved' | 'denied'}
          invalid = list of "row N: reason" strings (rows skipped)
          error   = hard-stop message or None
        """
        try:
            with open(csv_path, newline='', encoding='utf-8-sig') as f:
                rows = list(csv.reader(f))
        except FileNotFoundError:
            return {}, [], f"File not found: {csv_path}"
        except Exception as e:
            return {}, [], str(e)

        rows = [(n, r) for n, r in enumerate(rows, 1) if any(c.strip() for c in r)]
        if not rows:
            return {}, [], "The CSV file is empty."

        header = [c.strip().lower() for c in rows[0][1]]
        if 'email' not in header or 'setting' not in header:
            return {}, [], "The CSV must have a header row with 'email' and 'setting' columns."
        email_idx   = header.index('email')
        setting_idx = header.index('setting')

        targets, invalid = {}, []
        for n, row in rows[1:]:
            email   = row[email_idx].strip().lower()   if len(row) > email_idx   else ''
            setting = row[setting_idx].strip().lower() if len(row) > setting_idx else ''

            if '@' not in email:
                invalid.append(f"row {n}: missing or invalid email '{email}'")
                continue
            target = SETTING_VALUES.get(setting)
            if target is None:
                invalid.append(f"row {n}: setting '{setting}' for {email} "
                               "is not Approve or Deny")
                continue
            if email in targets and targets[email] != target:
                invalid.append(f"row {n}: {email} appears more than once with "
                               "different settings — skipped")
                targets[email] = None
                continue
            if email not in targets:
                targets[email] = target

        targets = {e: t for e, t in targets.items() if t is not None}
        if not targets:
            return {}, invalid, "The CSV has no valid rows. See the log for details."
        return targets, invalid, None

    def _lookup(self, wp_url, wp_user, wp_pass, emails):
        """Return (users, not_found) for a batch of emails. Raises ConnectionError."""
        try:
            resp = requests.post(
                f"{wp_url.rstrip('/')}{LOOKUP_ENDPOINT}",
                json={'emails': emails},
                auth=(wp_user, wp_pass),
                timeout=60
            )
        except requests.RequestException as e:
            raise ConnectionError(f"Could not connect to WordPress: {e}")
        self._check_status(resp)
        data = resp.json()
        return data.get('users', []), data.get('not_found', [])

    def _set_status(self, wp_url, wp_user, wp_pass, email, status):
        """Returns (message, is_error)."""
        try:
            resp = requests.post(
                f"{wp_url.rstrip('/')}{SET_ENDPOINT}",
                json={'email': email, 'status': status},
                auth=(wp_user, wp_pass),
                timeout=15
            )
            self._check_status(resp)
            return f"Set to {status_label(status)}", False
        except ConnectionError as e:
            return str(e), True
        except Exception as e:
            return str(e), True

    @staticmethod
    def _check_status(resp):
        if resp.status_code == 401:
            raise ConnectionError("401 Unauthorized — check credentials")
        if resp.status_code == 403:
            raise ConnectionError("403 Forbidden — account lacks admin access")
        if resp.status_code == 404 and 'rest_no_route' in resp.text:
            raise ConnectionError(PLUGIN_OUTDATED_MSG)
        if not resp.ok:
            try:
                msg = resp.json().get('message') or resp.text[:120]
            except ValueError:
                msg = resp.text[:120]
            raise ConnectionError(f"HTTP {resp.status_code}: {msg}")
