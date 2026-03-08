# Developer Reference

This document covers the full architecture, code structure, and internal workings of Auto Game Bot. It is written for contributors and anyone who wants to understand how the system works or extend it.

---

## Overview

Auto Game Bot is a Python application that runs a continuous loop:

1. Capture a screenshot of the game window.
2. Send the screenshot to a vision AI model.
3. The model returns one action keyword (e.g. "MOVE_FORWARD", "ATTACK").
4. Send the corresponding key or mouse button to the OS at the kernel level.
5. Repeat.

The loop is implemented as a LangGraph state machine. Each step is a node in the graph. The graph runs on a shared state dict (`BotState`) that flows through every node each frame.

---

## Repository structure

```
Auto-Game-Bot/
|
|-- main.py                   Entry point. Game selection prompt, starts the graph.
|-- config.py                 All configuration loaded from .env. Provider resolution.
|-- graph.py                  LangGraph graph definition and compile step.
|-- state.py                  BotState TypedDict shared by all nodes.
|-- requirements.txt          Python dependencies.
|-- .env.example              Template for environment variables.
|-- .env                      Your local credentials (git-ignored).
|
|-- nodes/
|   |-- capture.py            Node 1: screenshot via dxcam, JPEG encode, base64.
|   |-- analyze.py            Node 2: call LLM vision API, parse action keyword.
|   |-- act.py                Node 3: translate action -> key/mouse via InputController.
|   |-- __init__.py
|
|-- driver/
|   |-- input_controller.py   Wrapper around Interception + SendInput fallback.
|   |-- __init__.py
|
|-- games_config/
|   |-- README.md             How to add a new game config.
|   |-- info.md               Short notes.
|   |-- metal_gear_5_the_phantom_pain/
|       |-- config.json       Machine-readable key bindings for MGSV:TPP.
|       |-- metal_gear_5_the_phantom_pain.md   Human-readable key reference.
|
|-- Interception/
|   |-- Install-Win11.ps1     Windows 11 installer (re-signs driver, test signing).
|   |-- Uninstall-Win11.ps1   Removes the driver and services.
|   |-- driver/               Raw .sys driver files.
|   |-- library/              C headers for the Interception C API.
|   |-- licenses/             Interception license.
|
|-- test_driver.py            Quick manual test for keyboard/mouse input.
```

---

## state.py

`BotState` is a `TypedDict` that every node reads from and writes to. It flows through the entire graph each frame.

| Field            | Type               | Description                              |
| ---------------- | ------------------ | ---------------------------------------- |
| `screenshot_b64` | `str`              | Base64-encoded JPEG of the current frame |
| `action`         | `str`              | Action keyword returned by the LLM       |
| `frame_count`    | `int`              | Total frames processed so far            |
| `recent_actions` | `list[str]`        | Last 3 actions, fed back into the prompt |
| `timing`         | `dict[str, float]` | Per-node timing in ms (debug only)       |

---

## graph.py

Defines the LangGraph `StateGraph`. The topology is:

```
capture --> analyze --> act --> [should_continue?]
                                    |         |
                              (limit hit)   (keep going)
                                  END       capture
```

`should_continue` is a conditional edge. It checks `config.MAX_FRAMES`. If `MAX_FRAMES` is 0 (default), the bot runs forever. If set to a positive integer, the bot stops after that many frames.

`compile_graph()` is called from `main.py` after the game config is loaded. It compiles and returns the runnable graph app.

---

## config.py

Loads all values from `.env` via `python-dotenv`.

**Provider resolution**

`_resolve_provider()` runs once at import time. It:

- Reads `LLM_PROVIDER` from the environment. If set, validates that the required credentials for that provider are present, then returns that provider name.
- If `LLM_PROVIDER` is not set, checks each provider in order (azure -> openai -> gemini -> anthropic) and returns the first one with full credentials.
- Raises `RuntimeError` with a clear message if no provider has credentials.

The resolved provider is stored in `config.ACTIVE_PROVIDER` (a string: `"azure"`, `"openai"`, `"gemini"`, or `"anthropic"`).

**Game config loading**

`load_game_config(config_path)` reads a `config.json` file and overwrites the module-level `ACTION_LIST` and `VK_MAP` globals. This must be called before `compile_graph()` because the graph nodes read these values at runtime.

**Key fields**

| Variable            | Default              | Description                               |
| ------------------- | -------------------- | ----------------------------------------- |
| `ACTIVE_PROVIDER`   | auto                 | Resolved LLM provider name                |
| `ACTIVE_MODEL_NAME` | depends              | Model name string for the active provider |
| `ACTION_LIST`       | 9 generic actions    | List of valid action keywords             |
| `VK_MAP`            | generic bindings     | Dict mapping action -> binding dict       |
| `CAPTURE_REGION`    | `(0, 0, 1920, 1080)` | Screen area to capture                    |
| `CAPTURE_RESIZE`    | `512`                | Square size to resize screenshot to       |
| `JPEG_QUALITY`      | `80`                 | JPEG encode quality                       |
| `MAX_TOKENS`        | `10`                 | Max tokens for LLM response               |
| `TEMPERATURE`       | `0.0`                | LLM sampling temperature                  |
| `KEY_HOLD_MS`       | `50`                 | How long a key is held before release     |
| `MAX_FRAMES`        | `0`                  | Frames to run (0 = infinite)              |

---

## nodes/capture.py

Uses `dxcam` (DXGI Desktop Duplication API) for screen capture. The camera is created once at module level and reused every frame to avoid DXGI session overhead.

Steps each frame:

1. `camera.get_latest_frame()` — blocks until a fresh frame arrives (no polling).
2. Resize to `CAPTURE_RESIZE x CAPTURE_RESIZE` with `cv2.resize`.
3. JPEG-encode with `cv2.imencode` at `JPEG_QUALITY`.
4. Base64-encode the JPEG bytes.
5. Store the result in `state["screenshot_b64"]`.

The camera target FPS is set to 60 at startup. `dxcam` handles frame pacing internally.

---

## nodes/analyze.py

Sends the current screenshot to the active LLM provider and parses the response.

**LLM factory**

`_create_llm()` instantiates the correct LangChain chat model based on `config.ACTIVE_PROVIDER`:

| Provider    | LangChain class          | Package                  |
| ----------- | ------------------------ | ------------------------ |
| `azure`     | `AzureChatOpenAI`        | `langchain-openai`       |
| `openai`    | `ChatOpenAI`             | `langchain-openai`       |
| `gemini`    | `ChatGoogleGenerativeAI` | `langchain-google-genai` |
| `anthropic` | `ChatAnthropic`          | `langchain-anthropic`    |

The LLM is created on first call and cached in `_llm`. Imports are deferred to inside `_create_llm()` so unused provider packages do not cause import errors if not installed.

Note: Azure GPT-5 Nano does not accept a `temperature` parameter. It is omitted for the `azure` provider. All others pass `config.TEMPERATURE`.

**Prompt**

The system prompt lists the valid actions from `config.ACTION_LIST` and instructs the model to return exactly one word. The prompt is built lazily (not at import time) so game config changes made by `load_game_config()` are reflected correctly.

The user message includes:

- The last 3 actions as context (to help the model avoid repeating the same action in a loop).
- The current screenshot as a base64 JPEG image URL with `"detail": "low"` for cheapest/fastest vision processing.

**Response parsing**

The raw response is uppercased and split on whitespace. The first word is taken. If it is not in `ACTION_LIST`, the bot falls back to `"IDLE"`.

---

## nodes/act.py

Translates the action string to a physical key or mouse button.

Reads `binding = config.VK_MAP.get(action)`. The binding is a dict:

```json
{ "type": "keyboard", "key": "w" }
{ "type": "mouse", "button": "left" }
```

Or `None` for `IDLE` — no input is sent.

Dispatches to `InputController.press_key()` or `InputController.click_mouse()`.

---

## driver/input_controller.py

Provides keyboard and mouse input at the kernel level via the Interception driver, with a transparent fallback to Win32 SendInput.

**Startup**

At import time, the module checks if both `keyboard` and `mouse` Windows kernel services are in `RUNNING` state using `sc.exe query`. If they are, it sets `_INTERCEPTION_AVAILABLE = True` and uses the Interception API. Otherwise it warns and falls back to SendInput.

**Interception path**

Uses `interception-python` v1.13.6 string-based API:

- Keyboard: `interception.key_down("w")` / `interception.key_up("w")`
- Mouse: `interception.mouse_down(MouseButton.LEFT)` / `interception.mouse_up(MouseButton.LEFT)`

Key strings match the names used by `interception-python` (lowercase, e.g. `"w"`, `"space"`, `"shift"`, `"up"`, `"esc"`).

**SendInput fallback**

For keyboard: uses `ctypes` to call `user32.SendInput` with `INPUT_KEYBOARD` structs and Windows virtual-key codes.

For mouse: uses `ctypes` to call `user32.SendInput` with `INPUT_MOUSE` structs and `MOUSEEVENTF_*` flags for left/right/middle button down and up.

**Key methods**

| Method                         | Description                                            |
| ------------------------------ | ------------------------------------------------------ |
| `press_key(key, hold_ms)`      | Press and release a keyboard key                       |
| `click_mouse(button, hold_ms)` | Click a mouse button (`"left"`, `"right"`, `"middle"`) |
| `driver_status()`              | Returns a dict describing active input path            |

---

## games_config system

Each game lives in its own subfolder under `games_config/`:

```
games_config/
  <game_id>/
    config.json               Machine-readable bindings (loaded by the bot)
    <game_id>.md              Human-readable key reference (for your own use)
```

**config.json schema**

```json
{
  "game_name": "Display name shown in the selection menu",
  "game_id": "folder_name_used_as_identifier",
  "description": "Optional description",
  "action_list": ["ACTION_A", "ACTION_B", "IDLE"],
  "key_map": {
    "ACTION_A": { "type": "keyboard", "key": "w" },
    "ACTION_B": { "type": "mouse", "button": "left" },
    "IDLE": null
  }
}
```

Valid `key` strings for keyboard bindings are the same names accepted by `interception-python`: single letters (`"a"` to `"z"`), digits (`"0"` to `"9"`), and named keys like `"space"`, `"shift"`, `"ctrl"`, `"alt"`, `"enter"`, `"esc"`, `"tab"`, `"up"`, `"down"`, `"left"`, `"right"`, `"f1"` through `"f12"`, etc.

Valid `button` strings for mouse: `"left"`, `"right"`, `"middle"`.

`main.py` scans the `games_config/` folder at startup with `_discover_game_configs()` and shows the menu automatically. No code changes are needed to add a game — just drop in a new subfolder with a valid `config.json`.

---

## main.py flow

```
main()
  |
  |- _discover_game_configs()    scan games_config/ subfolders
  |- _select_game()              show numbered menu, get user input
  |- config.load_game_config()   override ACTION_LIST + VK_MAP
  |- compile_graph()             build LangGraph app
  |
  |- MAX_FRAMES == 0             app.stream(state)   <- infinite loop
  |- MAX_FRAMES > 0              app.invoke(state)   <- run N frames, exit
```

Signal handlers for SIGINT and SIGTERM call `_shutdown()` for a clean exit (camera released, no hanging DXGI session).

---

## LLM provider support

Adding a new provider requires changes in two files:

1. **`config.py`** — add the new API key and model variables, update `_resolve_provider()` to detect them, add the model name to `ACTIVE_MODEL_NAME`.
2. **`nodes/analyze.py`** — add a new `if provider == "newprovider":` branch in `_create_llm()` that imports the LangChain integration and returns the chat model instance.

The rest of the code is provider-agnostic and does not need to change.

---

## Adding a new game

1. Create `games_config/<game_id>/config.json` following the schema above.
2. Optionally create `games_config/<game_id>/<game_id>.md` with a human-readable key table.
3. Run the bot. The new game appears in the selection menu automatically.

---

## Testing input without running the full bot

`test_driver.py` provides a standalone script that sends a few keystrokes and mouse clicks directly through `InputController`. Run it after installing the driver to confirm input injection works before starting the bot.

```
python test_driver.py
```

---

## Environment variables reference

| Variable                   | Required           | Default                      | Description                 |
| -------------------------- | ------------------ | ---------------------------- | --------------------------- |
| `LLM_PROVIDER`             | No                 | auto                         | Force a specific provider   |
| `AZURE_OPENAI_ENDPOINT`    | If using azure     | —                            | Azure resource URL          |
| `AZURE_OPENAI_API_KEY`     | If using azure     | —                            | Azure API key               |
| `AZURE_OPENAI_API_VERSION` | No                 | `2025-01-01-preview`         | Azure API version           |
| `AZURE_DEPLOYMENT_NAME`    | No                 | `gpt-5-nano`                 | Deployed model name         |
| `OPENAI_API_KEY`           | If using openai    | —                            | OpenAI API key              |
| `OPENAI_MODEL`             | No                 | `gpt-4o`                     | OpenAI model name           |
| `GEMINI_API_KEY`           | If using gemini    | —                            | Google Gemini API key       |
| `GEMINI_MODEL`             | No                 | `gemini-2.0-flash`           | Gemini model name           |
| `ANTHROPIC_API_KEY`        | If using anthropic | —                            | Anthropic API key           |
| `ANTHROPIC_MODEL`          | No                 | `claude-3-5-sonnet-20241022` | Anthropic model name        |
| `CAPTURE_X`                | No                 | `0`                          | Game window left edge       |
| `CAPTURE_Y`                | No                 | `0`                          | Game window top edge        |
| `CAPTURE_W`                | No                 | `1920`                       | Capture width in pixels     |
| `CAPTURE_H`                | No                 | `1080`                       | Capture height in pixels    |
| `CAPTURE_RESIZE`           | No                 | `512`                        | Screenshot resize dimension |
| `JPEG_QUALITY`             | No                 | `80`                         | JPEG encode quality (1-100) |
| `MAX_TOKENS`               | No                 | `10`                         | Max tokens in LLM response  |
| `LLM_TEMPERATURE`          | No                 | `0.0`                        | LLM sampling temperature    |
| `KEY_HOLD_MS`              | No                 | `50`                         | Key hold duration in ms     |
| `MAX_FRAMES`               | No                 | `0`                          | Frame limit (0 = infinite)  |
| `DEBUG_SHOW_FRAME`         | No                 | `false`                      | Show live preview window    |
| `DEBUG_TIMING`             | No                 | `false`                      | Print per-frame timings     |

---

## Dependencies

| Package                  | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `dxcam`                  | DXGI screen capture (fastest on Windows)               |
| `langchain`, `langgraph` | Agent graph framework                                  |
| `langchain-openai`       | Azure OpenAI + OpenAI providers                        |
| `langchain-google-genai` | Google Gemini provider                                 |
| `langchain-anthropic`    | Anthropic Claude provider                              |
| `opencv-python-headless` | Image resize and JPEG encode                           |
| `interception-python`    | Python bindings for the Interception driver            |
| `python-dotenv`          | Load `.env` into environment variables                 |
| `pywin32`                | Windows API bindings (required by interception-python) |
