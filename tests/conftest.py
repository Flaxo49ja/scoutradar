"""Make src/ importable without installing. No network is ever touched:
the scoring tests run on the hand-prepared CSV in data/."""
import sys
from pathlib import Path

import pytest
import pandas as pd

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "data" / "players_sample.csv"


@pytest.fixture(scope="session")
def sample_df() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_CSV)


@pytest.fixture()
def tmp_csv(tmp_path, sample_df):
    """A writable copy of the sample for CLI tests that change thresholds."""
    p = tmp_path / "players.csv"
    sample_df.to_csv(p, index=False)
    return str(p)
