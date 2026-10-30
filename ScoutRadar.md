# ScoutRadar — find them before the hype

> A free, personal football scouting tool that flags players performing above
> their position, minutes and club profile before anyone starts tweeting about
> them.

Status: idea draft (reviewed 2026-10-12). Everything below is a plan, not code yet.
Data-limit findings and licensing notes are verified against the live sources —
see sections 5 and 8, and the open questions at the end.

---

## 1. What it is

ScoutRadar answers one question: **who is quietly outperforming their context
right now?** Not "who has the best stats" — who is doing well *relative to
their position, their minutes and their club's profile*, before that shows up
in transfer-rumour coverage.

- Tracks my teams: **Chelsea** (main, pinned), Leicester, Leeds.
- Scans **Premier League, Bundesliga, Serie A** by default; the league list is
  config, not code — add La Liga / Ligue 1 / Championship as one line.
- Outputs a ranked shortlist, per-player pages, watchlist + fixture alerts.
- Everything is derived data and honest methodology: a methodology page
  explains the score, and a backtest says whether the score ever worked.

The radar metaphor is the personality: the signal is the player, the noise is
the hype — and the tool's whole job is separating those two.

## 2. The score (the actual idea)

```
Breakout Score = weighted mix of:
  - position-relative performance   (per-90 KPIs z-scored vs same position)
  - rolling form                    (last 5-10 games weighted heavier)
  - output per minute               (low minutes, high contribution)
  - consistency                     (variance of per-90 output)
  - low-profile flag                (low minutes / smaller club bonus)
+ Isolation Forest anomaly detection to surface performers the weights miss
```

Pipeline:

1. Load player stats, normalise to per-90, drop players under a minutes
   threshold (starting value: 450 min over the season — a tune-me number).
2. Z-score / percentile each KPI **vs players in the same position group**.
3. Combine into the Breakout Score with weights in **one table, one file**
   (same pattern as ioc-triage's scoring table — never scattered maths).
4. Isolation Forest on the z-scored feature block for outliers the weights miss.
5. Backtest: rank using only data available *before* a past season, check
   whether the top-k actually broke out later. Precision@k, no leakage.

**Normalisation subtlety (from review):** per-league-per-position sounds right
but is statistically thin — with 3 leagues you have only ~30 players per
position per league. So:

- **Primary score: cross-league adjusted** (position group across all scanned
  leagues, with a league-strength adjustment).
- **Secondary view: per-league-per-position**, shown only when n > ~20
  players; otherwise fall back to the cross-league score and say so on the
  player page.

Big-goalkeepers, wide-forwards and pure No. 9s cannot share one score — the
KPI set per position group is selected per group, not a universal list.

## 3. Stack (keep it simple)

- **Python + pandas + scikit-learn.** One package, CLI entry points
  (`scout-radar rank`, `scout-radar fixtures`, `scout-radar alert`).
- **Storage: SQLite for cache/history, CSV for the human-readable outputs**
  (the ranked CSV is Step 1's deliverable and stays canonical).
- **No backend server.** Static dashboard on GitHub Pages
  (HTML/JS + Chart.js or Plotly reading committed JSON).
- **GitHub Actions cron:** fetch data → compute scores → commit JSON. Runs a
  few times per week, not per minute — the data updates slowly anyway.
- **Alerts: ntfy.sh** (phone + PC) and `notify-send` on Linux.

Conventions to keep (they're already working across my other projects):

- Thin dependencies. pandas + scikit-learn + requests is the whole list.
- **Offline tests against recorded pages** (FBref HTML fixtures), same pattern
  as ioc-triage's recorded API responses. The suite never touches the network.
- Weights, thresholds and league config in one place, described in the README.

## 4. The data layer (verified findings)

This section is from the 2026-10-12 source check — re-verify if building later.

### football-data.org (free tier)

- ✅ Fixtures, schedules (delayed), results (delayed), league tables, top
  scorers for **Premier League, Bundesliga, Serie A** — all on the free plan,
  plus Championship, La Liga, Ligue 1.
- **10 calls/minute.** Fine for a cron job that fetches fixtures/standings a
  few times per week.
- ❌ **No per-90 KPIs.** Free tier has no detailed player event statistics. It
  is a *schedules* source for this project, not a *KPIs* source.
- Usage: personal/non-commercial. Don't mirror their raw feed on the public
  dashboard — that's what their paid tiers exist for.

### FBref (the KPI workhorse)

- Free per-90 tables (mins, goals, xG-adjacent stats, progressive carries,
  tackles, blocks...) for all scanned leagues, refreshed every season.
- **No official API — HTML table scraping** (`pandas.read_html`). ToS is
  lenient on low-rate non-commercial use but silent about redistribution:
  **publish aggregates and derived scores, not raw scraped tables.**
- FBref goes down under peak load; it happens often. Therefore **cache-first
  scraping**: hit each page at most once per day, keep a local CSV/SQLite
  mirror, never re-scrape inside a session.

### StatsBomb Open Data

- ✅ Event data (JSON) for **specific past seasons** — e.g. Premier League
  2015/16, Ligue 1 2017/18. **No current-season data.**
- Role: **build and backtest the scoring method**, not live coverage. That is
  actually ideal: PL 2015/16's hype trajectories are fully in the past, so the
  backtest can run end-to-end before trusting the score on 2026/27 data.
- **License condition:** free for research/public use, but anything
  published must state the source as StatsBomb and use their logo (in their
  media pack). The methodology page carries that attribution.

## 5. Pipeline (delivery order — risk first)

1. **Step 1: ranked CSV script**, fed from a **static hand-prepared CSV**
   (~200 players, rough KPIs). Prove the scoring maths before any scraping.
   Deliverable: `out/ranked.csv` + a `--format markdown` table.
2. **Data layer:** FBref scrape → cache-first CSV/SQLite mirror. The riskiest
   part outside the maths. Fixture tests against saved HTML pages.
3. **Backtest on StatsBomb open seasons** (PL 2015/16 first). Report
   precision@k. Proves the score isn't garbage before a dashboard exists.
4. **Dashboard:** ranked shortlist with filters (position, age, league, min
   minutes); per-player page (per-90 bars, z-score radar, form trend);
   watchlist; fixtures for Chelsea/Leicester/Leeds; methodology page.
5. **Cron:** GH Actions fetch → score → commit JSON for the dashboard.
6. **Alerts:** watchlisted player starts, kickoff in 30 min, breakout
   performance in a match → ntfy.sh + notify-send.

## 6. Team Form tracker (scope addition)

Same fetch, different output:

- PPG, xG for/against per team per league.
- Rolling 5-game trend line.
- Flag **overperforming / underperforming vs xG** — Points per xG is the
  "lucky/unlucky" proxy; a team massively outperforming xG is a correction
  candidate, and the players on it inherit that context (the score's
  low-profile flag should read this, or "small club" quietly means "good team".)

## 7. Dashboard pages

- **Radar (home):** ranked shortlist, filters, pinned Chelsea team card.
- **Player page:** per-90 bars vs position median, z-score radar, form trend,
  which KPIs drove the score (occlusion-style explanation, the PhishGuard
  pattern: don't just show a number, show what moved it).
- **Teams:** Form tracker over/under-xG flags for scanned leagues.
- **Fixtures:** next fixtures for my three clubs with watchlist markers.
- **Methodology:** the score formula, weights, thresholds, data sources with
  logos/attribution, and the backtest result. Updated every time a weight
  changes — a score without a changelog is astrology.

## 8. Privacy & licensing notes

- Personal, non-commercial use. Dashboard is public but publishes **derived
  scores and aggregates only** — no raw FBref tables mirrored, no raw
  football-data.org feed reproduced.
- **StatsBomb attribution is a condition, not a courtesy:** source statement +
  logo on the methodology page and anywhere data-driven results are posted.
- FBref: low-rate, cached scraping only; respect robots.txt; if FBref
  operators ever signal disapproval, the scrape layer is modular enough to
  swap or stop.
- No personal data of anyone's — all data is public match statistics.
- The tool's verdicts are estimates about humans. Tone on the player pages
  must stay descriptive ("outperforming his position baseline by 1.4 SD")
  not evaluative ("future star"). A scouting tool that sounds like a
  certainty machine will be wrong publicly, and often.

## 9. Backtest design (the credibility layer)

- **Walk-forward:** for each past season, compute the score using only
  data available before the season start; collect top-k; compare against the
  season that followed. Precision@k reported per position group.
- **Breakout definition (starting values, tune-me):** minutes share jumps ≥ 2x
  or per-90 output improves ≥ 0.5 SD vs previous season.
- **Hype-proxy control:** exclude players already famous at prediction time
  (prior-season star ratings / big-club first-team regulars at big clubs) —
  otherwise the backtest measures "predicting what scouts already ranked",
  which is the opposite of the point.
- **Baseline to beat:** naive per-90 goals+assists ranking. If the Breakout
  Score can't beat "who scores most", the weighting is decoration.
- PL 2015/16 first (StatsBomb open data + fully known outcomes), then any
  season the fixture layer can reconstruct.

## 10. Repository layout (draft)

```
scoutradar/
  src/scoutradar/
    config.py          # league list, teams, weights, thresholds (one file)
    sources/           # fbref.py, footballdata.py (fetch + cache layer)
    model/             # normalise.py, score.py, anomaly.py, backtest.py
    report.py          # ranked CSV/markdown
    fixtures.py        # fixtures + watchlist matching
    alert.py           # ntfy.sh / notify-send
  tests/               # offline, fixture-HTML served, never hits network
  dashboard/           # static site committed to GitHub Pages
  data/                # committed JSON for the dashboard + CSV outputs
  .github/workflows/   # CI (pytest) + cron (fetch → score → commit)
```

## 11. Commands (draft)

- `scout-radar rank --pos FW --min-mins 450 --league all` → ranked.csv + table
- `scout-radar backtest --season 2015-16 --k 20`
- `scout-radar fixtures --team chelsea --watchlist`
- `scout-radar alert kickoff` / `scout-radar alert breakout`
- `scout-radar serve-dashboard` → builds static JSON + HTML (no server, just a
  build step for GitHub Pages)

## 12. Honest limits (write these on the dashboard)

- Per-90 stats reward players in good teams; z-scores expose the same risk in
  reverse. Cross-context comparison is the hard part and never fully solved.
- Isolation Forest finds *statistically unusual* players — some unusual
  players are just unusual (a striker who crosses a lot), not outstanding.
- Delayed scores on a cron pipeline — by design. ScoutRadar is for patterns
  over weeks, not live match tracking.
- Sample sizes per league-position are small; uncertainty is displayed, never
  hidden. A player with 480 minutes carries more noise than the z-score admits.

## 13. Suggestions to consider

- **Start with the maths on a CSV, not the scraping.** Step 1 exists for this.
- **Pin the score formula in tests** (golden-master style, PhishGuard
  pattern). Weight changes should be visible diffs, not silent drift.
- **Keep the score explainable on the player page.** If a number can't be
  defended in one sentence per component, drop the component.
- **Read-only dashboard data.** Cron commits JSON; Pages serves it; humans
  never interact with the pipeline.
- **Alert decisions live in config**, not code — which events matter is a
  taste question and it will change weekly.
- **Name check before committing:** search for ScoutRadar collisions on
  GitHub. It reads clean but verify.
- **License: MIT** for the code; data-attribution carried by the dashboard.

## 14. Open questions

- **The Henderson problem (added 2026-10-12, after Chelsea 5-1 Bournemouth):**
  the real thing that triggered this project tangibly: Jordan Henderson, 36,
  a summer signing no Chelsea fan had expectations for, debuted with a brace
  and an assist. In the score as designed, the low-profile flag would score
  him LOW (famous club, few minutes yet). Same trap for a 20-year-old Chelsea
  DM with 380 minutes (sample CSV: Callum Wright). Candidate fix: the
  low-profile component treats **recent transfers** (new club this season) as
  their own low-profile sub-case — unfamiliar club ≠ small club. The
  backtest ablation (flag vs no-flag) should test this variant too.
- **FBref redistribution silence:** they permit low-rate non-commercial
  access but say nothing about re-publishing. Aggregates-only policy is the
  answer for now — but should the dashboard even show per-player per-90
  *values*, or only z/percentile ranks? Ranks-only is safer and loses little.
- **Statistically thin per-league-position samples:** fall back to
  cross-league below n = 20 — confirmed as the rule, but should the player
  page *always* show the wider-n score with the narrower one as context?
- **Which breakout definition is the honest one?** Minutes-share jump is a
  "career progression" signal; per-90 SD jump is a "form" signal. They flag
  different players — possibly both, possibly two different tabs.
- **Isolation Forest contamination parameter** (expected outlier fraction)
  will dominate its output — needs tuning on the backtest, not by eye.
- **Does the low-profile flag double-count "good team" context?** Section 6
  suggests reading Team Form's xG-overperformance into it so a great player on
  a lucky-but-poor team isn't buried and a passenger on a great team isn't
  flagged. Worth a backtest ablation: score with vs without the flag.
- **StatsBomb 360 and lineups** — useful (starting XI data drives the
  "watchlisted player starts" alert) for open seasons, but current-season
  lineups must come from football-data.org, whose free tier is schedule-only.
  Is "player starts" detectable *reliably* enough on the free tier to be an
  alert type, or should v1 alerts be kickoff-only + breakout-after-the-fact?
