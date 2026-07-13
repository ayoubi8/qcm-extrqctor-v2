"""Deployment launcher for the FastAPI backend."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHONPATHS = [
    ROOT / "packages" / "domain" / "src",
    ROOT / "packages" / "shared" / "src",
    ROOT / "packages" / "application" / "src",
    ROOT / "packages" / "infrastructure" / "src",
    ROOT / "packages" / "observability" / "src",
    ROOT / "apps" / "api" / "src",
]

for path in reversed(PYTHONPATHS):
    sys.path.insert(0, str(path))

os.environ.setdefault("QCM_DEPLOY_TARGET", "vercel-api")

from qcm_api.main import app  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
