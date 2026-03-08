"""
Auto Game Bot — entry point.

Usage:
    python main.py

Environment:
    Copy .env.example to .env and fill in your Azure OpenAI credentials
    before running.

Keyboard shortcut to stop:
    Ctrl+C  →  clean shutdown (camera released, OpenCV window closed)
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time

import cv2

import config  # noqa: F401  (triggers dotenv load + validation early)
from graph import compile_graph
from nodes.capture import cleanup_camera
from state import initial_state


# ---------------------------------------------------------------------------
# Game selection
# ---------------------------------------------------------------------------

def _discover_game_configs() -> list[dict]:
    """Scan games_config/ and return a list of {name, id, path} dicts."""
    root = os.path.join(os.path.dirname(__file__), "games_config")
    games = []
    if not os.path.isdir(root):
        return games
    for entry in sorted(os.listdir(root)):
        cfg_path = os.path.join(root, entry, "config.json")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, encoding="utf-8") as f:
                    data = json.load(f)
                games.append({
                    "name": data.get("game_name", entry),
                    "id":   data.get("game_id", entry),
                    "path": cfg_path,
                })
            except Exception:
                pass
    return games


def _select_game() -> str | None:
    """
    Prompt the user to pick a game from games_config/.
    Returns the path to the chosen config.json, or None to use defaults.
    """
    games = _discover_game_configs()
    if not games:
        print("[game] No game configs found in games_config/ — using default key map.")
        return None

    print("\n" + "=" * 60)
    print("  Select a game config")
    print("=" * 60)
    for i, g in enumerate(games, 1):
        print(f"  [{i}] {g['name']}")
    print(f"  [0] Use default key map (no game selected)")
    print("=" * 60)

    while True:
        try:
            raw = input("  Enter number: ").strip()
        except EOFError:
            print("\n[game] No input — using default key map.")
            return None
        if not raw:
            continue
        try:
            choice = int(raw)
        except ValueError:
            print("  Invalid input — enter a number.")
            continue
        if choice == 0:
            print("[game] Using default key map.")
            return None
        if 1 <= choice <= len(games):
            selected = games[choice - 1]
            print(f"[game] Loaded: {selected['name']}")
            return selected["path"]
        print(f"  Please enter a number between 0 and {len(games)}.")


# ---------------------------------------------------------------------------
# Graceful shutdown helpers
# ---------------------------------------------------------------------------

def _shutdown(signum=None, frame=None) -> None:  # noqa: ANN001
    print("\n[main] Shutdown requested — cleaning up …")
    cleanup_camera()
    try:
        cv2.destroyAllWindows()
    except cv2.error:
        pass
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Game selection — must happen before compile_graph() so nodes see the
    # updated ACTION_LIST / VK_MAP.
    game_cfg_path = _select_game()
    if game_cfg_path:
        config.load_game_config(game_cfg_path)

    print("\n" + "=" * 60)
    print("  Auto Game Bot")
    print(f"  Provider: {config.ACTIVE_PROVIDER.upper()}")
    print(f"  Model  : {config.ACTIVE_MODEL_NAME}")
    print(f"  Region : {config.CAPTURE_REGION}")
    print(f"  Resize : {config.CAPTURE_RESIZE}px  JPEG Q={config.JPEG_QUALITY}")
    print(f"  Frames : {'∞' if config.MAX_FRAMES == 0 else config.MAX_FRAMES}")
    print(f"  Debug  : show_frame={config.DEBUG_SHOW_FRAME}  timing={config.DEBUG_TIMING}")
    print("=" * 60)
    print("Press Ctrl+C to stop.\n")

    app = compile_graph()
    state = initial_state()

    if config.MAX_FRAMES == 0:
        # Run forever — stream state updates frame-by-frame
        print("[main] Starting infinite game loop …")
        for chunk in app.stream(state, stream_mode="values"):
            state = chunk  # keep latest state in sync
    else:
        # Run for a fixed number of frames then exit cleanly
        print(f"[main] Running for {config.MAX_FRAMES} frames …")
        t_start = time.perf_counter()
        final = app.invoke(state)
        elapsed = time.perf_counter() - t_start
        frames = final.get("frame_count", 0)
        fps = frames / elapsed if elapsed > 0 else 0
        print(f"\n[main] Done. {frames} frames in {elapsed:.1f}s  ({fps:.1f} FPS)")

    _shutdown()


if __name__ == "__main__":
    main()
