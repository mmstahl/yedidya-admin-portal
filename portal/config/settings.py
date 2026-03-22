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
