from __future__ import annotations

import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2] / "Productivity & Recovery"
APP_ROOT = PROJECT_ROOT / "app"

for path in (PROJECT_ROOT, APP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

runpy.run_path(str(APP_ROOT / "pages" / "Product_Maturity.py"), run_name="__main__")
