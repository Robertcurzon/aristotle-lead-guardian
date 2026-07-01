"""Aristotle Lead Guardian Streamlit app."""

from __future__ import annotations

import asyncio
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from agents.followup_agent import generate_followup
from config.settings import settings
from core.ops import action_queue, at_risk_pipeline, autopilot_frame, conversation_timeline, pipeline_summary
from core.schema import load_sample_leads, validate_lead_frame
from core.scoring import score_leads, source_summary, summarize_leads
from dashboard.components.cards import metric_card
from dashboard.components.charts import priority_distribution, score_vs_timeline, source_pipeline
from dashboard.layout import configure_page, render_hero


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _compact_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return _money(value)


def _async_text(coro) -> str:
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def _load_input(use_sample: bool, uploaded_file) -> pd.DataFrame | None:
    if use_sample:
        return load_sample_leads()
    if uploaded_file is None:
        return None
    return pd.read_csv(uploaded_file)


def _lead_label(row: pd.Series) -> str:
    return f"{row['rescue_stage']} | {row['name']} | {row['source']} | {_compact_money(float(row['pipeline_value']))}"


def _chip_class(value: str) -> str:
    if value in {"Breach", "Rescue now", "Hot", "Needs approval"}:
        return "chip chip-danger"
    if value in {"Warm", "Work today", "Convert today", "Ready to send"}:
        return "chip chip-warm"
    if value in {"Won", "Appointment", "Scheduled"}:
        return "chip chip-green"
    return "chip"


def _render_lead_card(row: pd.Series) -> None:
    name = html.escape(str(row["name"]))
    source = html.escape(str(row["source"]))
    playbook = html.escape(str(row["playbook"]))
    action = html.escape(str(row["recommended_action"]))
    priority = html.escape(str(row["priority"]))
    stage = html.escape(str(row["rescue_stage"]))
    sla = html.escape(str(row["sla_status"]))
    pipeline = _compact_money(float(row["pipeline_value"]))
    st.markdown(
        f"""
        <div class="lead-card">
            <div class="lead-card-title">{name}</div>
            <div class="lead-card-meta">{source} - {pipeline} weighted pipeline - {playbook}</div>
            <div class="chip-row">
                <span class="{_chip_class(str(row['rescue_stage']))}">{stage}</span>
                <span class="{_chip_class(str(row['priority']))}">{priority}</span>
                <span class="{_chip_class(str(row['sla_status']))}">{sla}</span>
            </div>
            <div class="lead-card-action">{action}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _select_lead(queue: pd.DataFrame, label: str = "Lead") -> dict[str, object]:
    labels = [_lead_label(row) for _, row in queue.iterrows()]
    current = st.session_state.get("selected_lead_label", labels[0])
    index = labels.index(current) if current in labels else 0
    selected = st.selectbox(label, labels, index=index)
    st.session_state["selected_lead_label"] = selected
    return queue.iloc[labels.index(selected)].to_dict()


def _render_agent_workspace(lead: dict[str, object], vertical: str, tone: str) -> None:
    lcol, rcol = st.columns([0.38, 0.62])
    with lcol:
        st.markdown("#### Lead Brief")
        st.write(f"**Name:** {lead['name']}")
        st.write(f"**Status:** {lead['status']} | **Priority:** {lead['priority']} ({lead['lead_score']:.1f}/100)")
        st.write(f"**SLA:** {lead['sla_status']} | **Playbook:** {lead['playbook']}")
        st.write(f"**Pipeline:** {_money(float(lead['pipeline_value']))}")
        st.write(f"**Recommended action:** {lead['recommended_action']}")
        st.write(f"**Why now:** {lead['risk_reason']}")
        b1, b2, b3 = st.columns(3)
        b1.button("Approve", use_container_width=True)
        b2.button("Edit", use_container_width=True)
        b3.button("Skip", use_container_width=True)
    with rcol:
        st.markdown("#### Agent Draft")
        st.markdown(_async_text(generate_followup(lead, vertical=vertical, tone=tone)))


def _render_timeline(lead: dict[str, object]) -> None:
    for event in conversation_timeline(lead):
        st.markdown(
            f"""
            <div class="timeline-item">
                <div class="timeline-label">{html.escape(event["label"])}</div>
                <div class="timeline-date">{html.escape(event["date"])}</div>
                <div class="timeline-body">{html.escape(event["body"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_pipeline_board(queue: pd.DataFrame, stages: pd.DataFrame) -> None:
    st.markdown("#### Pipeline Board")
    cols = st.columns(len(stages))
    for col, stage in zip(cols, stages.itertuples(), strict=True):
        stage_rows = queue.loc[queue["status"].eq(stage.status)].head(4)
        with col:
            st.markdown(f"**{stage.status}**")
            st.caption(f"{int(stage.leads)} leads - {_compact_money(float(stage.pipeline_value))}")
            if stage_rows.empty:
                st.caption("No active leads")
            for _, row in stage_rows.iterrows():
                _render_lead_card(row)


def _render_command(queue: pd.DataFrame, stages: pd.DataFrame, vertical: str, tone: str, queue_size: int) -> None:
    st.subheader("Today's Rescue Desk")
    left, right = st.columns([0.46, 0.54])
    with left:
        st.markdown("#### Priority Queue")
        for _, row in queue.head(queue_size).iterrows():
            _render_lead_card(row)
    with right:
        lead = _select_lead(queue, "Open lead workspace")
        _render_agent_workspace(lead, vertical=vertical, tone=tone)
    _render_pipeline_board(queue, stages)


def _render_conversations(queue: pd.DataFrame, vertical: str, tone: str) -> None:
    st.subheader("Conversation Workspace")
    lead = _select_lead(queue, "Conversation lead")
    lcol, rcol = st.columns([0.42, 0.58])
    with lcol:
        st.markdown("#### Timeline")
        _render_timeline(lead)
    with rcol:
        _render_agent_workspace(lead, vertical=vertical, tone=tone)


def _render_autopilot() -> None:
    st.subheader("Agent Autopilot")
    st.caption("These controls model how the agent would run inside a CRM or GoHighLevel-style operating stack.")
    rules = autopilot_frame()
    for rule in rules.itertuples():
        c1, c2 = st.columns([0.08, 0.92])
        with c1:
            st.toggle("", value=bool(rule.enabled), key=f"rule_{rule.Index}", label_visibility="collapsed")
        with c2:
            st.markdown(f"**{rule.name}**")
            st.caption(f"Trigger: {rule.trigger}")
            st.caption(f"Action: {rule.action}")
            st.caption("Owner review required" if rule.owner_review else "Runs automatically")


def _render_reports(scored: pd.DataFrame, sources: pd.DataFrame) -> None:
    st.subheader("Revenue Intelligence")
    left, right = st.columns([0.58, 0.42])
    with left:
        st.plotly_chart(score_vs_timeline(scored), width="stretch")
    with right:
        st.plotly_chart(priority_distribution(scored), width="stretch")
    st.plotly_chart(source_pipeline(sources), width="stretch")
    st.dataframe(sources.style.format({"avg_score": "{:.1f}", "pipeline_value": "${:,.0f}"}), width="stretch")


def main() -> None:
    """Run the dashboard."""

    configure_page()
    render_hero()

    st.sidebar.markdown("#### Workspace")
    workspace = st.sidebar.radio(
        "Navigation",
        ["Command", "Pipeline", "Conversations", "Autopilot", "Reports", "Export"],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("#### Data Source")
    use_sample = st.sidebar.toggle("Use bundled demo leads", value=True)
    uploaded_file = st.sidebar.file_uploader("Upload lead CSV", type=["csv"], disabled=use_sample)
    vertical = st.sidebar.selectbox(
        "Business vertical",
        ["Real estate", "Roofing", "HVAC", "Med spa", "Agency", "Consulting", "Insurance", "Local services"],
        index=0,
    )
    tone = st.sidebar.selectbox("Follow-up tone", ["warm and direct", "premium and concise", "friendly and helpful"], index=0)
    queue_size = st.sidebar.slider("Action queue size", min_value=3, max_value=15, value=8)

    raw = _load_input(use_sample, uploaded_file)
    if raw is None:
        st.info("Upload a CSV to activate the Lead Rescue Desk, or switch on bundled demo leads in the sidebar.")
        st.stop()

    validation = validate_lead_frame(raw)
    if not validation.ok:
        st.error(f"CSV is missing required columns: {', '.join(validation.missing_columns)}")
        st.stop()
    if validation.extra_columns:
        st.warning(f"Extra columns ignored by the scoring engine: {', '.join(validation.extra_columns)}")

    scored = score_leads(raw)
    queue = action_queue(scored)
    summary = summarize_leads(scored)
    sources = source_summary(scored)
    stages = pipeline_summary(scored)

    with st.expander("Data Preview", expanded=False):
        st.dataframe(raw.head(8), width="stretch")

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Leads To Work", str(len(queue.loc[queue["rescue_stage"].isin(["Rescue now", "Convert today", "Work today"])])), "Human or agent action today")
    with c2:
        metric_card("Rescue Now", str(summary["sla_breaches"]), "SLA risk")
    with c3:
        metric_card("At-Risk Pipeline", _compact_money(at_risk_pipeline(scored)), "Hot, warm, or breached")
    p1, _p2 = st.columns([0.62, 0.38])
    with p1:
        metric_card("Best Source", str(summary["top_source"]), _compact_money(float(summary["pipeline_value"])))

    if workspace == "Command":
        _render_command(queue, stages, vertical=vertical, tone=tone, queue_size=queue_size)
    elif workspace == "Pipeline":
        _render_pipeline_board(queue, stages)
        st.dataframe(
            stages.style.format({"pipeline_value": "${:,.0f}", "avg_score": "{:.1f}"}),
            width="stretch",
        )
    elif workspace == "Conversations":
        _render_conversations(queue, vertical=vertical, tone=tone)
    elif workspace == "Autopilot":
        _render_autopilot()
    elif workspace == "Reports":
        _render_reports(scored, sources)
    else:
        export = queue.to_csv(index=False).encode("utf-8")
        st.subheader("Export")
        st.download_button("Download scored rescue queue CSV", data=export, file_name="lead_rescue_queue.csv", mime="text/csv")
        st.dataframe(queue, width="stretch")

    if not settings.anthropic_api_key:
        st.caption("Claude is not configured, so follow-up generation is using deterministic offline copy.")


if __name__ == "__main__":
    main()
