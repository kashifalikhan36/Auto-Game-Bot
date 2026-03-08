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

import signal
import sys
import time

import cv2

import config  # noqa: F401  (triggers dotenv load + validation early)
from graph import compile_graph
from nodes.capture import cleanup_camera
from state import initial_state


# ---------------------------------------------------------------------------
# Graceful shutdown helpers
# ---------------------------------------------------------------------------

def _shutdown(signum=None, frame=None) -> None:  # noqa: ANN001
    print("\n[main] Shutdown requested — cleaning up …")
    cleanup_camera()
    cv2.destroyAllWindows()
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Auto Game Bot")
    print(f"  Model  : {config.AZURE_DEPLOYMENT_NAME}")
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
