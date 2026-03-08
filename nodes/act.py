"""
Act node — translates the LLM action keyword into a real keypress
via the Interception kernel driver (or a safe fallback).
"""

from __future__ import annotations

import threading
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
# Binding dispatcher
# ---------------------------------------------------------------------------

def _execute_binding(controller: InputController, binding: dict) -> None:
    """Dispatch a key_map binding to the correct input method.

    Supported types:
      keyboard   — { "type": "keyboard", "key": str, "hold_ms"?: int }
      mouse      — { "type": "mouse", "button": str, "hold_ms"?: int }
      combo      — { "type": "combo", "keys": list[str], "hold_ms"?: int }
      mouse_move — { "type": "mouse_move", "dx": int, "dy": int, "steps"?: int }
      sequence   — { "type": "sequence", "steps": list[binding] }
      parallel   — { "type": "parallel", "actions": list[binding] }
    Each step in a sequence may include "delay_after_ms" for a post-step pause.
    Parallel actions all start simultaneously in separate threads and are joined
    before returning (blocks until the longest sub-action finishes).
    """
    input_type = binding.get("type", "keyboard")
    hold_ms = binding.get("hold_ms", config.KEY_HOLD_MS)

    if input_type == "keyboard":
        controller.press_key(binding["key"], hold_ms=hold_ms)
    elif input_type == "mouse":
        controller.click_mouse(binding["button"], hold_ms=hold_ms)
    elif input_type == "combo":
        controller.press_combo(binding["keys"], hold_ms=hold_ms)
    elif input_type == "mouse_move":
        controller.move_mouse(
            binding.get("dx", 0),
            binding.get("dy", 0),
            steps=binding.get("steps", 5),
        )
    elif input_type == "sequence":
        for step in binding.get("steps", []):
            _execute_binding(controller, step)
            delay = step.get("delay_after_ms", 0)
            if delay:
                time.sleep(delay / 1000.0)
    elif input_type == "parallel":
        threads = [
            threading.Thread(target=_execute_binding, args=(controller, sub), daemon=True)
            for sub in binding.get("actions", [])
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


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
    binding: dict | None = config.VK_MAP.get(action)

    if binding is not None:
        controller = _get_controller()
        _execute_binding(controller, binding)

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
