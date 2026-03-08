"""
Central configuration for the AI Game Bot.
All values are loaded from environment variables (see .env.example).
Game-specific tuning (capture region, key map) lives here too.

Supported LLM providers (at least ONE set of credentials is required):
  azure     — Azure OpenAI  (AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY)
  openai    — OpenAI        (OPENAI_API_KEY)
  gemini    — Google Gemini (GEMINI_API_KEY)
  anthropic — Anthropic     (ANTHROPIC_API_KEY)
  groq      — Groq          (GROQ_API_KEY)

Set LLM_PROVIDER=<name> to force a provider, or leave it unset for
auto-detection (first provider whose credentials are present wins).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Azure OpenAI  (optional — one provider must be configured)
# ---------------------------------------------------------------------------
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_DEPLOYMENT_NAME: str = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-5-nano")

# ---------------------------------------------------------------------------
# OpenAI  (optional)
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# ---------------------------------------------------------------------------
# Google Gemini  (optional)
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ---------------------------------------------------------------------------
# Anthropic Claude  (optional)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# ---------------------------------------------------------------------------
# Groq  (mandatory for vision stage; optional as decision provider)
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
# Model used for scene vision analysis (must support images)
GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
# Model used when Groq is also the decision provider (can be text-only for speed)
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

# ---------------------------------------------------------------------------
# Provider resolution — exactly one provider is selected at startup
# ---------------------------------------------------------------------------

def _resolve_provider() -> str:
    """Return the active LLM provider name, validating credentials exist."""
    explicit = os.getenv("LLM_PROVIDER", "").lower().strip()
    if explicit:
        valid = ("azure", "openai", "gemini", "anthropic", "groq")
        if explicit not in valid:
            raise RuntimeError(
                f"[config] Unknown LLM_PROVIDER '{explicit}'. "
                f"Must be one of: {', '.join(valid)}"
            )
        # Validate that the chosen provider has the required credentials
        missing: dict[str, list[str]] = {
            "azure":     [] if (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY) else ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
            "openai":    [] if OPENAI_API_KEY    else ["OPENAI_API_KEY"],
            "gemini":    [] if GEMINI_API_KEY    else ["GEMINI_API_KEY"],
            "anthropic": [] if ANTHROPIC_API_KEY else ["ANTHROPIC_API_KEY"],
            "groq":      [] if GROQ_API_KEY      else ["GROQ_API_KEY"],
        }
        if missing[explicit]:
            raise RuntimeError(
                f"[config] LLM_PROVIDER={explicit} but missing credentials: "
                + ", ".join(missing[explicit])
            )
        return explicit

    # Auto-detect: first provider with full credentials wins
    if AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY:
        return "azure"
    if OPENAI_API_KEY:
        return "openai"
    if GEMINI_API_KEY:
        return "gemini"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    if GROQ_API_KEY:
        return "groq"

    raise RuntimeError(
        "\n[config] No LLM credentials found. Set at least ONE provider in your .env:\n"
        "  Azure OpenAI : AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY\n"
        "  OpenAI       : OPENAI_API_KEY\n"
        "  Gemini       : GEMINI_API_KEY\n"
        "  Anthropic    : ANTHROPIC_API_KEY\n"
        "  Groq         : GROQ_API_KEY\n"
        "Optionally pin a provider with: LLM_PROVIDER=azure|openai|gemini|anthropic|groq"
    )


ACTIVE_PROVIDER: str = _resolve_provider()

# Human-readable model name for the chosen provider
ACTIVE_MODEL_NAME: str = {
    "azure":     AZURE_DEPLOYMENT_NAME,
    "openai":    OPENAI_MODEL,
    "gemini":    GEMINI_MODEL,
    "anthropic": ANTHROPIC_MODEL,
    "groq":      GROQ_MODEL,
}[ACTIVE_PROVIDER]

# ---------------------------------------------------------------------------
# Screenshot capture
# ---------------------------------------------------------------------------
# Backend: "dxcam" (fastest, DirectX games) or "mss" (works with Parsec,
# remote desktop, virtual displays — use this if the bot always outputs IDLE).
CAPTURE_BACKEND: str = os.getenv("CAPTURE_BACKEND", "dxcam").lower().strip()

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
# Maximum tokens the LLM can generate.
# IMPORTANT for reasoning models (GPT-5 Nano, o1, o3-mini, Gemini Thinking):
# These models spend tokens on internal reasoning before writing the visible
# answer. If MAX_TOKENS is too low (e.g. 10), all tokens are used for thinking
# and the visible response is empty ("") which the bot treats as IDLE.
# Set to 2000+ for reasoning models; 10-20 is fine for standard models.
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 10000))

# LLM temperature (0 = deterministic).  Azure GPT-5 Nano ignores this (default only).
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

# Human-readable game context description (loaded from game config)
GAME_CONTEXT: str = ""

# Per-action descriptions: {"ACTION_NAME": "what this action does"}
ACTION_DESCRIPTIONS: dict[str, str] = {}

# Situation labels the LLM can return
SITUATION_LIST: list[str] = ["EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"]

# Behavior tracks: situation → list of track-groups (see nodes/behaviors.py)
BEHAVIOR_CONFIG: dict = {}

# Named actions: label → list of tracks  (the LLM picks one label per frame)
NAMED_ACTIONS: dict[str, list[dict]] = {}

# Human-readable descriptions for each named action (fed into the LLM prompt)
NAMED_ACTION_DESCRIPTIONS: dict[str, str] = {}

# Decision rules shown to the LLM (loaded from game config, per-game)
# Each string is one line of the rules section.
DECISION_RULES: list[str] = []

# Critical constraints shown to the LLM (loaded from game config, per-game)
CONSTRAINTS: list[str] = []

# Checklist questions shown in the user turn to guide the LLM (per-game)
SITUATION_CHECKLIST: list[str] = []

# Prompt sent to Groq vision to produce the structured scene JSON (per-game)
# Empty string = no two-stage pipeline (legacy single-stage mode)
SCENE_ANALYSIS_PROMPT: str = ""

def load_game_config(config_path: str) -> None:
    """
    Load a games_config/<game_id>/config.json and override ACTION_LIST + VK_MAP
    at module level so all nodes pick up the new bindings.
    """
    import json
    global ACTION_LIST, VK_MAP, GAME_CONTEXT, ACTION_DESCRIPTIONS, SITUATION_LIST, BEHAVIOR_CONFIG, NAMED_ACTIONS, NAMED_ACTION_DESCRIPTIONS, DECISION_RULES, CONSTRAINTS, SITUATION_CHECKLIST, SCENE_ANALYSIS_PROMPT
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    ACTION_LIST = data["action_list"]
    VK_MAP = data["key_map"]
    GAME_CONTEXT = data.get("game_context", "")
    ACTION_DESCRIPTIONS = data.get("action_descriptions", {})
    if data.get("situation_list"):
        SITUATION_LIST = data["situation_list"]
    BEHAVIOR_CONFIG = data.get("behaviors", {})
    NAMED_ACTIONS = data.get("named_actions", {})
    NAMED_ACTION_DESCRIPTIONS = data.get("named_action_descriptions", {})
    DECISION_RULES = data.get("decision_rules", [])
    CONSTRAINTS = data.get("constraints", [])
    SITUATION_CHECKLIST = data.get("situation_checklist", [])
    SCENE_ANALYSIS_PROMPT = data.get("scene_analysis_prompt", "")
# fmt: on

# How long (ms) to hold a key down before releasing it
KEY_HOLD_MS: int = int(os.getenv("KEY_HOLD_MS", 50))

# How many past actions to feed back to the LLM as context (anti-repeat)
RECENT_ACTIONS_WINDOW: int = int(os.getenv("RECENT_ACTIONS_WINDOW", 8))

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

# If True, saves every captured frame as debug_frame.jpg in the repo root
# (lets you check what the bot actually sees without needing a GUI)
DEBUG_SAVE_FRAME: bool = os.getenv("DEBUG_SAVE_FRAME", "false").lower() == "true"

# If True, prints per-frame timing breakdown to stdout
DEBUG_TIMING: bool = os.getenv("DEBUG_TIMING", "false").lower() == "true"
