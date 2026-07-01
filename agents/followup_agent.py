"""Follow-up generation agent with deterministic and Claude-backed modes."""

from __future__ import annotations

from typing import Any

from agents.prompts import followup_prompt
from config.settings import settings


def offline_followup(lead: dict[str, Any], vertical: str = "Real estate", tone: str = "warm and direct") -> str:
    """Generate a deterministic follow-up when no LLM key is configured."""

    name = str(lead.get("name", "there")).split()[0]
    priority = str(lead.get("priority", "Warm"))
    notes = str(lead.get("notes", ""))
    timeline = lead.get("timeline_days", "soon")
    status = str(lead.get("status", "New")).lower()

    if str(lead.get("sla_status", "")).lower() == "breach":
        move = "Call first because the response-time SLA is already breached, then send the email/SMS below."
    elif priority == "Hot":
        move = "Try to convert the live intent into a scheduled appointment or proposal today."
    elif priority == "Warm":
        move = "Send one useful, specific follow-up and ask a simple qualifying question."
    else:
        move = "Keep the lead in nurture and look for a new engagement signal before heavy follow-up."

    context = f" I saw your note about {notes.rstrip('.')}" if notes else ""
    if status == "new":
        opening = "Thanks for reaching out"
    else:
        opening = "Wanted to follow up"

    return f"""### Recommended move
{move}

### Email draft
Subject: Quick next step

Hi {name},

{opening}.{context} Based on your timeline of about {timeline} days, the most useful next step is a quick conversation so we can narrow the options and avoid wasting your time.

Are you open to a 10-minute call today or tomorrow?

Best,
Your team

### SMS draft
Hi {name}, thanks for the interest. Based on your timeline, would a quick 10-minute call today or tomorrow help narrow the best next step?"""


async def generate_followup(
    lead: dict[str, Any],
    vertical: str = "Real estate",
    tone: str = "warm and direct",
) -> str:
    """Generate a follow-up plan for one lead, using Claude when configured."""

    if not settings.anthropic_api_key:
        return offline_followup(lead, vertical=vertical, tone=tone)

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.model,
            max_tokens=650,
            temperature=0.25,
            messages=[{"role": "user", "content": followup_prompt(lead, vertical, tone)}],
        )
        return response.content[0].text
    except Exception as exc:
        fallback = offline_followup(lead, vertical=vertical, tone=tone)
        return f"{fallback}\n\n> Claude generation was skipped: {exc}"

