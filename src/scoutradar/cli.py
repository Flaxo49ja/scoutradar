"""scout-radar CLI — Step 1 of the plan: a ranked CSV, scriptable exit
codes, human-readable table. No network; it reads a local CSV of per-90
KPIs (data/players_sample.csv until the FBref layer exists)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .score import MIN_MINUTES_DEFAULT, score_players

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "players_sample.csv"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="scout-radar",
        description="Flag players performing well relative to their position, minutes and club profile.",
    )
    p.add_argument("--csv", default=str(DEFAULT_CSV), help="input CSV of per-90 KPIs")
    p.add_argument("--pos", action="append", default=[],
                   help="restrict to position detail(s), e.g. --pos ST --pos AM (repeatable)")
    p.add_argument("--league", action="append", default=[],
                   help="restrict to league(s), repeatable")
    p.add_argument("--min-mins", type=int, default=MIN_MINUTES_DEFAULT,
                   help=f"minutes threshold (default {MIN_MINUTES_DEFAULT})")
    p.add_argument("--top", type=int, default=0, help="show only the top N rows in the table")
    p.add_argument("--out", default="out/ranked.csv", help="output CSV path")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    return p.parse_args(argv)


def render_human(df: pd.DataFrame, top: int = 0) -> str:
    cols = ["score", "player", "team", "league", "position", "age", "minutes"]
    view = df[cols].head(top) if top else df[cols]
    lines = [view.to_string(index=False)]
    lines.append("")
    lines.append("Why (top 3):")
    for _, row in df.head(top or 3).iterrows():
        lines.append(f"  {row['player']}: {row['reasons']}")
    return "\n".join(lines)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"error: input CSV not found: {csv_path}", file=sys.stderr)
        return 2

    df = pd.read_csv(csv_path)
    required = {"player", "team", "league", "position", "age", "minutes"}
    missing = required - set(df.columns)
    if missing:
        print(f"error: input CSV missing columns: {', '.join(sorted(missing))}", file=sys.stderr)
        return 2

    n_total = len(df)
    ranked = score_players(df, min_minutes=args.min_mins)
    ranked = ranked[ranked["minutes"] >= args.min_mins]

    if args.pos:
        ranked = ranked[ranked["position"].isin(args.pos)]
    if args.league:
        ranked = ranked[ranked["league"].isin(args.league)]

    if ranked.empty:
        print("no qualified players match the filters", file=sys.stderr)
        return 3

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(out_path, index=False)

    if args.json:
        print(ranked.to_json(orient="records", indent=2))
    else:
        print(f"ScoutRadar — {len(ranked)} of {n_total} players qualified "
              f"(min {args.min_mins} mins). Written to {out_path}\n")
        print(render_human(ranked, top=args.top))

    return 0


def main() -> None:
    try:
        sys.exit(run())
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
