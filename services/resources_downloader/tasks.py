"""
tasks.py
========
Celery task wrappers for the download engine.

These tasks bridge the gap between the API/scheduler layer and the engine:
    - FastAPI endpoint calls  →  download_task.delay(...)
    - Celery worker picks up  →  runs DownloadEngine.run()
    - Progress pushed to Redis via  self.update_state()
    - Client polls status via  download_task.AsyncResult(task_id)

Usage:
    from services.resources_downloader.tasks import download_task

    # Queue a background download
    result = download_task.delay("pexels_image", search_term="mountains", item_count=50)

    # Check status
    status = download_task.AsyncResult(result.id)
    print(status.state)   # "STARTED" / "PROGRESS" / "SUCCESS" / "FAILURE"
    print(status.info)    # {"current": 23, "total": 50, "status": "DOWNLOADING", ...}
"""

import logging
from typing import Any, Dict

from core.celery_app import app
from services.resources_downloader.engine import DownloadEngine
from services.resources_downloader.pipelines.registry import get_pipeline

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="resources.download",
    max_retries=2,
    default_retry_delay=60,
)
def download_task(self, pipeline_name: str, **kwargs) -> Dict[str, Any]:
    """
    Celery task that runs a download pipeline in the background.

    Args:
        pipeline_name: Registered pipeline name (e.g. "pexels_image")
        **kwargs: Arguments forwarded to the pipeline factory
                  (search_term, item_count, output_dir, etc.)

    Returns:
        Dict with download results:
            {
                "downloaded": 50,
                "failed": 2,
                "files": ["/data/downloads/cats_0001.jpg", ...],
                "requests_made": 3,
            }
    """
    task_id = self.request.id
    logger.info("Task %s: Starting pipeline '%s' with args: %s", task_id, pipeline_name, kwargs)

    # 1. Create config from the registered pipeline factory
    try:
        factory = get_pipeline(pipeline_name)
        config = factory(**kwargs)
    except (KeyError, TypeError) as e:
        logger.error("Task %s: Failed to create config — %s", task_id, e)
        raise

    # 2. Progress callback — pushes state to Redis via Celery
    def on_progress(current: int, total: int, status: str, meta: Dict):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "status": status,
                "provider": config.api_provider,
                "query": config.search_term,
                **{k: v for k, v in meta.items() if k != "files"},  # don't flood Redis with file lists mid-task
            },
        )

    # 3. Run the engine with progress reporting
    engine = DownloadEngine(config)
    paths = engine.run(on_progress=on_progress)

    result = {
        "downloaded": len(paths),
        "failed": engine._failed,
        "files": [str(p) for p in paths],
        "requests_made": 0,  # TODO: expose from engine if needed
        "provider": config.api_provider,
        "query": config.search_term,
    }

    logger.info("Task %s: Completed — %d files downloaded", task_id, len(paths))
    return result
