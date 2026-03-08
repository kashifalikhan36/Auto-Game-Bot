"""
Analyze node — sends the current screenshot to an LLM vision model
and returns a single action keyword (e.g. "JUMP", "LEFT", "IDLE").

Supported providers: azure, openai, gemini, anthropic
Active provider is chosen by config.ACTIVE_PROVIDER (auto-detected from .env).

Key latency choices:
  - detail="low"  : model processes a single 512-px tile (~85 tokens)
  - max_tokens=10 : stop generation immediately after the action word
  - Synchronous invoke (asyncio integration handled by LangGraph's astream)
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

import config
from state import BotState

# ---------------------------------------------------------------------------
# LLM client — created once on first use.
# ---------------------------------------------------------------------------
_llm: Any = None


def _create_llm() -> Any:
    """Instantiate the LangChain chat model for the active provider."""
    provider = config.ACTIVE_PROVIDER

    if provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            max_tokens=config.MAX_TOKENS,
            # temperature omitted: GPT-5 Nano only accepts its default value
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
# Prompt templates
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    """Build the system prompt dynamically from game config.
    Evaluated lazily so game configs loaded after import are reflected."""
    game_name: str = ""
    game_ctx: str = getattr(config, "GAME_CONTEXT", "")
    descriptions: dict = getattr(config, "ACTION_DESCRIPTIONS", {})

    # --- Build the action menu with descriptions ---
    action_lines = []
    for action in config.ACTION_LIST:
        desc = descriptions.get(action, "")
        if desc:
            action_lines.append(f"  {action}: {desc}")
        else:
            action_lines.append(f"  {action}")
    action_menu = "\n".join(action_lines)

    # --- Identify which actions exist for dynamic rule references ---
    available = set(config.ACTION_LIST)

    shoot          = next((a for a in ("AIM_SHOOT",)             if a in available), None)
    strafe_shoot_r = next((a for a in ("STRAFE_SHOOT_RIGHT",)    if a in available), None)
    strafe_shoot_l = next((a for a in ("STRAFE_SHOOT_LEFT",)     if a in available), None)
    cover          = next((a for a in ("TAKE_COVER", "CROUCH")   if a in available), None)
    sprint         = next((a for a in ("SPRINT_FORWARD",)        if a in available), None)
    sprint_look_r  = next((a for a in ("SPRINT_AND_LOOK_RIGHT",) if a in available), None)
    sprint_look_l  = next((a for a in ("SPRINT_AND_LOOK_LEFT",)  if a in available), None)
    move_look_r    = next((a for a in ("MOVE_AND_LOOK_RIGHT",)   if a in available), None)
    move_look_l    = next((a for a in ("MOVE_AND_LOOK_LEFT",)    if a in available), None)
    fwd            = next((a for a in ("MOVE_FORWARD",)          if a in available), None)
    dodge          = next((a for a in ("QUICK_DIVE", "DODGE")    if a in available), None)
    reload_        = next((a for a in ("RELOAD",)                if a in available), None)
    interact       = next((a for a in ("CONTEXT_ACTION", "INTERACT") if a in available), None)
    look_l         = next((a for a in ("LOOK_LEFT",)             if a in available), None)
    look_r         = next((a for a in ("LOOK_RIGHT",)            if a in available), None)

    # --- Build dynamic priority rules ---
    rules = []

    # Rule 1: enemy visible — shoot, optionally while strafing
    if shoot:
        strafe_opts = " / ".join(filter(None, [strafe_shoot_r, strafe_shoot_l]))
        if strafe_opts:
            rules.append(
                f"1. Enemy / hostile CLEARLY visible on screen right now → {shoot} to fire, "
                f"or {strafe_opts} to strafe while shooting"
            )
        else:
            rules.append(f"1. Enemy / hostile CLEARLY visible on screen right now → {shoot}")

    # Rule 2: cover when taking fire
    if cover and dodge:
        rules.append(
            f"2. Taking fire, bullets hitting nearby, or enemy about to shoot → "
            f"{dodge} to roll away or {cover} to crouch"
        )
    elif cover:
        rules.append(f"2. Taking fire or pinned down → {cover}")

    # Rule 3: interact prompt
    if interact:
        rules.append(f"3. On-screen interact prompt visible (door / item / NPC) → {interact}")

    # Rule 4: reload
    if reload_:
        rules.append(f"4. Ammo counter is low or weapon is empty → {reload_}")

    # Rule 5: movement combos — preferred for exploration
    combo_opts = " / ".join(filter(None, [sprint_look_r, sprint_look_l, move_look_r, move_look_l]))
    plain_move  = " / ".join(filter(None, [sprint, fwd]))
    if combo_opts:
        rules.append(
            f"5. No immediate threat — explore → {combo_opts} "
            f"(moves AND scans camera at the same time, highly preferred over standing still)"
        )
    elif plain_move:
        rules.append(f"5. No immediate threat — explore → {plain_move}")

    # Rule 6: pure look when already in cover and can't move
    if look_l or look_r:
        look_opts = " / ".join(filter(None, [look_l, look_r]))
        rules.append(f"6. In cover and not safe to move — scan the area → {look_opts}")

    rules.append("7. Otherwise → pick any movement action you haven't used in the last 3 frames")
    rules.append(
        "✗ DO NOT shoot when no enemy is visible — AIM alone without shooting wastes time\n"
        "✗ DO NOT stand still holding aim — always combine movement with actions\n"
        "✗ IDLE is ONLY valid during cutscenes, loading screens, or pause menus"
    )
    rules_text = "\n".join(rules)

    prompt = (
        "You are an AI agent directly controlling a video game character.\n"
        "Every decision you make is immediately executed as a real input.\n"
    )
    if game_ctx:
        prompt += f"\nGAME CONTEXT:\n{game_ctx}\n"

    prompt += (
        f"\nAVAILABLE ACTIONS (you must pick exactly one):\n{action_menu}\n"
        f"\nDECISION PRIORITY (apply top-to-bottom, pick the first rule that matches):\n{rules_text}\n"
        "\nOUTPUT FORMAT:\n"
        "Respond with EXACTLY ONE word — the action name. "
        "No punctuation, no explanation, no other text whatsoever."
    )
    return prompt


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    """Build a vision message with the current screenshot."""
    lines: list[str] = []

    # Recent action context
    if recent:
        lines.append(f"Recent actions (oldest → newest): {' → '.join(recent)}")

    # Active repeat-ban: if the last action repeats at the tail, forbid it
    if recent:
        last = recent[-1]
        streak = 0
        for a in reversed(recent):
            if a == last:
                streak += 1
            else:
                break
        if streak >= 2:
            lines.append(
                f"WARNING: You have chosen '{last}' {streak} times in a row. "
                f"You MUST pick a DIFFERENT action this turn."
            )

    lines.append(
        "Study the screenshot carefully: check for enemies, UI alerts, "
        "interact prompts, ammo levels, and terrain ahead. "
        "Apply the decision priority rules, then output ONE word — the action name."
    )

    return HumanMessage(
        content=[
            {"type": "text", "text": "\n".join(lines)},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_jpeg}",
                    "detail": "low",  # single 512-px tile — fast & cheap
                },
            },
        ]
    )


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def analyze_node(state: BotState) -> BotState:
    """
    LangGraph node: call the LLM with the current screenshot and get an action.

    Returns an updated state with:
      - action: uppercase action keyword
      - timing["analyze_ms"]: inference round-trip time (if DEBUG_TIMING)
    """
    t0 = time.perf_counter()

    b64 = state.get("screenshot_b64", "")
    if not b64:
        # No screenshot yet — default to IDLE
        return {**state, "action": "IDLE"}

    recent = list(state.get("recent_actions", []))
    llm = _get_llm()

    messages = [
        SystemMessage(content=_get_system_prompt()),
        _build_user_message(b64, recent),
    ]

    response = llm.invoke(messages)

    # Parse — strip whitespace, upper-case, validate against known actions
    raw: str = response.content.strip().upper()
    # Take only the first word in case the model outputs extra text
    action = raw.split()[0] if raw else "IDLE"
    if action not in config.ACTION_LIST:
        action = "IDLE"  # safe default for unrecognised outputs

    t1 = time.perf_counter()

    # Maintain a rolling window of recent actions (anti-repeat context)
    window = getattr(config, "RECENT_ACTIONS_WINDOW", 8)
    new_recent = (recent + [action])[-window:]

    updates: BotState = {
        "action": action,
        "recent_actions": new_recent,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
