# streamlit_app.py
import os
import json
import time
import requests
import streamlit as st

# ------------------------------
# Config
# ------------------------------
BACKEND_URL = os.getenv("ST_BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"

st.set_page_config(page_title="Multi‑Agent Real Estate Bot", page_icon="🏠", layout="centered")
st.title("🏠 Multi‑Agent Real Estate Chatbot")
st.caption("Image + Text | Agentic routing with feedback & memory")

# Session id
def _get_session_id() -> str:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(int(time.time()*1000))
    return st.session_state.session_id

sid = _get_session_id()

with st.sidebar:
    st.header("⚙️ Settings")
    st.text_input("Backend URL", value=BACKEND_URL, key="backend")
    st.write("Session:", sid)
    st.info("Set environment var ST_BACKEND_URL to change default backend.")

# Inputs
col1, col2 = st.columns(2)
with col1:
    location = st.text_input("📍 Location (optional)", placeholder="City or Country")
with col2:
    feedback_choice = st.selectbox("Feedback (optional)", ["", "up", "down"], index=0)

text = st.text_area("💬 Your message", placeholder="Ask a tenancy question or describe the issue…", height=120)
image_file = st.file_uploader("🖼️ Upload a property image (optional)", type=["jpg", "jpeg", "png"]) 

# Call backend
def call_backend(text: str, location: str, feedback: str, image_file) -> dict:
    url = f"{st.session_state.backend if 'backend' in st.session_state else BACKEND_URL}/chat"
    data = {
        "session_id": sid,
        "text": text or "",
        "location": location or "",
        "feedback": feedback or "",
    }
    files = None
    if image_file is not None:
        files = {"image": (image_file.name, image_file.getvalue(), image_file.type or "application/octet-stream")}

    resp = requests.post(url, data=data, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()

send = st.button("🚀 Send")

if send:
    if not text and not image_file:
        st.warning("Please enter a message or upload an image.")
    else:
        with st.spinner("Thinking…"):
            try:
                res = call_backend(text, location, feedback_choice, image_file)
                st.session_state.last_response = res
            except Exception as e:
                st.error(f"Request failed: {e}")

# Display
if "last_response" in st.session_state:
    res = st.session_state.last_response
    st.subheader("🤖 Agent Response")
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        st.metric("Agent", res.get("agent", "?"))
    with meta_col2:
        st.caption("Caption (if image)")
        st.code(res.get("caption") or "—", language="text")

    # Try pretty JSON first
    raw = res.get("response") or ""
    try:
        st.json(json.loads(raw))
    except Exception:
        st.write(raw)

    st.divider()
    st.subheader("👍 Quick Feedback")
    fb_cols = st.columns(3)
    with fb_cols[0]:
        if st.button("👍 Helpful"):
            try:
                call_backend("", location, "up", None)
                st.success("Thanks for the feedback!")
            except Exception as e:
                st.error(f"Feedback failed: {e}")
    with fb_cols[1]:
        if st.button("👎 Not helpful"):
            try:
                call_backend("", location, "down", None)
                st.success("Thanks, we will use this to improve.")
            except Exception as e:
                st.error(f"Feedback failed: {e}")
    with fb_cols[2]:
        st.caption("Feedback is stored server‑side in JSONL (see .feedback.jsonl)")

st.divider()
st.markdown("""
**How to run:**
1. Ensure your FastAPI backend is running on `http://127.0.0.1:8000`.
2. In another terminal:
   ```bash
   streamlit run streamlit_app.py
   ```
3. Optionally set a different backend:
   ```bash
   ST_BACKEND_URL=http://localhost:8000 streamlit run streamlit_app.py
   ```
""")
