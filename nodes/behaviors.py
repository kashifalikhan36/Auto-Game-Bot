"""
Behavior executor — translates a SITUATION label into real simultaneous inputs.

Architecture
============
The LLM classifies what it sees into ONE of 6 situations:
  EXPLORE  — no threat, move through the level
  COMBAT   — enemy visible, shoot
  EVADE    — taking fire / danger, dodge/dive
  COVER    — in cover, peek and scan
  INTERACT — prompt on screen, press action
  IDLE     — cutscene / menu / loading

For each situation, this module runs:
  • A set of simultaneous "held" keys (e.g. Shift+W)
  • Mouse movement (camera look)
  • Mouse clicks (shoot)
  • All truly parallel using threading

The game config supplies a "behaviors" dict that maps situation →
a list of concurrent action tracks. The executor runs all tracks
simultaneously and returns when all finish.

Track format (in config.json):
  { "keys": [...], "hold_ms": N }            — hold those keys for N ms
  { "mouse_move": {"dx": N, "dy": N} }       — smooth relative mouse move
  { "mouse_click": "left"|"right", "hold_ms": N }  — click
  Tracks are run in parallel threads.
"""

from __future__ import annotations

import random
import threading
import time

from driver.input_controller import InputController


# ---------------------------------------------------------------------------
# Low-level track runners (each runs in its own thread)
# ---------------------------------------------------------------------------

def _run_keys(ctrl: InputController, keys: list[str], hold_ms: int) -> None:
    """Hold all `keys` simultaneously for `hold_ms` ms then release."""
    ctrl.press_combo(keys, hold_ms=hold_ms)


def _run_mouse_move(ctrl: InputController, dx: int, dy: int, steps: int = 15) -> None:
    ctrl.move_mouse(dx, dy, steps=steps)


def _run_mouse_click(ctrl: InputController, button: str, hold_ms: int) -> None:
    ctrl.click_mouse(button, hold_ms=hold_ms)


def _run_sequence(ctrl: InputController, steps: list[dict]) -> None:
    """Sequential clicks/moves within one track (e.g. right-click then left-click)."""
    for step in steps:
        if "mouse_click" in step:
            _run_mouse_click(ctrl, step["mouse_click"], step.get("hold_ms", 80))
        elif "mouse_move" in step:
            mv = step["mouse_move"]
            _run_mouse_move(ctrl, mv.get("dx", 0), mv.get("dy", 0), mv.get("steps", 12))
        delay = step.get("delay_after_ms", 0)
        if delay:
            time.sleep(delay / 1000.0)


# ---------------------------------------------------------------------------
# Track dispatcher — starts one track in a thread
# ---------------------------------------------------------------------------

def _start_track(ctrl: InputController, track: dict) -> threading.Thread:
    """Parse a behavior track dict and start it in a daemon thread."""

    if "keys" in track:
        keys = track["keys"]
        hold_ms = track.get("hold_ms", 400)
        t = threading.Thread(target=_run_keys, args=(ctrl, keys, hold_ms), daemon=True)

    elif "mouse_move" in track:
        mv = track["mouse_move"]
        dx = mv.get("dx", 0)
        dy = mv.get("dy", 0)
        steps = mv.get("steps", 15)
        t = threading.Thread(target=_run_mouse_move, args=(ctrl, dx, dy, steps), daemon=True)

    elif "mouse_click" in track:
        button = track["mouse_click"]
        hold_ms = track.get("hold_ms", 80)
        t = threading.Thread(target=_run_mouse_click, args=(ctrl, button, hold_ms), daemon=True)

    elif "sequence" in track:
        t = threading.Thread(target=_run_sequence, args=(ctrl, track["sequence"]), daemon=True)

    else:
        # Unknown track — no-op thread
        t = threading.Thread(target=lambda: None, daemon=True)

    t.start()
    return t


# ---------------------------------------------------------------------------
# Behavior randomiser helpers
# ---------------------------------------------------------------------------

def _pick(options: list) -> object:
    """Pick a random element from a list."""
    return random.choice(options) if options else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_behavior(
    ctrl: InputController,
    situation: str,
    behavior_cfg: dict,
) -> None:
    """
    Run all parallel tracks for `situation`.

    `behavior_cfg` — the "behaviors" section from the game's config.json.
    Each situation maps to a list of track-groups; one group is chosen at
    random so the bot doesn't repeat the exact same motion every time.

    Structure:
        behaviors: {
          "EXPLORE": [
            [  <-- track-group 0: sprint right
              { "keys": ["shift","w"], "hold_ms": 1200 },
              { "mouse_move": { "dx": 400, "dy": 0, "steps": 12 } }
            ],
            [  <-- track-group 1: sprint left
              { "keys": ["shift","w"], "hold_ms": 1200 },
              { "mouse_move": { "dx": -400, "dy": 0, "steps": 12 } }
            ]
          ],
          ...
        }
    """
    groups: list[list[dict]] = behavior_cfg.get(situation, [])
    if not groups:
        # Unknown situation — do nothing and let the loop continue
        return

    tracks: list[dict] = _pick(groups)  # type: ignore[assignment]
    if not tracks:
        return

    # Fire all tracks simultaneously
    threads = [_start_track(ctrl, track) for track in tracks]
    for t in threads:
        t.join()
