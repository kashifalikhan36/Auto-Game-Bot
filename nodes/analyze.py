"""
Analyze node — sends the current screenshot to Azure OpenAI vision
and returns a single action keyword (e.g. "JUMP", "LEFT", "IDLE").

Key latency choices:
  - detail="low"  : model processes a single 512-px tile (~85 tokens)
  - max_tokens=10 : stop generation immediately after the action word
  - temperature=0 : deterministic, avoids sampling overhead
  - Synchronous invoke (asyncio integration handled by LangGraph's astream)
"""

from __future__ import annotations

import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

import config
from state import BotState

# ---------------------------------------------------------------------------
# LLM client — created once at import time.
# ---------------------------------------------------------------------------
_llm: AzureChatOpenAI | None = None


def _get_llm() -> AzureChatOpenAI:
    global _llm
    if _llm is None:
        _llm = AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            azure_deployment=config.AZURE_DEPLOYMENT_NAME,
            max_tokens=config.MAX_TOKENS,
            # temperature omitted: GPT-5 Nano only accepts the default value
        )
    return _llm


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a game-playing AI. "
    "You will receive a screenshot of a game. "
    "Your job is to decide the single best action to take RIGHT NOW. "
    "Respond with EXACTLY one word from this list — no punctuation, no explanation:\n"
    + ", ".join(config.ACTION_LIST)
)


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
                    "What is the best single action to take now? "
                    "Reply with one word only."
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
        SystemMessage(content=SYSTEM_PROMPT),
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

    # Maintain a rolling window of last 3 actions
    new_recent = (recent + [action])[-3:]

    updates: BotState = {
        "action": action,
        "recent_actions": new_recent,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
