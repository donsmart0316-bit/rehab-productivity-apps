from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "physio-tele-rehab" / "frontend"

if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

os.chdir(FRONTEND_ROOT)
runpy.run_path(str(FRONTEND_ROOT / "app.py"), run_name="__main__")
