import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn

uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
