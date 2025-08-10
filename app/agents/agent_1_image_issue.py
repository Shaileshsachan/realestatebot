from typing import Dict, Any
import json
from app.services.blip_captioner import caption_image_bytes
from app.services.prompt_loader import render_prompt
from app.services.llm_invoker import call_openai_prompt

def agent_1_node(state: Dict[str, Any]) -> Dict[str, Any]:
    image_bytes = state.get('image')
    user_text = state.get('text') or ''
    if not image_bytes:
        state["agent"] = "fallback"
        state["response"] = "Please upload a photo of the issue so I can diagnose it."
        return state
    
    caption = caption_image_bytes(image_bytes)
    prompt = render_prompt(
        "agent_1_diagnosis.j2",
        {
            "caption": caption,
            "user_text": user_text
        },)
    
    completion = call_openai_prompt(prompt)
    try:
        parsed = json.loads(completion)
        state["response"] = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        state["response"] = completion

    state["caption"] = caption
    state["agent"] = 'agent_1'
    return state