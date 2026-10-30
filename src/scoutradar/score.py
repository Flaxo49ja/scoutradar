"""The scoring engine. Weights live here and nowhere else — same discipline
as ioc-triage's classify.py.

Design notes:

- Pure functions over a pandas DataFrame. No network, no file I/O; the CLI
  and tests own that.
- The Breakout Score is a weighted sum of bounded components, 0-100.
- Weights are STARTING VALUES. The backtest (Step 3 of the plan) will move
  them or kill them; the point now is to have them in one place with tests
  pinning behaviour, not scattered across the codebase.
- Z-scores vs players in the same position GROUP (not per league-position —
  samples are too thin, as scoped in the plan doc).
"""
from __future__ import annotations

import pandas as pd

from .kpis import POSITION_GROUPS, POSITION_KPIS

# ---------------------------------------------------------------------------
# Weights — the one table. Shares of 100; truncate to int, never round up.
# ---------------------------------------------------------------------------
PERFORMANCE_MAX = 40   # position-relative output (mean z of the group's KPIs)
FORM_MAX = 15          # per-90 output scaled by recency proxy (minutes share)
OUTPUT_PER_MINUTE_MAX = 15  # contribution per minute played
CONSISTENCY_MAX = 10   # inverse variance of the KPI z-scores
LOW_PROFILE_MAX = 20   # low minutes / smaller-club bonus — the radar's job

# Minutes threshold: below this we do not score a player at all. Starting
# value from the plan doc (450); drop, don't guess.
MIN_MINUTES_DEFAULT = 450

# Low-profile flag: minutes below the group median AND club not in the set
# of "profile clubs" (big-club list is config, not code, per the plan).
BIG_CLUBS_DEFAULT = frozenset({
    "Chelsea", "AC Milan", "Dortmund", "Leipzig", "Sevilla",
    "Lazio", "Monaco", "Everton", "West Ham", "Wolves",
})


def position_group_for(position: str) -> str:
    """Detailed position (ST, AM...) -> group key into POSITION_KPIS."""
    group = POSITION_GROUPS.get(position)
    if group is None:
        raise ValueError(f"unknown position: {position!r}")
    if not POSITION_KPIS.get(group):
        raise ValueError(f"no KPI set defined for position group {group!r}")
    return group


def compute_zscores(df: pd.DataFrame, min_minutes: int = MIN_MINUTES_DEFAULT) -> pd.DataFrame:
    """Add a z_<kpi> column per KPI, z-scored within the player's position
    group. Players below the minutes threshold are dropped before scoring —
    never z-score against a pool that includes unqualified players."""
    qualified = df[df["minutes"] >= min_minutes].copy()
    qualified["group"] = qualified["position"].map(position_group_for)
    for group, chunk in qualified.groupby("group"):
        kpis = POSITION_KPIS[group]
        present = [k for k in kpis if k in chunk.columns]
        for kpi in present:
            col = f"z_{kpi}"
            qualified.loc[chunk.index, col] = (
                (chunk[kpi] - chunk[kpi].mean()) / chunk[kpi].std(ddof=0)
                if chunk[kpi].std(ddof=0) > 0 else 0.0
            )
    return qualified


def _performance_points(row: pd.Series, kpis: tuple[str, ...]) -> int:
    zs = [row.get(f"z_{kpi}", 0.0) for kpi in kpis]
    mean_z = sum(zs) / len(zs) if zs else 0.0
    return int(PERFORMANCE_MAX * max(0.0, min(1.0, (mean_z + 1) / 4)))
    # a mean z of +1 -> 50% of the pot; +3 or beyond -> full pot


def _output_per_minute_points(row: pd.Series, kpis: tuple[str, ...],
                              chunk: pd.DataFrame) -> int:
    # Contribution vs the positional pool: each KPI is min-max normalised
    # within the group, so a DM's 3 tackles/90 is not penalised for being a
    # smaller number than an ST's xG. Uses the same qualified pool as the
    # z-scores — a player can only beat players who were scored themselves.
    if chunk.empty:
        return 0
    ratios: list[float] = []
    for kpi in kpis:
        if kpi not in chunk.columns:
            continue
        col = chunk[kpi]
        span = col.max() - col.min()
        if span <= 0:
            continue
        ratios.append((row[kpi] - col.min()) / span)
    if not ratios:
        return 0
    return int(OUTPUT_PER_MINUTE_MAX * max(0.0, min(1.0, sum(ratios) / len(ratios))))


def _consistency_points(row: pd.Series, kpis: tuple[str, ...]) -> int:
    zs = [abs(row.get(f"z_{kpi}", 0.0)) for kpi in kpis]
    if not zs:
        return 0
    spread = max(zs) - min(zs)
    # Tight spread across the KPI block -> consistent performer.
    return int(CONSISTENCY_MAX * max(0.0, min(1.0, 1 - spread / 3)))


def _form_points(row: pd.Series, kpis: tuple[str, ...]) -> int:
    # Recency proxy: minutes share of the player's group. Reedier players get
    # form credit because a heavy minutes load means the form is being tested.
    minutes = row.get("minutes", 0)
    max_minutes = row.get("_group_max_minutes", minutes) or minutes
    share = minutes / max_minutes if max_minutes else 0.0
    return int(FORM_MAX * min(1.0, share))


def _low_profile_points(row: pd.Series, minutes_median: float) -> int:
    low_minutes = row.get("minutes", 0) < minutes_median
    small_club = row.get("team") not in BIG_CLUBS_DEFAULT
    if low_minutes and small_club:
        pts = LOW_PROFILE_MAX
    elif low_minutes or small_club:
        pts = LOW_PROFILE_MAX // 2
    else:
        pts = 0
    return pts


def score_players(df: pd.DataFrame, min_minutes: int = MIN_MINUTES_DEFAULT) -> pd.DataFrame:
    """Score every qualified player; returns a DataFrame with score and
    reasons per row, sorted by score descending."""
    scored = compute_zscores(df, min_minutes=min_minutes)
    scored["_group_max_minutes"] = scored.groupby("group")["minutes"].transform("max")
    scored["_minutes_median"] = scored.groupby("group")["minutes"].transform("median")
    rows = []
    for group, chunk in scored.groupby("group"):
        kpis = POSITION_KPIS[group]
        for _, row in chunk.iterrows():
            reasons: list[str] = []
            pts = 0

            p = _performance_points(row, kpis)
            pts += p
            reasons.append(f"position-relative performance (+{p}/{PERFORMANCE_MAX})")

            p = _output_per_minute_points(row, kpis, chunk)
            pts += p
            reasons.append(f"output per minute (+{p}/{OUTPUT_PER_MINUTE_MAX})")

            p = _consistency_points(row, kpis)
            pts += p
            reasons.append(f"consistency (+{p}/{CONSISTENCY_MAX})")

            p = _form_points(row, kpis)
            pts += p
            reasons.append(f"minutes-tested form (+{p}/{FORM_MAX})")

            p = _low_profile_points(row, row["_minutes_median"])
            pts += p
            flag = " and ".join(
                filter(None, [
                    "low minutes" if row["minutes"] < row["_minutes_median"] else None,
                    "smaller club" if row["team"] not in BIG_CLUBS_DEFAULT else None,
                ])
            )
            reasons.append(f"low-profile flag — {flag or 'none'} (+{p}/{LOW_PROFILE_MAX})")

            rows.append({
                **{c: row[c] for c in df.columns},
                "group": group,
                "score": min(100, pts),
                "reasons": "; ".join(reasons),
            })
    out = pd.DataFrame(rows)
    if out.empty:
        # No player qualified under the threshold: return the input's columns
        # plus the documented extras, so callers can fail cleanly instead of
        # crashing on a missing 'score' column.
        out = pd.DataFrame({c: pd.Series(dtype="object") for c in df.columns}
                           | {"group": pd.Series(dtype="str"),
                              "score": pd.Series(dtype="int"),
                              "reasons": pd.Series(dtype="str")})
        return out
    return out.sort_values("score", ascending=False).reset_index(drop=True)
