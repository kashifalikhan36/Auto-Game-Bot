# Forza Horizon 5 — Key Reference

Default PC keyboard bindings. Profile: WASD Drive.
If you have remapped any controls in-game, edit `config.json` in this folder to match.

---

## Driving

| Action                  | Bot action name    | Key        |
| ----------------------- | ------------------ | ---------- |
| Accelerate              | ACCELERATE         | W          |
| Brake / Reverse (hold)  | BRAKE              | S          |
| Steer left              | STEER_LEFT         | A          |
| Steer right             | STEER_RIGHT        | D          |
| Shift up                | SHIFT_UP           | E          |
| Shift down              | SHIFT_DOWN         | Q          |
| Clutch                  | CLUTCH             | Left Shift |
| E-brake                 | EBRAKE             | Space      |
| Rewind                  | REWIND             | R          |
| Activate (confirm)      | ACTIVATE           | Enter      |
| Switch camera           | SWITCH_CAMERA      | Tab        |
| Toggle convertible roof | TOGGLE_CONVERTIBLE | G          |

---

## Camera / Look

| Action       | Bot action name | Key         |
| ------------ | --------------- | ----------- |
| Look left    | LOOK_LEFT       | Left Arrow  |
| Look right   | LOOK_RIGHT      | Right Arrow |
| Look back    | LOOK_BACK       | Down Arrow  |
| Look forward | LOOK_FORWARD    | Up Arrow    |

---

## HUD and Features

| Action                  | Bot action name    | Key       |
| ----------------------- | ------------------ | --------- |
| Map                     | MAP                | M         |
| Horn                    | HORN               | H         |
| Toggle mini leaderboard | TOGGLE_LEADERBOARD | L         |
| Photo mode              | PHOTO_MODE         | P         |
| Radio previous          | RADIO_PREV         | -         |
| Radio next              | RADIO_NEXT         | =         |
| Telemetry               | TELEMETRY          | T         |
| Telemetry previous      | TELEMETRY_PREV     | Page Down |
| Telemetry next          | TELEMETRY_NEXT     | Page Up   |

---

## Anna / Forza Link

| Action                     | Bot action name | Key |
| -------------------------- | --------------- | --- |
| Activate Anna              | ACTIVATE_ANNA   | C   |
| Forza Link                 | FORZA_LINK      | V   |
| Anna / Forza Link option 1 | ANNA_OPTION_1   | 1   |
| Anna / Forza Link option 2 | ANNA_OPTION_2   | 2   |
| Anna / Forza Link option 3 | ANNA_OPTION_3   | 3   |
| Anna / Forza Link option 4 | ANNA_OPTION_4   | 4   |

---

## Notes

- BRAKE and STEER_LEFT/RIGHT are digital keys. The bot taps them for a fixed hold duration (`KEY_HOLD_MS` in `.env`, default 50 ms). For smoother steering consider increasing `KEY_HOLD_MS` to 100-150 ms.
- CLUTCH is only relevant if you are using a manual with clutch transmission setting in-game.
- IDLE sends no input. The AI uses this when it judges no action is needed.
- The arrow keys (LOOK_LEFT/RIGHT/BACK/FORWARD) move the camera while driving, not the car.
