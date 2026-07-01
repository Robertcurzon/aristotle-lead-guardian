"""Aristotle Lead Guardian Streamlit app."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from agents.followup_agent import generate_followup
from config.settings import settings
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
    return f"{row['priority']} | {row['name']} | {row['source']} | score {row['lead_score']:.1f}"


def main() -> None:
    """Run the dashboard."""

    configure_page()
    render_hero()

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
        st.info("Upload a CSV to activate the lead analysis, or switch on bundled demo leads in the sidebar.")
        st.stop()

    validation = validate_lead_frame(raw)
    if not validation.ok:
        st.error(f"CSV is missing required columns: {', '.join(validation.missing_columns)}")
        st.stop()
    if validation.extra_columns:
        st.warning(f"Extra columns ignored by the scoring engine: {', '.join(validation.extra_columns)}")

    scored = score_leads(raw)
    summary = summarize_leads(scored)
    sources = source_summary(scored)

    with st.expander("Data Preview", expanded=False):
        st.dataframe(raw.head(8), width="stretch")

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Total Leads", str(summary["total_leads"]), "Active lead book")
    with c2:
        metric_card("Hot Leads", str(summary["hot_leads"]), "High-priority follow-up")
    with c3:
        metric_card("SLA Breaches", str(summary["sla_breaches"]), "Needs attention now")
    p1, _p2 = st.columns([0.62, 0.38])
    with p1:
        metric_card("Est. Pipeline", _compact_money(float(summary["pipeline_value"])), f"Top source: {summary['top_source']}")

    st.subheader("Lead Guardian Command View")
    left, right = st.columns([0.58, 0.42])
    with left:
        st.plotly_chart(score_vs_timeline(scored), width="stretch")
    with right:
        st.plotly_chart(priority_distribution(scored), width="stretch")

    st.plotly_chart(source_pipeline(sources), width="stretch")

    st.subheader("Today\'s Action Queue")
    queue = scored.sort_values(["sla_status", "lead_score"], ascending=[True, False]).head(queue_size)
    st.dataframe(
        queue[
            [
                "lead_id",
                "name",
                "priority",
                "lead_score",
                "sla_status",
                "source",
                "status",
                "budget",
                "recommended_action",
                "risk_reason",
            ]
        ].style.format({"lead_score": "{:.1f}", "budget": "${:,.0f}"}),
        width="stretch",
    )

    tab_detail, tab_sources, tab_export = st.tabs(["Lead Agent", "Source Quality", "Export"])

    with tab_detail:
        selected_label = st.selectbox("Select lead", [_lead_label(row) for _, row in scored.iterrows()])
        selected_index = [_lead_label(row) for _, row in scored.iterrows()].index(selected_label)
        lead = scored.iloc[selected_index].to_dict()

        lcol, rcol = st.columns([0.42, 0.58])
        with lcol:
            st.markdown("#### Lead Snapshot")
            st.write(f"**Name:** {lead['name']}")
            st.write(f"**Priority:** {lead['priority']} ({lead['lead_score']:.1f}/100)")
            st.write(f"**SLA:** {lead['sla_status']}")
            st.write(f"**Recommended action:** {lead['recommended_action']}")
            st.write(f"**Risk reason:** {lead['risk_reason']}")
            st.write(f"**Notes:** {lead['notes']}")
        with rcol:
            st.markdown("#### Generated Follow-up")
            st.markdown(_async_text(generate_followup(lead, vertical=vertical, tone=tone)))

    with tab_sources:
        st.dataframe(sources.style.format({"avg_score": "{:.1f}", "pipeline_value": "${:,.0f}"}), width="stretch")

    with tab_export:
        export = scored.to_csv(index=False).encode("utf-8")
        st.download_button("Download scored leads CSV", data=export, file_name="scored_leads.csv", mime="text/csv")
        st.dataframe(scored, width="stretch")

    if not settings.anthropic_api_key:
        st.caption("Claude is not configured, so follow-up generation is using deterministic offline copy.")


if __name__ == "__main__":
    main()
