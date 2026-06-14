"""Tests for the cost-vs-performance pipeline comparison aggregation."""

import uuid

import pytest

from store.db import IntakeFieldRow, IntakeSession, TelemetryRow, init_db, session_scope
from telemetry import compare


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _seed(
    pipeline: str,
    session_id: str,
    costs: list[float],
    latencies: list[float],
    fields: list[str],
) -> None:
    with session_scope() as db:
        db.add(IntakeSession(id=session_id, pipeline=pipeline))
        for fid in fields:
            db.add(IntakeFieldRow(session_id=session_id, field_id=fid))
        for i, (c, lat) in enumerate(zip(costs, latencies, strict=False)):
            db.add(
                TelemetryRow(
                    session_id=session_id,
                    turn_index=i,
                    pipeline=pipeline,
                    llm_cost=c,
                    e2e_latency_ms=lat,
                )
            )


def test_aggregate_groups_and_costs_by_pipeline() -> None:
    p1 = f"cmp-a-{uuid.uuid4().hex[:6]}"
    p2 = f"cmp-b-{uuid.uuid4().hex[:6]}"
    # p1: two sessions, session costs 0.3 and 0.3 -> median 0.3
    _seed(p1, f"{p1}-s1", [0.1, 0.2], [100.0, 200.0], ["chief_complaint"])
    _seed(p1, f"{p1}-s2", [0.3], [300.0], ["chief_complaint", "severity"])
    # p2: one expensive session
    _seed(p2, f"{p2}-s1", [1.0], [1000.0], [])

    stats = {s.pipeline: s for s in compare.aggregate()}

    a = stats[p1]
    assert a.sessions == 2
    assert a.turns == 3
    assert a.median_cost_per_intake_usd == pytest.approx(0.3)
    assert a.p50_latency_ms == 200.0  # median of [100,200,300]
    assert 0.0 < a.avg_completion_rate < 1.0

    b = stats[p2]
    assert b.sessions == 1
    assert b.median_cost_per_intake_usd == pytest.approx(1.0)
    assert b.avg_completion_rate == 0.0


def test_outputs_serialize() -> None:
    pipe = f"cmp-csv-{uuid.uuid4().hex[:6]}"
    _seed(pipe, f"{pipe}-s1", [0.5], [150.0], ["chief_complaint"])
    dicts = compare.to_dicts()
    assert any(d["pipeline"] == pipe for d in dicts)
    csv_text = compare.to_csv()
    assert "pipeline" in csv_text.splitlines()[0]
