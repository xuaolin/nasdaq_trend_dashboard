# NASDAQ Trend System V2

A GitHub Pages dashboard that uses **QQQ as a tradable Nasdaq-100 proxy** and calculates:

- MA20 / MA60 / MA120 / MA200
- RSI(14)
- 20-day and 60-day momentum
- Distance from moving averages
- VIX
- Nasdaq-100 breadth: % above MA50 and MA200
- 0–100 Technical Score
- Rule-based BUY / HOLD / WAIT / REDUCE / DEFENSIVE signal

## Architecture

The browser never calls Yahoo Finance directly.

```text
GitHub Actions
   ↓
Python + yfinance
   ↓
data/technical.json
   ↓
GitHub Pages
   ↓
index.html + app.js
```

This avoids browser CORS issues and keeps the dashboard static-hosting friendly.

## Score

```text
Trend      40
Momentum   25
Deviation  15
Volatility 10
Breadth    10
Total     100
```

The rule engine is separate from the score. That is intentional: a very low score can mean an
extreme oversold market, while a falling score from a previously high level can indicate a more
important deterioration in trend.

## Quick setup

1. Create a new public GitHub repository.
2. Upload **all files and folders** in this package, including `.github/workflows/update-data.yml`.
3. Open the repository's **Actions** tab.
4. Open **Update Nasdaq Technical Data** and run **Run workflow** once.
5. Confirm that `data/technical.json` has been updated.
6. Go to **Settings → Pages**.
7. Under **Build and deployment**, choose **Deploy from a branch**.
8. Select your default branch (usually `main`) and folder `/ (root)`.
9. Save. Your dashboard will appear at your GitHub Pages URL.

## Automatic update

The included workflow runs on weekdays at `22:30 UTC`, after the normal U.S. stock-market session.
You can change the cron expression in:

`.github/workflows/update-data.yml`

GitHub Actions also supports manual `workflow_dispatch`.

## Data notes

Price and VIX data are requested through `yfinance`. Breadth uses the current Nasdaq-100
constituent table from Wikipedia and then downloads daily price history for those tickers.
If breadth retrieval fails on a run, the dashboard still updates and applies a neutral breadth score.

## Files

```text
index.html
styles.css
app.js
requirements.txt
scripts/update_data.py
data/technical.json
.github/workflows/update-data.yml
README.md
```

## Important

This project is an educational technical-analysis dashboard, not investment advice.
Signal thresholds are transparent so they can be backtested and changed.
