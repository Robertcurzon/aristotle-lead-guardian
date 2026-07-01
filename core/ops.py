"""Operational views for the Lead Rescue Desk."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PIPELINE_STAGES = ["New", "Contacted", "Nurture", "Appointment", "Won", "Lost"]


@dataclass(frozen=True)
class AutopilotRule:
    """Configurable automation shown in the operator console."""

    name: str
    trigger: str
    action: str
    owner_review: bool
    enabled: bool


AUTOPILOT_RULES = [
    AutopilotRule(
        name="Instant new-lead response",
        trigger="New lead arrives from web, portal, ad, or referral",
        action="Send SMS/email acknowledgment and ask one qualifying question",
        owner_review=False,
        enabled=True,
    ),
    AutopilotRule(
        name="Missed follow-up rescue",
        trigger="SLA breach or no contact within the configured window",
        action="Draft a direct rescue touch and move lead to today's queue",
        owner_review=True,
        enabled=True,
    ),
    AutopilotRule(
        name="Appointment conversion push",
        trigger="Hot lead with near-term timeline and no appointment",
        action="Recommend call script and appointment slot request",
        owner_review=True,
        enabled=True,
    ),
    AutopilotRule(
        name="Cold lead reactivation",
        trigger="Quiet nurture lead with budget and recent engagement",
        action="Send useful market/resource touch and ask if timing changed",
        owner_review=True,
        enabled=False,
    ),
    AutopilotRule(
        name="Review and referral ask",
        trigger="Lead marked Won",
        action="Draft review request and referral ask",
        owner_review=True,
        enabled=False,
    ),
]


def rescue_stage(row: pd.Series) -> str:
    """Return the operational rescue bucket for a scored lead."""

    if row["sla_status"] == "Breach":
        return "Rescue now"
    if row["priority"] == "Hot":
        return "Convert today"
    if row["priority"] == "Warm":
        return "Work today"
    if row["priority"] == "Nurture":
        return "Nurture"
    return "Monitor"


def playbook_for_lead(row: pd.Series) -> str:
    """Return the best-fit small-business playbook for a scored lead."""

    status = str(row["status"]).lower()
    if row["sla_status"] == "Breach" and status == "new":
        return "Speed-to-lead rescue"
    if row["sla_status"] == "Breach":
        return "Follow-up recovery"
    if row["priority"] == "Hot" and status != "appointment":
        return "Appointment setter"
    if row["priority"] == "Warm":
        return "Qualification touch"
    if status == "won":
        return "Review/referral ask"
    return "Nurture sequence"


def action_queue(scored: pd.DataFrame) -> pd.DataFrame:
    """Return the work queue ordered by operational urgency."""

    queue = scored.copy()
    queue["rescue_stage"] = queue.apply(rescue_stage, axis=1)
    queue["playbook"] = queue.apply(playbook_for_lead, axis=1)
    queue["agent_status"] = queue["rescue_stage"].map(
        {
            "Rescue now": "Needs approval",
            "Convert today": "Ready to send",
            "Work today": "Ready to send",
            "Nurture": "Scheduled",
            "Monitor": "Watching",
        }
    )
    stage_rank = {"Rescue now": 0, "Convert today": 1, "Work today": 2, "Nurture": 3, "Monitor": 4}
    queue["stage_rank"] = queue["rescue_stage"].map(stage_rank).fillna(9)
    return queue.sort_values(["stage_rank", "lead_score", "pipeline_value"], ascending=[True, False, False]).reset_index(drop=True)


def pipeline_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the pipeline by stage."""

    grouped = (
        scored.groupby("status", dropna=False)
        .agg(
            leads=("lead_id", "count"),
            pipeline_value=("pipeline_value", "sum"),
            avg_score=("lead_score", "mean"),
            at_risk=("sla_status", lambda values: int((values == "Breach").sum())),
        )
        .reindex(PIPELINE_STAGES)
        .fillna({"leads": 0, "pipeline_value": 0, "avg_score": 0, "at_risk": 0})
        .reset_index(names="status")
    )
    return grouped


def at_risk_pipeline(scored: pd.DataFrame) -> float:
    """Return estimated pipeline value attached to leads needing attention."""

    risky = scored.loc[scored["sla_status"].eq("Breach") | scored["priority"].isin(["Hot", "Warm"])]
    return float(risky["pipeline_value"].sum())


def conversation_timeline(lead: dict[str, object]) -> list[dict[str, str]]:
    """Build a deterministic conversation timeline for a lead."""

    created = str(lead.get("created_at", ""))[:10]
    last_contacted = str(lead.get("last_contacted_at", ""))[:10]
    timeline = [
        {
            "label": "Lead captured",
            "date": created,
            "body": f"{lead.get('source')} created a {lead.get('intent')} intent lead. Notes: {lead.get('notes')}",
        }
    ]
    if last_contacted and last_contacted != "NaT":
        timeline.append(
            {
                "label": "Last human touch",
                "date": last_contacted,
                "body": f"Status moved to {lead.get('status')}. Engagement score is {lead.get('engagement_score')}/100.",
            }
        )
    timeline.append(
        {
            "label": "Agent recommendation",
            "date": "Today",
            "body": f"{lead.get('recommended_action')} Reason: {lead.get('risk_reason')}",
        }
    )
    return timeline


def autopilot_frame() -> pd.DataFrame:
    """Return autopilot rules as a dataframe."""

    return pd.DataFrame([rule.__dict__ for rule in AUTOPILOT_RULES])

