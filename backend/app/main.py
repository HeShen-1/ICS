"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, sessions, chat, knowledge, feedback, stats

app = FastAPI(title="ICS Customer Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(feedback.router)
app.include_router(stats.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ICS Customer Service"}
