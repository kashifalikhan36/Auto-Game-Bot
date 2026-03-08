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
# String key → VK code conversion (for SendInput fallback)
# ---------------------------------------------------------------------------
def _key_str_to_vk(key: str) -> int:
    """Convert an interception-python key name string to a Windows VK code."""
    try:
        from interception._keycodes import get_key_information  # type: ignore
        return get_key_information(key.lower()).vk_code
    except Exception:
        # last-resort: try treating it as a single character
        return ctypes.windll.user32.VkKeyScanW(ord(key[0])) & 0xFF


# ---------------------------------------------------------------------------
# Main controller class
# ---------------------------------------------------------------------------

class InputController:
    """
    Thread-safe keyboard input controller.
    Uses the Interception kernel driver when available, otherwise SendInput.

    Keys are identified by interception-python string names:
      "a"–"z", "0"–"9", "space", "enter", "up", "down", "left", "right",
      "shift", "ctrl", "alt", "tab", "esc", "f1"–"f12", etc.
    """

    def __init__(self) -> None:
        self._use_interception = _INTERCEPTION_AVAILABLE

        if self._use_interception:
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

    def press_key(self, key: str, hold_ms: int = 50) -> None:
        """
        Press and release a key.

        Args:
            key:     Key name string understood by interception-python
                     e.g. "a", "space", "up", "enter", "f1".
            hold_ms: How long (ms) to hold the key down before releasing.
        """
        if self._use_interception:
            interception.key_down(key.lower())
            time.sleep(hold_ms / 1000.0)
            interception.key_up(key.lower())
        else:
            vk = _key_str_to_vk(key)
            _send_input_vk(vk, key_up=False)
            time.sleep(hold_ms / 1000.0)
            _send_input_vk(vk, key_up=True)

    def press_combo(self, keys: list[str], hold_ms: int = 50) -> None:
        """
        Press multiple keys simultaneously (e.g. ["shift", "a"]).
        All keys are pressed, held for hold_ms, then released in reverse order.
        """
        if self._use_interception:
            for k in keys:
                interception.key_down(k.lower())
            time.sleep(hold_ms / 1000.0)
            for k in reversed(keys):
                interception.key_up(k.lower())
        else:
            vks = [_key_str_to_vk(k) for k in keys]
            for vk in vks:
                _send_input_vk(vk, key_up=False)
            time.sleep(hold_ms / 1000.0)
            for vk in reversed(vks):
                _send_input_vk(vk, key_up=True)
