"""
LangGraph shared state definition.
Every node reads from and writes to a BotState dict.
"""

from typing import TypedDict


class BotState(TypedDict, total=False):
    # Raw base64-encoded JPEG screenshot (resized, ready for the LLM)
    screenshot_b64: str

    # Situation label returned by the LLM — one of the SITUATION_LIST
    # e.g. "EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"
    situation: str

    # Legacy single-action field (kept for timing/display only)
    action: str

    # Rolling counter of processed frames
    frame_count: int

    # Last N situations, used as context in the LLM prompt
    recent_actions: list[str]

    # Per-frame timing info for debugging (populated when DEBUG_TIMING=true)
    timing: dict[str, float]


def initial_state() -> BotState:
    """Return a clean starting state for the bot graph."""
    return BotState(
        screenshot_b64="",
        situation="EXPLORE",
        action="EXPLORE",
        frame_count=0,
        recent_actions=[],
        timing={},
    )
