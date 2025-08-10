# app/langgraph_builder.py
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.agents.agent_1_image_issue import agent_1_node
from app.agents.agent_2_faq import agent_2_node
from app.agents.fallback_clarifier import fallback_node
from app.feedback.feedback_logger import log_feedback
from app.memory.session_memory import update_memory
from app.router import classify_input

class GraphState(TypedDict, total=False):
    session_id: str
    image: Optional[bytes]
    text: Optional[str]
    location: Optional[str]
    caption: Optional[str]
    agent: Optional[str]   # "agent_1" | "agent_2" | "fallback"
    response: Optional[str]
    feedback: Optional[str]  # user rating/comment

def router_node(state: GraphState) -> GraphState:
    image = state.get("image")
    text = (state.get("text") or "").strip()
    if image:
        state["agent"] = "agent_1"
    else:
        state["agent"] = classify_input(text) or "fallback"
    return state

def agent_dispatcher(state: GraphState) -> str:
    agent = state.get("agent") or "fallback"
    return agent if agent in {"agent_1", "agent_2", "fallback"} else "fallback"

def feedback_node(state: GraphState) -> GraphState:
    # best-effort logging + memory
    try: 
        log_feedback(state)
    except Exception: 
        pass
    try:
        sid = state.get("session_id")
        if sid: 
            update_memory(sid, state)
    except Exception: pass
    return state

def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("router", router_node)
    builder.add_node("agent_1", agent_1_node)
    builder.add_node("agent_2", agent_2_node)
    builder.add_node("fallback", fallback_node)

    # IMPORTANT: do NOT name this node "feedback" because it's a state key
    builder.add_node("logmem", feedback_node)

    builder.set_entry_point("router")
    builder.add_conditional_edges(
        "router",
        agent_dispatcher,
        {
            "agent_1": "agent_1",
            "agent_2": "agent_2",
            "fallback": "fallback",
        },
    )

    builder.add_edge("agent_1", "logmem")
    builder.add_edge("agent_2", "logmem")
    builder.add_edge("fallback", "logmem")
    builder.add_edge("logmem", END)

    return builder.compile()
