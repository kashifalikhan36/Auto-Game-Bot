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
    """Build the system prompt with game context and the current ACTION_LIST.
    Evaluated lazily so game configs loaded after import are reflected."""
    action_str = ", ".join(config.ACTION_LIST)
    game_ctx: str = getattr(config, "GAME_CONTEXT", "")

    prompt = "You are an AI agent controlling a video game character via keyboard and mouse.\n"
    if game_ctx:
        prompt += f"Game context: {game_ctx}\n\n"

    prompt += (
        "Analyse the screenshot and choose the SINGLE best action to take RIGHT NOW.\n\n"
        "Strategy rules:\n"
        "- Enemies visible on screen → AIM_SHOOT or AIM then TAKE_COVER.\n"
        "- Alert/danger (red UI elements, gunfire) → SPRINT_FORWARD to escape or TAKE_COVER.\n"
        "- Open ground, no threats → SPRINT_FORWARD or MOVE_FORWARD to explore.\n"
        "- Haven't looked around recently → LOOK_LEFT or LOOK_RIGHT to survey.\n"
        "- Interact prompt visible → CONTEXT_ACTION.\n"
        "- Low ammo indicator → RELOAD.\n"
        "- NEVER repeat the same action more than twice consecutively — vary your play.\n"
        "- Only choose IDLE if a cutscene, loading screen, or menu is showing.\n\n"
        "Respond with EXACTLY ONE word from this list — no punctuation, no explanation:\n"
        + action_str
    )
    return prompt


def _build_user_message(b64_jpeg: str, recent: list[str]) -> HumanMessage:
    """Build a vision message with the current screenshot."""
    context = ""
    if recent:
        context = f"Recent actions (oldest→newest): {' → '.join(recent)}.\n"

    return HumanMessage(
        content=[
            {
                "type": "text",
                "text": (
                    f"{context}"
                    "What is the BEST single action to take now based on what you see? "
                    "Consider threats, environment, and recent actions before deciding. "
                    "Reply with ONE word only."
                ),
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_jpeg}",
                    "detail": "low",  # cheapest & fastest vision mode
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
