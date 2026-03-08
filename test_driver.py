"""
Quick driver verification script.
Run this BEFORE main.py to confirm keypress injection works.
It will press and release the 'A' key once after a 3-second countdown.
Watch your cursor in a text editor to see the 'a' appear.

Usage:
    python test_driver.py
"""

import time

print("Focus a text editor window NOW.")
for i in range(3, 0, -1):
    print(f"  Pressing 'A' in {i}s …")
    time.sleep(1)

from driver.input_controller import InputController  # noqa: E402

ctrl = InputController()
ctrl.press_key("a", hold_ms=80)
print("Key pressed! Did 'a' appear? If yes, the input driver is working correctly.")
