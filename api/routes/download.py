"""
download.py — Endpoints for resource downloading.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class DownloadRequest(BaseModel):
    pipeline: str = "pexels_image"
    search_term: str
    count: int = 25


@router.post("/")
def start_download(req: DownloadRequest):
    from services.resources_downloader.tasks import download_task
    task = download_task.delay(req.pipeline, search_term=req.search_term, item_count=req.count)
    return {"task_id": task.id, "status": "queued"}


@router.get("/status/{task_id}")
def check_download_status(task_id: str):
    from services.resources_downloader.tasks import download_task
    result = download_task.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.state, "info": result.info}
