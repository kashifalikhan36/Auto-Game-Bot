"""
Behavior executor — translates a SITUATION label into real simultaneous inputs.

Architecture
============
Three background daemon threads run CONTINUOUSLY, each owning a different
input resource so they never conflict:

  Worker-0  keyboard tracks   (e.g. shift+w sprint)
  Worker-1  mouse-move tracks (e.g. camera pan)
  Worker-2  click/sequence    (e.g. aim+shoot)

Each worker loops:
  1. Read the current situation.
  2. Collect all tracks of its type from that situation's groups.
  3. Pick one at random and execute it (blocking within the worker).
  4. Immediately go back to step 1.

This guarantees inputs are sent EVERY MOMENT — even while the AI is
processing the next screenshot (which takes 2-4 s).

act_node calls engine.update(situation, cfg) which is non-blocking.
Workers pick up the new situation on their very next loop iteration.

Track format (from config.json):
  { "keys": [...], "hold_ms": N }                    ← held repeatedly by Worker-0
  { "mouse_move": {"dx":N,"dy":N,"steps":N} }        ← sent repeatedly by Worker-1
  { "mouse_click": "left"|"right", "hold_ms": N }    ← fired by Worker-2
  { "sequence": [...] }                               ← sequential steps, Worker-2

Situations handled:
  EXPLORE  — no threat, move through the level
  INTERACT — prompt on screen, press action
  IDLE     — cutscene / menu / loading
"""

from __future__ import annotations

import random
import threading
import time

from driver.input_controller import InputController

# ---------------------------------------------------------------------------
# Worker type mapping — one resource type per worker, zero conflicts
# ---------------------------------------------------------------------------
# Worker-0 handles keyboard tracks    ("keys")
# Worker-1 handles camera tracks      ("mouse_move")
# Worker-2 handles click/seq tracks   ("mouse_click", "sequence")

_WORKER_TYPES: list[list[str]] = [
    ["keys"],
    ["mouse_move", "mouse_click", "sequence"],
]
_NUM_WORKERS = 2


# ---------------------------------------------------------------------------
# Low-level track runners (synchronous — called inside a worker thread)
# ---------------------------------------------------------------------------

def _run_keys(ctrl: InputController, keys: list[str], hold_ms: int) -> None:
    ctrl.press_combo(keys, hold_ms=hold_ms)


def _run_mouse_move(ctrl: InputController, dx: int, dy: int, steps: int = 15) -> None:
    ctrl.move_mouse(dx, dy, steps=steps)


def _run_mouse_click(ctrl: InputController, button: str, hold_ms: int) -> None:
    ctrl.click_mouse(button, hold_ms=hold_ms)


def _run_sequence(ctrl: InputController, steps: list[dict]) -> None:
    for step in steps:
        if "mouse_click" in step:
            _run_mouse_click(ctrl, step["mouse_click"], step.get("hold_ms", 80))
        elif "mouse_move" in step:
            mv = step["mouse_move"]
            _run_mouse_move(ctrl, mv.get("dx", 0), mv.get("dy", 0), mv.get("steps", 12))
        delay = step.get("delay_after_ms", 0)
        if delay:
            time.sleep(delay / 1000.0)


def _exec_track(ctrl: InputController, track: dict) -> None:
    """Execute one track dict synchronously (blocks until done)."""
    if "keys" in track:
        _run_keys(ctrl, track["keys"], track.get("hold_ms", 400))
    elif "mouse_move" in track:
        mv = track["mouse_move"]
        _run_mouse_move(ctrl, mv.get("dx", 0), mv.get("dy", 0), mv.get("steps", 15))
    elif "mouse_click" in track:
        _run_mouse_click(ctrl, track["mouse_click"], track.get("hold_ms", 80))
    elif "sequence" in track:
        _run_sequence(ctrl, track["sequence"])


# ---------------------------------------------------------------------------
# Continuous behavior engine
# ---------------------------------------------------------------------------

class BehaviorEngine:
    """
    Three persistent daemon threads looping CONTINUOUSLY.

    Each worker owns one input resource — so workers never conflict:
      Worker-0 → keyboard ("keys") tracks only
      Worker-1 → mouse-move tracks only
      Worker-2 → click/sequence tracks only

    Each worker's inner loop:
      1. Read current situation.
      2. Collect all tracks of its own type from that situation's groups.
      3. Pick one randomly, execute it (synchronous), repeat.

    Never pauses — even while the AI processes the next screenshot,
    the game receives continuous keyboard and mouse input.

    Usage (from act_node):
        engine = get_engine(ctrl)       # singleton, starts 3 workers on first call
        engine.update(situation, cfg)   # non-blocking, returns in microseconds
    """

    def __init__(self, ctrl: InputController) -> None:
        self._ctrl = ctrl
        self._situation: str = "IDLE"
        self._behavior_cfg: dict = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()

        for i in range(_NUM_WORKERS):
            t = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"BehaviorWorker-{i}",
                daemon=True,
            )
            t.start()

    def update(self, situation: str, behavior_cfg: dict) -> None:
        """Non-blocking: set new situation. Workers pick it up on next loop."""
        with self._lock:
            self._situation = situation
            self._behavior_cfg = behavior_cfg

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------

    def _get_state(self) -> tuple[str, dict]:
        with self._lock:
            return self._situation, self._behavior_cfg

    def _worker_loop(self, worker_id: int) -> None:
        """Tight loop: pick track → execute → repeat."""
        my_keys = _WORKER_TYPES[worker_id]
        # Stagger start so workers don't all fire at the exact same instant
        time.sleep(worker_id * 0.18)

        while not self._stop.is_set():
            sit, cfg = self._get_state()
            groups: list[list[dict]] = cfg.get(sit, [])

            # All tracks of this worker's type across every group
            tracks = [
                t for g in groups
                for t in g
                if any(k in t for k in my_keys)
            ]

            if not tracks:
                time.sleep(0.05)
                continue

            track = random.choice(tracks)
            try:
                _exec_track(self._ctrl, track)
            except Exception:
                time.sleep(0.05)


# ---------------------------------------------------------------------------
# Global singleton — created once on first use
# ---------------------------------------------------------------------------

_engine: BehaviorEngine | None = None


def get_engine(ctrl: InputController) -> BehaviorEngine:
    global _engine
    if _engine is None:
        _engine = BehaviorEngine(ctrl)
    return _engine


# ---------------------------------------------------------------------------
# Legacy one-shot helper (kept for compatibility; not used by act_node)
# ---------------------------------------------------------------------------

def execute_behavior(
    ctrl: InputController,
    situation: str,
    behavior_cfg: dict,
) -> None:
    """One-shot: run one random track-group and block until finished."""
    groups: list[list[dict]] = behavior_cfg.get(situation, [])
    if not groups:
        return
    group = random.choice(groups)
    threads = [
        threading.Thread(target=_exec_track, args=(ctrl, t), daemon=True)
        for t in group
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

