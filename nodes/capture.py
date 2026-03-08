"""
Capture node — takes a screenshot of the game window and encodes it
as a base64 JPEG ready for the LLM vision API.

Uses dxcam (DXGI Desktop Duplication API) for the lowest latency:
  - Works with DirectX exclusive full-screen games
  - Returns NumPy arrays directly — zero extra copy
  - Blocks until a fresh frame is available (no busy-wait polling)
"""

from __future__ import annotations

import base64
import time

import cv2
import dxcam
import numpy as np

import config
from state import BotState

# ---------------------------------------------------------------------------
# Module-level camera — created once, reused every frame (avoids overhead
# of opening/closing the DXGI session per capture).
# ---------------------------------------------------------------------------
_camera: dxcam.DXCamera | None = None


def _get_camera() -> dxcam.DXCamera:
    global _camera
    if _camera is None:
        region = config.CAPTURE_REGION  # (left, top, width, height)
        if region is not None:
            left, top, w, h = region
            # dxcam uses (left, top, right, bottom)
            _camera = dxcam.create(region=(left, top, left + w, top + h))
        else:
            _camera = dxcam.create()
        _camera.start(target_fps=60, video_mode=True)
    return _camera


def capture_node(state: BotState) -> BotState:
    """
    LangGraph node: capture a frame and encode it.

    Returns an updated state with:
      - screenshot_b64: base64-encoded JPEG string
      - timing["capture_ms"]: time spent in this node (if DEBUG_TIMING)
    """
    t0 = time.perf_counter()

    camera = _get_camera()

    # get_latest_frame() blocks until a fresh frame is available.
    frame: np.ndarray | None = camera.get_latest_frame()

    if frame is None:
        # Fallback: return unchanged state and let the loop retry next cycle.
        return state

    # dxcam returns BGR; resize to the configured square resolution.
    size = config.CAPTURE_RESIZE
    resized: np.ndarray = cv2.resize(frame, (size, size), interpolation=cv2.INTER_LINEAR)

    if config.DEBUG_SHOW_FRAME:
        cv2.imshow("AutoGameBot — capture preview", resized)
        cv2.waitKey(1)

    # Encode to JPEG bytes, then base64.
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY]
    success, buffer = cv2.imencode(".jpg", resized, encode_params)
    if not success:
        raise RuntimeError("cv2.imencode failed — cannot encode screenshot to JPEG")

    b64: str = base64.b64encode(buffer.tobytes()).decode("ascii")

    t1 = time.perf_counter()

    updates: BotState = {
        "screenshot_b64": b64,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["capture_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}


def cleanup_camera() -> None:
    """Call this on shutdown to release the DXGI session cleanly."""
    global _camera
    if _camera is not None:
        _camera.stop()
        _camera = None
