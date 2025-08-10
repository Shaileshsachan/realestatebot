from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from typing import Dict, Any

DEFAULT_TEMPLATES: Dict[str, str] = {
    "agent_1_diagnosis.j2": (
        """
        {% set guidance %}
        You are a Property Issue Detection Expert. Given an image description and optional user text:
        1) Diagnose likely issues visible in the property image.
        2) Provide practical troubleshooting steps and who to contact (plumber, electrician, painter, etc.).
        3) Ask **one** smart follow-up question if uncertainty remains.
        Reply clearly with short paragraphs and bullet points when helpful.
        {% endset %}
        SYSTEM: {{ guidance | trim }}

        IMAGE_DESCRIPTION: {{ caption }}
        USER_MESSAGE: {{ user_text or "No additional message." }}

        Return JSON with keys: issue, reasoning, recommendations, follow_up_question.
        """
    ),
    "agent_2_tenancy.j2": (
        """
        {% set guidance %}
        You are a Tenancy FAQ expert. Provide accurate, concise guidance on renting, deposits, eviction, notices,
        and landlord/tenant responsibilities. If a location is provided (city/country), adapt the answer
        with jurisdiction-aware language and disclaimers. Offer a short, actionable checklist.
        {% endset %}
        SYSTEM: {{ guidance | trim }}

        QUERY: {{ question }}
        LOCATION: {{ location or "unknown" }}

        Return JSON with keys: answer, checklist, disclaimer, ask_location (true/false).
        """
    ),
    "fallback_clarifier.j2": (
        """
        The user query was unclear. Ask a single clarifying question to route properly.
        Consider whether it's (A) image-based property issue, or (B) tenancy FAQ.
        USER_TEXT: {{ user_text or "" }}
        Return JSON with keys: clarifying_question, suggested_agent ("agent_1"|"agent_2").
        """
    ),
}

_env = None

def _get_env() -> Environment:
    global _env
    if _env is None:
        prompts_dir = Path(__file__).resolve().parents[1]/"prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        _env = Environment(
            loader=FileSystemLoader(prompts_dir),
            autoescape=select_autoescape(enabled_extensions=('j2',), default_for_string=False),
            trim_blocks=True,
            lstrip_blocks=True
        )
    return _env

def render_prompt(template_name: str, context: Dict[str, Any]) -> str:
    env = _get_env()
    try:
        template: Template = env.get_template(template_name)
        return template.render(**context)
    except Exception:
        raw = DEFAULT_TEMPLATES.get(template_name)
        if not raw:
            raise
        return Environment().from_string(raw).render(**context)