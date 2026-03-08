"""
Low-level wrapper around the Interception kernel driver.

The Interception driver must be installed BEFORE running this code:
  1. Download from: https://github.com/oblitum/Interception/releases
  2. Run install-interception.exe as Administrator
  3. Reboot
  4. pip install interception-python

If the driver is NOT installed, the class falls back to ctypes SendInput
so that development/testing can continue without the driver.
"""

from __future__ import annotations

import ctypes
import time
import warnings


# ---------------------------------------------------------------------------
# Try importing the Interception driver bindings
# ---------------------------------------------------------------------------
try:
    import interception  # type: ignore

    _INTERCEPTION_AVAILABLE = True
except ImportError:
    _INTERCEPTION_AVAILABLE = False
    warnings.warn(
        "interception-python not found or Interception driver not installed.\n"
        "Falling back to SendInput (ctypes). Input may be detectable by anti-cheat.\n"
        "See driver/input_controller.py for installation instructions.",
        stacklevel=2,
    )


# ---------------------------------------------------------------------------
# SendInput fallback structures (Windows API)
# ---------------------------------------------------------------------------
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

INPUT_KEYBOARD = 1


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT_UNION)]


def _send_input_vk(vk_code: int, key_up: bool) -> None:
    """Send a single virtual-key event via SendInput (user-mode fallback)."""
    flags = KEYEVENTF_KEYUP if key_up else KEYEVENTF_KEYDOWN
    inp = _INPUT(
        type=INPUT_KEYBOARD,
        _input=_INPUT_UNION(
            ki=_KEYBDINPUT(
                wVk=vk_code,
                wScan=0,
                dwFlags=flags,
                time=0,
                dwExtraInfo=None,  # type: ignore[arg-type]
            )
        ),
    )
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


# ---------------------------------------------------------------------------
# VK → scan-code conversion helper (used by Interception path)
# ---------------------------------------------------------------------------
def _vk_to_scan(vk_code: int) -> int:
    """Map a Windows virtual-key code to a hardware scan code."""
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, 0)  # MAPVK_VK_TO_VSC
    return scan


# ---------------------------------------------------------------------------
# Main controller class
# ---------------------------------------------------------------------------

class InputController:
    """
    Thread-safe keyboard input controller.
    Uses the Interception kernel driver when available, otherwise SendInput.
    """

    def __init__(self) -> None:
        self._use_interception = _INTERCEPTION_AVAILABLE
        self._ctx = None
        self._device = None

        if self._use_interception:
            self._ctx = interception.interception()
            # Find the first available keyboard device
            self._device = interception.INTERCEPTION_KEYBOARD(0)
            print("[InputController] Using Interception kernel driver.")
        else:
            print("[InputController] Using SendInput fallback.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def press_key(self, vk_code: int, hold_ms: int = 50) -> None:
        """
        Press and release a key identified by its Windows virtual-key code.

        Args:
            vk_code:  Windows VK_* constant (e.g. 0x20 = VK_SPACE).
            hold_ms:  How long (ms) to hold the key down before releasing.
        """
        if self._use_interception:
            self._interception_press(vk_code, hold_ms)
        else:
            self._sendinput_press(vk_code, hold_ms)

    def press_combo(self, vk_codes: list[int], hold_ms: int = 50) -> None:
        """
        Press multiple keys simultaneously (e.g. Shift+Attack).
        All keys are pressed, held for hold_ms, then released in reverse order.
        """
        for vk in vk_codes:
            self._key_down(vk)
        time.sleep(hold_ms / 1000.0)
        for vk in reversed(vk_codes):
            self._key_up(vk)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _interception_press(self, vk_code: int, hold_ms: int) -> None:
        scan = _vk_to_scan(vk_code)
        stroke_down = interception.key_stroke(
            scan,
            interception.interception_key_state.INTERCEPTION_KEY_DOWN,
            0,
        )
        stroke_up = interception.key_stroke(
            scan,
            interception.interception_key_state.INTERCEPTION_KEY_UP,
            0,
        )
        self._ctx.send(self._device, stroke_down)
        time.sleep(hold_ms / 1000.0)
        self._ctx.send(self._device, stroke_up)

    def _sendinput_press(self, vk_code: int, hold_ms: int) -> None:
        _send_input_vk(vk_code, key_up=False)
        time.sleep(hold_ms / 1000.0)
        _send_input_vk(vk_code, key_up=True)

    def _key_down(self, vk_code: int) -> None:
        if self._use_interception:
            scan = _vk_to_scan(vk_code)
            stroke = interception.key_stroke(
                scan,
                interception.interception_key_state.INTERCEPTION_KEY_DOWN,
                0,
            )
            self._ctx.send(self._device, stroke)
        else:
            _send_input_vk(vk_code, key_up=False)

    def _key_up(self, vk_code: int) -> None:
        if self._use_interception:
            scan = _vk_to_scan(vk_code)
            stroke = interception.key_stroke(
                scan,
                interception.interception_key_state.INTERCEPTION_KEY_UP,
                0,
            )
            self._ctx.send(self._device, stroke)
        else:
            _send_input_vk(vk_code, key_up=True)
