"""Pytest bootstrap: make `backend/` importable and use an isolated SQLite test DB.

`DATABASE_URL` is set here (before any module imports `config.settings`) so tests never touch
a real database.
"""

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

_TEST_DB = (ROOT / ".pytest_opd.db").as_posix()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB}")
