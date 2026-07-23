"""
Personal Sportsbook Odds Tracker
Supports main lines + Player Props
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

st.set_page_config(
    page_title="Odds Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us"

SPORTS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAF": "americanfootball_ncaaf",
    "NCAAB": "basketball_ncaab",
}

# Common player prop markets (The Odds API keys)
PLAYER_PROP_MARKETS = {
    "NBA": [
        "player_points", "player_rebounds", "player_assists",
        "player_threes", "player_blocks", "player_steals",
        "player_points_rebounds_assists", "player_points_rebounds",
        "player_points_assists", "player_rebounds_assists"
    ],
    "NFL": [
        "player_pass_yds", "player_pass_tds", "player_pass_completions",
        "player_rush_yds", "player_rush_tds", "player_receptions",
        "player_reception_yds", "player_reception_tds",
        "player_anytime_td", "player_1st_td", "player_pass_interceptions"
    ],
    "MLB": [
        "player_hits", "player_total_bases", "player_rbis",
        "player_runs_scored", "player_strikeouts", "player_home_runs",
        "player_stolen_bases", "player_hits_runs_rbis"
    ],
    "NHL": [
        "player_points", "player_goals", "player_assists",
        "player_shots_on_goal", "player_blocked_shots"
    ],
    "NCAAF": [
        "player_pass_yds", "player_rush_yds", "player_reception_yds",
        "player_anytime_td", "player_pass_tds"
    ],
    "NCAAB": [
        "player_points", "player_rebounds", "player_assists", "player_threes"
    ],
}

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
            description TEXT,
            price REAL,
            point REAL,
            last_update TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_odds_to_db(records: list, sport_key: str):
    if not records:
        return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    rows = []
    for r in records:
        rows.append((
            now, sport_key,
            r.get("event_id"), r.get("commence_time"),
            r.get("home_team"), r.get("away_team"),
            r.get("bookmaker"), r.get("market"),
            r.get("outcome"), r.get("description"),
            r.get("price"), r.get("point"), r.get("last_update")
        ))
    c.executemany("""
        INSERT INTO odds_snapshots
        (timestamp, sport_key, event_id, commence_time, home_team, away_team,
         bookmaker, market, outcome, description, price, point, last_update)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    return len(rows)


def get_api_key():
    # Prefer secrets, fall back to sidebar
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key", type="password")
    return key


def fetch_events(api_key: str, sport_key: str):
    """Get list of upcoming events (no odds yet)."""
    url = f"{API_BASE}/sports/{sport_key}/events"
    params = {"apiKey": api_key}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return []


def fetch_event_odds(api_key: str, sport_key: str, event_id: str, markets: str):
    """Fetch odds (including player props) for one specific event."""
    url = f"{API_BASE}/sports/{sport_key}/events/{event_id}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Could not fetch props for event: {e}")
        return None


def flatten_event_odds(event_data: dict) -> list:
    """Turn the event odds response into flat rows."""
    if not event_data:
        return []
    records = []
    event_id = event_data.get("id")
    home = event_data.get("home_team")
    away = event_data.get("away_team")
    commence = event_data.get("commence_time")

    for book in event_data.get("bookmakers", []):
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
                    "description": outcome.get("description"),  # player name for props
                    "price": outcome.get("price"),
                    "point": outcome.get("point"),
                    "last_update": last_update,
                })
    return records


def format_odds(price):
    if price is None:
        return "-"
    try:
        return f"{int(price):+d}"
    except:
        return str(price)


def main():
    init_db()

    st.title("📊 Personal Odds + Player Props Tracker")
    st.caption("Private use only • Data from The Odds API")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your API key in **Manage app → Secrets** or type it in the sidebar.")
        st.stop()

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]

        st.markdown("---")
        st.markdown("**What to fetch**")
        want_main = st.checkbox("Main lines (ML / Spread / Total)", value=True)
        want_props = st.checkbox("Player Props", value=True)

        prop_list = PLAYER_PROP_MARKETS.get(sport_name, [])
        if want_props and prop_list:
            selected_props = st.multiselect(
                "Which player props?",
                options=prop_list,
                default=prop_list[:4]  # first few by default
            )
        else:
            selected_props = []

    # ---- Step 1: Load games ----
    st.subheader("1. Upcoming Games")
    if st.button("Load Games", type="primary"):
        with st.spinner("Loading games..."):
            events = fetch_events(api_key, sport_key)
            st.session_state["events"] = events
            st.session_state["sport_key"] = sport_key
            st.session_state["sport_name"] = sport_name

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** to see upcoming matchups.")
        st.stop()

    # Show games in a nice table
    game_rows = []
    for e in events:
        game_rows.append({
            "id": e["id"],
            "Away": e.get("away_team"),
            "Home": e.get("home_team"),
            "Start (UTC)": e.get("commence_time", "")[:16].replace("T", " "),
        })
    games_df = pd.DataFrame(game_rows)
    st.dataframe(games_df[["Away", "Home", "Start (UTC)"]], use_container_width=True, hide_index=True)

    # ---- Step 2: Select games & fetch odds ----
    st.subheader("2. Fetch Odds / Player Props")

    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in game_rows}
    chosen_labels = st.multiselect("Select one or more games", list(options.keys()))

    if st.button("Fetch Selected Games", type="primary") and chosen_labels:
        all_records = []
        progress = st.progress(0)
        status = st.empty()

        markets = []
        if want_main:
            markets.extend(["h2h", "spreads", "totals"])
        if want_props and selected_props:
            markets.extend(selected_props)
        markets_str = ",".join(markets)

        for i, label in enumerate(chosen_labels):
            event_id = options[label]
            status.write(f"Fetching {label} ...")
            data = fetch_event_odds(api_key, sport_key, event_id, markets_str)
            records = flatten_event_odds(data)
            all_records.extend(records)
            progress.progress((i + 1) / len(chosen_labels))

        if all_records:
            n = save_odds_to_db(all_records, sport_key)
            st.success(f"Saved {n} odds rows")
            st.session_state["last_records"] = all_records
        else:
            st.warning("No odds returned. Try different markets or check your remaining credits.")

    # ---- Display results ----
    records = st.session_state.get("last_records", [])
    if records:
        st.subheader("Results")
        df = pd.DataFrame(records)

        # Filters
        c1, c2, c3 = st.columns(3)
        with c1:
            books = st.multiselect("Books", sorted(df["bookmaker"].unique()), default=[])
        with c2:
            mkts = st.multiselect("Markets", sorted(df["market"].unique()), default=[])
        with c3:
            # For props, filter by player name
            players = sorted([x for x in df["description"].dropna().unique() if x])
            player_filter = st.multiselect("Players", players, default=[])

        filtered = df.copy()
        if books:
            filtered = filtered[filtered["bookmaker"].isin(books)]
        if mkts:
            filtered = filtered[filtered["market"].isin(mkts)]
        if player_filter:
            filtered = filtered[filtered["description"].isin(player_filter)]

        # Nice display columns
        show = filtered[["home_team", "away_team", "bookmaker", "market", "description", "outcome", "price", "point"]].copy()
        show["price"] = show["price"].apply(format_odds)
        show = show.rename(columns={
            "description": "Player",
            "outcome": "Side",
            "price": "Odds",
            "point": "Line"
        })
        st.dataframe(show, use_container_width=True, height=500)

        # Quick best odds for a selected prop
        st.markdown("#### Best available prices")
        if not filtered.empty:
            best = (
                filtered.groupby(["market", "description", "outcome", "point"])["price"]
                .max()
                .reset_index()
                .sort_values(["market", "description"])
            )
            best["price"] = best["price"].apply(format_odds)
            st.dataframe(best, use_container_width=True)

    st.divider()
    st.caption("Personal use only • Credits are used per market per game when fetching props")


if __name__ == "__main__":
    main()
