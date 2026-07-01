"""Tests for lead scoring behavior."""

from __future__ import annotations

import pandas as pd

from core.schema import load_sample_leads
from core.scoring import score_leads, summarize_leads


def test_score_leads_adds_operating_columns() -> None:
    scored = score_leads(load_sample_leads(), now=pd.Timestamp("2026-06-30"))

    assert {"lead_score", "priority", "sla_status", "recommended_action", "pipeline_value"}.issubset(scored.columns)
    assert scored["lead_score"].between(0, 100).all()
    assert len(scored) == 18


def test_score_leads_flags_uncontacted_new_leads_as_breach() -> None:
    scored = score_leads(load_sample_leads(), now=pd.Timestamp("2026-06-30"))

    maya = scored.loc[scored["lead_id"].eq("L-1001")].iloc[0]

    assert maya["sla_status"] == "Breach"
    assert maya["priority"] == "Hot"


def test_summarize_leads_returns_dashboard_metrics() -> None:
    scored = score_leads(load_sample_leads(), now=pd.Timestamp("2026-06-30"))
    summary = summarize_leads(scored)

    assert summary["total_leads"] == 18
    assert summary["hot_leads"] >= 1
    assert summary["pipeline_value"] > 0

