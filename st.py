# streamlit_app.py
import os
import json
import time
import requests
import streamlit as st
from datetime import datetime

# ------------------------------
# Config
# ------------------------------
BACKEND_URL_DEFAULT = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT_PATH = "/chat"

st.set_page_config(page_title="Multi‑Agent Real Estate Chatbot", page_icon="🏠", layout="wide")

# ------------------------------
# Styles (chat bubbles)
# ------------------------------
CHAT_CSS = """
<style>
.chat-container {max-width: 860px; margin: 0 auto;}
.msg {padding: 0.75rem 1rem; border-radius: 18px; margin: 0.25rem 0; display: inline-block;}
.msg-user {background: #2563eb; color: white; border-bottom-right-radius: 6px;}
.msg-bot {background: #f3f4f6; color: #0f172a; border-bottom-left-radius: 6px;}
.meta {font-size: 0.75rem; color: #6b7280; margin-top: 0.15rem;}
.row {display: flex; gap: .5rem; align-items: flex-end;}
.row.right {justify-content: flex-end;}
.avatar {width: 36px; height: 36px; border-radius: 9999px; background: #e5e7eb; display:flex; align-items:center; justify-content:center; font-weight:600;}
.avatar.user {background:#1d4ed8; color:#fff;}
.avatar.bot {background:#e5e7eb; color:#111827;}
.codewrap {white-space: pre-wrap; word-break: break-word;}
.caption {font-size:.8rem; color:#4b5563; margin-top:.25rem}
.badge {display:inline-block; padding:.1rem .5rem; border-radius:9999px; font-size:.70rem; background:#e5e7eb; color:#111827;}
.badge.agent1{background:#dcfce7; color:#065f46}
.badge.agent2{background:#e0e7ff; color:#3730a3}
.badge.fallback{background:#fee2e2; color:#991b1b}
.hr{height:1px;background:#e5e7eb;margin:1rem 0}
</style>
"""

# ------------------------------
# Session state
# ------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role: "user"|"assistant", content:str, agent:str|None, caption:str|None, ts:str}]
if "session_id" not in st.session_state:
    st.session_state.session_id = str(int(time.time()*1000))
if "backend_url" not in st.session_state:
    st.session_state.backend_url = BACKEND_URL_DEFAULT

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.backend_url = st.text_input("Backend URL", value=st.session_state.backend_url)
    st.write("Session:", st.session_state.session_id)
    st.caption("Change the backend if deploying FastAPI elsewhere.")
    st.markdown("**Tips**\n- Send an image with the 📎 button\n- Use feedback buttons under assistant replies")

st.markdown(CHAT_CSS, unsafe_allow_html=True)

st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
st.title("🏠 Multi‑Agent Real Estate Chatbot")
st.caption("Agentic routing • Image + Text • Feedback + Memory")

# Render history
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
        st.markdown(f"<div class='{row_class}'>" \
                    f"<div class='{avatar_class}'>{avatar_text}</div>" \
                    f"<div>" \
                    f"<div class='msg {'msg-user' if is_user else 'msg-bot'} codewrap'>{content}</div>" \
                    f"<div class='meta'>{ts}</div>" \
                    f"</div></div>", unsafe_allow_html=True)
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
                        st.success("Appreciate the signal — we’ll improve.")
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

# Send handler
if user_text is not None:
    # Append user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_text,
        "agent": None,
        "caption": None,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    # Prepare request
    data = {
        "session_id": st.session_state.session_id,
        "text": user_text,
        "location": location,
    }
    files = None
    if upload_slot is not None:
        files = {"image": (upload_slot.name, upload_slot.getvalue(), upload_slot.type or "application/octet-stream")}

    # Call backend
    try:
        with st.spinner("Thinking…"):
            resp = requests.post(st.session_state.backend_url + CHAT_ENDPOINT_PATH, data=data, files=files, timeout=90)
            resp.raise_for_status()
            res = resp.json()
    except Exception as e:
        res = {"agent": "error", "response": f"Request failed: {e}", "caption": None}

    # Normalize assistant message
    display_text = ""
    raw = res.get("response") or ""
    try:
        display_text = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except Exception:
        display_text = raw

    st.session_state.messages.append({
        "role": "assistant",
        "content": display_text,
        "agent": res.get("agent"),
        "caption": res.get("caption"),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    st.experimental_rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.caption("Built with Streamlit • FastAPI • LangGraph • BLIP • OpenAI • Jinja2")
