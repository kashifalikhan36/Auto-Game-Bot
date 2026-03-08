"""
Patches behaviors.py, rewrites config.json, and rewrites analyze.py
with all new MGS5 scenarios: obstacle recovery, cover-fight, D-Horse.
"""
import json, pathlib

# =============================================================================
# 1. behaviors.py -- add "keys" support inside _run_sequence
# =============================================================================

bh = pathlib.Path("nodes/behaviors.py")
src = bh.read_text(encoding="utf-8")

OLD_SEQ = (
    'def _run_sequence(ctrl: InputController, steps: list[dict]) -> None:\n'
    '    for step in steps:\n'
    '        if "mouse_click" in step:\n'
    '            _run_mouse_click(ctrl, step["mouse_click"], step.get("hold_ms", 80))\n'
    '        elif "mouse_move" in step:\n'
    '            mv = step["mouse_move"]\n'
    '            _run_mouse_move(ctrl, mv.get("dx", 0), mv.get("dy", 0), mv.get("steps", 12))\n'
    '        delay = step.get("delay_after_ms", 0)\n'
    '        if delay:\n'
    '            time.sleep(delay / 1000.0)\n'
)
NEW_SEQ = (
    'def _run_sequence(ctrl: InputController, steps: list[dict]) -> None:\n'
    '    """Execute a sequential list of steps: keys, mouse_click, or mouse_move."""\n'
    '    for step in steps:\n'
    '        if "keys" in step:\n'
    '            _run_keys(ctrl, step["keys"], step.get("hold_ms", 80))\n'
    '        elif "mouse_click" in step:\n'
    '            _run_mouse_click(ctrl, step["mouse_click"], step.get("hold_ms", 80))\n'
    '        elif "mouse_move" in step:\n'
    '            mv = step["mouse_move"]\n'
    '            _run_mouse_move(ctrl, mv.get("dx", 0), mv.get("dy", 0), mv.get("steps", 12))\n'
    '        delay = step.get("delay_after_ms", 0)\n'
    '        if delay:\n'
    '            time.sleep(delay / 1000.0)\n'
)

if OLD_SEQ in src:
    bh.write_text(src.replace(OLD_SEQ, NEW_SEQ, 1), encoding="utf-8")
    print("behaviors.py  patched OK (_run_sequence now handles keys steps)")
else:
    print("behaviors.py  SKIP (pattern not found -- may already be patched)")

# =============================================================================
# 2. config.json -- 45 named actions covering all scenarios
# =============================================================================

cfg = {
  "game_name": "Metal Gear Solid V: The Phantom Pain",
  "game_id": "metal_gear_5_the_phantom_pain",
  "description": "Full PC keyboard+mouse bindings for MGSV:TPP (PC default layout).",
  "game_context": (
      "Metal Gear Solid V: The Phantom Pain (MGS5/MGSV). "
      "You are Big Boss (Snake) on foot or riding D-Horse. "
      "Enemies wear military uniforms and carry weapons. Red ! means spotted. "
      "MOVEMENT: W=run forward, Shift+W=sprint, S=backward, A=strafe-left, D=strafe-right. "
      "STANCE: C toggles crouch/prone (lower profile, slower, recovers health when prone). "
      "DODGE: Space=quick dive forward. "
      "COMBAT: Right-Mouse=aim, Left-Mouse=shoot, R=reload. "
      "INTERACT: E=context action (mount horse, open door, pick up item -- only when prompt visible). "
      "D-HORSE: Hold Q then press 2 to call D-Horse to your location. "
      "When horse arrives, press E to mount. While riding: W=trot, Shift+W=gallop, "
      "move mouse to steer, press E again to dismount. "
      "OBSTACLE: If path is blocked by wall/fence, try vaulting (Shift+W+Space), "
      "then swing camera and move around it, or back up and reorient. "
      "COVER FIGHTING: Go crouch (C), peek out and shoot (RMB+LMB), duck back (C) -- repeat. "
      "Goal: eliminate visible enemies, navigate outposts, use D-Horse for open roads."
  ),

  "situation_list": ["EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"],

  "behaviors": {
      "EXPLORE": [[{"keys": ["shift", "w"], "hold_ms": 1500}]],
      "COMBAT":  [[{"sequence": [
          {"mouse_click": "right", "hold_ms": 150, "delay_after_ms": 60},
          {"mouse_click": "left",  "hold_ms": 100}
      ]}]],
      "EVADE":    [[{"keys": ["space"], "hold_ms": 120}]],
      "COVER":    [[{"keys": ["c"], "hold_ms": 150}]],
      "INTERACT": [[{"keys": ["e"], "hold_ms": 200}]],
      "IDLE":     []
  },

  "named_actions": {

    # ── FORWARD MOVEMENT ──────────────────────────────────────────────────────
    "SPRINT_FORWARD":   [{"keys": ["shift", "w"], "hold_ms": 1500}],
    "RUN_FORWARD":      [{"keys": ["w"],           "hold_ms": 900}],

    # ── BACKWARD / LATERAL ────────────────────────────────────────────────────
    "RUN_BACKWARD":     [{"keys": ["s"], "hold_ms": 700}],
    "STRAFE_LEFT":      [{"keys": ["a"], "hold_ms": 600}],
    "STRAFE_RIGHT":     [{"keys": ["d"], "hold_ms": 600}],

    # ── SPRINT + CAMERA (exploration, obstacle avoidance while running) ───────
    "SPRINT_LOOK_RIGHT": [
        {"keys": ["shift", "w"],    "hold_ms": 1300},
        {"mouse_move": {"dx":  90, "dy": 0, "steps": 20}}
    ],
    "SPRINT_LOOK_LEFT": [
        {"keys": ["shift", "w"],    "hold_ms": 1300},
        {"mouse_move": {"dx": -90, "dy": 0, "steps": 20}}
    ],
    "SPRINT_LOOK_UP": [
        {"keys": ["shift", "w"],    "hold_ms": 1200},
        {"mouse_move": {"dx": 0, "dy": -60, "steps": 18}}
    ],

    # ── RUN + CAMERA (slower, more control) ───────────────────────────────────
    "RUN_LOOK_RIGHT": [
        {"keys": ["w"], "hold_ms": 900},
        {"mouse_move": {"dx":  80, "dy": 0, "steps": 18}}
    ],
    "RUN_LOOK_LEFT": [
        {"keys": ["w"], "hold_ms": 900},
        {"mouse_move": {"dx": -80, "dy": 0, "steps": 18}}
    ],

    # ── CAMERA ONLY (scanning, peeking, adjusting view) ───────────────────────
    "LOOK_RIGHT_BIG": [{"mouse_move": {"dx":  160, "dy":  0,   "steps": 22}}],
    "LOOK_LEFT_BIG":  [{"mouse_move": {"dx": -160, "dy":  0,   "steps": 22}}],
    "LOOK_RIGHT":     [{"mouse_move": {"dx":   90, "dy":  0,   "steps": 18}}],
    "LOOK_LEFT":      [{"mouse_move": {"dx":  -90, "dy":  0,   "steps": 18}}],
    "LOOK_UP":        [{"mouse_move": {"dx":    0, "dy": -70,  "steps": 15}}],
    "LOOK_DOWN":      [{"mouse_move": {"dx":    0, "dy":  55,  "steps": 15}}],

    # ── CROUCH / PRONE ────────────────────────────────────────────────────────
    "CROUCH_TOGGLE":       [{"keys": ["c"],       "hold_ms": 100}],
    "CROUCH_RUN_FORWARD":  [
        {"keys": ["c"],       "hold_ms": 100},
        {"keys": ["w"],       "hold_ms": 700}
    ],

    # ── EVASION ───────────────────────────────────────────────────────────────
    "QUICK_DIVE":       [{"keys": ["space"],           "hold_ms": 120}],
    "EVADE_RIGHT": [
        {"keys": ["shift", "w"],                       "hold_ms": 700},
        {"mouse_move": {"dx":  130, "dy": 0, "steps": 20}}
    ],
    "EVADE_LEFT": [
        {"keys": ["shift", "w"],                       "hold_ms": 700},
        {"mouse_move": {"dx": -130, "dy": 0, "steps": 20}}
    ],
    "SPRINT_BACKWARD":  [{"keys": ["shift", "s"],      "hold_ms": 600}],

    # ── OBSTACLE RECOVERY ─────────────────────────────────────────────────────
    # Step 1: vault over low obstacles (sprint + dive forward)
    "VAULT_OBSTACLE": [
        {"keys": ["shift", "w", "space"], "hold_ms": 300}
    ],
    # Step 2: swing camera to find open route then sprint that way
    "UNSTICK_SWING_RIGHT": [
        {"mouse_move": {"dx":  150, "dy": 0, "steps": 22}},
        {"keys": ["shift", "w"],           "hold_ms": 800}
    ],
    "UNSTICK_SWING_LEFT": [
        {"mouse_move": {"dx": -150, "dy": 0, "steps": 22}},
        {"keys": ["shift", "w"],            "hold_ms": 800}
    ],
    # Step 3: back up, swing camera, then drive forward (sequential -- Worker-1)
    "BACK_AND_TURN_RIGHT": [{"sequence": [
        {"keys": ["s"],                              "hold_ms": 500, "delay_after_ms": 120},
        {"mouse_move": {"dx": 130, "dy": 0, "steps": 20},"delay_after_ms": 120},
        {"keys": ["w"],                              "hold_ms": 700}
    ]}],
    "BACK_AND_TURN_LEFT": [{"sequence": [
        {"keys": ["s"],                               "hold_ms": 500, "delay_after_ms": 120},
        {"mouse_move": {"dx": -130, "dy": 0, "steps": 20},"delay_after_ms": 120},
        {"keys": ["w"],                               "hold_ms": 700}
    ]}],

    # ── COMBAT ────────────────────────────────────────────────────────────────
    "AIM_SHOOT": [{"sequence": [
        {"mouse_click": "right", "hold_ms": 150, "delay_after_ms": 60},
        {"mouse_click": "left",  "hold_ms": 100}
    ]}],
    "AIM_BURST": [{"sequence": [
        {"mouse_click": "right", "hold_ms": 150, "delay_after_ms": 60},
        {"mouse_click": "left",  "hold_ms": 100},
        {"mouse_click": "left",  "hold_ms": 100, "delay_after_ms": 70},
        {"mouse_click": "left",  "hold_ms": 100}
    ]}],
    "AIM_SHOOT_STRAFE_RIGHT": [
        {"sequence": [
            {"mouse_click": "right", "hold_ms": 150, "delay_after_ms": 60},
            {"mouse_click": "left",  "hold_ms": 100}
        ]},
        {"keys": ["d"], "hold_ms": 450}
    ],
    "AIM_SHOOT_STRAFE_LEFT": [
        {"sequence": [
            {"mouse_click": "right", "hold_ms": 150, "delay_after_ms": 60},
            {"mouse_click": "left",  "hold_ms": 100}
        ]},
        {"keys": ["a"], "hold_ms": 450}
    ],

    # ── COVER-FIGHT TACTICS ───────────────────────────────────────────────────
    # Peek out, fire, duck back into cover (sequential)
    "PEEK_SHOOT_COVER": [{"sequence": [
        {"mouse_click": "right", "hold_ms": 200, "delay_after_ms": 80},
        {"mouse_click": "left",  "hold_ms": 100, "delay_after_ms": 200},
        {"keys": ["c"],          "hold_ms": 80}
    ]}],
    # Aim + 3 shots + back to crouch
    "COVER_BURST_COVER": [{"sequence": [
        {"mouse_click": "right", "hold_ms": 200, "delay_after_ms": 80},
        {"mouse_click": "left",  "hold_ms": 100, "delay_after_ms": 60},
        {"mouse_click": "left",  "hold_ms": 100, "delay_after_ms": 60},
        {"mouse_click": "left",  "hold_ms": 100, "delay_after_ms": 200},
        {"keys": ["c"],          "hold_ms": 80}
    ]}],
    # Stay crouched / press C to ensure crouched
    "STAY_IN_COVER": [{"keys": ["c"], "hold_ms": 200}],

    # ── WEAPON MANAGEMENT ─────────────────────────────────────────────────────
    "RELOAD_WEAPON": [{"keys": ["r"], "hold_ms": 100}],

    # ── INTERACT ──────────────────────────────────────────────────────────────
    "INTERACT": [{"keys": ["e"], "hold_ms": 200}],

    # ── BINOCULARS ────────────────────────────────────────────────────────────
    "USE_BINOCULARS": [{"keys": ["f"], "hold_ms": 1200}],

    # ── D-HORSE MECHANICS ─────────────────────────────────────────────────────
    # Call D-Horse: hold Q (radio menu) → press 2 to select horse
    "CALL_HORSE": [{"sequence": [
        {"keys": ["q"], "hold_ms": 900, "delay_after_ms": 200},
        {"keys": ["2"], "hold_ms": 150}
    ]}],
    # Mount when horse is next to you / Dismount when already riding
    "MOUNT_DISMOUNT_HORSE": [{"keys": ["e"], "hold_ms": 200}],
    # Riding actions
    "HORSE_TROT_FORWARD":   [{"keys": ["w"],           "hold_ms": 1200}],
    "HORSE_GALLOP_FORWARD": [{"keys": ["shift", "w"],  "hold_ms": 1500}],
    "HORSE_RIDE_RIGHT": [
        {"keys": ["shift", "w"],                       "hold_ms": 1200},
        {"mouse_move": {"dx":  80, "dy": 0, "steps": 18}}
    ],
    "HORSE_RIDE_LEFT": [
        {"keys": ["shift", "w"],                       "hold_ms": 1200},
        {"mouse_move": {"dx": -80, "dy": 0, "steps": 18}}
    ],
    "HORSE_SLOW_STOP": [{"keys": ["s"], "hold_ms": 400}],

    # ── DO NOTHING ────────────────────────────────────────────────────────────
    "DO_NOTHING": []
  },

  "named_action_descriptions": {
    "SPRINT_FORWARD":         "Shift+W -- sprint straight ahead. Path is clear, no enemies or obstacles.",
    "RUN_FORWARD":            "W -- run forward carefully. Use in semi-open areas or when approaching an area.",
    "RUN_BACKWARD":           "S -- run backward. Retreat slightly while keeping eyes on an enemy.",
    "STRAFE_LEFT":            "A -- sidestep left. Step around an obstacle or wall on the right side.",
    "STRAFE_RIGHT":           "D -- sidestep right. Step around an obstacle or wall on the left side.",
    "SPRINT_LOOK_RIGHT":      "Shift+W + camera right -- sprint and pan right. Curve right or scan right while running.",
    "SPRINT_LOOK_LEFT":       "Shift+W + camera left -- sprint and pan left. Curve left or scan left while running.",
    "SPRINT_LOOK_UP":         "Shift+W + tilt up -- sprint and check high ground, windows, or rooftops.",
    "RUN_LOOK_RIGHT":         "W + camera right -- run and pan right slowly. Controlled movement around right-side obstacle.",
    "RUN_LOOK_LEFT":          "W + camera left -- run and pan left slowly. Controlled movement around left-side obstacle.",
    "LOOK_RIGHT_BIG":         "BIG camera sweep RIGHT 160px -- use when wall blocks path, sweep to find open space on right.",
    "LOOK_LEFT_BIG":          "BIG camera sweep LEFT 160px -- use when wall blocks path, sweep to find open space on left.",
    "LOOK_RIGHT":             "Camera pan right 90px -- peek right from cover, scan right for enemies, adjust view.",
    "LOOK_LEFT":              "Camera pan left 90px -- peek left from cover, scan left for enemies, adjust view.",
    "LOOK_UP":                "Tilt camera up -- check rooftops, windows, high ground, elevated enemies.",
    "LOOK_DOWN":              "Tilt camera down -- check ground ahead, look for prone enemies or items.",
    "CROUCH_TOGGLE":          "C -- toggle crouch/prone. Hide behind cover, lower profile, recover health while prone.",
    "CROUCH_RUN_FORWARD":     "C then W -- crouch and move forward stealthily. Use in open areas with distant enemies.",
    "QUICK_DIVE":             "Space -- emergency dive/roll. Use ONLY when bullets are hitting near Snake or enemy is firing.",
    "EVADE_RIGHT":            "Shift+W + hard camera right -- sprint away breaking contact to the right.",
    "EVADE_LEFT":             "Shift+W + hard camera left -- sprint away breaking contact to the left.",
    "SPRINT_BACKWARD":        "Shift+S -- sprint backward. Create distance from a close enemy.",
    "VAULT_OBSTACLE":         "Shift+W+Space -- sprint-vault over a low wall, fence, or rock. Use when path is blocked by a low obstacle.",
    "UNSTICK_SWING_RIGHT":    "Camera 150px right + sprint -- swing view to find open route right then sprint that way. Use when stuck against a wall with open space on right.",
    "UNSTICK_SWING_LEFT":     "Camera 150px left + sprint -- swing view to find open route left then sprint that way. Use when stuck against a wall with open space on left.",
    "BACK_AND_TURN_RIGHT":    "S back up + camera right + W -- back away from wall, reorient camera right, move forward again. Use when totally stuck.",
    "BACK_AND_TURN_LEFT":     "S back up + camera left + W -- back away from wall, reorient camera left, move forward again. Use when totally stuck.",
    "AIM_SHOOT":              "RMB aim + LMB fire once -- single shot at clearly visible enemy.",
    "AIM_BURST":              "RMB aim + LMB fire 3x -- burst fire at stationary or close-range enemy.",
    "AIM_SHOOT_STRAFE_RIGHT": "Fire + strafe D right -- shoot enemy while sidestepping right to dodge return fire.",
    "AIM_SHOOT_STRAFE_LEFT":  "Fire + strafe A left -- shoot enemy while sidestepping left to dodge return fire.",
    "PEEK_SHOOT_COVER":       "RMB aim + LMB fire + C crouch -- peek out of cover, fire once at enemy, immediately duck back. Best for single-shot cover fighting.",
    "COVER_BURST_COVER":      "Aim + fire 3 shots + C crouch -- pop out and dump max damage then return to cover. Use on close or stationary enemies.",
    "STAY_IN_COVER":          "C -- press to stay/go prone/crouch. Use when enemy is actively shooting and you need to stay behind cover to recover health.",
    "RELOAD_WEAPON":          "R -- reload. Use ONLY when ammo counter shows 0 or magazine is critically low.",
    "INTERACT":               "E -- context action. Use ONLY when on-screen E prompt is visible near object, door, or NPC.",
    "USE_BINOCULARS":         "Hold F -- equip binoculars to scout and tag enemies. Use in safe open areas before approaching.",
    "CALL_HORSE":             "Hold Q + press 2 -- radio D-Horse to your location. Use when on open road with no immediate threats and no horse visible.",
    "MOUNT_DISMOUNT_HORSE":   "E -- mount D-Horse when standing next to it. Press E again to dismount when already riding.",
    "HORSE_TROT_FORWARD":     "W while riding -- trot forward on horseback. Use for careful horse movement.",
    "HORSE_GALLOP_FORWARD":   "Shift+W while riding -- gallop at full speed on horseback. Use on open straight roads.",
    "HORSE_RIDE_RIGHT":       "Shift+W + camera right while riding -- gallop and steer horse to the right.",
    "HORSE_RIDE_LEFT":        "Shift+W + camera left while riding -- gallop and steer horse to the left.",
    "HORSE_SLOW_STOP":        "S while riding -- slow down or stop D-Horse. Use when approaching enemy area.",
    "DO_NOTHING":             "No input. Use ONLY during cutscenes, loading screens, menus, or dialogues when Snake cannot move."
  },

  "action_list": ["EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"],
  "action_descriptions": {
    "EXPLORE":  "No enemies visible -- move and scan",
    "COMBAT":   "Enemy visible -- aim and shoot",
    "EVADE":    "Taking fire -- dodge or sprint away",
    "COVER":    "Enemy nearby -- crouch and peek",
    "INTERACT": "Prompt on screen -- press E",
    "IDLE":     "Cutscene/menu -- no input"
  },
  "key_map": {
    "EXPLORE": None, "COMBAT": None, "EVADE": None,
    "COVER": None,   "INTERACT": None, "IDLE": None
  }
}

out = pathlib.Path("games_config/metal_gear_5_the_phantom_pain/config.json")
out.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"config.json   written OK ({len(cfg['named_actions'])} named actions, {out.stat().st_size} bytes)")

# =============================================================================
# 3. nodes/analyze.py -- comprehensive decision logic
# =============================================================================

ANALYZE = '''\
"""
Analyze node -- sends the current screenshot to an LLM vision model and has
the AI pick a SPECIFIC KEY ACTION to execute RIGHT NOW in MGS5.

Scenarios covered:
  - Normal exploration / movement
  - Combat: shoot, burst, strafe-fire
  - Cover fighting: peek-shoot-cover cycle
  - Evading gunfire: dive, sprint away
  - Obstacle recovery: vault, camera swing, back-and-turn
  - D-Horse: call, mount, ride, dismount
  - Interact (E prompt visible)
  - Idle (cutscene / menu)

Providers: azure, openai, gemini, anthropic
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

import config
from state import BotState

# ---------------------------------------------------------------------------
# LLM client
# ---------------------------------------------------------------------------
_llm: Any = None


def _create_llm() -> Any:
    provider = config.ACTIVE_PROVIDER
    if provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            max_tokens=config.MAX_TOKENS,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            max_output_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=config.ANTHROPIC_API_KEY,
            model=config.ANTHROPIC_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )
    raise RuntimeError(f"[analyze] Unknown provider \'{provider}\'")


def _get_llm() -> Any:
    global _llm
    if _llm is None:
        _llm = _create_llm()
    return _llm


# ---------------------------------------------------------------------------
# Situation mapper
# ---------------------------------------------------------------------------

def _action_to_situation(action: str) -> str:
    a = action.upper()
    if any(x in a for x in ("AIM", "SHOOT", "BURST", "RELOAD")):
        return "COMBAT"
    if any(x in a for x in ("QUICK_DIVE", "EVADE", "SPRINT_BACKWARD")):
        return "EVADE"
    if any(x in a for x in ("LOOK_RIGHT", "LOOK_LEFT", "LOOK_UP", "LOOK_DOWN",
                              "CROUCH", "PRONE", "PEEK", "COVER")):
        return "COVER"
    if action == "INTERACT":
        return "INTERACT"
    if action == "DO_NOTHING":
        return "IDLE"
    return "EXPLORE"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    descriptions: dict = getattr(config, "NAMED_ACTION_DESCRIPTIONS", {})
    game_ctx: str      = getattr(config, "GAME_CONTEXT", "")

    lines = [
        "You are an AI agent controlling a real video game character in REAL TIME.",
        "You receive a screenshot every few seconds and MUST pick ONE action to execute NOW.",
        "Your choice is immediately sent as real keyboard and mouse input.",
        "",
    ]
    if game_ctx:
        lines += ["=== GAME INFO ===", game_ctx, ""]

    lines += ["=== AVAILABLE ACTIONS -- pick EXACTLY ONE ===", ""]
    for name in named_actions:
        desc = descriptions.get(name, "")
        lines.append(f"  {name}")
        if desc:
            lines.append(f"    {desc}")
    lines.append("")

    lines += [
        "=== DECISION RULES (apply TOP TO BOTTOM -- choose the FIRST matching rule) ===",
        "",

        "RULE 1 -- AMMO EMPTY [highest urgency for weapon]:",
        "  HUD ammo counter shows 0 or weapon is empty",
        "  => RELOAD_WEAPON",
        "",

        "RULE 2 -- ENEMY CLEARLY VISIBLE (enemy body on screen right now):",
        "  Enemy stationary or at close range",
        "  => AIM_BURST",
        "  Enemy moving or at medium range",
        "  => AIM_SHOOT",
        "  Enemy on your right -- sidestep left while firing",
        "  => AIM_SHOOT_STRAFE_LEFT",
        "  Enemy on your left -- sidestep right while firing",
        "  => AIM_SHOOT_STRAFE_RIGHT",
        "",

        "RULE 3 -- TAKING FIRE / COVER FIGHTING (enemy shooting at Snake):",
        "  Snake is being shot at and NOT yet in cover:",
        "  => STAY_IN_COVER  (press C immediately to crouch/prone behind cover)",
        "  Snake is crouched/prone in cover and enemy is still shooting:",
        "    Enemy close or stationary => COVER_BURST_COVER  (aim+3shots+crouch back)",
        "    Enemy far or moving       => PEEK_SHOOT_COVER   (aim+1shot+crouch back)",
        "  After shooting, enemy keeps firing -- stay low:",
        "  => STAY_IN_COVER",
        "  Health is critically low while under fire:",
        "  => CROUCH_RUN_FORWARD  (crawl away to break line of sight)",
        "",

        "RULE 4 -- EMERGENCY DODGE (bullets/explosion VERY close, red screen flash):",
        "  => QUICK_DIVE",
        "  Then immediately:",
        "  => EVADE_RIGHT   OR   EVADE_LEFT   (sprint away from the source of fire)",
        "",

        "RULE 5 -- STUCK ON OBSTACLE / WALL (path blocked, same wall filling screen):",
        "  Step A: Try to vault over a low wall/fence/rock",
        "  => VAULT_OBSTACLE  (Shift+W+Space -- sprint and jump)",
        "  Step B: Still blocked -- open space visible on the RIGHT",
        "  => UNSTICK_SWING_RIGHT  (sweep camera right 150px then sprint)",
        "  Step B: Still blocked -- open space visible on the LEFT",
        "  => UNSTICK_SWING_LEFT   (sweep camera left 150px then sprint)",
        "  Step C: Completely stuck -- back up and reorient",
        "     Open route appears to be on the RIGHT after backing up",
        "  => BACK_AND_TURN_RIGHT  (S + camera right + W)",
        "     Open route appears to be on the LEFT after backing up",
        "  => BACK_AND_TURN_LEFT   (S + camera left + W)",
        "  Signs you are STUCK: wall/fence fills the frame, no progress after 2+ W presses.",
        "",

        "RULE 6 -- INTERACT PROMPT VISIBLE (E icon on screen):",
        "  An on-screen prompt with E key icon near object / door / NPC",
        "  => INTERACT",
        "",

        "RULE 7 -- YELLOW ALERT / STEALTH (enemy searching, not yet shooting):",
        "  Yellow ! or enemy patrol searching -- hide immediately",
        "  => CROUCH_TOGGLE  (press C to crouch/prone -- recovers health)",
        "  Need to peek at the situation without fully exposing Snake",
        "  => LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
        "",

        "RULE 8 -- D-HORSE RIDING (currently ON horseback -- horse body/neck visible in view, riding HUD shown):",
        "  Road ahead is straight and clear",
        "  => HORSE_GALLOP_FORWARD",
        "  Road curves to the RIGHT",
        "  => HORSE_RIDE_RIGHT",
        "  Road curves to the LEFT",
        "  => HORSE_RIDE_LEFT",
        "  Approaching an enemy area or tight passage -- slow down",
        "  => HORSE_SLOW_STOP",
        "  Need to dismount (entering combat / tight area on foot)",
        "  => MOUNT_DISMOUNT_HORSE  (press E to get off)",
        "",

        "RULE 9 -- D-HORSE AVAILABLE NEARBY (horse standing close, not yet mounted):",
        "  D-Horse is visible on screen within reach",
        "  => MOUNT_DISMOUNT_HORSE  (press E to mount)",
        "",

        "RULE 10 -- CALL D-HORSE (on open road, no enemies nearby, no horse visible):",
        "  Snake is on an open road or wide flat area, safe, no horse in sight",
        "  => CALL_HORSE  (hold Q + press 2 to radio for D-Horse delivery)",
        "",

        "RULE 11 -- SCOUT UNKNOWN AREA (limited view, can\'t see what is ahead):",
        "  Cannot see what is around a corner or over a ridge -- scan first",
        "  => USE_BINOCULARS  (hold F to scout and tag enemies safely)",
        "  OR pan the camera to see:",
        "  => LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
        "",

        "RULE 12 -- EXPLORE / MOVE (default -- no immediate threats):",
        "  Clear path straight ahead, no enemies, no obstacles",
        "  => SPRINT_FORWARD",
        "  Path curves or you want to scan while running",
        "  => SPRINT_LOOK_RIGHT   OR   SPRINT_LOOK_LEFT   OR   SPRINT_LOOK_UP",
        "  Narrow passage or cautious movement needed",
        "  => RUN_FORWARD   OR   RUN_LOOK_RIGHT   OR   RUN_LOOK_LEFT",
        "  Need to step around something small",
        "  => STRAFE_LEFT   OR   STRAFE_RIGHT",
        "",

        "RULE 13 -- DO NOTHING [lowest priority]:",
        "  Cutscene playing / loading screen / in-game menu / dialogue box",
        "  => DO_NOTHING",
        "",

        "=== CRITICAL CONSTRAINTS ===",
        "* NEVER pick DO_NOTHING if Snake can move freely on foot or horseback.",
        "* NEVER pick INTERACT unless the E prompt icon is literally visible on screen NOW.",
        "* NEVER pick AIM_SHOOT / AIM_BURST unless an enemy body is CLEARLY visible.",
        "* NEVER pick CALL_HORSE if already riding or if enemies are nearby.",
        "* NEVER stand still in the open with a clear path -- always move.",
        "* If you picked the same action 3+ times in a row and nothing changed, pick a different one from the same rule.",
        "",

        "=== OUTPUT FORMAT ===",
        "Respond with EXACTLY ONE word -- the action name. No punctuation, no explanation.",
    ]
    return "\\n".join(lines)


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    lines: list[str] = []

    if recent:
        lines.append("Recent actions (oldest->newest): " + " -> ".join(recent))

    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        last = recent[-1]
        if not any(x in last for x in ("AIM", "SHOOT", "BURST")):
            lines.append(
                f"WARNING: \'{last}\' chosen {len(recent)} times in a row. "
                "The situation has likely changed -- pick a DIFFERENT action."
            )

    lines.append(
        "Examine the screenshot carefully and answer these questions:\\n"
        "  1. Is an enemy body clearly visible? -> RULE 2\\n"
        "  2. Is Snake being shot at / under fire? -> RULE 3\\n"
        "  3. Is there a wall/fence blocking the path directly ahead? -> RULE 5\\n"
        "  4. Is Snake currently riding D-Horse (horse HUD visible)? -> RULE 8\\n"
        "  5. Is D-Horse standing nearby? -> RULE 9\\n"
        "  6. Is the E interact prompt on screen? -> RULE 6\\n"
        "  7. Is ammo counter at 0? -> RULE 1\\n"
        "  8. Is it a cutscene/menu/loading screen? -> RULE 13\\n"
        "  9. Otherwise -> RULE 12 (explore)\\n"
        "Output ONE action name."
    )

    return HumanMessage(content=[
        {"type": "text", "text": "\\n".join(lines)},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_jpeg}",
                "detail": "low",
            },
        },
    ])


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def analyze_node(state: BotState) -> BotState:
    """
    LangGraph node: LLM picks a specific key action from the named_actions menu.

    Returns updated state:
      chosen_action  -- exact action name (e.g. "AIM_SHOOT", "VAULT_OBSTACLE")
      situation      -- broad category derived from chosen_action
      action         -- same as chosen_action (display compat)
      recent_actions -- rolling window of last N actions
    """
    t0 = time.perf_counter()

    b64 = state.get("screenshot_b64", "")
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    default_action = "SPRINT_FORWARD" if named_actions else "EXPLORE"

    if not b64:
        sit = _action_to_situation(default_action)
        return {**state,
                "chosen_action": default_action,
                "situation": sit,
                "action": default_action}

    recent = list(state.get("recent_actions", []))
    llm    = _get_llm()

    messages = [
        SystemMessage(content=_get_system_prompt()),
        _build_user_message(b64, recent),
    ]
    response = llm.invoke(messages)

    raw: str = response.content.strip().upper()
    word = raw.split()[0] if raw else default_action

    if named_actions:
        chosen_action = word if word in named_actions else default_action
    else:
        situations: list[str] = getattr(
            config, "SITUATION_LIST",
            ["EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"]
        )
        chosen_action = word if word in situations else default_action

    situation = _action_to_situation(chosen_action)
    t1 = time.perf_counter()

    window = getattr(config, "RECENT_ACTIONS_WINDOW", 8)
    new_recent = (recent + [chosen_action])[-window:]

    updates: BotState = {
        "chosen_action": chosen_action,
        "situation":     situation,
        "action":        chosen_action,
        "recent_actions": new_recent,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
'''

ap = pathlib.Path("nodes/analyze.py")
ap.write_text(ANALYZE, encoding="utf-8")
print(f"analyze.py    written OK ({ap.stat().st_size} bytes)")
print()
print("All done!")
