"""Dashboard metric card components."""

from __future__ import annotations

import streamlit as st


def metric_card(label: str, value: str, note: str = "") -> None:
    """Render a compact dashboard metric card."""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

