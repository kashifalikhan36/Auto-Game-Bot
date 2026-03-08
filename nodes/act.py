"""
Act node — drives real simultaneous hardware inputs based on a SITUATION label.

Architecture
============
analyze_node classifies the screenshot into one of:
  EXPLORE | COMBAT | EVADE | COVER | INTERACT | IDLE

act_node dispatches to nodes/behaviors.py which runs PARALLEL threads so
keys, mouse movement, and mouse clicks can all fire at the same time.

The game config's "behaviors" section defines exactly which tracks to run
for each situation, with random variation between track-groups.
"""

from __future__ import annotations

import time

import config
from driver.input_controller import InputController
from nodes.behaviors import execute_behavior
from state import BotState

# ---------------------------------------------------------------------------
# Singleton input controller
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
    LangGraph node: execute hardware inputs for the current situation.

    Reads state["situation"] and drives the behavior tracks defined in
    config.BEHAVIOR_CONFIG[situation].  All tracks run simultaneously.
    """
    t0 = time.perf_counter()

    situation: str = state.get("situation", "EXPLORE")
    ctrl = _get_controller()

    behavior_cfg: dict = getattr(config, "BEHAVIOR_CONFIG", {})
    execute_behavior(ctrl, situation, behavior_cfg)

    t1 = time.perf_counter()
    frame_count = state.get("frame_count", 0) + 1

    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["act_ms"] = round((t1 - t0) * 1000, 2)
        total = sum(v for v in timing.values())
        timing["total_ms"] = round(total, 2)
        print(
            f"[frame {frame_count:05d}] sit={situation:<10} "
            f"capture={timing.get('capture_ms', 0):.1f}ms  "
            f"analyze={timing.get('analyze_ms', 0):.1f}ms  "
            f"act={timing.get('act_ms', 0):.1f}ms  "
            f"total={timing['total_ms']:.1f}ms"
        )
        return {**state, "frame_count": frame_count, "timing": timing}

    print(f"[frame {frame_count:05d}] situation={situation}")
    return {**state, "frame_count": frame_count}

