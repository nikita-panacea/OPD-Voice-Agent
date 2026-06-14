"""Comparison endpoints: cost-vs-performance across pipelines (CLAUDE.md §9.4).

Exposes the `telemetry.compare` aggregation over the API for a future dashboard / CSV export.
Staff-gated (reuses the `require_staff` dependency).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from api.sessions import require_staff
from telemetry import compare

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/compare", dependencies=[Depends(require_staff)])
def compare_pipelines() -> list[dict]:
    """Per-pipeline cost-vs-performance summary (cost/intake, latency, completion)."""
    return compare.to_dicts()


@router.get("/compare.csv", dependencies=[Depends(require_staff)])
def compare_pipelines_csv() -> Response:
    """Same comparison as CSV for spreadsheet export."""
    return Response(content=compare.to_csv(), media_type="text/csv")
