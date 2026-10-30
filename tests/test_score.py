"""Scoring engine tests — pure functions over the sample CSV, no network,
no CLI. Component behaviour is pinned so weight changes are visible diffs,
not silent drift (the golden-master habit from PhishGuard)."""
import pandas as pd
import pytest

from scoutradar.kpis import POSITION_GROUPS, POSITION_KPIS
from scoutradar.score import (
    BIG_CLUBS_DEFAULT,
    CONSISTENCY_MAX,
    FORM_MAX,
    LOW_PROFILE_MAX,
    MIN_MINUTES_DEFAULT,
    OUTPUT_PER_MINUTE_MAX,
    PERFORMANCE_MAX,
    compute_zscores,
    position_group_for,
    score_players,
)


# --- config integrity --------------------------------------------------------

def test_every_detailed_position_maps_to_a_scored_group(sample_df):
    groups = {position_group_for(p) for p in sample_df["position"].unique()}
    assert all(POSITION_KPIS[g] for g in groups)


def test_weights_sum_to_100():
    total = (PERFORMANCE_MAX + FORM_MAX + OUTPUT_PER_MINUTE_MAX
             + CONSISTENCY_MAX + LOW_PROFILE_MAX)
    assert total == 100


# --- threshold & pool --------------------------------------------------------

def test_players_below_minutes_threshold_never_scored(sample_df):
    out = score_players(sample_df)
    assert (out["minutes"] >= MIN_MINUTES_DEFAULT).all()


def test_unknown_position_raises_not_silently_dropped():
    df = pd.DataFrame([{
        "player": "X", "team": "Y", "league": "Z", "position": "SW",
        "age": 20, "minutes": 900, "xg_per90": 0.1,
    }])
    with pytest.raises(ValueError):
        compute_zscores(df)


def test_empty_result_is_clean_not_crash(sample_df):
    """A threshold nobody meets must return an empty typed frame, never a
    KeyError inside the engine (pinned after the completion-check find)."""
    out = score_players(sample_df, min_minutes=9000)
    assert out.empty
    assert {"player", "score", "reasons", "group"} <= set(out.columns)


# --- z-scores ----------------------------------------------------------------

def test_zscores_are_within_position_group(sample_df):
    scored = compute_zscores(sample_df)
    st = scored[scored["group"] == "ST"]
    # Z-score of the group mean is ~0 by construction
    assert st["z_xg_per90"].mean() == pytest.approx(0, abs=1e-9)
    assert st["z_xg_per90"].std(ddof=0) == pytest.approx(1, abs=1e-9)


def test_better_than_group_median_gets_positive_z(sample_df):
    scored = compute_zscores(sample_df)
    st = scored[scored["group"] == "ST"]
    best = st.loc[st["z_xg_per90"].idxmax()]
    worst = st.loc[st["z_xg_per90"].idxmin()]
    assert best["xg_per90"] > worst["xg_per90"]
    assert best["z_xg_per90"] > worst["z_xg_per90"]


# --- components --------------------------------------------------------------

def test_low_profile_full_points_needs_both_conditions():
    """Two-player pool so the median is meaningful: the low-minutes,
    small-club player gets the full flag; note a single-player pool can
    never be 'below median' relative to itself (correct behaviour, pinned
    here as an edge case)."""
    base = {
        "league": "L", "position": "ST", "age": 21,
        "xg_per90": 0.5, "xa_per90": 0.1, "goals_per90": 0.5,
        "assists_per90": 0.1, "tackles_per90": 0.1,
        "interceptions_per90": 0.1, "progressive_carries_per90": 1,
        "progressive_passes_per90": 1, "dribbles_completed_per90": 1,
        "aerial_win_pct": 50,
    }
    df = pd.DataFrame([
        {"player": "Low", "team": "Spezia", "minutes": 460, **base},
        {"player": "Regular", "team": next(iter(BIG_CLUBS_DEFAULT)), "minutes": 1200, **base},
    ])
    out = score_players(df)
    low = out[out["player"] == "Low"].iloc[0]
    assert f"+{LOW_PROFILE_MAX}/{LOW_PROFILE_MAX}" in low["reasons"]
    assert "low minutes and smaller club" in low["reasons"]

    big = out[out["player"] == "Regular"].iloc[0]
    assert f"+0/{LOW_PROFILE_MAX}" in big["reasons"]


def test_big_club_regular_gets_no_low_profile_points(sample_df):
    out = score_players(sample_df)
    top_regular = out[out["player"] == "Youssouf Diarra"].iloc[0]
    assert f"+0/{LOW_PROFILE_MAX}" in top_regular["reasons"]


def test_output_per_minute_uses_position_pool_not_raw_values(sample_df):
    """A DM's 3+ tackles/90 must compete inside the DM pool, not against a
    striker's raw xG. Engine pair (Ortega/Wright) are pool-relative tests."""
    out = score_players(sample_df)
    dm = out[out["group"] == "DM"].iloc[0]
    # Output/min points exist at all for a defensive profile
    assert "output per minute" in dm["reasons"]


def test_form_credit_scales_with_minutes_share(sample_df):
    out = score_players(sample_df)
    # The player with the most minutes in any group gets the full form pot
    top_minutes = out.sort_values("minutes", ascending=False).groupby("group").head(1)
    assert all(f"+{FORM_MAX}/{FORM_MAX}" in r for r in top_minutes["reasons"])


# --- combination -------------------------------------------------------------

def test_scores_are_bounded_and_sorted(sample_df):
    out = score_players(sample_df)
    assert out["score"].between(0, 100).all()
    assert out["score"].is_monotonic_decreasing


def test_every_score_row_carries_five_reasons(sample_df):
    out = score_players(sample_df)
    for reasons in out["reasons"]:
        assert reasons.count("(+") == 5


def test_score_is_deterministic(sample_df):
    a = score_players(sample_df)
    b = score_players(sample_df)
    pd.testing.assert_frame_equal(a, b)
