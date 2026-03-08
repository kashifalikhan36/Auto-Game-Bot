"""
Low-level wrapper around the Interception kernel driver.

Installation (Windows 11 — use the new installer):
  1. Open PowerShell as Administrator inside the repository root.
  2. Run:  ./Interception/Install-Win11.ps1
     This will:
       a. Create and trust a self-signed test code-signing certificate.
       b. Re-sign keyboard.sys / mouse.sys with SHA-256 Authenticode.
       c. Enable Test Signing mode (bcdedit /set testsigning on).
       d. Copy drivers to System32/Drivers/ and register kernel services.
       e. Add UpperFilters registry entries for keyboard and mouse classes.
  3. Disable Secure Boot in BIOS/UEFI (required for test-signed drivers).
  4. Reboot.
  5. pip install interception-python

To uninstall:  ./Interception/Uninstall-Win11.ps1

If the driver is NOT installed, the class falls back to Win32 SendInput
so development/testing continues without the driver.  Input via SendInput
is detectable by user-mode anti-cheat; install the driver for kernel-level
input injection.

Driver status check at runtime
─────────────────────────────
Call InputController.driver_status() to get a dict describing what is active.
"""

from __future__ import annotations

import ctypes
import time
import warnings


# ---------------------------------------------------------------------------
# Check whether the Interception kernel services are actually running.
# The Python bindings import alone is not sufficient — the kernel driver
# (keyboard service + mouse service) must also be loaded.
# ---------------------------------------------------------------------------
import subprocess as _sp
import sys as _sys


def _service_running(name: str) -> bool:
    """Return True if the named Windows kernel service is in RUNNING state."""
    try:
        result = _sp.run(
            ["sc.exe", "query", name],
            capture_output=True, text=True, timeout=3
        )
        return "RUNNING" in result.stdout
    except Exception:
        return False


def _interception_driver_loaded() -> bool:
    """True when BOTH keyboard and mouse Interception services are running."""
    return _service_running("keyboard") and _service_running("mouse")


# ---------------------------------------------------------------------------
# Try importing the Interception driver bindings
# ---------------------------------------------------------------------------
try:
    import interception  # type: ignore

    if _interception_driver_loaded():
        _INTERCEPTION_AVAILABLE = True
    else:
        _INTERCEPTION_AVAILABLE = False
        warnings.warn(
            "interception-python is installed but the kernel driver services\n"
            "('keyboard' and 'mouse') are NOT running.\n"
            "Run: .\\Interception\\Install-Win11.ps1  (as Administrator) then reboot.\n"
            "Falling back to SendInput.",
            stacklevel=2,
        )
except ImportError:
    _INTERCEPTION_AVAILABLE = False
    warnings.warn(
        "interception-python package not found.\n"
        "Install with:  pip install interception-python\n"
        "Then run:      .\\Interception\\Install-Win11.ps1  (as Administrator) and reboot.\n"
        "Falling back to SendInput (detectable by user-mode anti-cheat).",
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
            print("[InputController] Using Interception kernel driver (kernel-level, stealthy).")
        else:
            print("[InputController] Using SendInput fallback (user-mode).")
            print("[InputController] To install the kernel driver run:")
            print("[InputController]   ./Interception/Install-Win11.ps1  (as Administrator)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def driver_status() -> dict:
        """
        Return a dict describing the current driver status.

        Keys:
          - mode:            'interception' | 'sendinput'
          - python_pkg:      bool — interception-python package importable?
          - kbd_svc_running: bool — 'keyboard' kernel service running?
          - mouse_svc_running: bool — 'mouse' kernel service running?
          - install_cmd:     str — command to install if not available
        """
        try:
            import interception  # type: ignore  # noqa: F401
            pkg = True
        except ImportError:
            pkg = False

        kbd_svc   = _service_running("keyboard")
        mouse_svc = _service_running("mouse")
        active    = pkg and kbd_svc and mouse_svc

        return {
            "mode":              "interception" if active else "sendinput",
            "python_pkg":        pkg,
            "kbd_svc_running":   kbd_svc,
            "mouse_svc_running": mouse_svc,
            "install_cmd":       r"./Interception/Install-Win11.ps1  (run as Administrator, then reboot)",
        }

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
