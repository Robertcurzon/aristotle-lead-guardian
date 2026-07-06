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


def followup_debt(scored: pd.DataFrame) -> pd.DataFrame:
    """Bucket leads by how long they have gone without follow-up."""

    debt = scored.copy()
    debt["followup_age_days"] = debt["days_since_contact"].fillna(debt["lead_age_days"])
    debt["bucket"] = pd.cut(
        debt["followup_age_days"],
        bins=[-1, 1, 3, 7, float("inf")],
        labels=["0-24h", "1-3d", "4-7d", "7d+"],
    )
    grouped = (
        debt.groupby("bucket", observed=False)
        .agg(leads=("lead_id", "count"), pipeline_value=("pipeline_value", "sum"))
        .reset_index()
    )
    return grouped


def source_leakage(scored: pd.DataFrame) -> pd.DataFrame:
    """Calculate missed-follow-up leakage by acquisition source."""

    source = scored.copy()
    source["leaking"] = source["sla_status"].eq("Breach") | source["days_since_contact"].gt(3)
    grouped = (
        source.groupby("source", dropna=False)
        .agg(
            leads=("lead_id", "count"),
            leaking_leads=("leaking", "sum"),
            pipeline_value=("pipeline_value", "sum"),
            leaked_pipeline=("pipeline_value", lambda values: float(values[source.loc[values.index, "leaking"]].sum())),
        )
        .reset_index()
    )
    grouped["leakage_rate"] = (grouped["leaking_leads"] / grouped["leads"]).fillna(0)
    return grouped.sort_values(["leakage_rate", "pipeline_value"], ascending=[False, False])


def playbook_mix(queue: pd.DataFrame) -> pd.DataFrame:
    """Summarize recommended lead rescue playbooks."""

    return (
        queue.groupby("playbook", dropna=False)
        .agg(actions=("lead_id", "count"), pipeline_value=("pipeline_value", "sum"))
        .reset_index()
        .sort_values("actions", ascending=False)
    )


def rescue_funnel(scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    """Build a high-level lead rescue funnel."""

    needs_work = queue["rescue_stage"].isin(["Rescue now", "Convert today", "Work today"])
    at_risk = scored["sla_status"].eq("Breach") | scored["priority"].isin(["Hot", "Warm"])
    ready = queue["agent_status"].eq("Ready to send")
    approval = queue["agent_status"].eq("Needs approval")
    return pd.DataFrame(
        [
            {"stage": "Total leads", "count": int(len(scored))},
            {"stage": "Needs work", "count": int(needs_work.sum())},
            {"stage": "At risk", "count": int(at_risk.sum())},
            {"stage": "Ready to send", "count": int(ready.sum())},
            {"stage": "Human approval", "count": int(approval.sum())},
        ]
    )


def agent_workload(queue: pd.DataFrame) -> dict[str, int]:
    """Return counts for agent-ready and human-review work."""

    return {
        "total_actions": int(queue["rescue_stage"].isin(["Rescue now", "Convert today", "Work today"]).sum()),
        "ready_to_send": int(queue["agent_status"].eq("Ready to send").sum()),
        "needs_approval": int(queue["agent_status"].eq("Needs approval").sum()),
    }


def lead_book_health_score(scored: pd.DataFrame) -> int:
    """Calculate a compact 0-100 lead book health score."""

    if scored.empty:
        return 0
    active = scored.loc[~scored["status"].astype(str).str.lower().isin(["won", "lost"])]
    if active.empty:
        return 100
    sla_health = 1 - active["sla_status"].eq("Breach").mean()
    hot = active.loc[active["priority"].eq("Hot")]
    hot_coverage = 1.0 if hot.empty else 1 - hot["sla_status"].eq("Breach").mean()
    recent_followup = active["days_since_contact"].fillna(active["lead_age_days"]).le(3).mean()
    score = (0.45 * sla_health + 0.35 * hot_coverage + 0.20 * recent_followup) * 100
    return int(round(max(0, min(100, score))))


def rescue_impact_estimate(scored: pd.DataFrame, recovery_rate: float = 0.20, commission_rate: float = 0.03) -> dict[str, float]:
    """Estimate upside if a share of at-risk pipeline is recovered."""

    risk = at_risk_pipeline(scored)
    recovered_pipeline = risk * recovery_rate
    estimated_revenue = recovered_pipeline * commission_rate
    return {
        "at_risk_pipeline": risk,
        "recovered_pipeline": recovered_pipeline,
        "estimated_revenue": estimated_revenue,
    }
