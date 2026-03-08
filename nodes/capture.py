"""
Capture node — takes a screenshot of the game window and encodes it
as a base64 JPEG ready for the LLM vision API.

Two backends are supported (set CAPTURE_BACKEND in .env):

  dxcam (default)
    Uses DXGI Desktop Duplication API. Fastest option for DirectX
    full-screen games running directly on this PC.
    Does NOT work with Parsec, remote desktop, or virtual displays.

  mss
    Uses GDI BitBlt. Slightly slower but works with anything visible
    on screen, including Parsec streams, OBS virtual camera, and
    remote desktop sessions.
"""

from __future__ import annotations

import base64
import time
from typing import Any

import cv2
import numpy as np

import config
from state import BotState

# ---------------------------------------------------------------------------
# dxcam backend (DXGI)
# ---------------------------------------------------------------------------
_dxcam_camera: Any = None


def _get_dxcam_camera() -> Any:
    global _dxcam_camera
    if _dxcam_camera is None:
        import dxcam
        region = config.CAPTURE_REGION
        if region is not None:
            left, top, w, h = region
            _dxcam_camera = dxcam.create(region=(left, top, left + w, top + h))
        else:
            _dxcam_camera = dxcam.create()
        _dxcam_camera.start(target_fps=60, video_mode=True)
    return _dxcam_camera


def _capture_dxcam() -> np.ndarray | None:
    frame = _get_dxcam_camera().get_latest_frame()
    return frame  # BGR ndarray or None


# ---------------------------------------------------------------------------
# mss backend (GDI — works with Parsec, remote desktop, virtual displays)
# ---------------------------------------------------------------------------
_mss_instance: Any = None


def _get_mss() -> Any:
    global _mss_instance
    if _mss_instance is None:
        import mss
        _mss_instance = mss.mss()
    return _mss_instance


def _capture_mss() -> np.ndarray | None:
    sct = _get_mss()
    region = config.CAPTURE_REGION
    if region is not None:
        left, top, w, h = region
        monitor = {"left": left, "top": top, "width": w, "height": h}
    else:
        monitor = sct.monitors[1]  # primary monitor
    screenshot = sct.grab(monitor)
    # mss returns BGRA — drop the alpha channel to get BGR
    frame = np.array(screenshot)[:, :, :3]
    return frame


# ---------------------------------------------------------------------------
# Shared encode step
# ---------------------------------------------------------------------------

def _encode_frame(frame: np.ndarray) -> str:
    """Resize to CAPTURE_RESIZE and return a base64-encoded JPEG string."""
    size = config.CAPTURE_RESIZE
    resized = cv2.resize(frame, (size, size), interpolation=cv2.INTER_LINEAR)

    if config.DEBUG_SHOW_FRAME:
        try:
            cv2.imshow("AutoGameBot — capture preview", resized)
            cv2.waitKey(1)
        except cv2.error:
            pass

    if config.DEBUG_SAVE_FRAME:
        cv2.imwrite("debug_frame.jpg", resized)

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY]
    success, buffer = cv2.imencode(".jpg", resized, encode_params)
    if not success:
        raise RuntimeError("cv2.imencode failed — cannot encode screenshot to JPEG")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def capture_node(state: BotState) -> BotState:
    """
    LangGraph node: capture a frame and encode it.

    Returns an updated state with:
      - screenshot_b64: base64-encoded JPEG string
      - timing["capture_ms"]: time spent in this node (if DEBUG_TIMING)
    """
    t0 = time.perf_counter()

    backend = config.CAPTURE_BACKEND
    if backend == "mss":
        frame = _capture_mss()
    else:
        frame = _capture_dxcam()

    if frame is None:
        return state

    b64 = _encode_frame(frame)

    t1 = time.perf_counter()

    updates: BotState = {"screenshot_b64": b64}
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["capture_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}


def cleanup_camera() -> None:
    """Release capture resources on shutdown."""
    global _dxcam_camera, _mss_instance
    if _dxcam_camera is not None:
        try:
            _dxcam_camera.stop()
        except Exception:
            pass
        _dxcam_camera = None
    if _mss_instance is not None:
        try:
            _mss_instance.close()
        except Exception:
            pass
        _mss_instance = None
