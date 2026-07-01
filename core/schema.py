"""CSV schema validation and normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "lead_id",
    "created_at",
    "name",
    "email",
    "phone",
    "source",
    "status",
    "budget",
    "intent",
    "timeline_days",
    "last_contacted_at",
    "engagement_score",
    "notes",
}

OPTIONAL_COLUMNS = {"assigned_to", "region", "service_type", "preferred_channel"}
SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_leads.csv"


@dataclass(frozen=True)
class ValidationResult:
    """Result returned by lead CSV validation."""

    ok: bool
    missing_columns: tuple[str, ...]
    extra_columns: tuple[str, ...]


def snake_case(value: str) -> str:
    """Convert a column label into snake_case."""

    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_")
    return cleaned.lower()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized snake_case column names."""

    normalized = df.copy()
    normalized.columns = [snake_case(col) for col in normalized.columns]
    return normalized


def validate_lead_frame(df: pd.DataFrame) -> ValidationResult:
    """Validate a lead dataframe against the required CSV schema."""

    columns = set(normalize_columns(df).columns)
    missing = tuple(sorted(REQUIRED_COLUMNS - columns))
    allowed = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
    extra = tuple(sorted(columns - allowed))
    return ValidationResult(ok=not missing, missing_columns=missing, extra_columns=extra)


def load_sample_leads() -> pd.DataFrame:
    """Load bundled demo leads."""

    return pd.read_csv(SAMPLE_PATH)

