# ScoutRadar

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)
[![CI](https://github.com/Flaxo49ja/scoutradar/actions/workflows/ci.yml/badge.svg)](https://github.com/Flaxo49ja/scoutradar/actions/workflows/ci.yml)

A free, personal football scouting tool that flags players performing well
relative to their **position, minutes and club profile** — before the hype.
Built for the question every scout actually asks: not "who has the best
stats?" but "who is quietly outperforming their context?"

**Status: Step 1 done** — the scoring engine and ranked-CSV CLI work end-to-end
on a hand-prepared sample table (`data/players_sample.csv`, invented-but-
plausible players). No scraping, no network, no API keys. The data layer
(FBref), backtest, dashboard, cron and alerts come next; the plan lives in
[`ScoutRadar.md`](ScoutRadar.md).

## Install

```bash
git clone https://github.com/Flaxo49ja/scoutradar.git && cd scoutradar
pip install --editable ".[dev]"
python -m pytest -q     # offline suite, 20 tests, never touches the network
```

## Usage

```bash
scout-radar                                    # score everything, write out/ranked.csv
scout-radar --top 10                           # show only the top 10 in the table
scout-radar --pos ST --pos AM                  # filter by detailed position (repeatable)
scout-radar --league "Premier League"          # filter by league (repeatable)
scout-radar --min-mins 300                     # lower the minutes threshold
scout-radar --json                             # machine-readable records
```

Exit codes: `0` ranked successfully, `2` usage error (bad CSV/columns),
`3` no qualified players matched the filters.

The ranked CSV carries every input column plus `group`, `score` (0–100) and
`reasons` — one line explaining each component's contribution, so a row can be
audited without reading code.

## The Breakout Score

A weighted sum of bounded components. **Weights live in one table
(`src/scoutradar/score.py`) and nowhere else.**

| Component | Max | What it measures |
|---|---|---|
| Position-relative performance | 40 | Mean z-score of the position group's KPIs (per-90, vs same position group) |
| Output per minute | 15 | KPIs min-max normalised within the position pool |
| Minutes-tested form | 15 | Minutes share of the position group — heavy load = tested form |
| Consistency | 10 | Spread across the KPI z-block; tight spread scores high |
| Low-profile flag | 20 | Below-median minutes + smaller club — the radar's whole job |

Rules of the engine:

- Players under the minutes threshold (default 450) are **dropped before
  z-scoring**, so an unqualified player never contaminates the pool they are
  measured against.
- KPIs are z-scored **per position group, cross-league** — per-
  league-per-position is statistically thin at this sample size (see plan doc).
- Which KPIs matter for which position is one table
  (`src/scoutradar/kpis.py`): a ST is judged on xG/goals/aerials, a DM on
  tackles/interceptions/progression. Never one universal list.
- Every point is truncated, never rounded up: the engine does not overstate.

## Tests

```bash
python -m pytest -q
```

The suite pins component behaviour the way PhishGuard pins model output: if a
weight changes, a test diff shows it — scores must never drift silently.
All tests run offline on the committed CSV.

## Roadmap (delivery order — risk first)

1. ✅ **Step 1** — scoring engine + ranked CSV on a static input table.
2. **Data layer** — FBref scrape → cache-first CSV/SQLite mirror, offline
   fixture tests against saved HTML.
3. **Backtest** — walk-forward on StatsBomb Open Data (PL 2015/16 first),
   precision@k, hype-proxy control. The credibility layer.
4. **Dashboard** — static JSON + HTML on GitHub Pages.
5. **Cron** — GitHub Actions: fetch → score → commit JSON.
6. **Alerts** — ntfy.sh / notify-send for watchlist + fixture events.

## Honest limits (read before trusting a number)

- The sample CSV is **invented placeholder data** — scores are real, the
  players are not. Everything works; nothing is scouting-true until the FBref
  layer lands.
- Per-90 stats reward players in good teams; z-scores shift the problem, not
  solve it. Cross-context comparison is the hard part.
- Weights are starting values, not findings. The backtest decides whether
  they survive.
- The score is an estimate about a human. It reads "outperforming his
  position baseline by 1.4 SD", never "future star".

## License

MIT — see [LICENSE](LICENSE).
