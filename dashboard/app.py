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
from core.ops import (
    action_queue,
    agent_workload,
    at_risk_pipeline,
    followup_debt,
    lead_book_health_score,
    playbook_mix,
    rescue_funnel,
    rescue_impact_estimate,
    source_leakage,
)
from core.schema import load_sample_leads, validate_lead_frame
from core.scoring import score_leads, source_summary
from dashboard.components.cards import metric_card
from dashboard.components.charts import (
    followup_debt_chart,
    health_gauge,
    playbook_mix_chart,
    rescue_funnel_chart,
    score_vs_timeline,
    source_leakage_chart,
    source_pipeline,
)
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


def _demo_analysis_date(raw: pd.DataFrame, use_sample: bool) -> pd.Timestamp | None:
    """Pin bundled demo scoring to the sample's own timeline."""

    if not use_sample or "created_at" not in raw.columns:
        return None
    latest = pd.to_datetime(raw["created_at"], errors="coerce").max()
    if pd.isna(latest):
        return None
    return latest.normalize()


def _chip_class(value: str) -> str:
    if value in {"Breach", "Rescue now", "Hot", "Needs approval"}:
        return "chip chip-danger"
    if value in {"Warm", "Work today", "Convert today", "Ready to send"}:
        return "chip chip-warm"
    if value in {"Won", "Appointment", "Scheduled"}:
        return "chip chip-green"
    return "chip"


def _render_action_card(row: pd.Series, rank: int) -> None:
    name = html.escape(str(row["name"]))
    source = html.escape(str(row["source"]))
    playbook = html.escape(str(row["playbook"]))
    action = html.escape(str(row["recommended_action"]))
    reason = html.escape(str(row["risk_reason"]))
    priority = html.escape(str(row["priority"]))
    stage = html.escape(str(row["rescue_stage"]))
    pipeline = _compact_money(float(row["pipeline_value"]))
    st.markdown(
        f"""
        <div class="lead-card">
            <div class="lead-card-meta">#{rank} Action Pack</div>
            <div class="lead-card-title">{name}</div>
            <div class="lead-card-meta">{source} - {pipeline} weighted pipeline - {playbook}</div>
            <div class="chip-row">
                <span class="{_chip_class(str(row['rescue_stage']))}">{stage}</span>
                <span class="{_chip_class(str(row['priority']))}">{priority}</span>
                <span class="{_chip_class(str(row['agent_status']))}">{html.escape(str(row['agent_status']))}</span>
            </div>
            <div class="lead-card-action"><strong>Next:</strong> {action}<br><strong>Why:</strong> {reason}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_action_pack(queue: pd.DataFrame, vertical: str, tone: str, key_prefix: str) -> None:
    st.subheader("Today's Top 3 Action Pack")
    top = queue.head(3)
    cols = st.columns(3)
    for idx, (col, (_, row)) in enumerate(zip(cols, top.iterrows(), strict=True), start=1):
        with col:
            _render_action_card(row, idx)

    labels = [f"{row['name']} - {row['playbook']} - {_compact_money(float(row['pipeline_value']))}" for _, row in queue.iterrows()]
    selected = st.selectbox("Open full action pack", labels, key=f"{key_prefix}_lead_select")
    lead = queue.iloc[labels.index(selected)].to_dict()
    lcol, rcol = st.columns([0.38, 0.62])
    with lcol:
        st.markdown("#### Lead Brief")
        st.write(f"**Name:** {lead['name']}")
        st.write(f"**Status:** {lead['status']} | **Priority:** {lead['priority']} ({lead['lead_score']:.1f}/100)")
        st.write(f"**Action status:** {lead['agent_status']}")
        st.write(f"**Pipeline:** {_money(float(lead['pipeline_value']))}")
        st.write(f"**Recommended action:** {lead['recommended_action']}")
        st.write(f"**Why now:** {lead['risk_reason']}")
    with rcol:
        st.markdown("#### Drafted Next Touch")
        st.markdown(_async_text(generate_followup(lead, vertical=vertical, tone=tone)))


def _render_overview(scored: pd.DataFrame, queue: pd.DataFrame) -> None:
    health = lead_book_health_score(scored)
    workload = agent_workload(queue)
    debt = followup_debt(scored)
    leakage = source_leakage(scored)
    funnel = rescue_funnel(scored, queue)
    playbooks = playbook_mix(queue)
    impact = rescue_impact_estimate(scored)

    debt_count = int(debt.loc[debt["bucket"].isin(["4-7d", "7d+"]), "leads"].sum())
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Health Score", f"{health}/100", "Response and follow-up coverage")
    with c2:
        metric_card("Pipeline At Risk", _compact_money(impact["at_risk_pipeline"]), "Hot, warm, or overdue")
    with c3:
        metric_card("Follow-Up Debt", str(debt_count), "Leads 4+ days quiet")
    with c4:
        metric_card("Agent Actions", str(workload["total_actions"]), f"{workload['ready_to_send']} ready, {workload['needs_approval']} review")

    left, right = st.columns([0.38, 0.62])
    with left:
        st.plotly_chart(health_gauge(health), width="stretch")
        st.markdown("#### Rescue Impact")
        st.write(f"If 20% of at-risk pipeline is recovered, projected recovered pipeline is **{_compact_money(impact['recovered_pipeline'])}**.")
        st.write(f"At a 3% revenue/commission assumption, that is roughly **{_compact_money(impact['estimated_revenue'])}**.")
    with right:
        st.plotly_chart(rescue_funnel_chart(funnel), width="stretch")

    v1, v2 = st.columns(2)
    with v1:
        st.plotly_chart(followup_debt_chart(debt), width="stretch")
    with v2:
        st.plotly_chart(source_leakage_chart(leakage), width="stretch")

    st.plotly_chart(playbook_mix_chart(playbooks), width="stretch")


def _render_diagnostics(scored: pd.DataFrame) -> None:
    sources = source_summary(scored)
    st.subheader("Diagnostics")
    left, right = st.columns([0.55, 0.45])
    with left:
        st.plotly_chart(score_vs_timeline(scored), width="stretch")
    with right:
        st.plotly_chart(source_pipeline(sources), width="stretch")
    st.dataframe(sources.style.format({"avg_score": "{:.1f}", "pipeline_value": "${:,.0f}"}), width="stretch")


def main() -> None:
    """Run the dashboard."""

    configure_page()
    render_hero()

    with st.expander("Inputs & CSV Upload", expanded=False):
        c1, c2 = st.columns([0.34, 0.66])
        with c1:
            use_sample = st.toggle("Use bundled demo leads", value=True)
            vertical = st.selectbox(
                "Business vertical",
                ["Real estate", "Roofing", "HVAC", "Med spa", "Agency", "Consulting", "Insurance", "Local services"],
                index=0,
            )
            tone = st.selectbox("Follow-up tone", ["warm and direct", "premium and concise", "friendly and helpful"], index=0)
        with c2:
            uploaded_file = st.file_uploader("Upload lead CSV", type=["csv"], disabled=use_sample)
            st.caption("Use the bundled sample for demo mode, or upload a CRM/export CSV that matches the documented schema.")

    raw = _load_input(use_sample, uploaded_file)
    if raw is None:
        st.info("Upload a CSV to activate the Lead Guardian analysis, or switch on bundled demo leads in the sidebar.")
        st.stop()

    validation = validate_lead_frame(raw)
    if not validation.ok:
        st.error(f"CSV is missing required columns: {', '.join(validation.missing_columns)}")
        st.stop()
    if validation.extra_columns:
        st.warning(f"Extra columns ignored by the scoring engine: {', '.join(validation.extra_columns)}")

    scored = score_leads(raw, now=_demo_analysis_date(raw, use_sample))
    queue = action_queue(scored)

    with st.expander("Data Preview", expanded=False):
        st.dataframe(raw.head(8), width="stretch")

    mode = st.radio(
        "View",
        ["Overview", "Action Pack", "Diagnostics", "Export"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "Overview":
        _render_overview(scored, queue)
        _render_action_pack(queue, vertical=vertical, tone=tone, key_prefix="overview")
    elif mode == "Action Pack":
        _render_action_pack(queue, vertical=vertical, tone=tone, key_prefix="actions")
    elif mode == "Diagnostics":
        _render_diagnostics(scored)
    else:
        export = queue.to_csv(index=False).encode("utf-8")
        st.subheader("Export")
        st.download_button("Download lead action pack CSV", data=export, file_name="lead_action_pack.csv", mime="text/csv")
        st.dataframe(queue, width="stretch")

    if not settings.anthropic_api_key:
        st.caption("Claude is not configured, so follow-up generation is using deterministic offline copy.")


if __name__ == "__main__":
    main()
