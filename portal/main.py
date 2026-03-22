"""
Yedidya Admin Portal — entry point.
"""
import sys
import os

# Ensure the repo root is on sys.path so `portal` is importable
# whether this file is run as `python portal/main.py` or `python -m portal.main`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# When running from source, ensure the sub-project is importable for defaults_manager.
# (For the bundled .exe, PyInstaller handles this via the .spec datas.)
from portal.config.settings import SUB_PROJECT_MEMBERS_LIST
if SUB_PROJECT_MEMBERS_LIST not in sys.path:
    sys.path.insert(0, SUB_PROJECT_MEMBERS_LIST)

from portal.gui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
