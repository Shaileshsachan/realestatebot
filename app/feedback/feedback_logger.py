import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

_feedback_file = Path(__file__).resolve().parents[1]/"feedback_log.jsonl"

def log_feedback(state: Dict[str, Any]) -> None:
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": state.get("session_id"),
        "agent": state.get("agent"),
        "input_text": state.get("text"),
        "image_caption": state.get("caption"),
        "response": state.get("response"),
        "feedback": state.get("feedback"),
    }
    with _feedback_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")