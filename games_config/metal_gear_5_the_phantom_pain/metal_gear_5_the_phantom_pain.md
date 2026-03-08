# Metal Gear Solid V: The Phantom Pain — PC Key Reference

> **Game ID:** `metal_gear_5_the_phantom_pain`  
> **Config file:** `games_config/metal_gear_5_the_phantom_pain/config.json`  
> **Platform:** PC (Steam / Microsoft Store)

This document lists every default PC key binding and maps each one to the
bot action name the LLM will output. Edit `config.json` if you have remapped
any keys inside the game.

---

## Bot Action List

The LLM will respond with **exactly one** of these words per frame:

```
MOVE_FORWARD  MOVE_BACKWARD  MOVE_LEFT  MOVE_RIGHT
SPRINT_TOGGLE  WALK_TOGGLE  CHANGE_STANCE  CONTEXT_ACTION  QUICK_DIVE
ZOOM_SWITCH  RELOAD  AIM  ATTACK  BINOCULARS  RADIO
LIGHTS_TOGGLE  PAUSE  IDROID  PLACE_MARKER  HELP
MENU_UP  MENU_DOWN  MENU_LEFT  MENU_RIGHT
SWITCH_TAB_LEFT  SWITCH_TAB_RIGHT
QUICK_PRIMARY  QUICK_SECONDARY  QUICK_SUPPORT  QUICK_ITEM
LIGHT_TOGGLE  SUPPRESSOR_TOGGLE
IDLE
```

---

## Key Bindings Reference

### Menu Selection

| Action | Default Key | Bot Action Name |
|--------|------------|-----------------|
| Move cursor up | `W` | `MENU_UP` |
| Move cursor down | `S` | `MENU_DOWN` |
| Move cursor right | `D` | `MENU_RIGHT` |
| Move cursor left | `A` | `MENU_LEFT` |
| Switch Tabs (Left) | `1` | `SWITCH_TAB_LEFT` |
| Switch Tabs (Right) | `3` | `SWITCH_TAB_RIGHT` |

---

### Player Controls (On Foot)

| Action | Default Key | Bot Action Name |
|--------|------------|-----------------|
| Move (run) forward | `W` | `MOVE_FORWARD` |
| Move (run) backward | `S` | `MOVE_BACKWARD` |
| Move (run) left | `A` | `MOVE_LEFT` |
| Move (run) right | `D` | `MOVE_RIGHT` |
| Switch between run/dash | `Shift` | `SPRINT_TOGGLE` |
| Switch between walk/run | `Ctrl` | `WALK_TOGGLE` |
| Change stance | `C` | `CHANGE_STANCE` |
| Context-sensitive action | `E` | `CONTEXT_ACTION` |
| Quick dive | `Space` | `QUICK_DIVE` |
| Switch Zoom | `V` | `ZOOM_SWITCH` |

---

### Player Controls (On Foot — Part 2)

| Action | Default Key | Bot Action Name |
|--------|------------|-----------------|
| Reload / pick up | `R` | `RELOAD` |
| Ready weapon (hold) | `Right Mouse Button` | `AIM` |
| Attack / CQC | `Left Mouse Button` | `ATTACK` |
| Binoculars (hold) | `F` | `BINOCULARS` |
| Radio | `Q` | `RADIO` |
| Turn lights ON/OFF (driving) | `X` | `LIGHTS_TOGGLE` |
| Pause | `Esc` | `PAUSE` |
| Open iDroid data device | `Tab` | `IDROID` |
| Place marker | `Middle Mouse Button` | `PLACE_MARKER` |
| Menu Controls (iDroid help) | `H` | `HELP` |

---

### Menu Controls (Selecting Weapons)

| Action | Default Key | Bot Action Name |
|--------|------------|-----------------|
| Quick change — primary weapon | `1` | `QUICK_PRIMARY` |
| Quick change — secondary weapon | `2` | `QUICK_SECONDARY` |
| Quick change — support item | `3` | `QUICK_SUPPORT` |
| Quick change — item | `4` | `QUICK_ITEM` |
| Move cursor up | `↑` | `MENU_UP` |
| Move cursor down | `↓` | `MENU_DOWN` |
| Move cursor right | `→` | `MENU_RIGHT` |
| Move cursor left | `←` | `MENU_LEFT` |
| Light ON/OFF | `T` | `LIGHT_TOGGLE` |
| Suppressor ON/OFF | `G` | `SUPPRESSOR_TOGGLE` |

---

## Input Type Summary

| Input Type | Actions |
|-----------|---------|
| **Keyboard** | All movement, stances, reload, radio, iDroid, zoom, menus, quick-change |
| **Mouse — Left Button** | `ATTACK` (shoot / CQC) |
| **Mouse — Right Button** | `AIM` (ready weapon) |
| **Mouse — Middle Button** | `PLACE_MARKER` |
| **No Input** | `IDLE` |

---

## Notes

- **AIM + ATTACK** are the most common combat pairing. The LLM should output
  `AIM` first then `ATTACK` on separate frames to simulate proper aiming before
  shooting, matching human behaviour.
- **SPRINT_TOGGLE** and **WALK_TOGGLE** are toggles, not holds — a single
  press switches the speed mode. The bot does not need to hold these.
- **BINOCULARS** is a *hold* in-game. If you want sustained binocular use,
  increase `KEY_HOLD_MS` in `.env` while that action is selected.
- **CONTEXT_ACTION** (`E`) covers multiple in-game behaviours (grabbing ledges,
  interrogating enemies, entering vehicles). Context is inferred by position.
- The `IDLE` action produces no input — use it when the LLM determines no
  immediate action is needed.

---

## Customising Key Maps

Open `config.json` and change the `"key"` value for any action:

```jsonc
// Example: remap RELOAD from R to X
"RELOAD": { "type": "keyboard", "key": "x" }
```

To remap a mouse button:
```jsonc
"ATTACK": { "type": "mouse", "button": "left" }
// Valid button values: "left", "right", "middle"
```

To disable an action entirely (no input sent):
```jsonc
"BINOCULARS": null
```
