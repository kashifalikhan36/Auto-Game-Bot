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


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    lines: list[str] = []

    if recent:
        lines.append("Recent actions (oldest->newest): " + " -> ".join(recent))

    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        last = recent[-1]
        if not any(x in last for x in ("AIM", "SHOOT", "BURST")):
            lines.append(
                f"WARNING: '{last}' chosen {len(recent)} times in a row. "
                "The situation has likely changed -- pick a DIFFERENT action."
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
