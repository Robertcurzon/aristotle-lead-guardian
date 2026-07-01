"""Centralized runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    brand_name: str = os.getenv("LEAD_GUARDIAN_BRAND_NAME", "Aristotle Lead Guardian")
    default_vertical: str = os.getenv("LEAD_GUARDIAN_DEFAULT_VERTICAL", "Real estate")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("LEAD_GUARDIAN_MODEL", "claude-sonnet-4-6")
    hot_threshold: float = float(os.getenv("LEAD_GUARDIAN_HOT_THRESHOLD", "75"))
    warm_threshold: float = float(os.getenv("LEAD_GUARDIAN_WARM_THRESHOLD", "55"))
    nurture_threshold: float = float(os.getenv("LEAD_GUARDIAN_NURTURE_THRESHOLD", "35"))
    sla_hours_new: int = int(os.getenv("LEAD_GUARDIAN_SLA_HOURS_NEW", "4"))
    sla_hours_contacted: int = int(os.getenv("LEAD_GUARDIAN_SLA_HOURS_CONTACTED", "48"))


settings = Settings()

