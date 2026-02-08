"""Snippets API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from linux_whispr.features.snippets import SnippetEngine

router = APIRouter(tags=["snippets"])


class AddSnippetRequest(BaseModel):
    trigger: str
    expansion: str


def _get_snippets() -> SnippetEngine:
    se = SnippetEngine()
    se.load()
    return se


@router.get("/snippets")
async def get_snippets() -> dict:
    """Get all snippets."""
    se = _get_snippets()
    return {
        "snippets": [{"trigger": s.trigger, "expansion": s.expansion} for s in se.snippets],
    }


@router.post("/snippets")
async def add_snippet(req: AddSnippetRequest) -> dict:
    """Add a new snippet."""
    se = _get_snippets()
    se.add(req.trigger, req.expansion)
    return {"status": "ok", "message": f"Snippet '{req.trigger}' added"}


@router.delete("/snippets/{trigger}")
async def remove_snippet(trigger: str) -> dict:
    """Remove a snippet by trigger phrase."""
    se = _get_snippets()
    removed = se.remove(trigger)
    if removed:
        return {"status": "ok", "message": f"Snippet '{trigger}' removed"}
    return {"status": "error", "message": f"Snippet '{trigger}' not found"}
