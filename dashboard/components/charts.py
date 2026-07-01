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

