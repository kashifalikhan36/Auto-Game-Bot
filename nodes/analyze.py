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
    raise RuntimeError(f"[analyze] Unknown provider '{provider}'")


def _get_llm() -> Any:
    global _llm
    if _llm is None:
        _llm = _create_llm()
    return _llm


# ---------------------------------------------------------------------------
# Situation mapper
# ---------------------------------------------------------------------------

def _action_to_situation(action: str) -> str:
    """Map a named action to a broad situation label.
    Handles both FH5 and MGS5 action namespaces.
    """
    a = action.upper()

    # ── FH5 situations ──────────────────────────────────────────────────────
    if a == "DO_NOTHING":
        return "MENU"
    # Recovery/off-road checked FIRST (before generic THROTTLE / NUDGE matches)
    if any(x in a for x in ("OFFROAD", "ROAD_NUDGE", "ROAD_RETURN", "ROAD_RECOVER",
                             "UNSTICK", "REVERSE")):
        return "RECOVER"
    if any(x in a for x in ("DRIFT", "HANDBRAKE", "SPIN_RECOVER", "DRIFT_ZONE")):
        return "DRIFT"
    if any(x in a for x in ("FULL_THROTTLE", "THROTTLE", "DRAG", "SPEED_TRAP",
                             "SHIFT_UP", "SHIFT_DOWN")):
        return "RACING"
    if any(x in a for x in ("ACCEL_LEFT", "ACCEL_RIGHT", "CORNER", "BRAKE",
                             "OVERTAKE", "SWERVE", "NUDGE", "JUMP")):
        return "RACING"
    if a == "SPEED_TRAP_BLAST":
        return "STUNT"

    # ── MGS5 situations ─────────────────────────────────────────────────────
    if any(x in a for x in ("AIM", "SHOOT", "BURST", "RELOAD")):
        return "COMBAT"
    if any(x in a for x in ("QUICK_DIVE", "EVADE", "SPRINT_BACKWARD")):
        return "EVADE"
    if any(x in a for x in ("CROUCH", "PRONE", "PEEK", "COVER",
                             "LOOK_RIGHT", "LOOK_LEFT")):
        return "COVER"
    if a == "INTERACT":
        return "INTERACT"

    return "EXPLORE"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    descriptions: dict  = getattr(config, "NAMED_ACTION_DESCRIPTIONS", {})
    game_ctx: str       = getattr(config, "GAME_CONTEXT", "")
    rules: list[str]    = getattr(config, "DECISION_RULES", [])
    constraints: list[str] = getattr(config, "CONSTRAINTS", [])

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

    if rules:
        lines += ["=== DECISION RULES (apply TOP TO BOTTOM -- choose the FIRST matching rule) ===", ""]
        lines += rules
        lines.append("")

    if constraints:
        lines += ["=== CRITICAL CONSTRAINTS ==="]
        lines += constraints
        lines.append("")

    lines += [
        "=== OUTPUT FORMAT ===",
        "Respond with EXACTLY ONE word -- the action name. No punctuation, no explanation.",
    ]
    return "\n".join(lines)


def _build_user_message(b64_jpeg: str, recent: list[str],
                        recent_situations: list[str] | None = None) -> HumanMessage:
    lines: list[str] = []

    if recent:
        lines.append("Recent actions (oldest->newest): " + " -> ".join(recent))
    if recent_situations:
        lines.append("Recent situations: " + " -> ".join(recent_situations))

    if len(recent) >= 3:
        last = recent[-1]
        last_n = recent[-3:]

        # ── STUCK DETECTION (highest priority warning) ───────────────────────
        # Only "struggling" actions count -- OFFROAD_* and ROAD_NUDGE_* repeated
        # while not on a clear road.  Pure FULL_THROTTLE/ACCEL are normal racing;
        # they should NOT trigger the stuck alert.
        _struggling_set = {
            "OFFROAD_THROTTLE", "OFFROAD_LEFT", "OFFROAD_RIGHT", "OFFROAD_CAREFUL",
            "ROAD_NUDGE_LEFT", "ROAD_NUDGE_RIGHT",
            "ROAD_RETURN_LEFT", "ROAD_RETURN_RIGHT",
        }
        _reverse_set = {
            "UNSTICK_REVERSE", "UNSTICK_REVERSE_LEFT", "UNSTICK_REVERSE_RIGHT",
            "REVERSE", "REVERSE_LEFT", "REVERSE_RIGHT",
        }
        recent4 = recent[-4:]
        struggling = [a for a in recent4 if a in _struggling_set]
        rev_attempts = [a for a in recent4 if a in _reverse_set]
        # Also check if situation stayed RECOVER the whole time (truly stuck)
        stuck_via_situation = (
            recent_situations is not None
            and len(recent_situations) >= 3
            and all(s == "RECOVER" for s in recent_situations[-3:])
        )
        if len(struggling) >= 3 and not rev_attempts:
            lines.append(
                "*** STUCK ALERT ***: You have picked recovery/offroad actions "
                f"({', '.join(struggling)}) multiple times with no progress. "
                "The car is PHYSICALLY BLOCKED by a wall or tree -- throttle will NOT help. "
                "You MUST reverse to break free:\n"
                "  - Space to the LEFT behind the car  -> UNSTICK_REVERSE_LEFT\n"
                "  - Space to the RIGHT behind the car -> UNSTICK_REVERSE_RIGHT\n"
                "  - No clear direction               -> UNSTICK_REVERSE\n"
                "Do NOT pick any throttle, offroad, or nudge action until after reversing."
            )
        elif stuck_via_situation and not rev_attempts:
            lines.append(
                "*** STUCK ALERT ***: Situation has been RECOVER for 3+ frames. "
                "The car is not making forward progress. Reverse to escape:\n"
                "  UNSTICK_REVERSE_LEFT / UNSTICK_REVERSE_RIGHT / UNSTICK_REVERSE"
            )

        # ── Same action 3+ times in a row ────────────────────────────────────
        elif len(set(last_n)) == 1 and last not in _reverse_set:
            repeat_count = sum(1 for x in recent if x == last)
            lines.append(
                f"WARNING: '{last}' repeated {repeat_count} times in a row -- "
                "strategy is NOT working. Pick a DIFFERENT action. "
                "On a clear road: FULL_THROTTLE. Stuck against obstacle: UNSTICK_REVERSE_*."
            )

        # ── OFFROAD actions dominating a road race ────────────────────────────
        offroad_recent = [x for x in recent[-5:] if "OFFROAD" in x]
        if len(offroad_recent) >= 3:
            lines.append(
                "WARNING: OFFROAD_* chosen many times in a row. "
                "OFFROAD actions are ONLY for cross-country/dirt events. "
                "If tarmac road is visible ahead: pick FULL_THROTTLE. "
                "If off road beside a paved road: pick ROAD_RETURN_* or ROAD_NUDGE_*."
            )

        # ── NUDGE oscillation ─────────────────────────────────────────────────
        nudge_recent = [x for x in recent[-4:] if "NUDGE" in x]
        if len(nudge_recent) >= 3:
            lines.append(
                "WARNING: NUDGE actions alternating left/right -- this is oscillation. "
                "STOP nudging. Pick FULL_THROTTLE and drive straight. "
                "Only nudge again if a road EDGE is immediately beside the car."
            )

    checklist: list[str] = getattr(config, "SITUATION_CHECKLIST", [])
    if checklist:
        lines += checklist
    else:
        lines.append("Examine the screenshot and output ONE action name.")

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
    # Use the first named action as the default (game-agnostic fallback)
    default_action = next(iter(named_actions), "EXPLORE")

    if not b64:
        sit = _action_to_situation(default_action)
        return {**state,
                "chosen_action": default_action,
                "situation": sit,
                "action": default_action}

    recent = list(state.get("recent_actions", []))
    recent_situations = list(state.get("recent_situations", []))
    llm    = _get_llm()

    messages = [
        SystemMessage(content=_get_system_prompt()),
        _build_user_message(b64, recent, recent_situations),
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
    new_recent_situations = (recent_situations + [situation])[-window:]

    updates: BotState = {
        "chosen_action":      chosen_action,
        "situation":          situation,
        "action":             chosen_action,
        "recent_actions":     new_recent,
        "recent_situations":  new_recent_situations,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
