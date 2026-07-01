"""Tests for follow-up generation fallback behavior."""

from __future__ import annotations

from agents.followup_agent import offline_followup


def test_offline_followup_contains_required_sections() -> None:
    lead = {
        "name": "Maya Patel",
        "priority": "Hot",
        "sla_status": "Breach",
        "status": "New",
        "timeline_days": 7,
        "notes": "Asked about school districts",
    }

    text = offline_followup(lead)

    assert "### Recommended move" in text
    assert "### Email draft" in text
    assert "### SMS draft" in text
    assert "Maya" in text

