import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env")

_client: Optional[OpenAI] = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def call_openai_prompt(prompt_text: str, *, model: str = "gpt-4o-mini", system: Optional[str] = None) -> str:
    client = _get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt_text})

    resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
    return resp.choices[0].message.content.strip()