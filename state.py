"""
LangGraph shared state definition.
Every node reads from and writes to a BotState dict.
"""

from typing import TypedDict


class BotState(TypedDict, total=False):
    # Raw base64-encoded JPEG screenshot (resized, ready for the LLM)
    screenshot_b64: str

    # Action keyword returned by the LLM (e.g. "JUMP", "LEFT", "IDLE")
    action: str

    # Rolling counter of processed frames
    frame_count: int

    # Last N actions, used as optional context in the LLM prompt
    recent_actions: list[str]

    # Per-frame timing info for debugging (populated when DEBUG_TIMING=true)
    timing: dict[str, float]


def initial_state() -> BotState:
    """Return a clean starting state for the bot graph."""
    return BotState(
        screenshot_b64="",
        action="IDLE",
        frame_count=0,
        recent_actions=[],
        timing={},
    )
