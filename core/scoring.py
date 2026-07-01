"""Lead scoring, SLA risk detection, and portfolio summaries."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config.settings import settings
from core.schema import normalize_columns, validate_lead_frame

INTENT_POINTS = {
    "ready": 25.0,
    "high": 22.0,
    "medium": 14.0,
    "researching": 8.0,
    "low": 6.0,
}

STATUS_PROBABILITY = {
    "new": 0.12,
    "contacted": 0.15,
    "nurture": 0.07,
    "appointment": 0.26,
    "won": 1.0,
    "lost": 0.0,
}


def _now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc)).tz_localize(None).normalize()


def _days_since(series: pd.Series, now: pd.Timestamp) -> pd.Series:
    dates = pd.to_datetime(series, errors="coerce").dt.tz_localize(None)
    return (now - dates).dt.total_seconds().div(86400).clip(lower=0)


def _priority(score: float) -> str:
    if score >= settings.hot_threshold:
        return "Hot"
    if score >= settings.warm_threshold:
        return "Warm"
    if score >= settings.nurture_threshold:
        return "Nurture"
    return "Low"


def _sla_status(status: str, age_days: float, days_since_contact: float | None) -> str:
    status_key = status.strip().lower()
    if status_key in {"won", "lost"}:
        return "Closed"
    if status_key == "new" and age_days * 24 > settings.sla_hours_new:
        return "Breach"
    if status_key == "contacted" and days_since_contact is not None and days_since_contact * 24 > settings.sla_hours_contacted:
        return "Breach"
    if status_key in {"new", "contacted"}:
        return "Watch"
    return "OK"


def _recommended_action(priority: str, sla_status: str, status: str) -> str:
    if sla_status == "Breach" and status.strip().lower() == "new":
        return "Call now, then send a short value-first follow-up."
    if sla_status == "Breach":
        return "Send a personalized re-engagement touch and schedule a next step."
    if priority == "Hot":
        return "Move to appointment or proposal while intent is fresh."
    if priority == "Warm":
        return "Send a helpful follow-up with one clear question."
    if priority == "Nurture":
        return "Place into weekly nurture with a specific useful resource."
    return "Keep in low-frequency nurture unless new engagement appears."


def score_leads(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Validate, enrich, and score a lead dataframe."""

    normalized = normalize_columns(df)
    validation = validate_lead_frame(normalized)
    if not validation.ok:
        missing = ", ".join(validation.missing_columns)
        raise ValueError(f"Lead CSV is missing required columns: {missing}")

    scored = normalized.copy()
    current_date = now or _now()
    scored["created_at"] = pd.to_datetime(scored["created_at"], errors="coerce")
    scored["last_contacted_at"] = pd.to_datetime(scored["last_contacted_at"], errors="coerce")
    scored["budget"] = pd.to_numeric(scored["budget"], errors="coerce").fillna(0).clip(lower=0)
    scored["timeline_days"] = pd.to_numeric(scored["timeline_days"], errors="coerce").fillna(365).clip(lower=0)
    scored["engagement_score"] = pd.to_numeric(scored["engagement_score"], errors="coerce").fillna(0).clip(0, 100)

    scored["lead_age_days"] = _days_since(scored["created_at"], current_date).fillna(365)
    contact_age = _days_since(scored["last_contacted_at"], current_date)
    scored["days_since_contact"] = contact_age

    recency = (20 - scored["lead_age_days"] * 2.2).clip(lower=0, upper=20)
    intent = scored["intent"].astype(str).str.lower().map(INTENT_POINTS).fillna(8)
    engagement = scored["engagement_score"] / 100 * 18
    budget = np.log1p(scored["budget"]).div(np.log1p(max(scored["budget"].max(), 1))).fillna(0) * 14
    timeline = np.select(
        [
            scored["timeline_days"].le(7),
            scored["timeline_days"].le(30),
            scored["timeline_days"].le(90),
        ],
        [18, 13, 8],
        default=3,
    )
    status_penalty = scored["status"].astype(str).str.lower().map({"lost": -50, "won": -20}).fillna(0)

    raw_score = recency + intent + engagement + budget + timeline + status_penalty
    scored["lead_score"] = raw_score.clip(lower=0, upper=100).round(1)
    scored["priority"] = scored["lead_score"].map(_priority)
    scored["sla_status"] = [
        _sla_status(row.status, row.lead_age_days, None if pd.isna(row.days_since_contact) else row.days_since_contact)
        for row in scored.itertuples()
    ]
    scored["recommended_action"] = [
        _recommended_action(row.priority, row.sla_status, row.status)
        for row in scored.itertuples()
    ]
    scored["conversion_probability"] = scored["status"].astype(str).str.lower().map(STATUS_PROBABILITY).fillna(0.1)
    scored.loc[scored["priority"].eq("Hot"), "conversion_probability"] += 0.08
    scored.loc[scored["priority"].eq("Warm"), "conversion_probability"] += 0.03
    scored["conversion_probability"] = scored["conversion_probability"].clip(0, 1)
    scored["pipeline_value"] = (scored["budget"] * scored["conversion_probability"]).round(0)
    scored["risk_reason"] = np.select(
        [
            scored["sla_status"].eq("Breach"),
            scored["priority"].eq("Hot"),
            scored["days_since_contact"].gt(7),
        ],
        [
            "Response-time SLA is already breached.",
            "High intent, strong engagement, and near-term timeline.",
            "Lead has gone quiet for more than a week.",
        ],
        default="Normal monitoring cadence.",
    )
    return scored.sort_values(["sla_status", "lead_score"], ascending=[True, False]).reset_index(drop=True)


def summarize_leads(scored: pd.DataFrame) -> dict[str, float | int | str]:
    """Summarize the scored lead book for dashboard KPI cards."""

    hot = int(scored["priority"].eq("Hot").sum())
    breaches = int(scored["sla_status"].eq("Breach").sum())
    pipeline = float(scored["pipeline_value"].sum())
    top_source = "No leads"
    if not scored.empty:
        top_source = str(scored.groupby("source")["pipeline_value"].sum().sort_values(ascending=False).index[0])
    return {
        "total_leads": int(len(scored)),
        "hot_leads": hot,
        "sla_breaches": breaches,
        "pipeline_value": pipeline,
        "top_source": top_source,
    }


def source_summary(scored: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scored leads by acquisition source."""

    grouped = (
        scored.groupby("source", dropna=False)
        .agg(
            leads=("lead_id", "count"),
            avg_score=("lead_score", "mean"),
            hot_leads=("priority", lambda values: int((values == "Hot").sum())),
            pipeline_value=("pipeline_value", "sum"),
        )
        .reset_index()
    )
    return grouped.sort_values("pipeline_value", ascending=False)

