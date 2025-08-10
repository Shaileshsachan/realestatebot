from typing import Literal

ISSUE_KWS = {
    "mold", "mould", "leak", "leaking", "damp", "moisture", "crack", "cracks",
    "peel", "peeling", "paint", "fixture", "tap", "faucet", "toilet", "drain",
    "stain", "stains", "ceiling", "wall", "tile", "tiles", "window", "door",
}
FAQ_KWS = {
    "notice", "evict", "eviction", "deposit", "rent", "increase", "agreement",
    "contract", "lease", "terminate", "termination", "repair", "responsibility",
    "landlord", "tenant", "tenancy", "inventory", "inspection",
}

AgentName = Literal["agent_1", "agent_2", "fallback"]

def classify_input(text: str) -> AgentName:
    t = (text or "").lower()
    if not t:
        return "fallback"
    if any(kw in t for kw in ISSUE_KWS):
        return "agent_1"
    if any(kw in t for kw in FAQ_KWS):
        return "agent_2"
    return "fallback"