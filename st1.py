# streamlit_app.py
import os
import json
import time
import requests
import streamlit as st
from datetime import datetime
from pathlib import Path

# ------------------------------
# Config
# ------------------------------
BACKEND_URL_DEFAULT = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT_PATH = "/chat"
PERSIST_DIR = Path(os.getenv("ST_CHAT_DIR", ".chats"))
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Multi‑Agent Real Estate Chatbot", page_icon="🏠", layout="wide")

# ------------------------------
# Theme + CSS
# ------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

THEME_CSS_LIGHT = """
:root { --bg:#ffffff; --fg:#0f172a; --muted:#6b7280; --bot:#f3f4f6; --user:#2563eb; --chip:#e5e7eb; --ok:#16a34a; --warn:#b91c1c; }
"""
THEME_CSS_DARK = """
:root { --bg:#0b1220; --fg:#e5e7eb; --muted:#94a3b8; --bot:#0f172a; --user:#1d4ed8; --chip:#1f2937; --ok:#22c55e; --warn:#ef4444; }
"""

CHAT_CSS = """
<style>
body { background: var(--bg); color: var(--fg); }
.chat-container {max-width: 900px; margin: 0 auto;}
.msg {padding: 0.75rem 1rem; border-radius: 18px; margin: 0.25rem 0; display: inline-block;}
.msg-user {background: var(--user); color: white; border-bottom-right-radius: 6px;}
.msg-bot {background: var(--bot); color: var(--fg); border-bottom-left-radius: 6px;}
.meta {font-size: 0.75rem; color: var(--muted); margin-top: 0.15rem;}
.row {display: flex; gap: .5rem; align-items: flex-end;}
.row.right {justify-content: flex-end;}
.avatar {width: 36px; height: 36px; border-radius: 9999px; background: var(--chip); display:flex; align-items:center; justify-content:center; font-weight:600;}
.avatar.user {background: var(--user); color:#fff;}
.avatar.bot {background: var(--chip); color:var(--fg);}
.codewrap {white-space: pre-wrap; word-break: break-word;}
.caption {font-size:.8rem; color:var(--muted); margin-top:.25rem}
.badge {display:inline-block; padding:.1rem .5rem; border-radius:9999px; font-size:.70rem; background:var(--chip); color:var(--fg); margin-right:.3rem}
.badge.agent1{background:#dcfce7; color:#065f46}
.badge.agent2{background:#e0e7ff; color:#3730a3}
.badge.fallback{background:#fee2e2; color:#991b1b}
.hr{height:1px;background:var(--chip);margin:1rem 0}
.thumb {max-width: 220px; border-radius: 8px; margin-top: .35rem; border:1px solid var(--chip)}
</style>
"""

# ------------------------------
# Persistence helpers
# ------------------------------

def _session_file(session_id: str) -> Path:
    return PERSIST_DIR / f"{session_id}.jsonl"


def save_turn(session_id: str, payload: dict) -> None:
    try:
        f = _session_file(session_id)
        with f.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_session(session_id: str) -> list[dict]:
    f = _session_file(session_id)
    turns = []
    if f.exists():
        with f.open("r", encoding="utf-8") as fp:
            for line in fp:
                try:
                    turns.append(json.loads(line))
                except Exception:
                    continue
    return turns

# ------------------------------
# Session state
# ------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, agent, caption, ts, image_name}]
if "session_id" not in st.session_state:
    st.session_state.session_id = str(int(time.time()*1000))
if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL_DEFAULT

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.backend_url = st.text_input("Backend URL", value=st.session_state.backend_url)
    st.write("Session:", st.session_state.session_id)
    st.toggle("Dark mode", key="dark_mode")
    if st.button("🧹 New chat"):
        st.session_state.session_id = str(int(time.time()*1000))
        st.session_state.messages = []
        st.rerun()
    if st.button("💾 Save transcript"):
        data = {"session_id": st.session_state.session_id, "messages": st.session_state.messages}
        st.download_button("Download JSON", data=json.dumps(data, ensure_ascii=False, indent=2), file_name=f"chat_{st.session_state.session_id}.json", mime="application/json")
    st.caption("Transcripts also persist to .chats/{session}.jsonl")

# Apply theme
st.markdown(f"<style>{THEME_CSS_DARK if st.session_state.dark_mode else THEME_CSS_LIGHT}</style>", unsafe_allow_html=True)
st.markdown(CHAT_CSS, unsafe_allow_html=True)

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
st.title("🏠 Multi‑Agent Real Estate Chatbot")
st.caption("Chat with an assistant that can analyze images and answer tenancy FAQs. Supports feedback + memory.")

# Render history
for i, m in enumerate(st.session_state.messages):
    role = m.get("role")
    content = m.get("content", "")
    agent = m.get("agent")
    caption = m.get("caption")
    ts = m.get("ts")
    image_name = m.get("image_name")

    is_user = role == "user"
    row_class = "row right" if is_user else "row"
    avatar_class = "avatar user" if is_user else "avatar bot"
    avatar_text = "U" if is_user else "🤖"

    with st.container():
        st.markdown(f"<div class='{row_class}'>" \
                    f"<div class='{avatar_class}'>{avatar_text}</div>" \
                    f"<div>" \
                    f"<div class='msg {'msg-user' if is_user else 'msg-bot'} codewrap'>{content}</div>" \
                    f"<div class='meta'>{ts}</div>" \
                    f"</div></div>", unsafe_allow_html=True)
        if is_user and image_name:
            st.caption("Attached image:")
            st.image(image_name, caption=image_name, use_column_width=False)
        if not is_user:
            # Assistant metadata
            if agent:
                badge_cls = 'badge ' + ( 'agent1' if agent=='agent_1' else ('agent2' if agent=='agent_2' else 'fallback') )
                st.markdown(f"<span class='{badge_cls}'>Agent: {agent}</span>", unsafe_allow_html=True)
            if caption:
                st.markdown(f"<div class='caption'><b>Caption:</b> {caption}</div>", unsafe_allow_html=True)
            # Feedback row
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
            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

# --- Input row (chat style) ---
col_left, col_right = st.columns([8, 2])
with col_left:
    user_text = st.chat_input("Type a message…")
with col_right:
    upload_slot = st.file_uploader(" ", type=["png", "jpg", "jpeg"], label_visibility="collapsed", accept_multiple_files=False)
    st.caption("📎 Attach an image")

location = st.text_input("📍 Location (optional)", key="loc_input", placeholder="City or Country")

# Call backend helper

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

# Send handler
if user_text is not None:
    # Append user message
    msg_user = {
        "role": "user",
        "content": user_text,
        "agent": None,
        "caption": None,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_name": upload_slot.name if upload_slot else None,
    }
    st.session_state.messages.append(msg_user)
    save_turn(st.session_state.session_id, msg_user)

    # Call backend
    try:
        with st.spinner("Thinking…"):
            res = call_backend(user_text, location, upload_slot)
    except Exception as e:
        res = {"agent": "error", "response": f"Request failed: {e}", "caption": None}

    # Normalize assistant message
    raw = res.get("response") or ""
    try:
        display_text = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except Exception:
        display_text = raw

    msg_bot = {
        "role": "assistant",
        "content": display_text,
        "agent": res.get("agent"),
        "caption": res.get("caption"),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "image_name": None,
    }
    st.session_state.messages.append(msg_bot)
    save_turn(st.session_state.session_id, msg_bot)

    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Built with Streamlit • FastAPI • LangGraph • BLIP • OpenAI • Jinja2 • Persistent sessions")
