"""
FastAPI entry point.

Dev:  uvicorn app.main:app --reload --port 8000  +  npm run dev (port 5173)
Prod: npm run build  then  uvicorn app.main:app --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.proxy import router as proxy_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="TEG Chatbot API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(proxy_router)

DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
