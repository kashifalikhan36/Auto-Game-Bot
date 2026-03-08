"""
Act node — translates the LLM action keyword into a real keypress
via the Interception kernel driver (or a safe fallback).
"""

from __future__ import annotations

import time

import config
from driver.input_controller import InputController
from state import BotState

# ---------------------------------------------------------------------------
# Singleton input controller (opens the driver handle once)
# ---------------------------------------------------------------------------
_controller: InputController | None = None


def _get_controller() -> InputController:
    global _controller
    if _controller is None:
        _controller = InputController()
    return _controller


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def act_node(state: BotState) -> BotState:
    """
    LangGraph node: press the key corresponding to `state["action"]`.

    Returns an updated state with:
      - frame_count incremented by 1
      - timing["act_ms"]: time spent sending input (if DEBUG_TIMING)
    """
    t0 = time.perf_counter()

    action: str = state.get("action", "IDLE")
    key: str | None = config.VK_MAP.get(action)

    if key is not None:
        controller = _get_controller()
        controller.press_key(key, hold_ms=config.KEY_HOLD_MS)

    t1 = time.perf_counter()

    frame_count = state.get("frame_count", 0) + 1

    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["act_ms"] = round((t1 - t0) * 1000, 2)
        total = sum(v for v in timing.values())
        timing["total_ms"] = round(total, 2)
        print(
            f"[frame {frame_count:05d}] action={action:<10} "
            f"capture={timing.get('capture_ms', 0):.1f}ms  "
            f"analyze={timing.get('analyze_ms', 0):.1f}ms  "
            f"act={timing.get('act_ms', 0):.1f}ms  "
            f"total={timing['total_ms']:.1f}ms"
        )
        return {**state, "frame_count": frame_count, "timing": timing}

    print(f"[frame {frame_count:05d}] action={action}")
    return {**state, "frame_count": frame_count}
