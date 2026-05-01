"""
main.py — FastAPI application entry point.

Run: uvicorn api.main:app --reload
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import content, media, social, download, scheduler, health

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")

app = FastAPI(
    title="SMA-Enterprise",
    description="Enterprise Social Media Automation Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, tags=["Health"])
app.include_router(content.router, prefix="/content", tags=["Content"])
app.include_router(media.router, prefix="/media", tags=["Media"])
app.include_router(social.router, prefix="/social", tags=["Social"])
app.include_router(download.router, prefix="/download", tags=["Download"])
app.include_router(scheduler.router, prefix="/schedule", tags=["Scheduler"])
