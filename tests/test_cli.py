"""End-to-end CLI tests through run(): filters, output CSV artifact, JSON
mode, exit codes. Runs entirely offline on the committed sample CSV."""
import json

import pandas as pd

from scoutradar import cli


def test_ranked_csv_is_written_and_sorted(tmp_csv, tmp_path):
    out = tmp_path / "ranked.csv"
    code = cli.run(["--csv", tmp_csv, "--out", str(out)])
    assert code == 0
    assert out.exists()
    df = pd.read_csv(out)
    assert df["score"].is_monotonic_decreasing
    assert set(df.columns) >= {"score", "player", "team", "league", "position", "age", "minutes"}


def test_min_mins_filter_removes_unqualified(tmp_csv, tmp_path):
    out = tmp_path / "ranked.csv"
    cli.run(["--csv", tmp_csv, "--out", str(out), "--min-mins", "500"])
    df = pd.read_csv(out)
    assert (df["minutes"] >= 500).all()


def test_religiable_threshold_zero_includes_everyone(tmp_csv, tmp_path):
    out = tmp_path / "ranked.csv"
    cli.run(["--csv", tmp_csv, "--out", str(out), "--min-mins", "0"])
    df = pd.read_csv(out)
    sample = pd.read_csv(tmp_csv)
    assert len(df) == len(sample)


def test_position_filter(tmp_csv, tmp_path):
    out = tmp_path / "ranked.csv"
    cli.run(["--csv", tmp_csv, "--out", str(out),
             "--pos", "ST", "--min-mins", "200"])
    df = pd.read_csv(out)
    assert (df["position"] == "ST").all()


def test_league_filter(tmp_csv, tmp_path):
    out = tmp_path / "ranked.csv"
    cli.run(["--csv", tmp_csv, "--out", str(out),
             "--league", "Serie A", "--min-mins", "200"])
    df = pd.read_csv(out)
    assert (df["league"] == "Serie A").all()


def test_json_mode_shape(tmp_csv, tmp_path, capsys):
    cli.run(["--csv", tmp_csv, "--out", str(tmp_path / "r.csv"),
             "--json", "--min-mins", "200"])
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list) and payload
    for row in payload:
        assert {"score", "player", "team", "league", "position", "reasons"} <= set(row)


def test_missing_csv_is_usage_error(tmp_path):
    assert cli.run(["--csv", str(tmp_path / "nope.csv")]) == 2
