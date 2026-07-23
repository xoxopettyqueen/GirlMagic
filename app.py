"""
Girl Magic Odds Tracker ✨
Batters focused + probable pitchers for matchup context
Locked to FanDuel • DraftKings • BetMGM • Bet365
"""

import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

st.set_page_config(
    page_title="Girl Magic Odds ✨",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 40%, #1f0f2e 100%);
        color: #fce7f3;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2a1435 0%, #1c0d24 100%);
        border-right: 1px solid #a855f7;
    }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }
    span[data-baseweb="tag"] { background-color: #db2777 !important; }
    .hot-card {
        background: linear-gradient(90deg, #831843, #4c1d95);
        border: 2px solid #f472b6;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0;
        color: #fdf2f8;
    }
    .pitcher-box {
        background: #2d1b3d;
        border: 1px solid #c084fc;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 6px 0;
        color: #fce7f3;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"
PREFERRED_BOOKS = ["fanduel", "draftkings", "betmgm", "bet365"]

SPORTS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
}

PLAYER_PROP_MARKETS = {
    "NBA": ["player_points", "player_rebounds", "player_assists", "player_threes", "player_blocks", "player_steals"],
    "NFL": ["player_pass_yds", "player_pass_tds", "player_rush_yds", "player_rush_tds", "player_receptions", "player_reception_yds", "player_anytime_td"],
    "MLB": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_strikeouts", "pitcher_strikeouts"],
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS odds_snapshots")
    c.execute("""CREATE TABLE odds_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, sport_key TEXT,
        event_id TEXT, commence_time TEXT, home_team TEXT, away_team TEXT,
        bookmaker TEXT, market TEXT, outcome TEXT, description TEXT,
        price REAL, point REAL, last_update TEXT)""")
    conn.commit()
    conn.close()

def save_odds_to_db(records, sport_key):
    if not records: return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    rows = [(now, sport_key, r.get("event_id"), r.get("commence_time"), r.get("home_team"), r.get("away_team"),
             r.get("bookmaker"), r.get("market"), r.get("outcome"), r.get("description"),
             r.get("price"), r.get("point"), r.get("last_update")) for r in records]
    c.executemany("INSERT INTO odds_snapshots (timestamp, sport_key, event_id, commence_time, home_team, away_team, bookmaker, market, outcome, description, price, point, last_update) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return len(rows)

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key 🔑", type="password")
    return key

def fetch_events(api_key, sport_key):
    try:
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error loading games: {e}")
        return []

def fetch_event_odds(api_key, sport_key, event_id, markets):
    params = {"apiKey": api_key, "regions": REGIONS, "markets": markets, "oddsFormat": "american", "dateFormat": "iso"}
    try:
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events/{event_id}/odds", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Could not fetch this game: {e}")
        return None

def flatten_event_odds(event_data):
    if not event_data: return []
    records = []
    for book in event_data.get("bookmakers", []):
        for market in book.get("markets", []):
            for outcome in market.get("outcomes", []):
                records.append({
                    "event_id": event_data.get("id"),
                    "commence_time": event_data.get("commence_time"),
                    "home_team": event_data.get("home_team"),
                    "away_team": event_data.get("away_team"),
                    "bookmaker": book.get("key"),
                    "market": market.get("key"),
                    "outcome": outcome.get("name"),
                    "description": outcome.get("description"),
                    "price": outcome.get("price"),
                    "point": outcome.get("point"),
                    "last_update": book.get("last_update"),
                })
    return records

def format_odds(price):
    if price is None: return "-"
    try: return f"{int(price):+d}"
    except: return str(price)

def last_two_digits(price):
    try: return abs(int(price)) % 100
    except: return None

def get_initials(name):
    parts = str(name).strip().split()
    if not parts: return None, None
    first = parts[0][0].upper() if parts[0] else None
    last = parts[-1][0].upper() if len(parts) > 1 else None
    return first, last

def is_preferred(book):
    if not book: return False
    b = book.lower()
    return any(p in b for p in PREFERRED_BOOKS)

def fetch_probable_pitchers():
    """Get today's probable pitchers from MLB Stats API (free)."""
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        pitchers = {}
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                teams = game.get("teams", {})
                away = teams.get("away", {})
                home = teams.get("home", {})
                away_name = away.get("team", {}).get("name", "")
                home_name = home.get("team", {}).get("name", "")
                away_p = away.get("probablePitcher", {}).get("fullName", "TBD")
                home_p = home.get("probablePitcher", {}).get("fullName", "TBD")
                key = f"{away_name} @ {home_name}"
                pitchers[key] = {"away_pitcher": away_p, "home_pitcher": home_p}
                # also store short names for matching
                pitchers[away_name] = away_p
                pitchers[home_name] = home_p
        return pitchers
    except Exception as e:
        st.warning(f"Could not load probable pitchers: {e}")
        return {}

def build_hot_list(df):
    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "odds": None, "market": None, "matchup": ""})

    props = df[
        (df["description"].notna()) & 
        (df["description"] != "") & 
        (df["bookmaker"].apply(is_preferred))
    ].copy()

    if props.empty:
        return []

    # BetMGM Same Odds
    mgm = props[props["bookmaker"].str.lower().str.contains("betmgm|mgm", na=False)]
    for (market, price), group in mgm.groupby(["market", "price"]):
        players = list(group["description"].unique())
        if len(players) >= 2:
            key = " + ".join(sorted(players))
            matchup = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}"
            scores[key]["score"] += 4
            scores[key]["reasons"].append(f"BetMGM Same Odds {format_odds(price)}")
            scores[key]["players"].update(players)
            scores[key]["odds"] = format_odds(price)
            scores[key]["market"] = market
            scores[key]["matchup"] = matchup

    # Bet365 +850
    bet365 = props[props["bookmaker"].str.lower().str.contains("bet365", na=False)]
    for _, row in bet365.iterrows():
        try:
            if abs(int(row["price"])) == 850:
                player = row.get("description") or row.get("outcome")
                if player:
                    key = player
                    scores[key]["score"] += 3
                    scores[key]["reasons"].append("Bet365 +850")
                    scores[key]["players"].add(player)
                    scores[key]["odds"] = format_odds(row["price"])
                    scores[key]["market"] = row["market"]
                    scores[key]["matchup"] = f"{row['away_team']} @ {row['home_team']}"
        except:
            pass

    # DraftKings ending 10
    dk = props[props["bookmaker"].str.lower().str.contains("draftkings|dk", na=False)]
    for _, row in dk.iterrows():
        if last_two_digits(row["price"]) == 10:
            player = row.get("description") or row.get("outcome")
            if player:
                key = player
                scores[key]["score"] += 3
                scores[key]["reasons"].append("DraftKings ends in 10")
                scores[key]["players"].add(player)
                scores[key]["odds"] = format_odds(row["price"])
                scores[key]["market"] = row["market"]
                scores[key]["matchup"] = f"{row['away_team']} @ {row['home_team']}"

    # Name matching
    for _, group in props.groupby("market"):
        players = list(group["description"].unique())
        matchup = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}" if len(group) else ""

        name_counts = defaultdict(list)
        for p in players:
            name_counts[p].append(p)
        for name, lst in name_counts.items():
            if len(lst) >= 2:
                scores[name]["score"] += 4
                scores[name]["reasons"].append("Exact same name")
                scores[name]["players"].add(name)
                scores[name]["matchup"] = matchup

        initials_map = defaultdict(list)
        for p in players:
            first, last = get_initials(p)
            if first and last:
                initials_map[first + last].append(p)
        for key_init, names in initials_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 3
                scores[key]["reasons"].append(f"Same initials {key_init}")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

        first_map = defaultdict(list)
        for p in players:
            first, _ = get_initials(p)
            if first:
                first_map[first].append(p)
        for letter, names in first_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 1
                scores[key]["reasons"].append(f"Same first letter {letter}")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

        for i, p1 in enumerate(players):
            first1, last1 = get_initials(p1)
            if not last1: continue
            for p2 in players[i+1:]:
                first2, _ = get_initials(p2)
                if first2 and last1 == first2:
                    key = " + ".join(sorted([p1, p2]))
                    scores[key]["score"] += 2
                    scores[key]["reasons"].append(f"Cross initial ({last1})")
                    scores[key]["players"].update([p1, p2])
                    scores[key]["matchup"] = matchup

    hot = []
    for key, data in scores.items():
        if data["score"] > 0:
            hot.append({
                "label": key,
                "score": data["score"],
                "reasons": list(set(data["reasons"])),
                "players": list(data["players"]),
                "odds": data["odds"],
                "market": data["market"],
                "matchup": data["matchup"]
            })
    return sorted(hot, key=lambda x: x["score"], reverse=True)

def main():
    init_db()
    st.title("💖 Girl Magic Odds Tracker ✨")
    st.caption("Batters focused • Probable pitchers for context • Locked to FD / DK / MGM / Bet365")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your API key in Manage app → Secrets.")
        st.stop()

    with st.sidebar:
        st.header("✨ Settings")
        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]
        st.markdown("---")
        want_main = st.checkbox("Main lines (ML / Spread / Total)", value=False)
        want_props = st.checkbox("Player Props", value=True)
        prop_list = PLAYER_PROP_MARKETS.get(sport_name, [])
        selected_props = st.multiselect("Which player props?", prop_list, default=["batter_home_runs"] if "batter_home_runs" in prop_list else prop_list[:2]) if want_props and prop_list else []
        st.markdown("---")
        line_mode = st.radio("Prop lines", ["Only 1 (lowest)", "All lines"], index=0)
        max_hot = st.slider("Max Hot List items", 3, 12, 7)

    # Probable pitchers
    pitchers = fetch_probable_pitchers()

    st.subheader("1️⃣ Upcoming Games")
    if st.button("Load Games 💫", type="primary"):
        with st.spinner("Loading..."):
            st.session_state["events"] = fetch_events(api_key, sport_key)
            st.session_state["sport_key"] = sport_key

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games 💫** first.")
        st.stop()

    game_rows = []
    for e in events:
        away = e.get("away_team", "")
        home = e.get("home_team", "")
        start = (e.get("commence_time") or "")[:16].replace("T", " ")
        game_rows.append({"id": e["id"], "Away": away, "Home": home, "Start": start})
    st.dataframe(pd.DataFrame(game_rows)[["Away", "Home", "Start"]], use_container_width=True, hide_index=True)

    st.subheader("2️⃣ Fetch Odds")
    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in game_rows}
    chosen = st.multiselect("Select games", list(options.keys()))
    if st.button("Fetch Selected Games 💖", type="primary") and chosen:
        all_records = []
        markets = (["h2h", "spreads", "totals"] if want_main else []) + selected_props
        if not markets:
            st.warning("Select at least one market type.")
            st.stop()
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(markets))
            all_records.extend(flatten_event_odds(data))
            progress.progress((i+1)/len(chosen))
        if all_records:
            st.success(f"Saved {save_odds_to_db(all_records, sport_key)} rows ✨")
            preferred_found = sorted(set(r["bookmaker"] for r in all_records if r.get("bookmaker") and is_preferred(r["bookmaker"])))
            if preferred_found:
                st.success(f"Preferred books found: {', '.join(preferred_found)}")
            else:
                st.warning("None of your four preferred books were returned for these props.")
            st.session_state["last_records"] = all_records
            st.session_state["chosen_games"] = chosen
        else:
            st.warning("No odds returned.")

    records = st.session_state.get("last_records", [])
    if records:
        st.subheader("3️⃣ Matchup Context + Hot List")

        # Show probable pitchers for selected games
        chosen_games = st.session_state.get("chosen_games", [])
        if chosen_games and pitchers:
            st.markdown("#### ⚾ Probable Pitchers (for batter matchup context)")
            for g in chosen_games:
                info = pitchers.get(g)
                if info:
                    st.markdown(
                        f'<div class="pitcher-box"><b>{g}</b><br>'
                        f'Away SP: {info["away_pitcher"]} &nbsp;|&nbsp; Home SP: {info["home_pitcher"]}</div>',
                        unsafe_allow_html=True
                    )

        df = pd.DataFrame(records)
        if line_mode == "Only 1 (lowest)" and "point" in df.columns:
            df = df.sort_values("point").groupby(
                ["description", "market", "bookmaker", "outcome"], dropna=False
            ).first().reset_index()

        hot = build_hot_list(df)[:max_hot]
        if hot:
            st.markdown("#### 🔥 Hot List (Batters)")
            for item in hot:
                reasons = " • ".join(item["reasons"])
                matchup = item.get("matchup", "")
                st.markdown(
                    f'<div class="hot-card">'
                    f'<b>{item["label"]}</b> &nbsp; <span style="color:#f9a8d4">Score: {item["score"]}</span><br>'
                    f'<small>{matchup}</small><br>'
                    f'<span style="color:#f9a8d4">{reasons}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("No strong combinations found on FanDuel / DK / BetMGM / Bet365 yet.")

        st.markdown("---")
        show = df[["home_team", "away_team", "bookmaker", "market", "description", "outcome", "price", "point"]].copy()
        show["price"] = show["price"].apply(format_odds)
        show = show.rename(columns={"description": "Player", "outcome": "Side", "price": "Odds", "point": "Line"})
        st.dataframe(show, use_container_width=True, height=400)

    st.caption("💖 Girl Magic • Batters focused • Locked to FD / DK / MGM / Bet365")

if __name__ == "__main__":
    main()
