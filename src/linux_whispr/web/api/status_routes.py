"""Status API routes."""

from __future__ import annotations

from fastapi import APIRouter

from linux_whispr.constants import VERSION

router = APIRouter(tags=["status"])


@router.get("/status")
async def get_status() -> dict:
    """Get application status and version info."""
    return {
        "version": VERSION,
        "status": "running",
        "app_name": "LinuxWhispr",
    }
