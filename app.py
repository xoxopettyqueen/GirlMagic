"""
Girl Magic Odds Tracker ✨
Tab 1 = Odds + Tricks
Tab 2 = Batters + Pitchers (with platoon splits)
"""

import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
import time

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 40%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435 0%, #1c0d24 100%); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button { background: linear-gradient(90deg, #ec4899, #a855f7) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; }
    span[data-baseweb="tag"] { background-color: #db2777 !important; }
    .hot-card { background: linear-gradient(90deg, #831843, #4c1d95); border: 2px solid #f472b6; border-radius: 12px; padding: 14px 18px; margin: 10px 0; color: #fdf2f8; }
    .matchup-card { background: #2d1b3d; border: 1px solid #c084fc; border-radius: 10px; padding: 12px 16px; margin: 8px 0; color: #fce7f3; }
    .batter-card { background: #1f0f2e; border: 1px solid #a855f7; border-radius: 8px; padding: 10px 14px; margin: 6px 0; font-size: 0.95rem; }
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
        st.error(f"Error: {e}")
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

def search_player_id(name):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}&sportIds=1"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            people = r.json().get("people", [])
            if people:
                return people[0].get("id"), people[0].get("fullName")
    except: pass
    return None, None

def get_batter_stats_with_platoon(player_id):
    """Basic season stats + attempt at vs L / vs R."""
    if not player_id: return None
    result = {"avg": "-", "hr": "-", "ops": "-", "vs_l": "-", "vs_r": "-"}
    season = date.today().year
    try:
        # Overall
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group=hitting&season={season}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            splits = r.json().get("stats", [{}])[0].get("splits", [])
            if splits:
                stat = splits[0].get("stat", {})
                result["avg"] = stat.get("avg", "-")
                result["hr"] = stat.get("homeRuns", "-")
                result["ops"] = stat.get("ops", "-")
    except: pass

    # Try platoon (vs L / vs R) - using sitCodes
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group=hitting&season={season}&sitCodes=vl,vr"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            for split in r.json().get("stats", [{}])[0].get("splits", []):
                code = split.get("split", {}).get("code", "")
                stat = split.get("stat", {})
                ops = stat.get("ops", "-")
                if code == "vl":
                    result["vs_l"] = ops
                elif code == "vr":
                    result["vs_r"] = ops
    except: pass

    return result

def build_hot_list(df):
    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "matchup": ""})
    props = df[
        (df["description"].notna()) & (df["description"] != "") &
        (df["bookmaker"].apply(is_preferred)) &
        (df["outcome"].str.lower() == "over")
    ].copy()
    if props.empty: return []

    mgm = props[props["bookmaker"].str.lower().str.contains("betmgm|mgm", na=False)]
    for (market, price), group in mgm.groupby(["market", "price"]):
        players = list(group["description"].unique())
        if len(players) >= 2:
            key = " + ".join(sorted(players))
            scores[key]["score"] += 5
            scores[key]["reasons"].append(f"BetMGM Same Odds {format_odds(price)}")
            scores[key]["players"].update(players)
            scores[key]["matchup"] = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}"

    for _, row in mgm.iterrows():
        last = last_two_digits(row["price"])
        if last in (25, 50, 75):
            p = row["description"]
            scores[p]["score"] += 3
            scores[p]["reasons"].append(f"BetMGM ends in {last}")
            scores[p]["players"].add(p)
            scores[p]["matchup"] = f"{row['away_team']} @ {row['home_team']}"

    for _, row in props[props["bookmaker"].str.lower().str.contains("bet365", na=False)].iterrows():
        try:
            if abs(int(row["price"])) == 850:
                p = row["description"]
                scores[p]["score"] += 3
                scores[p]["reasons"].append("Bet365 +850")
                scores[p]["players"].add(p)
                scores[p]["matchup"] = f"{row['away_team']} @ {row['home_team']}"
        except: pass

    for _, row in props[props["bookmaker"].str.lower().str.contains("draftkings|dk", na=False)].iterrows():
        if last_two_digits(row["price"]) == 10:
            p = row["description"]
            scores[p]["score"] += 3
            scores[p]["reasons"].append("DraftKings ends in 10")
            scores[p]["players"].add(p)
            scores[p]["matchup"] = f"{row['away_team']} @ {row['home_team']}"

    for _, group in props.groupby("market"):
        players = list(group["description"].unique())
        matchup = f"{group['away_team'].iloc[0]} @ {group['home_team'].iloc[0]}" if len(group) else ""
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

    hot = []
    for key, data in scores.items():
        if data["score"] > 0:
            is_pair = " + " in key or " / " in key
            hot.append({
                "label": key, "score": data["score"] + (2 if is_pair else 0),
                "reasons": list(set(data["reasons"])), "players": list(data["players"]),
                "matchup": data["matchup"], "is_pair": is_pair
            })
    return sorted(hot, key=lambda x: (x["is_pair"], x["score"]), reverse=True)

def main():
    init_db()
    st.title("💖 Girl Magic Odds Tracker ✨")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add API key in Manage app → Secrets")
        st.stop()

    with st.sidebar:
        st.header("✨ Settings")
        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]
        prop_list = PLAYER_PROP_MARKETS.get(sport_name, [])
        selected_props = st.multiselect("Props", prop_list, default=["batter_home_runs"] if "batter_home_runs" in prop_list else prop_list[:2])
        line_mode = st.radio("Lines", ["Only 1 (lowest)", "All lines"], index=0)
        max_hot = st.slider("Max items", 3, 15, 8)

    if st.button("Load Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key, sport_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** first")
        st.stop()

    game_rows = [{"id": e["id"], "Away": e.get("away_team"), "Home": e.get("home_team"), "Start": (e.get("commence_time") or "")[:16].replace("T", " ")} for e in events]
    st.dataframe(pd.DataFrame(game_rows)[["Away", "Home", "Start"]], use_container_width=True, hide_index=True)

    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in game_rows}
    chosen = st.multiselect("Select games", list(options.keys()))

    if st.button("Fetch Selected Games 💖", type="primary") and chosen:
        all_records = []
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(selected_props))
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
    pitchers = fetch_probable_pitchers()
    chosen_games = st.session_state.get("chosen_games", [])

    tab1, tab2 = st.tabs(["🎯 Odds + Tricks", "⚾ Batters + Pitchers"])

    with tab1:
        st.subheader("Odds Tricks & Best Pairs")
        if not records:
            st.info("Fetch games first")
        else:
            df = pd.DataFrame(records)
            df = df[df["outcome"].str.lower() == "over"]
            if line_mode == "Only 1 (lowest)" and "point" in df.columns:
                df = df.sort_values("point").groupby(["description", "market", "bookmaker"], dropna=False).first().reset_index()
            hot = build_hot_list(df)[:max_hot]
            if hot:
                for item in hot:
                    reasons = " • ".join(item["reasons"])
                    tag = "PAIR" if item["is_pair"] else "SINGLE"
                    st.markdown(f'<div class="hot-card"><b>{item["label"]}</b> [{tag}] Score: {item["score"]}<br><small>{item.get("matchup","")}</small><br>{reasons}</div>', unsafe_allow_html=True)
            else:
                st.caption("No strong pairs on BetMGM / DraftKings / Bet365 yet.")
            st.markdown("---")
            show = df[["home_team", "away_team", "bookmaker", "market", "description", "price", "point"]].copy()
            show["price"] = show["price"].apply(format_odds)
            show = show.rename(columns={"description": "Player", "price": "Odds", "point": "Line"})
            st.dataframe(show, use_container_width=True, height=350)

    with tab2:
        st.subheader("Batters + Pitchers (with Platoon)")
        if not chosen_games:
            st.info("Fetch games first")
        else:
            for g in chosen_games:
                info = pitchers.get(g, {"away": "TBD", "home": "TBD"})
                st.markdown(f'<div class="matchup-card"><b>{g}</b><br>Away SP: <b>{info["away"]}</b><br>Home SP: <b>{info["home"]}</b></div>', unsafe_allow_html=True)

                if records:
                    df = pd.DataFrame(records)
                    game_batters = df[
                        ((df["away_team"] + " @ " + df["home_team"]) == g) &
                        (df["description"].notna())
                    ]["description"].unique().tolist()

                    if game_batters:
                        st.write("**Batters + Platoon Splits:**")
                        for batter in sorted(game_batters)[:10]:
                            pid, _ = search_player_id(batter)
                            stats = get_batter_stats_with_platoon(pid) if pid else None
                            if stats:
                                st.markdown(
                                    f'<div class="batter-card">'
                                    f'<b>{batter}</b><br>'
                                    f'AVG {stats["avg"]} | HR {stats["hr"]} | OPS {stats["ops"]}<br>'
                                    f'<b>vs LHP:</b> {stats["vs_l"]} &nbsp;|&nbsp; <b>vs RHP:</b> {stats["vs_r"]}'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(f'<div class="batter-card"><b>{batter}</b><br><small>Stats not found</small></div>', unsafe_allow_html=True)
                            time.sleep(0.2)
                    else:
                        st.caption("No batter names found for this game.")
                st.markdown("---")

            st.caption("Platoon = vs LHP / vs RHP OPS when available from MLB Stats API")

    st.caption("💖 Girl Magic • Odds Tricks + Batters with Platoon")

if __name__ == "__main__":
    main()
