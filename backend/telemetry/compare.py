"""Cost-vs-performance comparison across pipelines (CLAUDE.md §9.4).

Aggregates the per-turn `telemetry` rows (tagged by pipeline) plus captured fields into
one summary row per pipeline: number of sessions/turns, **median cost per intake**, p50/p95
**end-to-end latency**, and average **completion rate**. This is the artifact that answers
"which pipeline for production?" from real sessions.

Usage:
  - programmatic:  `from telemetry.compare import aggregate; aggregate()`
  - API:           `GET /api/compare` (staff-gated)
  - CLI:           `python -m telemetry.compare`           (table)
                   `python -m telemetry.compare --csv`     (CSV)

Pure DB reads — contains no clinical content (§9).
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import asdict, dataclass

from intake.questions import required_field_ids
from store.db import IntakeFieldRow, IntakeSession, TelemetryRow, session_scope


@dataclass
class PipelineStats:
    """Aggregated cost/performance for one pipeline."""

    pipeline: str
    sessions: int
    turns: int
    median_cost_per_intake_usd: float
    avg_cost_per_intake_usd: float
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    avg_completion_rate: float


def _percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile (pct in 0..100); None for empty input."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = max(1, min(len(ordered), round(pct / 100 * len(ordered))))
    return round(ordered[rank - 1], 3)


def _median(values: list[float]) -> float:
    """Median of a list (0.0 for empty)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def aggregate() -> list[PipelineStats]:
    """Compute per-pipeline comparison stats from the telemetry + intake tables."""
    required = required_field_ids()
    n_required = len(required) or 1

    with session_scope() as db:
        telemetry = db.query(TelemetryRow).all()
        # completion per session = filled required fields / total required
        field_rows = db.query(IntakeFieldRow.session_id, IntakeFieldRow.field_id).all()
        sessions = db.query(IntakeSession.id, IntakeSession.pipeline).all()

    # session_id -> pipeline (prefer the session row; fall back to telemetry's tag)
    session_pipeline: dict[str, str] = {sid: pipe for sid, pipe in sessions}

    # session_id -> set of captured required field ids
    filled: dict[str, set[str]] = defaultdict(set)
    for sid, fid in field_rows:
        if fid in required:
            filled[sid].add(fid)

    # group telemetry: pipeline -> {session_id -> cost}, pipeline -> [latencies], counts
    cost_by_session: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    latencies: dict[str, list[float]] = defaultdict(list)
    turns: dict[str, int] = defaultdict(int)
    session_ids: dict[str, set[str]] = defaultdict(set)

    for row in telemetry:
        pipe = row.pipeline or session_pipeline.get(row.session_id, "unknown")
        cost_by_session[pipe][row.session_id] += row.stt_cost + row.llm_cost + row.tts_cost
        if row.e2e_latency_ms is not None:
            latencies[pipe].append(row.e2e_latency_ms)
        turns[pipe] += 1
        session_ids[pipe].add(row.session_id)

    stats: list[PipelineStats] = []
    for pipe, per_session_cost in cost_by_session.items():
        costs = list(per_session_cost.values())
        sids = session_ids[pipe]
        completions = [len(filled.get(sid, set())) / n_required for sid in sids]
        stats.append(
            PipelineStats(
                pipeline=pipe,
                sessions=len(sids),
                turns=turns[pipe],
                median_cost_per_intake_usd=round(_median(costs), 6),
                avg_cost_per_intake_usd=round(sum(costs) / len(costs), 6) if costs else 0.0,
                p50_latency_ms=_percentile(latencies[pipe], 50),
                p95_latency_ms=_percentile(latencies[pipe], 95),
                avg_completion_rate=(
                    round(sum(completions) / len(completions), 3) if completions else 0.0
                ),
            )
        )

    stats.sort(key=lambda s: s.median_cost_per_intake_usd)
    return stats


def to_dicts() -> list[dict]:
    """Aggregation as plain dicts (for the API)."""
    return [asdict(s) for s in aggregate()]


def to_csv() -> str:
    """Aggregation as CSV text."""
    rows = to_dicts()
    buf = io.StringIO()
    fields = [
        "pipeline",
        "sessions",
        "turns",
        "median_cost_per_intake_usd",
        "avg_cost_per_intake_usd",
        "p50_latency_ms",
        "p95_latency_ms",
        "avg_completion_rate",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def format_table() -> str:
    """Aggregation as a human-readable text table (for the CLI)."""
    stats = aggregate()
    if not stats:
        return "No telemetry yet. Run some sessions first."
    header = (
        f"{'pipeline':<18}{'sess':>5}{'turns':>6}{'med $/intake':>14}"
        f"{'p50 ms':>9}{'p95 ms':>9}{'completion':>12}"
    )
    lines = [header, "-" * len(header)]
    for s in stats:
        lines.append(
            f"{s.pipeline:<18}{s.sessions:>5}{s.turns:>6}"
            f"{s.median_cost_per_intake_usd:>14.6f}"
            f"{(s.p50_latency_ms or 0):>9.0f}{(s.p95_latency_ms or 0):>9.0f}"
            f"{s.avg_completion_rate * 100:>11.0f}%"
        )
    return "\n".join(lines)


def _main() -> None:
    import sys

    from store.db import init_db

    init_db()  # safe on a fresh DB (no-op if tables exist)
    if "--csv" in sys.argv:
        print(to_csv())
    else:
        print(format_table())


if __name__ == "__main__":
    _main()
