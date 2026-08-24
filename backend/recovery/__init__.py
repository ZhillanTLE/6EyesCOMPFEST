"""
Windfall abandoned-cart recovery pipeline.

Loading backend/.env here is deliberate. `backend/app.py` already calls
load_dotenv, but the tools do not import the Flask app: running
`python -m backend.tools.gemini_probe` after putting a key in backend/.env
reported "no GEMINI_API_KEY", which is the exact opposite of what a preflight
is for. Any entry point that touches this package now sees the same
configuration the server does.

override=False so a variable set on the command line beats the file:

    WINDFALL_FIXTURES=0 python -m backend.app

has to mean what it says even when backend/.env pins it to 1.
"""
from pathlib import Path as _Path

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:  # python-dotenv is in requirements; degrade rather than crash
    pass
else:
    _load_dotenv(_Path(__file__).resolve().parents[1] / ".env", override=False)
