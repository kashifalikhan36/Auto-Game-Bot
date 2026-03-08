# Game Configs

This folder contains per-game keyboard/mouse configurations for the Auto Game Bot.

## Folder Structure

```
games_config/
  README.md                          ← this file
  <game_id>/
    <game_id>.md                     ← human-readable key reference
    config.json                      ← machine-readable config loaded by the bot
```

## How to Add a New Game

1. Create a subfolder: `games_config/<game_id>/`
2. Copy an existing `config.json` and update:
   - `game_name`, `game_id`, `description`
   - `action_list` — the ONE-WORD action names the LLM will output
   - `key_map` — maps each action to a keyboard key or mouse button
3. Create a `<game_id>.md` documenting all bindings for reference.
4. Run `python main.py` — the game will appear in the selection menu automatically.

## config.json Schema

```jsonc
{
  "game_name": "Display Name", // shown in selection menu
  "game_id": "snake_case_id", // must match the folder name
  "description": "...",
  "action_list": ["ACTION_A", "ACTION_B", "IDLE"], // LLM will pick from these
  "key_map": {
    "ACTION_A": { "type": "keyboard", "key": "w" }, // key string
    "ACTION_B": { "type": "mouse", "button": "left" }, // left/right/middle
    "IDLE": null, // no input
  },
}
```

### Valid keyboard key strings

Single letters: `"a"` – `"z"`  
Numbers: `"0"` – `"9"`  
Special: `"space"`, `"enter"`, `"tab"`, `"esc"`, `"shift"`, `"ctrl"`, `"alt"`  
Arrows: `"up"`, `"down"`, `"left"`, `"right"`  
Function keys: `"f1"` – `"f12"`

### Valid mouse button strings

`"left"`, `"right"`, `"middle"`

## Available Games

| Game ID                       | Game Name                            |
| ----------------------------- | ------------------------------------ |
| metal_gear_5_the_phantom_pain | Metal Gear Solid V: The Phantom Pain |
