# Personal Sportsbook Odds Tracker

A private Streamlit dashboard that tracks live sportsbook odds and historical line-movement patterns.

Built for **you only**. No public sharing required.

---

## Features

- Live odds from 40+ sportsbooks via **The Odds API**
- Automatic saving of every snapshot to a local SQLite database
- Interactive tables with filters (team, book, market)
- Best-price finder for moneylines
- Line-movement charts (moneyline + spreads) over time
- Simple pattern detection (line shortened vs drifted)
- Completely local – your data never leaves your machine

---

## Quick Start (3 minutes)

### 1. Get a free API key
Go to → [https://the-odds-api.com](https://the-odds-api.com)  
Sign up → you get **500 free credits per month**.

### 2. Install & run

```bash
# Clone or download this folder, then:
cd odds-tracker

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### 3. Use it
1. Paste your API key in the sidebar
2. Pick a sport (NFL, NBA, MLB, etc.)
3. Click **Fetch & Save Current Odds**
4. Repeat a few times during the day to build history
5. Explore the movement charts

---

## How the data works

Every time you click “Fetch & Save”, the app:
1. Calls The Odds API
2. Flattens the response
3. Appends rows into `odds_data.db` (SQLite file next to the app)

You can open `odds_data.db` with any SQLite viewer or even Excel if you export it.

---

## Tips for pattern tracking

- Fetch odds every 15–60 minutes on game days
- Watch for **steam moves** (sudden sharp movement across multiple books)
- Compare opening line vs current line (shown in the Pattern Stats section)
- Best prices are highlighted so you can shop lines quickly

---

## File structure

```
odds-tracker/
├── app.py              ← Main Streamlit application
├── requirements.txt    ← Python packages
├── README.md           ← This file
└── odds_data.db        ← Created automatically (your historical data)
```

---

## Optional: Auto-refresh (advanced)

If you want the app to fetch automatically, you can later add:
- A simple cron job / Task Scheduler that runs a small Python script
- Or use Streamlit’s experimental fragment + timer

For most personal use, manually clicking “Fetch” a few times per day is enough and saves API credits.

---

## Privacy & Safety

- Everything runs on your computer
- API key stays in the sidebar (or you can put it in a `.env` file later)
- Never deploy this publicly with your real API key visible

---

Enjoy tracking the lines.  
If you want extra features (props, CLV calculator, Telegram alerts, etc.) just ask.
