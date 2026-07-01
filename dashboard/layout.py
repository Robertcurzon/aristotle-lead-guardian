"""Page layout and styling."""

from __future__ import annotations

import streamlit as st

from config.settings import settings


def configure_page() -> None:
    """Configure Streamlit page and app CSS."""

    st.set_page_config(page_title=settings.brand_name, page_icon="AG", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1500px; }
        h1, h2, h3 { letter-spacing: 0 !important; }
        .ag-hero { padding: 0.9rem 0 0.95rem 0; border-bottom: 1px solid rgba(148,163,184,0.22); margin-bottom: 1rem; }
        .ag-title { font-size: clamp(2.1rem, 4vw, 4.1rem); line-height: 1.02; font-weight: 760; color: #f8fafc; margin: 0; }
        .ag-subtitle { max-width: 1060px; color: #cbd5e1; font-size: 1.03rem; line-height: 1.55; margin-top: 0.65rem; }
        .metric-card { border: 1px solid rgba(148,163,184,0.22); background: #111827; border-radius: 8px; padding: 1rem; min-height: 112px; }
        .metric-label { color: #94a3b8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
        .metric-value { color: #f8fafc; font-size: 1.75rem; font-weight: 740; margin-top: 0.25rem; overflow-wrap: anywhere; }
        .metric-note { color: #94a3b8; font-size: 0.86rem; }
        div[data-testid="stExpander"] { border: 1px solid rgba(148,163,184,0.20); border-radius: 8px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """Render the dashboard hero."""

    st.markdown(
        """
        <div class="ag-hero">
            <div class="ag-title">Aristotle Lead Guardian</div>
            <div class="ag-subtitle">
                An AI-assisted revenue protection agent for small businesses: score incoming leads,
                surface follow-up risk, and draft the next touch before good opportunities go cold.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

