from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from app.api.routes import auth, user, admin, chatroom, message, websocket, meeting
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.core.ai_service import analyze_meeting

app = FastAPI()
AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/uploads/avatars",
    StaticFiles(directory=str(AVATAR_DIR)),
    name="avatars",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)
app.include_router(chatroom.router)
app.include_router(message.router)
app.include_router(websocket.router)
app.include_router(meeting.router)

@app.get("/test-meeting-ai")
async def test_meeting_ai():
    conversation = """
    Fahad: Can we meet tomorrow at 3 PM to discuss the project?
    Ahmed: Yes, that works for me.
    """

    result = await analyze_meeting(conversation)

    return result