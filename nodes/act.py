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
from nodes.behaviors import get_engine
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
    LangGraph node: execute hardware inputs for the action chosen by the LLM.

    Reads state["chosen_action"] (e.g. "AIM_SHOOT", "SPRINT_LOOK_RIGHT") and
    drives exactly those tracks defined in config.NAMED_ACTIONS[chosen_action].
    All tracks run simultaneously (keyboard worker + mouse/click worker).
    """
    t0 = time.perf_counter()

    chosen_action: str = state.get("chosen_action", "SPRINT_FORWARD")
    situation: str = state.get("situation", "EXPLORE")
    ctrl = _get_controller()

    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})

    # Non-blocking -- starts/updates the persistent 2-worker engine.
    # Workers loop continuously so inputs fire even while the AI is thinking.
    engine = get_engine(ctrl)
    engine.update(chosen_action, named_actions)

    t1 = time.perf_counter()
    frame_count = state.get("frame_count", 0) + 1

    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["act_ms"] = round((t1 - t0) * 1000, 2)
        total = sum(v for v in timing.values())
        timing["total_ms"] = round(total, 2)
        print(
            f"[frame {frame_count:05d}] action={chosen_action:<25} sit={situation:<8} "
            f"capture={timing.get('capture_ms', 0):.1f}ms  "
            f"analyze={timing.get('analyze_ms', 0):.1f}ms  "
            f"act={timing.get('act_ms', 0):.1f}ms  "
            f"total={timing['total_ms']:.1f}ms"
        )
        return {**state, "frame_count": frame_count, "timing": timing}

    print(f"[frame {frame_count:05d}] action={chosen_action:<25} situation={situation}")
    return {**state, "frame_count": frame_count}

