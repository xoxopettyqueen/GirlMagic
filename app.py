"""
Girl Magic Odds Tracker ✨
Only Overs • Best pairs • Locked to BetMGM / DK / Bet365
"""

import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 40%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435 0%, #1c0d24 100%); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button { background: linear-gradient(90deg, #ec4899, #a855f7) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; }
    span[data-baseweb="tag"] { background-color: #db2777 !important; }
    .hot-card { background: linear-gradient(90deg, #831843, #4c1d95); border: 2px solid #f472b6; border-radius: 12px; padding: 14px 18px; margin: 10px 0; color: #fdf2f8; }
    .pitcher-box { background: #2d1b3d; border: 1px solid #c084fc; border-radius: 10px; padding: 8px 12px; margin: 4px 0; color: #fce7f3; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"
PREFERRED_BOOKS = ["betmgm", "draftkings", "bet365"]

SPORTS = {"NFL": "americanfootball_nfl", "NBA": "basketball_nba", "MLB": "baseball_mlb"}

PLAYER_PROP_MARKETS = {
    "NBA": ["player_points", "player_rebounds", "player_assists", "player_threes"],
    "NFL": ["player_pass_yds", "player_rush_yds", "player_receptions", "player_reception_yds", "player_anytime_td"],
    "MLB": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_strikeouts"],
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
    if not key: key = st.sidebar.text_input("Odds API Key 🔑", type="password")
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
        st.warning(f"Could not fetch: {e}")
        return None

def flatten_event_odds(event_data):
    if not event_data: return []
    records = []
    for book in event_data.get("bookmakers", []):
        for market in book.get("markets", []):
            for outcome in market.get("outcomes", []):
                records.append({
                    "event_id": event_data.get("id"), "commence_time": event_data.get("commence_time"),
                    "home_team": event_data.get("home_team"), "away_team": event_data.get("away_team"),
                    "bookmaker": book.get("key"), "market": market.get("key"),
                    "outcome": outcome.get("name"), "description": outcome.get("description"),
                    "price": outcome.get("price"), "point": outcome.get("point"),
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
    return any(p in book.lower() for p in PREFERRED_BOOKS)

def fetch_probable_pitchers():
    today = date.today().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        pitchers = {}
        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams = g.get("teams", {})
                away_name = teams.get("away", {}).get("team", {}).get("name", "")
                home_name = teams.get("home", {}).get("team", {}).get("name", "")
                away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "TBD")
                home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "TBD")
                pitchers[f"{away_name} @ {home_name}"] = {"away": away_p, "home": home_p}
        return pitchers
    except: return {}

def build_hot_list(df):
    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "matchup": ""})

    # Only preferred books + Only Overs
    props = df[
        (df["description"].notna()) & (df["description"] != "") &
        (df["bookmaker"].apply(is_preferred)) &
        (df["outcome"].str.lower() == "over")
    ].copy()

    if props.empty: return []

    # 1. BetMGM Same Odds
    mgm = props[props["bookmaker"].str.lower().str.contains("betmgm|mgm", na=False)]
    for (market, price), group in mgm.groupby(["market", "price"]):
        players = list(group["description"].unique())
        if len(players) >= 2:
            key = " + ".join(sorted(players))
            scores[key]["score"] += 5
            scores[key]["reasons"].append(f"BetMGM Same Odds {format_odds(price)}")
            scores[key]["players"].update(players)
            scores[key]["matchup"] = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}"

    # 2. BetMGM ending 25/50/75
    for _, row in mgm.iterrows():
        last = last_two_digits(row["price"])
        if last in (25, 50, 75):
            player = row["description"]
            scores[player]["score"] += 3
            scores[player]["reasons"].append(f"BetMGM ends in {last}")
            scores[player]["players"].add(player)
            scores[player]["matchup"] = f"{row['away_team']} @ {row['home_team']}"

    # 3. Bet365 +850
    bet365 = props[props["bookmaker"].str.lower().str.contains("bet365", na=False)]
    for _, row in bet365.iterrows():
        try:
            if abs(int(row["price"])) == 850:
                player = row["description"]
                scores[player]["score"] += 3
                scores[player]["reasons"].append("Bet365 +850")
                scores[player]["players"].add(player)
                scores[player]["matchup"] = f"{row['away_team']} @ {row['home_team']}"
        except: pass

    # 4. DraftKings ending 10
    dk = props[props["bookmaker"].str.lower().str.contains("draftkings|dk", na=False)]
    for _, row in dk.iterrows():
        if last_two_digits(row["price"]) == 10:
            player = row["description"]
            scores[player]["score"] += 3
            scores[player]["reasons"].append("DraftKings ends in 10")
            scores[player]["players"].add(player)
            scores[player]["matchup"] = f"{row['away_team']} @ {row['home_team']}"

    # 5. Out-of-order
    for (book, market), group in props.groupby(["bookmaker", "market"]):
        if len(group) < 3: continue
        group = group.copy()
        group["sort_price"] = group["price"].apply(lambda x: x if x < 0 else x + 10000)
        sorted_g = group.sort_values("sort_price")
        players = sorted_g["description"].tolist()
        prices = sorted_g["price"].tolist()
        for i in range(len(prices)-1):
            if prices[i] > 0 and prices[i+1] < 0 and abs(prices[i]-prices[i+1]) > 400:
                key = f"{players[i]} / {players[i+1]}"
                scores[key]["score"] += 2
                scores[key]["reasons"].append("Out-of-order odds")
                scores[key]["players"].update([players[i], players[i+1]])
                scores[key]["matchup"] = f"{sorted_g['away_team'].iloc[0]} @ {sorted_g['home_team'].iloc[0]}"

    # 6. Name matching (pairs prioritized)
    for _, group in props.groupby("market"):
        players = list(group["description"].unique())
        matchup = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}" if len(group) else ""

        # Exact name
        for name, lst in defaultdict(list, {p: [p] for p in players}).items():
            if players.count(name) >= 2:
                scores[name]["score"] += 4
                scores[name]["reasons"].append("Exact same name")
                scores[name]["players"].add(name)
                scores[name]["matchup"] = matchup

        # Full initials
        initials_map = defaultdict(list)
        for p in players:
            f, l = get_initials(p)
            if f and l: initials_map[f+l].append(p)
        for k, names in initials_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 4
                scores[key]["reasons"].append(f"Same initials {k}")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

        # Cross initial
        for i, p1 in enumerate(players):
            _, last1 = get_initials(p1)
            if not last1: continue
            for p2 in players[i+1:]:
                first2, _ = get_initials(p2)
                if first2 and last1 == first2:
                    key = " + ".join(sorted([p1, p2]))
                    scores[key]["score"] += 3
                    scores[key]["reasons"].append(f"Cross initial ({last1})")
                    scores[key]["players"].update([p1, p2])
                    scores[key]["matchup"] = matchup

        # First letter
        first_map = defaultdict(list)
        for p in players:
            f, _ = get_initials(p)
            if f: first_map[f].append(p)
        for letter, names in first_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 1
                scores[key]["reasons"].append(f"Same first letter {letter}")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

    # Build final list - prefer pairs
    hot = []
    for key, data in scores.items():
        if data["score"] > 0:
            is_pair = " + " in key or " / " in key
            hot.append({
                "label": key,
                "score": data["score"] + (2 if is_pair else 0),  # boost pairs
                "reasons": list(set(data["reasons"])),
                "players": list(data["players"]),
                "matchup": data["matchup"],
                "is_pair": is_pair
            })
    return sorted(hot, key=lambda x: (x["is_pair"], x["score"]), reverse=True)

def main():
    init_db()
    st.title("💖 Girl Magic Odds Tracker ✨")
    st.caption("Only Overs • Best Pairs • Locked to BetMGM / DraftKings / Bet365")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add API key in Manage app → Secrets")
        st.stop()

    with st.sidebar:
        st.header("✨ Settings")
        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]
        want_props = st.checkbox("Player Props", value=True)
        prop_list = PLAYER_PROP_MARKETS.get(sport_name, [])
        selected_props = st.multiselect("Props", prop_list, default=["batter_home_runs"] if "batter_home_runs" in prop_list else prop_list[:2]) if want_props else []
        line_mode = st.radio("Lines", ["Only 1 (lowest)", "All lines"], index=0)
        max_hot = st.slider("Max pairs/items", 3, 15, 8)

    pitchers = fetch_probable_pitchers()

    st.subheader("1️⃣ Games")
    if st.button("Load Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key, sport_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click Load Games first")
        st.stop()

    game_rows = [{"id": e["id"], "Away": e.get("away_team"), "Home": e.get("home_team"), "Start": (e.get("commence_time") or "")[:16].replace("T", " ")} for e in events]
    st.dataframe(pd.DataFrame(game_rows)[["Away", "Home", "Start"]], use_container_width=True, hide_index=True)

    st.subheader("2️⃣ Fetch")
    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in game_rows}
    chosen = st.multiselect("Select games", list(options.keys()))
    if st.button("Fetch Selected Games 💖", type="primary") and chosen:
        all_records = []
        markets = selected_props
        if not markets:
            st.warning("Select props")
            st.stop()
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(markets))
            all_records.extend(flatten_event_odds(data))
            progress.progress((i+1)/len(chosen))
        if all_records:
            st.success(f"Saved {save_odds_to_db(all_records, sport_key)} rows")
            preferred = sorted(set(r["bookmaker"] for r in all_records if is_preferred(r.get("bookmaker"))))
            if preferred: st.success(f"Preferred books: {', '.join(preferred)}")
            else: st.warning("None of BetMGM / DraftKings / Bet365 returned")
            st.session_state["last_records"] = all_records
            st.session_state["chosen_games"] = chosen
        else:
            st.warning("No odds returned")

    records = st.session_state.get("last_records", [])
    if records:
        st.subheader("3️⃣ Best Pairs + Context")

        chosen_games = st.session_state.get("chosen_games", [])
        if chosen_games and pitchers:
            with st.expander("⚾ Probable Pitchers (context only)", expanded=False):
                for g in chosen_games:
                    info = pitchers.get(g)
                    if info:
                        st.markdown(f'<div class="pitcher-box"><b>{g}</b><br>Away: {info["away"]} | Home: {info["home"]}</div>', unsafe_allow_html=True)

        df = pd.DataFrame(records)
        # Only Overs
        df = df[df["outcome"].str.lower() == "over"]

        if line_mode == "Only 1 (lowest)" and "point" in df.columns:
            df = df.sort_values("point").groupby(["description", "market", "bookmaker"], dropna=False).first().reset_index()

        hot = build_hot_list(df)[:max_hot]
        if hot:
            st.markdown("#### 🔥 Best Pairs / Plays")
            for item in hot:
                reasons = " • ".join(item["reasons"])
                pair_tag = "PAIR" if item["is_pair"] else "SINGLE"
                st.markdown(f'<div class="hot-card"><b>{item["label"]}</b> &nbsp; [{pair_tag}] Score: {item["score"]}<br><small>{item.get("matchup","")}</small><br>{reasons}</div>', unsafe_allow_html=True)
        else:
            st.caption("No strong pairs/plays on BetMGM / DraftKings / Bet365 yet.")

        st.markdown("---")
        show = df[["home_team", "away_team", "bookmaker", "market", "description", "outcome", "price", "point"]].copy()
        show["price"] = show["price"].apply(format_odds)
        show = show.rename(columns={"description": "Player", "outcome": "Side", "price": "Odds", "point": "Line"})
        st.dataframe(show, use_container_width=True, height=350)

    st.caption("💖 Girl Magic • Only Overs • Best Pairs • BetMGM / DK / Bet365")

if __name__ == "__main__":
    main()
