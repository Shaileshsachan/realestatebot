from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from app.langgraph_builder import build_graph
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Real Estate Bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.streamlit.app","https://fatakpay.streamlit.app"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
_graph = build_graph()

@app.post("/chat")
async def chat(
    session_id: str = Form(...),
    text: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    feedback: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    image_bytes = await image.read() if image else None

    state = {
        "session_id": session_id,
        "text": text,
        "location": location,
        "feedback": feedback,
        "image": image_bytes,
    }

    result = _graph.invoke(state)

    payload = {
        "agent": result.get("agent"),
        "caption": result.get("caption"),
        "response": result.get("response"),
    }
    return JSONResponse(payload)