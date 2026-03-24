"""
Portal settings: paths resolved for both development and PyInstaller .exe.
"""
import os
import sys

# Sub-project location.
# Development: actual OneDrive path (override with env var if needed).
# PyInstaller bundle: code is extracted to _MEIPASS/members_list/.
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
    SUB_PROJECT_MEMBERS_LIST = os.path.join(_BASE, 'members_list')
    FONTS_DIR = os.path.join(_BASE, 'assets', 'fonts')
else:
    SUB_PROJECT_MEMBERS_LIST = os.environ.get(
        'YEDIDYA_MEMBERS_LIST_DIR',
        r"D:\OneDrive - ITCB\Support\UtilInstalls\MemberList-Generator"
    )
    FONTS_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'assets', 'fonts'
    )

KEYRING_SERVICE = 'YedidyaPortal'

# Seed values shown in the credentials dialog on first run.
# Passwords and WP username are intentionally blank — each admin enters their own.
CREDENTIAL_SEEDS = {
    'staging': {
        'wp_url':        'https://staging-9e0a-kehilatyedidya.wpcomstaging.com/',
        'wp_user':       '',
        'wp_password':   '',
        'sftp_host':     'sftp.wp.com',
        'sftp_user':     'staging-9e0a-kehilatyedidya.wordpress.com',
        'sftp_password': '',
    },
    'production': {
        'wp_url':        'https://yedidya.org.il',
        'wp_user':       '',
        'wp_password':   '',
        'sftp_host':     'sftp.wp.com',
        'sftp_user':     'kehilatyedidya.wordpress.com',
        'sftp_password': '',
    },
}
