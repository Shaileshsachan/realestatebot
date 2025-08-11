# streamlit_app.py
import os
import json
import time
import re
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path

# =============================
# Config
# =============================
BACKEND_URL_DEFAULT = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT_PATH = "/chat"
PERSIST_DIR = Path(os.getenv("ST_CHAT_DIR", ".chats"))
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Multi‑Agent Real Estate Chatbot", page_icon="🏠", layout="wide")

# =============================
# Theme + CSS
# =============================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

THEME_CSS_LIGHT = ":root { --bg:#ffffff; --fg:#0f172a; --muted:#6b7280; --bot:#f3f4f6; --user:#2563eb; --chip:#e5e7eb; }"
THEME_CSS_DARK  = ":root { --bg:#0b1220; --fg:#e5e7eb; --muted:#94a3b8; --bot:#0f172a; --user:#1d4ed8; --chip:#1f2937; }"

CHAT_CSS = """
<style>
body { background: var(--bg); color: var(--fg); }
.chat-container {max-width: 900px; margin: 0 auto;}
.msg {padding: .75rem 1rem; border-radius: 18px; margin: .25rem 0; display: inline-block;}
.msg-user {background: var(--user); color: white; border-bottom-right-radius: 6px;}
.msg-bot {background: var(--bot); color: var(--fg); border-bottom-left-radius: 6px;}
.meta {font-size: .75rem; color: var(--muted); margin-top: .15rem;}
.row {display: flex; gap: .5rem; align-items: flex-end;}
.row.right {justify-content: flex-end;}
.avatar {width: 36px; height: 36px; border-radius: 9999px; background: var(--chip); display:flex; align-items:center; justify-content:center; font-weight:600;}
.avatar.user {background: var(--user); color:#fff;}
.avatar.bot {background: var(--chip); color:var(--fg);}
.codewrap {white-space: pre-wrap; word-break: break-word;}
.caption {font-size:.8rem; color:var(--muted); margin-top:.25rem}
.badge {display:inline-block; padding:.05rem .5rem; border-radius:9999px; font-size:.70rem; background:var(--chip); color:var(--fg); margin-right:.3rem}
.badge.agent1{background:#dcfce7; color:#065f46}
.badge.agent2{background:#e0e7ff; color:#3730a3}
.badge.fallback{background:#fee2e2; color:#991b1b}
.hr{height:1px;background:var(--chip);margin:1rem 0}
</style>
"""

STICKY_CSS = """
<style>
/* keep input controls visible like a footer */
.block-container { padding-bottom: 7rem; }
[data-testid="stBottomBlockContainer"] { position: sticky; bottom: 0; background: var(--bg); padding-top: .5rem; }
</style>
"""

# =============================
# Persistence helpers
# =============================

def _session_file(session_id: str) -> Path:
    return PERSIST_DIR / f"{session_id}.jsonl"


def save_turn(session_id: str, payload: dict) -> None:
    try:
        with _session_file(session_id).open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


# =============================
# Session state
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, agent, caption, ts}]
if "session_id" not in st.session_state:
    st.session_state.session_id = str(int(time.time()*1000))
if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL_DEFAULT

# Seed a friendly welcome once
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hi! 👋 I can diagnose property issues from photos and answer tenancy questions.\n\nTry one:",
        "agent": "agent_2",
        "caption": None,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.backend_url = st.text_input("Backend URL", value=st.session_state.backend_url)
    st.write("Session:", st.session_state.session_id)
    st.toggle("Dark mode", key="dark_mode")
    show_raw = st.toggle("Show raw JSON (dev)", value=False)
    if st.button("🧹 New chat"):
        st.session_state.session_id = str(int(time.time()*1000))
        st.session_state.messages = []
        st.rerun()
    data = {"session_id": st.session_state.session_id, "messages": st.session_state.messages}
    st.download_button("💾 Save transcript", data=json.dumps(data, ensure_ascii=False, indent=2), file_name=f"chat_{st.session_state.session_id}.json", mime="application/json")

# Apply theme
st.markdown(f"<style>{THEME_CSS_DARK if st.session_state.dark_mode else THEME_CSS_LIGHT}</style>", unsafe_allow_html=True)
st.markdown(CHAT_CSS + STICKY_CSS, unsafe_allow_html=True)

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
st.title("🏠 Multi‑Agent Real Estate Chatbot")
st.caption("Minimal chat UI • Image + Text • Agent badges • Feedback • Persistent sessions")

# Quick-start chips
chip_cols = st.columns([1,1,1,1])
chips = [
    "How much notice to vacate in London?",
    "Can my landlord increase rent mid-term?",
    "What’s wrong with this damp wall?",
    "Deposit not returned—what can I do?",
]
for idx, c in enumerate(chips):
    with chip_cols[idx]:
        if st.button(c, use_container_width=True, key=f"chip_{idx}"):
            # st.session_state.pending_quick = c
            st.rerun()

# =============================
# Pretty rendering helpers
# =============================

def _fmt_list(items):
    if not items:
        return ""
    return "\n".join(f"• {i}" for i in items)


def _strip_code_fences(text: str) -> str:
    if not isinstance(text, str):
        return text
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def render_pretty(agent: str, raw: str) -> str:
    """Convert JSON-ish responses into human-friendly chat text."""
    if not raw:
        return ""
    cleaned = _strip_code_fences(raw)

    # Try JSON
    data = None
    try:
        data = json.loads(cleaned)
    except Exception:
        data = None

    if isinstance(data, dict):
        if agent == "agent_1":
            issue = data.get("issue")
            reasoning = data.get("reasoning")
            recs = data.get("recommendations") or {}
            steps = recs.get("steps") if isinstance(recs, dict) else (
                data.get("recommendations") if isinstance(data.get("recommendations"), list) else []
            )
            who = recs.get("who_to_contact") if isinstance(recs, dict) else []
            follow = data.get("follow_up_question")
            parts = []
            if issue: parts.append(f"Likely issue: {issue}")
            if reasoning: parts.append(f"Why: {reasoning}")
            if steps: parts.append("What you can do now:\n" + _fmt_list(steps))
            if who: parts.append("Who to contact:\n" + _fmt_list(who))
            if follow: parts.append(f"Quick question: {follow}")
            return "\n\n".join(parts) or cleaned

        if agent == "agent_2":
            answer     = data.get("answer")
            checklist  = data.get("checklist")
            disclaimer = data.get("disclaimer")
            ask_loc    = data.get("ask_location")
            parts = []
            if answer:    parts.append(answer)
            if checklist: parts.append("Checklist:\n" + _fmt_list(checklist))
            if disclaimer:parts.append(disclaimer if isinstance(disclaimer, str) else "")
            if ask_loc:   parts.append("If you share your city/country, I can be more specific.")
            return "\n\n".join(parts) or cleaned

        clar = data.get("clarifying_question")
        sugg = data.get("suggested_agent")
        if clar or sugg:
            extra = f"\n\nSuggested route: {sugg}" if sugg else ""
            return (clar or "").strip() + extra

    # Not JSON → show cleaned text
    return cleaned

# =============================
# Backend call
# =============================

def call_backend(text: str, location: str, image_file) -> dict:
    data = {
        "session_id": st.session_state.session_id,
        "text": text or "",
        "location": location or "",
    }
    files = None
    if image_file is not None:
        files = {"image": (image_file.name, image_file.getvalue(), image_file.type or "application/octet-stream")}
    resp = requests.post(st.session_state.backend_url + CHAT_ENDPOINT_PATH, data=data, files=files, timeout=90)
    resp.raise_for_status()
    return resp.json()

# =============================
# Render history
# =============================
for i, m in enumerate(st.session_state.messages):
    role = m.get("role")
    content = m.get("content", "")
    agent = m.get("agent")
    caption = m.get("caption")
    ts = m.get("ts")

    is_user = role == "user"
    row_class = "row right" if is_user else "row"
    avatar_class = "avatar user" if is_user else "avatar bot"
    avatar_text = "U" if is_user else "🤖"

    with st.container():
        st.markdown(
            f"<div class='{row_class}'>"
            # f"<div class='{avatar_class}'>{avatar_text}</div>"
            f"<div>"
            f"<div class='msg {'msg-user' if is_user else 'msg-bot'} codewrap'>{content}</div>"
            f"<div class='meta'>{ts}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if not is_user:
            if agent:
                badge_cls = 'badge ' + ( 'agent1' if agent=='agent_1' else ('agent2' if agent=='agent_2' else 'fallback') )
                st.markdown(f"<span class='{badge_cls}'>Agent: {agent}</span>", unsafe_allow_html=True)
            if caption:
                st.markdown(f"<div class='caption'><b>Caption:</b> {caption}</div>", unsafe_allow_html=True)
            cols = st.columns(3)
            with cols[0]:
                if st.button("👍 Helpful", key=f"up_{i}"):
                    try:
                        requests.post(
                            st.session_state.backend_url + CHAT_ENDPOINT_PATH,
                            data={"session_id": st.session_state.session_id, "text": "", "feedback": "up"},
                            timeout=15,
                        )
                        st.success("Thanks for the feedback!")
                    except Exception as e:
                        st.error(f"Feedback failed: {e}")
            with cols[1]:
                if st.button("👎 Not helpful", key=f"down_{i}"):
                    try:
                        requests.post(
                            st.session_state.backend_url + CHAT_ENDPOINT_PATH,
                            data={"session_id": st.session_state.session_id, "text": "", "feedback": "down"},
                            timeout=15,
                        )
                        st.success("We appreciate the signal.")
                    except Exception as e:
                        st.error(f"Feedback failed: {e}")

            # Suggested replies (heuristic)
            sugs = []
            if m.get("agent") == "agent_1":
                sugs = ["Show another angle", "It’s near the bathroom", "How to prevent this?"]
            elif m.get("agent") == "agent_2":
                sugs = ["What’s the notice period?", "Can rent be raised?", "Deposit rules?"]
            elif m.get("agent") == "fallback":
                sugs = ["Diagnose property issue", "I have a tenancy question"]
            if sugs:
                sug_cols = st.columns(min(3, len(sugs)))
                for j, s in enumerate(sugs):
                    with sug_cols[j]:
                        if st.button(s, key=f"sug_{i}_{j}", use_container_width=True):
                            st.session_state.pending_quick = s
                            st.rerun()
            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

# =============================
# Input row
# =============================
col_left, col_right = st.columns([8, 2])
with col_left:
    # If a chip was clicked, treat it as input; else use chat_input
    if st.session_state.get("pending_quick"):
        user_text = st.session_state.pop("pending_quick")
    else:
        user_text = st.chat_input("Type a message…")
with col_right:
    upload_slot = st.file_uploader(" ", type=["png", "jpg", "jpeg"], label_visibility="collapsed", accept_multiple_files=False)
    st.caption("📎 Attach an image")
    if upload_slot is not None:
        st.image(upload_slot.getvalue(), caption=upload_slot.name, use_container_width=False, width=220)
        
        if st.button("Send image", key="send_img_btn", use_container_width=True):
            st.session_state.pending_send_image = True
            st.rerun()

location = st.text_input("📍 Location (optional)", key="loc_input", placeholder="City or Country")
st.caption("Press **Enter** to send text • Or click **Send image** after attaching a photo")

if st.session_state.get("pending_send_image") and user_text is None:
    user_text = ""
    st.session_state.pending_send_image = False

if user_text is not None:
    # user turn
    msg_user = {
        "role": "user",
        "content": user_text,
        "agent": None,
        "caption": None,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    st.session_state.messages.append(msg_user)
    save_turn(st.session_state.session_id, msg_user)

    # typing indicator
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("🟢 **Assistant is typing…**")

    # backend
    try:
        with st.spinner("Thinking…"):
            res = call_backend(user_text, location, upload_slot)
        st.toast("Response ready ✅", icon="✅")
    except Exception as e:
        st.toast("Request failed", icon="❌")
        res = {"agent": "error", "response": f"Request failed: {e}", "caption": None}

    # assistant turn
    raw = res.get("response") or ""
    pretty = raw if show_raw else render_pretty(res.get("agent"), raw)

    msg_bot = {
        "role": "assistant",
        "content": pretty,
        "agent": res.get("agent"),
        "caption": res.get("caption"),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    st.session_state.messages.append(msg_bot)
    save_turn(st.session_state.session_id, msg_bot)

    placeholder.empty()
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)