from typing import Dict, Any
import threading

_memory_store: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

def get_memory(session_id: str) -> Dict[str, Any]:
    with _lock:
        return _memory_store.get(session_id, {}).copy()

def update_memory(session_id: str, state: Dict[str, Any]) -> None:
    with _lock:
        _memory_store[session_id] = state.copy()

def clear_memory(session_id: str) -> None:
    with _lock:
        if session_id in _memory_store:
            del _memory_store[session_id]