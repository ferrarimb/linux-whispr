"""Configuration API routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from linux_whispr.config import AppConfig

router = APIRouter(tags=["config"])


def _get_config() -> AppConfig:
    return AppConfig.load()


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _strip_none(v)
        elif v is not None:
            result[k] = v
    return result


@router.get("/config")
async def get_config() -> dict:
    """Get the full application configuration."""
    config = _get_config()
    return _strip_none(asdict(config))


@router.put("/config")
async def update_config(data: dict[str, Any]) -> dict:
    """Update configuration with partial data. Merges with existing config."""
    config = _get_config()

    section_map = {
        "audio": config.audio,
        "stt": config.stt,
        "ai": config.ai,
        "hotkey": config.hotkey,
        "injection": config.injection,
        "history": config.history,
        "adaptive": config.adaptive,
    }

    for section_name, section_obj in section_map.items():
        if section_name in data and isinstance(data[section_name], dict):
            for key, val in data[section_name].items():
                if hasattr(section_obj, key):
                    setattr(section_obj, key, val)

    if "autostart" in data:
        config.autostart = data["autostart"]
    if "first_run" in data:
        config.first_run = data["first_run"]

    config.save()
    return {"status": "ok", "message": "Configuration saved"}


@router.post("/config/reset")
async def reset_config() -> dict:
    """Reset configuration to defaults."""
    config = AppConfig()
    config.save()
    return {"status": "ok", "message": "Configuration reset to defaults"}
