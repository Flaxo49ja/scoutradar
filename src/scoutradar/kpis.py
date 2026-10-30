# Position group -> KPI columns that matter for that group. One place,
# one page: if a KPI can't be defended in a sentence for a group, it does
# not appear for that group.
POSITION_KPIS: dict[str, tuple[str, ...]] = {
    "GK": (),  # not in the sample data yet; fill before adding GK rows
    "DF": (
        "tackles_per90",
        "interceptions_per90",
        "progressive_passes_per90",
        "aerial_win_pct",
    ),
    "FB": (
        "tackles_per90",
        "interceptions_per90",
        "progressive_passes_per90",
        "progressive_carries_per90",
        "dribbles_completed_per90",
    ),
    "MF": (
        "progressive_passes_per90",
        "progressive_carries_per90",
        "tackles_per90",
        "interceptions_per90",
    ),
    "DM": (
        "tackles_per90",
        "interceptions_per90",
        "progressive_passes_per90",
    ),
    "AM": (
        "xa_per90",
        "progressive_passes_per90",
        "progressive_carries_per90",
        "dribbles_completed_per90",
    ),
    "W": (
        "xg_per90",
        "xa_per90",
        "progressive_carries_per90",
        "dribbles_completed_per90",
    ),
    "ST": (
        "xg_per90",
        "goals_per90",
        "xa_per90",
        "aerial_win_pct",
    ),
}

# Detailed position -> group. Every detailed position in the data must map
# to a group that has KPIs.
POSITION_GROUPS: dict[str, str] = {
    "CB": "DF",
    "FB": "FB",
    "DM": "DM",
    "CM": "MF",
    "AM": "AM",
    "W": "W",
    "ST": "ST",
    "GK": "GK",
}
