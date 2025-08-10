from typing import Dict, Any
import json
from app.services.prompt_loader import render_prompt
from app.services.llm_invoker import call_openai_prompt

def agent_2_node(state: Dict[str, Any]) -> Dict[str, Any]:
    question = (state.get("text") or "").strip()
    location = (state.get("location") or "").strip() or None

    prompt = render_prompt(
        "agent_2_tenancy.j2",
        {
            "question": question,
            "location": location
        },
    )

    completion = call_openai_prompt(prompt)

    try:
        parsed = json.loads(completion)
        state["response"] = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        state["response"] = completion

    state["agent"] = "agent_2"
    return state