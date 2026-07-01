"""Versioned prompt templates for lead follow-up generation."""

from __future__ import annotations

FOLLOWUP_PROMPT_VERSION = "lead-followup-v1.0"


def followup_prompt(lead: dict[str, object], vertical: str, tone: str) -> str:
    """Build a concise prompt for a small-business lead follow-up."""

    return f"""
Prompt version: {FOLLOWUP_PROMPT_VERSION}

You are Aristotle Lead Guardian, an AI sales operations agent for a {vertical} business.
Write a practical follow-up for the lead below. Use a {tone} tone.

Rules:
- Return markdown with exactly three sections: "Recommended move", "Email draft", and "SMS draft".
- Keep the email under 120 words.
- Keep the SMS under 280 characters.
- Do not invent unavailable facts.
- Reference the lead context when useful.
- Make the next step specific and easy to answer.

Lead:
- Name: {lead.get("name")}
- Status: {lead.get("status")}
- Source: {lead.get("source")}
- Intent: {lead.get("intent")}
- Timeline days: {lead.get("timeline_days")}
- Budget/deal size: {lead.get("budget")}
- Engagement score: {lead.get("engagement_score")}
- Priority: {lead.get("priority")}
- SLA status: {lead.get("sla_status")}
- Risk reason: {lead.get("risk_reason")}
- Notes: {lead.get("notes")}
""".strip()

