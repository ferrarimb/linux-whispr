"""Model management API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from linux_whispr.config import AppConfig
from linux_whispr.stt.model_manager import ModelManager

router = APIRouter(tags=["models"])


def _get_model_manager() -> ModelManager:
    return ModelManager()


@router.get("/models")
async def list_models() -> dict:
    """List all supported Whisper models with download status."""
    mm = _get_model_manager()
    config = AppConfig.load()
    models = mm.list_models()
    return {
        "models": [
            {
                "name": m.name,
                "size_mb": m.size_mb,
                "downloaded": m.downloaded,
                "active": m.name == config.stt.model,
            }
            for m in models
        ],
        "active_model": config.stt.model,
    }


@router.post("/models/{name}/download")
async def download_model(name: str) -> dict:
    """Download a Whisper model."""
    mm = _get_model_manager()
    try:
        mm.download(name)
        return {"status": "ok", "message": f"Model '{name}' downloaded"}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Download failed: {e}"}


@router.delete("/models/{name}")
async def delete_model(name: str) -> dict:
    """Delete a downloaded model."""
    mm = _get_model_manager()
    deleted = mm.delete(name)
    if deleted:
        return {"status": "ok", "message": f"Model '{name}' deleted"}
    return {"status": "error", "message": f"Model '{name}' not found or not downloaded"}


@router.get("/models/disk-usage")
async def get_disk_usage() -> dict:
    """Get total disk usage of downloaded models."""
    mm = _get_model_manager()
    usage_bytes = mm.get_disk_usage()
    return {
        "bytes": usage_bytes,
        "mb": round(usage_bytes / (1024 * 1024), 1),
        "gb": round(usage_bytes / (1024 * 1024 * 1024), 2),
    }
