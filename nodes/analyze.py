"""
Analyze node â€” two-stage pipeline for games with vision scene analysis:

  Stage 1 (Groq vision)  : screenshot â†’ structured JSON scene description
  Stage 2 (Decision LLM) : JSON + concise rules â†’ ONE named action (text only)

For games without scene_analysis_prompt (e.g. MGS5), falls back to the
original single-stage mode where the decision LLM receives the image directly.

Providers for decision: azure, openai, gemini, anthropic, groq
Vision Stage: always Groq (fast, cheap, multimodal)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

import config
from state import BotState

# ---------------------------------------------------------------------------
# Vision LLM â€” always Groq (handles the screenshot â†’ JSON stage)
# ---------------------------------------------------------------------------
_vision_llm: Any = None


def _create_vision_llm() -> Any:
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "[analyze] GROQ_API_KEY is required for scene vision analysis. "
            "Set GROQ_API_KEY in your .env file."
        )
    from langchain_groq import ChatGroq
    return ChatGroq(
        api_key=config.GROQ_API_KEY,
        model=config.GROQ_VISION_MODEL,
        max_tokens=512,
        temperature=0.0,
    )


def _get_vision_llm() -> Any:
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = _create_vision_llm()
    return _vision_llm


# ---------------------------------------------------------------------------
# Decision LLM â€” configured provider (text only, no images in this stage)
# ---------------------------------------------------------------------------
_decision_llm: Any = None


def _create_decision_llm() -> Any:
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
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            api_key=config.GROQ_API_KEY,
            model=config.GROQ_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
        )
    raise RuntimeError(f"[analyze] Unknown provider '{provider}'")


def _get_decision_llm() -> Any:
    global _decision_llm
    if _decision_llm is None:
        _decision_llm = _create_decision_llm()
    return _decision_llm


# ---------------------------------------------------------------------------
# Situation mapper
# ---------------------------------------------------------------------------

def _action_to_situation(action: str) -> str:
    """Map a named action to a broad situation label.
    Handles both FH5 and MGS5 action namespaces.
    """
    a = action.upper()

    # â”€â”€ FH5 situations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if a == "DO_NOTHING":
        return "MENU"
    # Recovery checked FIRST (before generic THROTTLE/NUDGE matches)
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

    # â”€â”€ MGS5 situations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
# System prompt (used by both pipeline modes)
# ---------------------------------------------------------------------------

def _get_system_prompt() -> str:
    named_actions: dict    = getattr(config, "NAMED_ACTIONS", {})
    descriptions: dict     = getattr(config, "NAMED_ACTION_DESCRIPTIONS", {})
    game_ctx: str          = getattr(config, "GAME_CONTEXT", "")
    rules: list[str]       = getattr(config, "DECISION_RULES", [])
    constraints: list[str] = getattr(config, "CONSTRAINTS", [])

    lines = [
        "You are an AI agent controlling a real video game in REAL TIME via keyboard.",
        "Each frame you receive scene data and MUST pick ONE action to execute immediately.",
        "",
    ]
    if game_ctx:
        lines += ["=== GAME ===", game_ctx, ""]

    lines += ["=== AVAILABLE ACTIONS (pick EXACTLY ONE) ===", ""]
    for name in named_actions:
        desc = descriptions.get(name, "")
        lines.append(f"  {name}" + (f" â€” {desc}" if desc else ""))
    lines.append("")

    if rules:
        lines += ["=== DECISION RULES (first match wins) ===", ""]
        lines += rules
        lines.append("")

    if constraints:
        lines += ["=== HARD CONSTRAINTS ==="]
        lines += constraints
        lines.append("")

    lines += [
        "=== OUTPUT ===",
        "Reply with EXACTLY ONE word â€” the action name. No punctuation, no explanation.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 1 â€” Groq vision: screenshot â†’ JSON scene dict
# ---------------------------------------------------------------------------

_SCENE_FALLBACK: dict = {
    "event": "freeroam",
    "car_on_road": True,
    "car_speed": "medium",
    "car_state": "normal",
    "road_ahead": "straight",
    "racing_line": "none",
    "hazard_type": "none",
    "hazard_direction": "none",
    "surface": "tarmac",
    "menu_visible": False,
    "overtake_possible": False,
}


def _analyze_scene(b64_jpeg: str, scene_prompt: str) -> dict:
    """Call Groq vision with the screenshot; return parsed scene JSON dict."""
    vision = _get_vision_llm()
    msg = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_jpeg}", "detail": "low"},
        },
        {"type": "text", "text": scene_prompt},
    ])
    try:
        resp = vision.invoke([msg])
        text = resp.content.strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as exc:
        print(f"[analyze] scene vision error: {exc}")
    return dict(_SCENE_FALLBACK)


# ---------------------------------------------------------------------------
# Stage 2 â€” Decision message builder (text only â€” no image)
# ---------------------------------------------------------------------------

_STRUGGLING_SET = {
    "OFFROAD_THROTTLE", "OFFROAD_LEFT", "OFFROAD_RIGHT", "OFFROAD_CAREFUL",
    "ROAD_NUDGE_LEFT", "ROAD_NUDGE_RIGHT", "ROAD_RETURN_LEFT", "ROAD_RETURN_RIGHT",
}
_REVERSE_SET = {
    "UNSTICK_REVERSE", "UNSTICK_REVERSE_LEFT", "UNSTICK_REVERSE_RIGHT",
    "REVERSE", "REVERSE_LEFT", "REVERSE_RIGHT",
}


def _build_decision_message(
    scene: dict,
    recent: list[str],
    recent_situations: list[str],
) -> HumanMessage:
    lines: list[str] = []

    if scene:
        lines.append("Scene: " + json.dumps(scene))
    if recent:
        lines.append("Recent actions (oldestâ†’newest): " + " â†’ ".join(recent))
    if recent_situations:
        lines.append("Recent situations: " + " â†’ ".join(recent_situations))

    # Stuck detection
    recent4 = recent[-4:]
    struggling = [a for a in recent4 if a in _STRUGGLING_SET]
    rev_attempts = [a for a in recent4 if a in _REVERSE_SET]
    stuck_via_sit = (
        len(recent_situations) >= 3
        and all(s == "RECOVER" for s in recent_situations[-3:])
    )

    if (len(struggling) >= 3 or stuck_via_sit) and not rev_attempts:
        lines.append(
            "*** STUCK ALERT ***: Car is physically blocked â€” throttle/offroad is not helping. "
            "Reverse to escape:\n"
            "  hazard on LEFT  â†’ UNSTICK_REVERSE_RIGHT\n"
            "  hazard on RIGHT â†’ UNSTICK_REVERSE_LEFT\n"
            "  unclear         â†’ UNSTICK_REVERSE\n"
            "Do NOT pick throttle, offroad, or nudge until after reversing."
        )
    elif len(recent) >= 3 and len(set(recent[-3:])) == 1 and recent[-1] not in _REVERSE_SET:
        lines.append(
            f"WARNING: '{recent[-1]}' repeated {sum(1 for x in recent if x == recent[-1])}x â€” "
            "not working. Pick a different action."
        )
    elif len([x for x in recent[-5:] if "OFFROAD" in x]) >= 3:
        lines.append(
            "WARNING: OFFROAD_* repeated. "
            "Tarmac visible? â†’ FULL_THROTTLE. Beside road? â†’ ROAD_RETURN_* or ROAD_NUDGE_*."
        )
    elif len([x for x in recent[-4:] if "NUDGE" in x]) >= 3:
        lines.append("WARNING: NUDGE oscillation. Stop nudging â€” pick FULL_THROTTLE.")

    lines.append("Output ONE action name.")
    return HumanMessage(content="\n".join(lines))


# ---------------------------------------------------------------------------
# Legacy single-stage message builder (image â†’ decision LLM)
# Used for games without scene_analysis_prompt (e.g. MGS5)
# ---------------------------------------------------------------------------

def _build_user_message(b64_jpeg: str, recent: list[str],
                        recent_situations: list[str] | None = None) -> HumanMessage:
    """Original single-stage: image + text sent to the main decision LLM."""
    lines: list[str] = []
    if recent:
        lines.append("Recent actions (oldestâ†’newest): " + " â†’ ".join(recent))
    if recent_situations:
        lines.append("Recent situations: " + " â†’ ".join(recent_situations))

    recent4 = recent[-4:]
    struggling = [a for a in recent4 if a in _STRUGGLING_SET]
    rev_attempts = [a for a in recent4 if a in _REVERSE_SET]
    stuck_via_sit = (
        recent_situations is not None
        and len(recent_situations) >= 3
        and all(s == "RECOVER" for s in recent_situations[-3:])
    )
    if (len(struggling) >= 3 or stuck_via_sit) and not rev_attempts:
        lines.append(
            "*** STUCK ALERT ***: Reverse to escape: "
            "UNSTICK_REVERSE_LEFT / UNSTICK_REVERSE_RIGHT / UNSTICK_REVERSE"
        )
    elif len(recent) >= 3 and len(set(recent[-3:])) == 1 and recent[-1] not in _REVERSE_SET:
        lines.append(f"WARNING: '{recent[-1]}' repeated. Pick a different action.")

    checklist: list[str] = getattr(config, "SITUATION_CHECKLIST", [])
    lines += checklist if checklist else ["Examine the screenshot. Output ONE action name."]

    return HumanMessage(content=[
        {"type": "text", "text": "\n".join(lines)},
        {"type": "image_url",
         "image_url": {"url": f"data:image/jpeg;base64,{b64_jpeg}", "detail": "low"}},
    ])


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

def analyze_node(state: BotState) -> BotState:
    """
    Two-stage pipeline (FH5): Groq vision â†’ JSON â†’ decision LLM â†’ action name.
    Single-stage fallback (MGS5): image â†’ decision LLM â†’ action name.
    """
    t0 = time.perf_counter()

    b64 = state.get("screenshot_b64", "")
    named_actions: dict = getattr(config, "NAMED_ACTIONS", {})
    default_action = next(iter(named_actions), "EXPLORE")

    if not b64:
        sit = _action_to_situation(default_action)
        return {**state, "chosen_action": default_action,
                "situation": sit, "action": default_action}

    recent = list(state.get("recent_actions", []))
    recent_situations = list(state.get("recent_situations", []))
    system = SystemMessage(content=_get_system_prompt())

    scene_prompt: str = getattr(config, "SCENE_ANALYSIS_PROMPT", "")

    if scene_prompt:
        # â”€â”€ Two-stage: Groq vision â†’ decision LLM (text only) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        scene = _analyze_scene(b64, scene_prompt)
        print(f"[scene] {json.dumps(scene)}")
        messages = [system, _build_decision_message(scene, recent, recent_situations)]
        response = _get_decision_llm().invoke(messages)
    else:
        # â”€â”€ Legacy single-stage: image sent directly to decision LLM â”€â”€â”€â”€â”€â”€â”€â”€
        messages = [system, _build_user_message(b64, recent, recent_situations)]
        response = _get_decision_llm().invoke(messages)

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
    new_recent_sits = (recent_situations + [situation])[-window:]

    updates: BotState = {
        "chosen_action":     chosen_action,
        "situation":         situation,
        "action":            chosen_action,
        "recent_actions":    new_recent,
        "recent_situations": new_recent_sits,
    }
    if config.DEBUG_TIMING:
        timing = dict(state.get("timing", {}))
        timing["analyze_ms"] = round((t1 - t0) * 1000, 2)
        updates["timing"] = timing

    return {**state, **updates}
