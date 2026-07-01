"""CLI utility for scoring a lead CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from core.scoring import score_leads


def main() -> None:
    """Score a lead CSV and write the enriched output."""

    parser = argparse.ArgumentParser(description="Score leads with Aristotle Lead Guardian.")
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("scored_leads.csv"))
    args = parser.parse_args()

    scored = score_leads(pd.read_csv(args.input_csv))
    scored.to_csv(args.output, index=False)
    print(f"Wrote {len(scored)} scored leads to {args.output}")


if __name__ == "__main__":
    main()

