"""Dictionary API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from linux_whispr.features.dictionary import Dictionary

router = APIRouter(tags=["dictionary"])


class AddWordRequest(BaseModel):
    word: str
    source: str = "manual"
    category: str = "general"


def _get_dictionary() -> Dictionary:
    d = Dictionary()
    d.load()
    return d


@router.get("/dictionary")
async def get_dictionary() -> dict:
    """Get all dictionary entries and corrections."""
    d = _get_dictionary()
    return {
        "entries": [asdict(e) for e in d.entries],
        "corrections": [asdict(c) for c in d.corrections],
    }


@router.post("/dictionary/words")
async def add_word(req: AddWordRequest) -> dict:
    """Add a word to the dictionary."""
    d = _get_dictionary()
    d.add_word(req.word, source=req.source, category=req.category)
    d.save()
    return {"status": "ok", "message": f"Word '{req.word}' added"}


@router.delete("/dictionary/words/{word}")
async def remove_word(word: str) -> dict:
    """Remove a word from the dictionary."""
    d = _get_dictionary()
    removed = d.remove_word(word)
    if removed:
        return {"status": "ok", "message": f"Word '{word}' removed"}
    return {"status": "error", "message": f"Word '{word}' not found"}


@router.delete("/dictionary/corrections/{index}")
async def remove_correction(index: int) -> dict:
    """Remove a correction by index."""
    d = _get_dictionary()
    if 0 <= index < len(d.corrections):
        removed = d.corrections.pop(index)
        d.save()
        return {"status": "ok", "message": f"Correction '{removed.heard} → {removed.corrected}' removed"}
    return {"status": "error", "message": "Invalid correction index"}
