"""Tests for lead CSV schema validation."""

from __future__ import annotations

import pandas as pd

from core.schema import normalize_columns, validate_lead_frame


def test_normalize_columns_converts_to_snake_case() -> None:
    df = pd.DataFrame({"Lead ID": ["L-1"], "Created At": ["2026-06-30"]})

    normalized = normalize_columns(df)

    assert list(normalized.columns) == ["lead_id", "created_at"]


def test_validate_lead_frame_reports_missing_columns() -> None:
    result = validate_lead_frame(pd.DataFrame({"lead_id": ["L-1"]}))

    assert not result.ok
    assert "created_at" in result.missing_columns

