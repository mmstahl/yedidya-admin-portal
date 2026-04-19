"""
DB Extract action.

Calls the /wp-json/yedidya/v1/db-extract endpoint with a caller-specified
list of fields (wp_users columns and/or usermeta keys), then writes the
result to a CSV file.
"""
import csv
import requests

from portal.actions.base_action import BaseAction, ActionResult
from portal.credentials.credential_manager import get as get_cred

DB_EXTRACT_ENDPOINT = '/wp-json/yedidya/v1/db-extract'


class DbExtractAction(BaseAction):
    name = "DB Extract"
    description = "Extract WordPress user fields to a CSV file"

    # These two are always extracted as the first two columns regardless of
    # what the caller specifies.
    FIXED_FIELDS = ['user_login', 'user_email']

    def run(self, fields: list[str], csv_path: str, env: str = 'staging',
            gender: str | None = None, privacy: str | None = None) -> ActionResult:
        """
        Fetch the requested fields for every user and write to csv_path.

        user_login and user_email are always prepended as the first two
        columns; they do not need to be included in `fields`.

        fields   — additional field names (wp_users columns and/or usermeta keys)
        csv_path — absolute path for the output CSV
        env      — 'staging' or 'production'
        gender   — 'male', 'female', or None (no filter)
        privacy  — 'Yes', 'No', or None (no filter on contact_list_privacy_setting)
        """
        # Build full field list: record_type first, then fixed, then caller fields.
        extra = [f for f in fields if f not in self.FIXED_FIELDS]
        all_fields = ['record_type'] + self.FIXED_FIELDS + extra

        wp_url  = get_cred('wp_url',      env)
        wp_user = get_cred('wp_user',     env)
        wp_pass = get_cred('wp_password', env)

        try:
            url    = f"{wp_url.rstrip('/')}{DB_EXTRACT_ENDPOINT}"
            params = {'fields': ','.join(f for f in all_fields if f != 'record_type')}
            if gender:
                params['gender'] = gender
            if privacy:
                params['privacy'] = privacy
            resp = requests.get(
                url,
                params=params,
                auth=(wp_user, wp_pass),
                timeout=60,
            )
            if resp.status_code == 401:
                return ActionResult(False, "401 Unauthorized — check credentials.")
            if resp.status_code == 403:
                return ActionResult(False, "403 Forbidden — account lacks admin access.")
            resp.raise_for_status()
            rows = resp.json()
        except Exception as e:
            return ActionResult(False, str(e))

        if not rows:
            return ActionResult(False, "The endpoint returned no data.")

        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='raise')
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            return ActionResult(False, f"Failed to write CSV: {e}")

        return ActionResult(True, f"Extracted {len(rows)} rows.", data=csv_path)
