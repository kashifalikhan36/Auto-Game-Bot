"""
Central configuration for the AI Game Bot.
All values are loaded from environment variables (see .env.example).
Game-specific tuning (capture region, key map) lives here too.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Azure OpenAI
# ---------------------------------------------------------------------------
AZURE_OPENAI_ENDPOINT: str = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY: str = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_DEPLOYMENT_NAME: str = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-nano")

# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------
# Game window region to capture: (left, top, width, height) in screen pixels.
# Set to None to capture the entire primary monitor.
CAPTURE_REGION: tuple[int, int, int, int] | None = (
    int(os.getenv("CAPTURE_X", 0)),
    int(os.getenv("CAPTURE_Y", 0)),
    int(os.getenv("CAPTURE_W", 1920)),
    int(os.getenv("CAPTURE_H", 1080)),
)

# Resolution fed to the LLM (square crop; "low" detail = 512 px max)
CAPTURE_RESIZE: int = int(os.getenv("CAPTURE_RESIZE", 512))

# JPEG quality used when base64-encoding the screenshot (80 = good trade-off)
JPEG_QUALITY: int = int(os.getenv("JPEG_QUALITY", 80))

# ---------------------------------------------------------------------------
# LLM inference
# ---------------------------------------------------------------------------
# Maximum tokens the LLM can generate.  Single-word outputs → keep this tiny.
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 10))

# LLM temperature (0 = deterministic, fast)
TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", 0.0))

# ---------------------------------------------------------------------------
# Game actions & key map
# ---------------------------------------------------------------------------
# The bot understands these action names (returned by the LLM).
# Map each name → Windows virtual-key code (VK codes) used by the input driver.
# Common VK codes:  https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
# fmt: off
ACTION_LIST: list[str] = [
    "UP", "DOWN", "LEFT", "RIGHT",
    "JUMP", "ATTACK", "DEFEND", "INTERACT",
    "IDLE",
]

# Key map: action name -> {"type": "keyboard", "key": str}
#                      or {"type": "mouse", "button": str}
#                      or None (no input)
# Populated from .env defaults or overridden by load_game_config().
VK_MAP: dict[str, dict | None] = {
    "UP":       {"type": "keyboard", "key": "up"},
    "DOWN":     {"type": "keyboard", "key": "down"},
    "LEFT":     {"type": "keyboard", "key": "left"},
    "RIGHT":    {"type": "keyboard", "key": "right"},
    "JUMP":     {"type": "keyboard", "key": "space"},
    "ATTACK":   {"type": "keyboard", "key": "z"},
    "DEFEND":   {"type": "keyboard", "key": "x"},
    "INTERACT": {"type": "keyboard", "key": "enter"},
    "IDLE":     None,
}
# fmt: on

# ---------------------------------------------------------------------------
# Game config loader
# ---------------------------------------------------------------------------

def load_game_config(config_path: str) -> None:
    """
    Load a games_config/<game_id>/config.json and override ACTION_LIST + VK_MAP
    at module level so all nodes pick up the new bindings.
    """
    import json
    global ACTION_LIST, VK_MAP
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    ACTION_LIST = data["action_list"]
    VK_MAP = data["key_map"]
# fmt: on

# How long (ms) to hold a key down before releasing it
KEY_HOLD_MS: int = int(os.getenv("KEY_HOLD_MS", 50))

# ---------------------------------------------------------------------------
# Bot loop
# ---------------------------------------------------------------------------
# Maximum number of frames to process before stopping (0 = run forever)
MAX_FRAMES: int = int(os.getenv("MAX_FRAMES", 0))

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
# If True, shows a live OpenCV window with the resized screenshot
DEBUG_SHOW_FRAME: bool = os.getenv("DEBUG_SHOW_FRAME", "false").lower() == "true"

# If True, prints per-frame timing breakdown to stdout
DEBUG_TIMING: bool = os.getenv("DEBUG_TIMING", "false").lower() == "true"
