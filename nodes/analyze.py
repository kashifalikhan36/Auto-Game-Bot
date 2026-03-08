"""
Analyze node -- sends the current screenshot to an LLM vision model and has
the AI pick a SPECIFIC KEY ACTION (e.g. AIM_SHOOT, SPRINT_LOOK_RIGHT).

The LLM is shown the full named_actions menu from the game config and selects
exactly one action name per frame.  act_node then executes those tracks
(keyboard + mouse) directly via nodes/behaviors.py.

Supported providers: azure, openai, gemini, anthropic
Active provider is chosen by config.ACTIVE_PROVIDER (auto-detected from .env).
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
    """Derive a broad situation label from a named action for display/logging."""
    if any(x in action for x in ("AIM", "SHOOT", "BURST", "STRAFE")):
        return "COMBAT"
    if any(x in action for x in ("DIVE", "EVADE", "SPRINT_BACK")):
        return "EVADE"
    if any(x in action for x in ("PEEK", "CROUCH")):
        return "COVER"
    if action == "INTERACT_OBJECT":
        return "INTERACT"
    if action == "DO_NOTHING":
        return "IDLE"
    return "EXPLORE"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    """Build the system prompt that asks the LLM to pick a specific key action."""
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    descriptions: dict = getattr(config, "NAMED_ACTION_DESCRIPTIONS", {})
    game_ctx: str = getattr(config, "GAME_CONTEXT", "")

    lines = [
        "You are an AI agent directly controlling a video game character.",
        "You see a screenshot and decide which key action to perform RIGHT NOW.",
        "",
    ]
    if game_ctx:
        lines += [f"GAME: {game_ctx}", ""]

    lines += ["AVAILABLE KEY ACTIONS (choose exactly one):", ""]
    for name in named_actions:
        desc = descriptions.get(name, "")
        lines.append(f"  {name}: {desc}" if desc else f"  {name}")

    lines += [
        "",
        "DECISION RULES (apply top-to-bottom, pick the FIRST rule that matches):",
        "  1. Enemy clearly visible on screen RIGHT NOW",
        "     -> AIM_SHOOT / AIM_BURST / AIM_SHOOT_STRAFE_RIGHT / AIM_SHOOT_STRAFE_LEFT",
        "  2. Bullets incoming, taking fire, or enemy about to shoot",
        "     -> DIVE_DODGE / EVADE_SPRINT_RIGHT / EVADE_SPRINT_LEFT / SPRINT_BACK",
        "  3. Interact prompt visible on screen (door, item, NPC)",
        "     -> INTERACT_OBJECT",
        "  4. Enemy nearby but not clearly visible -- peek from cover",
        "     -> PEEK_RIGHT / PEEK_LEFT / PEEK_UP / CROUCH_PEEK_RIGHT / CROUCH_PEEK_LEFT",
        "  5. No immediate threat -- explore and move forward",
        "     -> SPRINT_FORWARD / SPRINT_LOOK_RIGHT / SPRINT_LOOK_LEFT"
        " / SPRINT_LOOK_UP_RIGHT / SPRINT_LOOK_UP_LEFT",
        "  6. Cutscene, menu, or loading screen -- do nothing",
        "     -> DO_NOTHING",
        "",
        "OUTPUT: Respond with EXACTLY ONE word -- the action name from the list above.",
        "No explanation, no punctuation, no other text whatsoever.",
    ]
    return "\n".join(lines)


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    """Build the per-frame vision message."""
    lines: list[str] = []

    if recent:
        lines.append(f"Recent actions (oldest -> newest): {' -> '.join(recent)}")

    # Warn if the same non-combat action repeated 3+ times
    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        last = recent[-1]
        if not any(x in last for x in ("AIM", "SHOOT", "BURST")):
            lines.append(
                f"WARNING: '{last}' chosen {len(recent)} times in a row. "
                "Pick a DIFFERENT action unless the screenshot clearly still demands it."
            )

    lines.append(
        "Study the screenshot carefully: are enemies visible? Taking fire? "
        "Interact prompt on screen? Loading screen or cutscene? "
        "Apply the decision rules and output ONE action name."
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

    Returns updated state with:
      - chosen_action: named action the LLM selected (e.g. "AIM_SHOOT", "SPRINT_LOOK_RIGHT")
      - situation: broad category derived from chosen_action (for display)
      - action: same as chosen_action (display/logging compat)
      - recent_actions: rolling window of last N chosen actions
    """
    t0 = time.perf_counter()

    b64 = state.get("screenshot_b64", "")
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    default_action = "SPRINT_FORWARD" if named_actions else "EXPLORE"

    if not b64:
        sit = _action_to_situation(default_action)
        return {**state, "chosen_action": default_action, "situation": sit, "action": default_action}

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

    # Validate: must be a known named action
    if named_actions:
        chosen_action = word if word in named_actions else default_action
    else:
        # Fallback: validate against situation list
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
