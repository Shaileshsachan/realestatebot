from typing import Dict, Any
import json
from app.services.prompt_loader import render_prompt
from app.services.llm_invoker import call_openai_prompt

def fallback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    user_text = state.get("text") or ""
    prompt = render_prompt("fallback_clarifier.j2", {"user_text": user_text})
    completion = call_openai_prompt(prompt)

    try:
        parsed = json.loads(completion)
        state["response"] = json.dumps(parsed, ensure_ascii=False, indent=2)
        suggested = parsed.get("suggested_agent")
        if suggested in {"agent_1", "agent_2"}:
            state["agent"] = suggested
        else:
            state["agent"] = "fallback"
    except Exception:
        state["response"] = completion
        state["agent"] = "fallback"
    
    return state