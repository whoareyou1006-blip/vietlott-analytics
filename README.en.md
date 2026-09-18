# 🎰 Vietlott Power 6/55 — Analytics & Prediction

Open-source dashboard that merges Power 6/55 draw results from **4 sources** into a single
SQLite database, then runs statistical predictions with **honest, verified verdicts**.

> **The only honest prediction tool**: every strategy is backtested against 300 draws and
> compared to pure randomness — because a random game has no winning system, we say so.

## ✨ Features

- **4-source data integration** (merged, cross-verified):
  | Source | Data |
  |---|---|
  | `vividraw/vietlim` (GitHub) | Full history — 1,399 draws (2017-08-01 → today) |
  | `xosovietlott.org` | All-time frequency table |
  | `atrungroi.com` | 100-draw frequency, number pairs, Jackpot history |
  | `kqxs.day` (wp-json API) | Draw results + **Jackpot 1/2 values** |

- **One unified SQLite DB** (`data/vietlott.db`): draws, frequencies (all-time/30/60/90),
  overdue numbers, Power numbers, pairs, Jackpot history.

- **2-series prediction engine** (v2):
  1. **Balanced** — time-decayed frequency + mean reversion, structure 3-odd/3-even, sum ~170
  2. **Hot + Cold** — recent hot numbers + long-overdue numbers, structure 4-odd/2-even
  - Structural constraints from real statistics: odd/even, sum 106–228 (90%), ≥4 decades, ≤2 consecutive
  - The two series never share a number (12/55 coverage)

- **Honest backtesting**: 300-draw walk-forward. Result — **every strategy equals randomness**.
  Reported truthfully, not to sell tickets.

- **Real probabilities** (hypergeometric): 0-hit 48.2%, 1-hit 39.5%, 2-hit 11.0%, 3-hit 1.27%,
  4-hit 0.06%, 5-hit 0.001%, Jackpot 1-in-28.9M. Buying more tickets is the only real edge.

- **Web dashboard** (no internet, no CDN): draws, frequency charts, overdue numbers, Jackpot,
  pairs, verification, data sources.

- **Auto-update** (v3): server checks for new draws **every 30 min**; on a new draw it
  auto-updates the DB and auto-runs both statistical + AI prediction. Manual update button too.

- **AI Mode** (v3): predict 2 series via **Google Gemini / OpenAI / Ollama (Cloud or local)**
  — stock context + stats sent to the model, AI returns 2 numbers sets with reasons.

> ## ⚠️ Disclaimer
> Power 6/55 is a random draw. Host-verified 300-draw backtests show all statistical strategies
> perform **no better than random**. Prediction only helps pick well-structured, non-duplicate
> tickets — it **cannot increase your odds**. The only real edge: buy more tickets. Play responsibly.

## 🚀 Quick start (fresh clone)

Requires **Python 3.8+** (stdlib only — no pip install needed).

```bash
git clone https://github.com/whoareyou1006-blip/vietlott-analytics.git
cd vietlott-analytics

python scripts/fetch_data.py    # collect from 4 sources (~1 min, needs internet)
python scripts/build_db.py      # build the SQLite database
python app/server.py 8000       # open http://localhost:8000
```

## 🌐 Deploy to Render (free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/whoareyou1006-blip/vietlott-analytics)

Or: Render.com → **New → Blueprint** → select this repo → **Apply**. `render.yaml` builds the
DB and starts the server automatically; it reads the `PORT` env var (Table-friendly).

## ⚙️ Commands

```
python scripts/fetch_data.py    # or fetch_data.py — collect raw data
python scripts/build_db.py      # build vietlott.db
python scripts/verify_db.py     # verify DB integrity
python scripts/predict.py       # console prediction + backtest
python app/server.py 8000       # web dashboard
```

## 📦 Structure

```
.
├── app           # web server + dashboard (index.html)
├── scripts       # fetch / build / predict / AI / auto-update
├── reports      # analysis docs (English + Vietnamese)
├── data         # generated at runtime (gitignored)
├── render.yaml  # Render blueprint
└── start.bat     # 1-click launcher (Windows)
```

## 📊 API

| Endpoint | Description |
|---|---|
| `/api/stats` | Overview (draws count, range, top jackpot) |
| `/api/draws?limit=20` | Latest draws |
| `/api/frequency?scope=all_time\|last_30\|last_60\|last_90\|power` | Frequencies |
| `/api/gan` | Overdue days per number |
| `/api/predict` | 2 predicted series + raw signals + structure |
| `/api/backtest?n=300` | Walk-forward results vs randomness |
| `/api/probabilities` | True odds for a 6/55 ticket |
| `/api/jackpots` | Top-20 Jackpot history |
| `/api/pairs` | Frequent number pairs |
| `/api/sources` | 4-source health |
| `POST /api/update` | Fetch new draws (background) |
| `GET /api/update/status` | Update + auto-predict status |
| `GET/POST /api/ai/config` | AI provider config (key masked) |
| `POST /api/ai/check` | Test AI connection |
| `POST /api/ai/models` | Load available models |
| `POST /api/ai/predict` | Predict 2 series via AI |

## 🛠 Tech

- Python stdlib only: `http.server`, `sqlite3`, `urllib` — zero dependencies, runs anywhere.
- SQLite WAL mode for concurrent reads.
- Full auto-update loop with 30-min background thread.

## 📄 License

MIT — free to use, modify, and share. Analytics only; not affiliated with Vietlott.
