"""Plotly charts for lead operations."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLOR_SEQUENCE = ["#38bdf8", "#34d399", "#f59e0b", "#f43f5e", "#a78bfa"]


def priority_distribution(scored: pd.DataFrame) -> go.Figure:
    """Render lead counts by priority."""

    order = ["Hot", "Warm", "Nurture", "Low"]
    counts = scored["priority"].value_counts().reindex(order).fillna(0).reset_index()
    counts.columns = ["priority", "count"]
    fig = px.bar(counts, x="priority", y="count", color="priority", color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_layout(template="plotly_dark", title="Lead Priority Mix", showlegend=False, margin=dict(l=10, r=10, t=48, b=10))
    return fig


def source_pipeline(source_frame: pd.DataFrame) -> go.Figure:
    """Render estimated pipeline value by source."""

    fig = px.bar(
        source_frame,
        x="pipeline_value",
        y="source",
        orientation="h",
        color="avg_score",
        color_continuous_scale="Teal",
        title="Estimated Pipeline by Source",
    )
    fig.update_layout(template="plotly_dark", yaxis={"categoryorder": "total ascending"}, margin=dict(l=10, r=10, t=48, b=10))
    return fig


def score_vs_timeline(scored: pd.DataFrame) -> go.Figure:
    """Render lead score against buying timeline."""

    fig = px.scatter(
        scored,
        x="timeline_days",
        y="lead_score",
        size="budget",
        color="priority",
        hover_name="name",
        hover_data=["source", "status", "sla_status"],
        color_discrete_sequence=COLOR_SEQUENCE,
        title="Urgency Lens: Score vs Timeline",
    )
    fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=48, b=10))
    return fig


def health_gauge(score: int) -> go.Figure:
    """Render a lead book health score gauge."""

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 34}},
            title={"text": "Lead Book Health", "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#38bdf8"},
                "steps": [
                    {"range": [0, 45], "color": "rgba(244,63,94,0.26)"},
                    {"range": [45, 75], "color": "rgba(245,158,11,0.24)"},
                    {"range": [75, 100], "color": "rgba(34,197,94,0.22)"},
                ],
            },
        )
    )
    fig.update_layout(template="plotly_dark", height=260, margin=dict(l=10, r=10, t=42, b=10))
    return fig


def rescue_funnel_chart(funnel: pd.DataFrame) -> go.Figure:
    """Render a compact lead rescue funnel."""

    fig = go.Figure(
        go.Funnel(
            y=funnel["stage"],
            x=funnel["count"],
            textinfo="value+percent initial",
            marker={"color": ["#38bdf8", "#34d399", "#f59e0b", "#f97316", "#f43f5e"]},
        )
    )
    fig.update_layout(template="plotly_dark", title="Lead Rescue Funnel", height=310, margin=dict(l=10, r=10, t=48, b=10))
    return fig


def followup_debt_chart(debt: pd.DataFrame) -> go.Figure:
    """Render follow-up debt by age bucket."""

    fig = px.bar(
        debt,
        x="bucket",
        y="leads",
        color="bucket",
        color_discrete_sequence=["#34d399", "#38bdf8", "#f59e0b", "#f43f5e"],
        title="Follow-Up Debt",
        hover_data={"pipeline_value": ":$,.0f"},
    )
    fig.update_layout(template="plotly_dark", showlegend=False, margin=dict(l=10, r=10, t=48, b=10))
    return fig


def source_leakage_chart(leakage: pd.DataFrame) -> go.Figure:
    """Render source-level missed-follow-up leakage."""

    chart = leakage.sort_values("leakage_rate", ascending=True)
    fig = px.bar(
        chart,
        x="leakage_rate",
        y="source",
        orientation="h",
        color="leaked_pipeline",
        color_continuous_scale="Reds",
        title="Source Leakage",
        hover_data={"leads": True, "leaking_leads": True, "leaked_pipeline": ":$,.0f", "leakage_rate": ":.0%"},
    )
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=48, b=10))
    return fig


def playbook_mix_chart(playbooks: pd.DataFrame) -> go.Figure:
    """Render the mix of recommended action playbooks."""

    chart = playbooks.sort_values("actions", ascending=True)
    fig = px.bar(
        chart,
        x="actions",
        y="playbook",
        orientation="h",
        color="pipeline_value",
        color_continuous_scale="Teal",
        title="Recommended Playbook Mix",
        hover_data={"pipeline_value": ":$,.0f"},
    )
    fig.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=48, b=10))
    return fig
