"""
Windfall test package.

Pins the inference-related environment BEFORE any test module imports
backend.recovery, which is where backend/.env is loaded.

Without this the suite inherits whatever a developer happens to have in
backend/.env: a real GEMINI_API_KEY plus WINDFALL_LIVE_INFERENCE=1 made two
gating tests fail and sent other tests off to call Gemini for real, turning a
4-second offline suite into a slow, network-dependent, differently-configured
one. Tests must assert what the code does, not what one machine is set up to
do.

The recovery package loads .env with override=False, so values already present
here win. Individual tests still set what they need on top.
"""
import os

os.environ["WINDFALL_FIXTURES"] = "1"   # the suite's default: replay, no network
os.environ["WINDFALL_LIVE_INFERENCE"] = ""
os.environ["MOCK_LLM"] = ""
os.environ["GEMINI_API_KEY"] = ""
