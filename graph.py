"""
LangGraph agent graph definition.

Graph topology (fixed, deterministic — no LLM-driven routing):

    [capture] ──► [analyze] ──► [act] ──► (loop or stop)
                                             │
                                         back to [capture]

The "should_continue" edge checks MAX_FRAMES; if 0, runs forever.
"""

from __future__ import annotations

import config
from nodes.act import act_node
from nodes.analyze import analyze_node
from nodes.capture import capture_node
from state import BotState

from langgraph.graph import StateGraph, END


# ---------------------------------------------------------------------------
# Conditional edge — continue looping or stop
# ---------------------------------------------------------------------------

def should_continue(state: BotState) -> str:
    """Return the name of the next node to execute."""
    max_frames = config.MAX_FRAMES
    if max_frames > 0 and state.get("frame_count", 0) >= max_frames:
        return END  # type: ignore[return-value]
    return "capture"


# ---------------------------------------------------------------------------
# Build and compile the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct the LangGraph StateGraph for the game bot."""
    graph = StateGraph(BotState)

    # Register nodes
    graph.add_node("capture", capture_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("act", act_node)

    # Entry point
    graph.set_entry_point("capture")

    # Fixed sequential edges
    graph.add_edge("capture", "analyze")
    graph.add_edge("analyze", "act")

    # Conditional loop-back or stop after "act"
    graph.add_conditional_edges(
        "act",
        should_continue,
        {
            "capture": "capture",
            END: END,
        },
    )

    return graph


def compile_graph():
    """Return a compiled, runnable LangGraph application."""
    return build_graph().compile()
