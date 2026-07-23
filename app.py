"""
Personal Sportsbook Odds Tracker
Built for private use only.
Tracks live odds + historical line movement patterns.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

# -------------------------------------------------
# Config
# -------------------------------------------------
st.set_page_config(
    page_title="Odds Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"

# Popular sports keys from The Odds API
SPORTS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAF": "americanfootball_ncaaf",
    "NCAAB": "basketball_ncaab",
    "Soccer - EPL": "soccer_epl",
    "Soccer - MLS": "soccer_usa_mls",
    "UFC / MMA": "mma_mixed_martial_arts",
}

MARKETS = {
    "Moneyline (h2h)": "h2h",
    "Spreads": "spreads",
    "Totals (Over/Under)": "totals",
}

REGIONS = "us"  # us, uk, eu, au

# -------------------------------------------------
# Database helpers
# -------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sport_key TEXT,
            event_id TEXT,
            commence_time TEXT,
            home_team TEXT,
            away_team TEXT,
            bookmaker TEXT,
            market TEXT,
            outcome TEXT,
            price REAL,
            point REAL,
            last_update TEXT
        )
    """)
    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_time 
        ON odds_snapshots(event_id, timestamp)
    """)
    conn.commit()
    conn.close()


def save_odds_to_db(odds_data: list, sport_key: str):
    """Save a list of odds records to SQLite."""
    if not odds_data:
        return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    rows = []
    for item in odds_data:
        rows.append((
            now,
            sport_key,
            item.get("event_id"),
            item.get("commence_time"),
            item.get("home_team"),
            item.get("away_team"),
            item.get("bookmaker"),
            item.get("market"),
            item.get("outcome"),
            item.get("price"),
            item.get("point"),
            item.get("last_update"),
        ))
    c.executemany("""
        INSERT INTO odds_snapshots 
        (timestamp, sport_key, event_id, commence_time, home_team, away_team,
         bookmaker, market, outcome, price, point, last_update)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)


def load_historical(event_id: str = None, hours: int = 48) -> pd.DataFrame:
    """Load recent historical snapshots."""
    conn = sqlite3.connect(DB_PATH)
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    if event_id:
        query = """
            SELECT * FROM odds_snapshots 
            WHERE event_id = ? AND timestamp >= ?
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn, params=(event_id, cutoff))
    else:
        query = """
            SELECT * FROM odds_snapshots 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 5000
        """
        df = pd.read_sql_query(query, conn, params=(cutoff,))
    conn.close()
    return df


def get_latest_snapshot() -> pd.DataFrame:
    """Get the most recent snapshot of all odds."""
    conn = sqlite3.connect(DB_PATH)
    # Get the latest timestamp first
    latest = pd.read_sql_query(
        "SELECT MAX(timestamp) as ts FROM odds_snapshots", conn
    )
    if latest.empty or latest["ts"].iloc[0] is None:
        conn.close()
        return pd.DataFrame()
    ts = latest["ts"].iloc[0]
    df = pd.read_sql_query(
        "SELECT * FROM odds_snapshots WHERE timestamp = ?", conn, params=(ts,)
    )
    conn.close()
    return df


# -------------------------------------------------
# API helpers
# -------------------------------------------------
def fetch_odds(api_key: str, sport_key: str, markets: str = "h2h,spreads,totals") -> list:
    """
    Fetch current odds from The Odds API.
    Returns a flattened list of records ready for the database.
    """
    url = f"{API_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return []

    records = []
    for event in data:
        event_id = event.get("id")
        home = event.get("home_team")
        away = event.get("away_team")
        commence = event.get("commence_time")
        for book in event.get("bookmakers", []):
            book_key = book.get("key")
            last_update = book.get("last_update")
            for market in book.get("markets", []):
                market_key = market.get("key")
                for outcome in market.get("outcomes", []):
                    records.append({
                        "event_id": event_id,
                        "commence_time": commence,
                        "home_team": home,
                        "away_team": away,
                        "bookmaker": book_key,
                        "market": market_key,
                        "outcome": outcome.get("name"),
                        "price": outcome.get("price"),
                        "point": outcome.get("point"),
                        "last_update": last_update,
                    })
    return records


def get_remaining_requests(api_key: str) -> dict:
    """Check remaining API quota (from response headers ideally, but we can call sports list)."""
    url = f"{API_BASE}/sports"
    try:
        resp = requests.get(url, params={"apiKey": api_key}, timeout=10)
        remaining = resp.headers.get("x-requests-remaining", "unknown")
        used = resp.headers.get("x-requests-used", "unknown")
        return {"remaining": remaining, "used": used}
    except Exception:
        return {"remaining": "?", "used": "?"}


# -------------------------------------------------
# UI Helpers
# -------------------------------------------------
def american_to_decimal(american: float) -> float:
    if american is None:
        return None
    if american > 0:
        return round(1 + american / 100, 3)
    else:
        return round(1 + 100 / abs(american), 3)


def format_odds(price):
    if price is None:
        return "-"
    return f"{int(price):+d}" if price == int(price) else f"{price:+.1f}"


# -------------------------------------------------
# Main App
# -------------------------------------------------
def main():
    init_db()

    st.title("📊 Personal Odds Tracker")
    st.caption("Private dashboard for sportsbook odds & line movement patterns")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        api_key = st.text_input(
            "The Odds API Key",
            type="password",
            help="Get a free key at https://the-odds-api.com (500 credits/month free)"
        )

        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]

        selected_markets = st.multiselect(
            "Markets",
            options=list(MARKETS.keys()),
            default=["Moneyline (h2h)", "Spreads"]
        )
        market_keys = ",".join([MARKETS[m] for m in selected_markets]) if selected_markets else "h2h"

        auto_refresh = st.checkbox("Show refresh button", value=True)

        st.divider()
        st.markdown("### How to use")
        st.markdown("""
        1. Paste your free API key  
        2. Choose sport & markets  
        3. Click **Fetch & Save Odds**  
        4. Explore current lines + historical movement  
        """)
        st.markdown("---")
        st.caption("Data is stored locally in `odds_data.db`")

    # ---- Fetch Section ----
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        fetch_btn = st.button("🔄 Fetch & Save Current Odds", type="primary", use_container_width=True)
    with col2:
        if api_key:
            quota = get_remaining_requests(api_key)
            st.metric("API Credits Left", quota.get("remaining", "?"))
    with col3:
        st.metric("DB File", "odds_data.db" if DB_PATH.exists() else "Not created")

    if fetch_btn:
        if not api_key:
            st.warning("Please enter your The Odds API key in the sidebar.")
        else:
            with st.spinner(f"Fetching {sport_name} odds..."):
                records = fetch_odds(api_key, sport_key, market_keys)
                if records:
                    n = save_odds_to_db(records, sport_key)
                    st.success(f"Saved {n} odds rows for {sport_name}")
                else:
                    st.warning("No odds returned. Check sport key or API quota.")

    st.divider()

    # ---- Current Odds Table ----
    st.subheader("📈 Latest Odds Snapshot")
    latest = get_latest_snapshot()

    if latest.empty:
        st.info("No data yet. Click **Fetch & Save Current Odds** to get started.")
        # Show a small demo with mock data so the UI isn't empty
        st.markdown("#### Demo preview (mock data)")
        mock = pd.DataFrame([
            {"home_team": "Chiefs", "away_team": "Bills", "bookmaker": "draftkings", "market": "h2h", "outcome": "Chiefs", "price": -150},
            {"home_team": "Chiefs", "away_team": "Bills", "bookmaker": "fanduel", "market": "h2h", "outcome": "Chiefs", "price": -145},
            {"home_team": "Chiefs", "away_team": "Bills", "bookmaker": "betmgm", "market": "h2h", "outcome": "Chiefs", "price": -155},
            {"home_team": "Chiefs", "away_team": "Bills", "bookmaker": "draftkings", "market": "h2h", "outcome": "Bills", "price": +130},
            {"home_team": "Chiefs", "away_team": "Bills", "bookmaker": "fanduel", "market": "h2h", "outcome": "Bills", "price": +125},
        ])
        st.dataframe(mock, use_container_width=True)
    else:
        # Clean view
        display_cols = ["home_team", "away_team", "bookmaker", "market", "outcome", "price", "point", "commence_time"]
        available = [c for c in display_cols if c in latest.columns]
        df_view = latest[available].copy()
        df_view["price"] = df_view["price"].apply(format_odds)

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            teams = sorted(set(df_view["home_team"].tolist() + df_view["away_team"].tolist()))
            team_filter = st.multiselect("Filter teams", teams, default=[])
        with fcol2:
            books = sorted(df_view["bookmaker"].unique())
            book_filter = st.multiselect("Filter books", books, default=[])
        with fcol3:
            mkts = sorted(df_view["market"].unique())
            mkt_filter = st.multiselect("Filter markets", mkts, default=[])

        filtered = df_view.copy()
        if team_filter:
            filtered = filtered[
                filtered["home_team"].isin(team_filter) | filtered["away_team"].isin(team_filter)
            ]
        if book_filter:
            filtered = filtered[filtered["bookmaker"].isin(book_filter)]
        if mkt_filter:
            filtered = filtered[filtered["market"].isin(mkt_filter)]

        st.dataframe(
            filtered.sort_values(["home_team", "market", "bookmaker"]),
            use_container_width=True,
            height=400
        )

        # Best odds highlight
        st.markdown("#### 🏆 Best available prices (Moneyline)")
        ml = latest[latest["market"] == "h2h"].copy()
        if not ml.empty:
            best = (
                ml.groupby(["home_team", "away_team", "outcome"])["price"]
                .max()
                .reset_index()
                .sort_values(["home_team", "outcome"])
            )
            best["price"] = best["price"].apply(format_odds)
            st.dataframe(best, use_container_width=True)

    # ---- Line Movement / Patterns ----
    st.divider()
    st.subheader("📉 Line Movement & Patterns")

    hist = load_historical(hours=72)
    if hist.empty:
        st.info("No historical data yet. Fetch odds a few times over the day to see movement charts.")
    else:
        # Select an event
        events = hist[["event_id", "home_team", "away_team"]].drop_duplicates()
        event_options = {
            f"{row.away_team} @ {row.home_team}": row.event_id
            for _, row in events.iterrows()
        }
        if event_options:
            chosen_label = st.selectbox("Select game for line movement", list(event_options.keys()))
            chosen_id = event_options[chosen_label]

            game_hist = hist[hist["event_id"] == chosen_id].copy()
            game_hist["timestamp"] = pd.to_datetime(game_hist["timestamp"])

            # Moneyline movement chart
            ml_hist = game_hist[game_hist["market"] == "h2h"]
            if not ml_hist.empty:
                fig = px.line(
                    ml_hist,
                    x="timestamp",
                    y="price",
                    color="bookmaker",
                    line_dash="outcome",
                    title=f"Moneyline Movement – {chosen_label}",
                    labels={"price": "American Odds", "timestamp": "Time"},
                )
                fig.update_layout(height=450, hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)

            # Spreads movement
            sp_hist = game_hist[game_hist["market"] == "spreads"]
            if not sp_hist.empty:
                fig2 = px.line(
                    sp_hist,
                    x="timestamp",
                    y="point",
                    color="bookmaker",
                    line_dash="outcome",
                    title=f"Spread Movement – {chosen_label}",
                    labels={"point": "Point Spread", "timestamp": "Time"},
                )
                fig2.update_layout(height=400, hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)

            # Simple pattern stats
            st.markdown("#### Quick Pattern Stats")
            if not ml_hist.empty:
                open_prices = ml_hist.sort_values("timestamp").groupby(["bookmaker", "outcome"]).first()["price"]
                close_prices = ml_hist.sort_values("timestamp").groupby(["bookmaker", "outcome"]).last()["price"]
                move = (close_prices - open_prices).reset_index()
                move.columns = ["bookmaker", "outcome", "price_move"]
                move["direction"] = move["price_move"].apply(
                    lambda x: "🔴 Shortened" if x < 0 else ("🟢 Drifted" if x > 0 else "—")
                )
                st.dataframe(move, use_container_width=True)

    # Footer
    st.divider()
    st.caption(
        "Built for personal use only • Data from The Odds API • "
        "Store your API key securely • Never share this dashboard publicly if your key is embedded"
    )


if __name__ == "__main__":
    main()
