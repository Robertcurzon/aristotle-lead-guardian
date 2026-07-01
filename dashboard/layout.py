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
        .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1500px; }
        h1, h2, h3 { letter-spacing: 0 !important; }
        .ag-hero { padding: 0.9rem 0 0.95rem 0; border-bottom: 1px solid rgba(148,163,184,0.22); margin-bottom: 1rem; }
        .ag-title { font-size: clamp(2.1rem, 4vw, 4.1rem); line-height: 1.02; font-weight: 760; color: #f8fafc; margin: 0; }
        .ag-subtitle { max-width: 1060px; color: #cbd5e1; font-size: 1.03rem; line-height: 1.55; margin-top: 0.65rem; }
        .metric-card { border: 1px solid rgba(148,163,184,0.22); background: #111827; border-radius: 8px; padding: 1rem; min-height: 112px; }
        .metric-label { color: #94a3b8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
        .metric-value { color: #f8fafc; font-size: 1.75rem; font-weight: 740; margin-top: 0.25rem; overflow-wrap: anywhere; }
        .metric-note { color: #94a3b8; font-size: 0.86rem; }
        .lead-card { border: 1px solid rgba(148,163,184,0.20); background: #0f172a; border-radius: 8px; padding: 0.85rem; margin-bottom: 0.65rem; }
        .lead-card-title { color: #f8fafc; font-weight: 730; font-size: 1.02rem; }
        .lead-card-meta { color: #94a3b8; font-size: 0.84rem; margin-top: 0.2rem; }
        .lead-card-action { color: #cbd5e1; font-size: 0.9rem; margin-top: 0.55rem; line-height: 1.45; }
        .chip-row { display: flex; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.5rem; }
        .chip { display: inline-flex; align-items: center; border-radius: 999px; padding: 0.16rem 0.48rem; font-size: 0.72rem; font-weight: 700; border: 1px solid rgba(148,163,184,0.20); color: #dbeafe; background: rgba(59,130,246,0.14); }
        .chip-danger { color: #fecdd3; background: rgba(244,63,94,0.16); border-color: rgba(244,63,94,0.38); }
        .chip-warm { color: #fde68a; background: rgba(245,158,11,0.16); border-color: rgba(245,158,11,0.36); }
        .chip-green { color: #bbf7d0; background: rgba(34,197,94,0.14); border-color: rgba(34,197,94,0.34); }
        .pipeline-lane { border: 1px solid rgba(148,163,184,0.18); background: #0b1220; border-radius: 8px; padding: 0.75rem; min-height: 250px; }
        .pipeline-title { color: #f8fafc; font-weight: 730; font-size: 0.95rem; margin-bottom: 0.25rem; }
        .pipeline-meta { color: #94a3b8; font-size: 0.78rem; margin-bottom: 0.65rem; }
        .timeline-item { border-left: 2px solid #38bdf8; padding-left: 0.8rem; margin-bottom: 1rem; }
        .timeline-label { color: #f8fafc; font-weight: 720; }
        .timeline-date { color: #94a3b8; font-size: 0.78rem; }
        .timeline-body { color: #cbd5e1; font-size: 0.92rem; margin-top: 0.18rem; }
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
            <div class="ag-title">AI Lead Rescue Desk</div>
            <div class="ag-subtitle">
                A small-business revenue operator for finding missed opportunities, prioritizing the next touch,
                and turning lead follow-up into a visible daily workflow.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
