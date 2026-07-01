"""Tests for operational rescue desk views."""

from __future__ import annotations

import pandas as pd

from core.ops import action_queue, autopilot_frame, pipeline_summary
from core.schema import load_sample_leads
from core.scoring import score_leads


def test_action_queue_adds_rescue_fields() -> None:
    scored = score_leads(load_sample_leads(), now=pd.Timestamp("2026-06-30"))
    queue = action_queue(scored)

    assert {"rescue_stage", "playbook", "agent_status"}.issubset(queue.columns)
    assert queue.iloc[0]["rescue_stage"] == "Rescue now"


def test_pipeline_summary_includes_core_stages() -> None:
    scored = score_leads(load_sample_leads(), now=pd.Timestamp("2026-06-30"))
    stages = pipeline_summary(scored)

    assert list(stages["status"]) == ["New", "Contacted", "Nurture", "Appointment", "Won", "Lost"]
    assert stages["leads"].sum() == len(scored)


def test_autopilot_frame_has_enabled_rules() -> None:
    rules = autopilot_frame()

    assert "Instant new-lead response" in set(rules["name"])
    assert rules["enabled"].any()

