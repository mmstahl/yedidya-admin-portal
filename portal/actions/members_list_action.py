"""
Members List action: fetch → pre-process → generate PDF → SFTP upload.
Imports pipeline functions from the sub-project in-place (no copying).

Two-phase API:
  run_generate() — steps 1-3 (fetch, pre-process, generate PDF)
  run_upload()   — step 4 (SFTP upload)
  run()          — convenience wrapper: calls both (used for staging + standalone)
"""
import os
import sys
import importlib.util

from portal.actions.base_action import BaseAction, ActionResult
from portal.config.settings import SUB_PROJECT_MEMBERS_LIST, FONTS_DIR
from portal.credentials.credential_manager import get as get_cred
import defaults_manager as dm


def _load_generator():
    """Load MemberList Generator.py (has a space in name) via importlib."""
    path = os.path.join(SUB_PROJECT_MEMBERS_LIST, "MemberList Generator.py")
    spec = importlib.util.spec_from_file_location("memberlist_generator", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ensure_importable():
    if SUB_PROJECT_MEMBERS_LIST not in sys.path:
        sys.path.insert(0, SUB_PROJECT_MEMBERS_LIST)


class MembersListAction(BaseAction):
    name = "Members List"
    description = "Generate and upload member list"

    # ------------------------------------------------------------------
    # Phase 1 — Generate PDF (steps 1-3)
    # ------------------------------------------------------------------

    def run_generate(self, raw_csv_path, processed_csv_path, pdf_path,
                     progress_callback=None, env='staging') -> ActionResult:
        """
        Fetch members, pre-process CSV, generate PDF.
        Returns ActionResult; on success result.data = pdf_path.
        """
        _ensure_importable()
        from fetch_members import fetch_members
        from pre_process import pre_process

        wp_url      = get_cred('wp_url',      env)
        wp_user     = get_cred('wp_user',     env)
        wp_password = get_cred('wp_password', env)

        log   = []
        total = 3  # generate phase has 3 steps

        def _step(n, msg):
            log.append(msg)
            if progress_callback:
                progress_callback(n, total, msg)

        # Step 1 — Fetch
        _step(1, "Fetching members from WordPress...")
        try:
            count = fetch_members(wp_url, wp_user, wp_password, raw_csv_path)
            log.append(f"  ✓ Fetched {count} members")
        except Exception as e:
            return ActionResult(False, str(e), log)

        # Step 2 — Pre-process
        _step(2, "Pre-processing CSV...")
        try:
            count = pre_process(raw_csv_path, processed_csv_path)
            log.append(f"  ✓ Processed {count} entries")
        except Exception as e:
            return ActionResult(False, str(e), log)

        # Step 3 — Generate PDF
        _step(3, "Generating PDF...")
        try:
            generator = _load_generator()
            generator.generate_pdf(processed_csv_path, pdf_path, fonts_dir=FONTS_DIR)
            log.append(f"  ✓ PDF saved: {pdf_path}")
        except Exception as e:
            return ActionResult(False, str(e), log)

        return ActionResult(True, "PDF generated successfully.", log, data=pdf_path)

    # ------------------------------------------------------------------
    # Phase 2 — Upload (step 4)
    # ------------------------------------------------------------------

    def run_upload(self, pdf_path, sftp_remote_path,
                   progress_callback=None, env='staging') -> ActionResult:
        """Upload the generated PDF via SFTP."""
        _ensure_importable()
        from upload import upload_sftp

        sftp_host     = get_cred('sftp_host',     env)
        sftp_user     = get_cred('sftp_user',     env)
        sftp_password = get_cred('sftp_password', env)

        log = []

        def _step(n, msg):
            log.append(msg)
            if progress_callback:
                progress_callback(n, 1, msg)

        _step(1, "Uploading to server...")
        try:
            upload_sftp(pdf_path, sftp_host, sftp_user, sftp_password, sftp_remote_path)
            log.append(f"  ✓ Uploaded to {sftp_remote_path}")
        except Exception as e:
            return ActionResult(False, str(e), log)

        return ActionResult(True, "Uploaded successfully.", log)

    # ------------------------------------------------------------------
    # Convenience wrapper — full pipeline (staging + standalone)
    # ------------------------------------------------------------------

    def run(self, raw_csv_path, processed_csv_path, pdf_path, sftp_remote_path,
            progress_callback=None, env='staging') -> ActionResult:
        """Run the full pipeline in one call (used for staging and run.py)."""

        def _gen_progress(step, total, msg):
            if progress_callback:
                progress_callback(step, total + 1, msg)   # total+1 to leave room for upload step

        def _upl_progress(step, total, msg):
            if progress_callback:
                progress_callback(4, 4, msg)

        result = self.run_generate(raw_csv_path, processed_csv_path, pdf_path,
                                   progress_callback=_gen_progress, env=env)
        if not result.success:
            return result

        return self.run_upload(pdf_path, sftp_remote_path,
                               progress_callback=_upl_progress, env=env)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def save_defaults(self, raw_csv_path, processed_csv_path, pdf_path,
                      sftp_remote_path, env='staging'):
        """Persist any changed paths as new defaults (SFTP path is per-env)."""
        dm.set_default('members_list', 'raw_csv_path',            raw_csv_path)
        dm.set_default('members_list', 'processed_csv_path',      processed_csv_path)
        dm.set_default('members_list', 'pdf_path',                pdf_path)
        dm.set_default('members_list', f'{env}_sftp_remote_path', sftp_remote_path)

    def get_defaults(self, env='staging'):
        base = dm.get_all('members_list')
        base['sftp_remote_path'] = dm.get('members_list', f'{env}_sftp_remote_path')
        return base
