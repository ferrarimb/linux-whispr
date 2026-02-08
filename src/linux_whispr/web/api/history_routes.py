"""History API routes."""

from __future__ import annotations

import json
from dataclasses import asdict

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from linux_whispr.features.history import HistoryManager

router = APIRouter(tags=["history"])


def _get_history_manager() -> HistoryManager:
    hm = HistoryManager()
    hm.open()
    return hm


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str = Query("", description="Search query"),
) -> dict:
    """Get paginated transcription history."""
    hm = _get_history_manager()
    try:
        if q:
            entries = hm.search(q, limit=limit * page)
            # Manual pagination over search results
            start = (page - 1) * limit
            page_entries = entries[start : start + limit]
            total = len(entries)
        else:
            # For pagination without search, get a larger set and slice
            all_entries = hm.get_recent(limit=limit * page + limit)
            start = (page - 1) * limit
            page_entries = all_entries[start : start + limit]
            total_entries = hm.get_recent(limit=10000)
            total = len(total_entries)

        return {
            "entries": [asdict(e) for e in page_entries],
            "page": page,
            "limit": limit,
            "total": total,
            "has_more": page * limit < total,
        }
    finally:
        hm.close()


@router.get("/history/stats")
async def get_history_stats() -> dict:
    """Get aggregate history statistics."""
    hm = _get_history_manager()
    try:
        all_entries = hm.get_recent(limit=100000)
        total_entries = len(all_entries)
        total_words = sum(e.word_count for e in all_entries)
        total_duration = sum(e.duration for e in all_entries)
        avg_duration = total_duration / total_entries if total_entries > 0 else 0.0

        # Today's entries
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        today_entries = [e for e in all_entries if e.timestamp.startswith(today)]
        today_count = len(today_entries)
        today_words = sum(e.word_count for e in today_entries)

        # Languages used
        languages = {}
        for e in all_entries:
            lang = e.language or "unknown"
            languages[lang] = languages.get(lang, 0) + 1

        return {
            "total_entries": total_entries,
            "total_words": total_words,
            "total_duration": round(total_duration, 1),
            "avg_duration": round(avg_duration, 1),
            "today_entries": today_count,
            "today_words": today_words,
            "languages": languages,
        }
    finally:
        hm.close()


@router.delete("/history/{entry_id}")
async def delete_history_entry(entry_id: int) -> dict:
    """Delete a single history entry."""
    hm = _get_history_manager()
    try:
        deleted = hm.delete(entry_id)
        if deleted:
            return {"status": "ok", "message": f"Entry {entry_id} deleted"}
        return {"status": "error", "message": f"Entry {entry_id} not found"}
    finally:
        hm.close()


@router.delete("/history")
async def clear_history() -> dict:
    """Delete all history entries."""
    hm = _get_history_manager()
    try:
        count = hm.clear()
        return {"status": "ok", "message": f"Cleared {count} entries"}
    finally:
        hm.close()


@router.get("/history/export")
async def export_history() -> JSONResponse:
    """Export all history as JSON."""
    hm = _get_history_manager()
    try:
        entries = hm.get_recent(limit=100000)
        data = [asdict(e) for e in entries]
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": "attachment; filename=linux-whispr-history.json"},
        )
    finally:
        hm.close()
