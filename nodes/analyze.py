"""
Analyze node -- sends the current screenshot to an LLM vision model and has
the AI pick a SPECIFIC KEY ACTION to execute RIGHT NOW.

The LLM sees the full list of named_actions from the game config and selects
exactly one per frame.  act_node forwards the choice to the behavior engine
which executes the matching key/mouse tracks simultaneously.

Supported providers: azure, openai, gemini, anthropic
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

import config
from state import BotState

# ---------------------------------------------------------------------------
# LLM client -- created once on first use.
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

    raise RuntimeError(f"[analyze] Unknown provider '{provider}'")


def _get_llm() -> Any:
    global _llm
    if _llm is None:
        _llm = _create_llm()
    return _llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _action_to_situation(action: str) -> str:
    """Map a named action back to a broad situation label for display/logging."""
    a = action.upper()
    if any(x in a for x in ("AIM", "SHOOT", "BURST", "RELOAD")):
        return "COMBAT"
    if any(x in a for x in ("QUICK_DIVE", "EVADE", "SPRINT_BACKWARD")):
        return "EVADE"
    if any(x in a for x in ("LOOK_RIGHT", "LOOK_LEFT", "LOOK_UP", "LOOK_DOWN",
                              "CROUCH", "PRONE", "PEEK")):
        return "COVER"
    if action == "INTERACT":
        return "INTERACT"
    if action == "DO_NOTHING":
        return "IDLE"
    return "EXPLORE"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    """Build the system prompt listing all named actions and decision rules."""
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    descriptions: dict = getattr(config, "NAMED_ACTION_DESCRIPTIONS", {})
    game_ctx: str = getattr(config, "GAME_CONTEXT", "")

    lines = [
        "You are an AI agent controlling a video game character in REAL TIME.",
        "You receive a screenshot every few seconds and must pick ONE action to perform.",
        "Your choice is immediately executed as real keyboard and mouse input.",
        "",
    ]

    if game_ctx:
        lines += ["== GAME INFO ==", game_ctx, ""]

    # Build the full action menu
    lines += ["== AVAILABLE ACTIONS (pick EXACTLY ONE) ==", ""]
    for name, desc in descriptions.items():
        if name in named_actions:
            lines.append(f"  {name}")
            lines.append(f"    {desc}")
    lines.append("")

    lines += [
        "== DECISION RULES — apply top to bottom, pick the FIRST rule that fits ==",
        "",
        "RULE 1 — RELOAD (highest urgency if ammo is 0):",
        "  Ammo counter on HUD shows 0 or magazine is empty",
        "  -> RELOAD_WEAPON",
        "",
        "RULE 2 — SHOOT ENEMY (enemy character clearly on screen right now):",
        "  Enemy standing still or moving slowly, clearly in front",
        "  -> AIM_BURST",
        "  Enemy moving, far away, or in cover",
        "  -> AIM_SHOOT",
        "  Enemy on your right side while shooting",
        "  -> AIM_SHOOT_STRAFE_LEFT  (sidestep left to stay out of their aim)",
        "  Enemy on your left side while shooting",
        "  -> AIM_SHOOT_STRAFE_RIGHT (sidestep right to stay out of their aim)",
        "",
        "RULE 3 — EVADE (bullets near you / red alert / Snake is taking damage):",
        "  Bullets or explosions very close to Snake",
        "  -> QUICK_DIVE",
        "  Enemy is chasing from behind or you need to break contact",
        "  -> EVADE_RIGHT   OR   EVADE_LEFT   OR   SPRINT_BACKWARD",
        "",
        "RULE 4 — CROUCH / HIDE (enemy alert cone nearby but enemy not shooting yet):",
        "  Yellow alert indicator visible / enemy searching / low health",
        "  -> CROUCH_TOGGLE  (press C to go prone/crouch — recovers health, lowers profile)",
        "  Need to peek at the situation from cover",
        "  -> LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
        "",
        "RULE 5 — INTERACT (on-screen prompt visible):",
        "  A button prompt with E icon appears near an object, door, or NPC",
        "  -> INTERACT",
        "",
        "RULE 6 — OBSTACLE / WALL BLOCKING PATH:",
        "  The path directly ahead is blocked by a wall, fence, or cliff edge:",
        "  a) FIRST try a big camera sweep to find the open route:",
        "     Open space on right -> LOOK_RIGHT_BIG  then  RUN_LOOK_RIGHT",
        "     Open space on left  -> LOOK_LEFT_BIG   then  RUN_LOOK_LEFT",
        "  b) If still blocked, sidestep around it:",
        "     -> STRAFE_LEFT  OR  STRAFE_RIGHT",
        "  c) If in a tight corridor, back up first:",
        "     -> RUN_BACKWARD",
        "",
        "RULE 7 — SCOUT unknown area (no enemies visible yet, limited view):",
        "  You can't see what's ahead or the path curves:",
        "  -> USE_BINOCULARS  (hold F to tag enemies before moving in)",
        "  OR pan the camera to look:",
        "  -> LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
        "",
        "RULE 8 — EXPLORE (default — path is clear, no immediate threats):",
        "  Clear path straight ahead, no enemies, no obstacles visible",
        "  -> SPRINT_FORWARD",
        "  Path curves or you want to scan while running:",
        "  -> SPRINT_LOOK_RIGHT   OR   SPRINT_LOOK_LEFT   OR   SPRINT_LOOK_UP",
        "  Narrow passage or need careful movement:",
        "  -> RUN_FORWARD   OR   RUN_LOOK_RIGHT   OR   RUN_LOOK_LEFT",
        "",
        "RULE 9 — DO NOTHING (lowest priority):",
        "  A cutscene is playing / loading screen / dialogue / in-game menu",
        "  -> DO_NOTHING",
        "",
        "== CRITICAL RULES ==",
        "* NEVER pick DO_NOTHING if Snake can move freely.",
        "* NEVER pick INTERACT unless the E prompt is literally on screen right now.",
        "* NEVER pick AIM_SHOOT or AIM_BURST unless an enemy character body is clearly visible.",
        "* NEVER stand still when there is an open path -- always move.",
        "* If the same action has been chosen 3 times in a row and the situation has NOT changed,",
        "  pick a different action from the same category.",
        "",
        "== OUTPUT FORMAT ==",
        "Respond with EXACTLY ONE word -- the action name from the list above.",
        "No punctuation, no explanation, nothing else.",
    ]
    return "\n".join(lines)


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    """Build the per-frame vision message."""
    lines: list[str] = []

    if recent:
        lines.append(f"Recent actions (oldest -> newest): {chr(32).join(f'{a}' for a in recent)}")

    # Warn if stuck in a loop
    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        last = recent[-1]
        if not any(x in last for x in ("AIM", "SHOOT", "BURST")):
            lines.append(
                f"WARNING: '{last}' chosen {len(recent)} times in a row. "
                "The situation must have changed -- pick a DIFFERENT action this frame."
            )

    lines.append(
        "Look at the screenshot carefully. Check for:\n"
        "  - Enemies (military uniforms, weapons) visible on screen? -> SHOOT rules\n"
        "  - Red ! alert / bullets nearby / Snake taking damage? -> EVADE rules\n"
        "  - E interact prompt visible? -> INTERACT\n"
        "  - Ammo counter at 0? -> RELOAD_WEAPON\n"
        "  - Wall or obstacle blocking the path ahead? -> OBSTACLE rules\n"
        "  - Open path ahead? -> EXPLORE rules\n"
        "  - Cutscene / loading / menu? -> DO_NOTHING\n"
        "Output ONE action name."
    )

    return HumanMessage(content=[
        {"type": "text", "text": "\n".join(lines)},
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
    LangGraph node: the LLM sees the screenshot and picks a specific key action.

    Returns updated state:
      - chosen_action  named action the LLM selected (e.g. "AIM_SHOOT")
      - situation      broad category derived from chosen_action (for display)
      - action         same as chosen_action (display/logging compat)
      - recent_actions rolling window of last N chosen actions
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
    llm = _get_llm()

    messages = [
        SystemMessage(content=_get_system_prompt()),
        _build_user_message(b64, recent),
    ]

    response = llm.invoke(messages)

    # Parse -- strip whitespace, upper-case, take first word
    raw: str = response.content.strip().upper()
    word = raw.split()[0] if raw else default_action

    # Validate against known named actions
    if named_actions:
        chosen_action = word if word in named_actions else default_action
    else:
        situations: list[str] = getattr(config, "SITUATION_LIST",
                                        ["EXPLORE", "COMBAT", "EVADE", "COVER", "INTERACT", "IDLE"])
        chosen_action = word if word in situations else default_action

    situation = _action_to_situation(chosen_action)

    t1 = time.perf_counter()

    window = getattr(config, "RECENT_ACTIONS_WINDOW", 8)
    new_recent = (recent + [chosen_action])[-window:]

    updates: BotState = {
        "chosen_action": chosen_action,
        "situation": situation,
        "action": chosen_action,
        "recent_actions": new_recent,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
