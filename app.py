"""
Girl Magic Odds Tracker ✨
Clean version – 4 tabs only
"""

import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict
import statistics

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 40%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435 0%, #1c0d24 100%); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button { background: linear-gradient(90deg, #ec4899, #a855f7) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; }
    .flag-card { background: #2a1435; border: 1px solid #f472b6; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
    .matchup-card { background: #2d1b3d; border: 1px solid #c084fc; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
    .player-card { background: #1f0f2e; border: 1px solid #a855f7; border-radius: 8px; padding: 10px 14px; margin: 6px 0; }
    .launch-card { background: #2a1435; border: 1px solid #f472b6; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"
PREFERRED_BOOKS = ["fanduel", "draftkings", "betmgm", "williamhill_us", "bet365"]

SPORTS = {"MLB": "baseball_mlb", "NBA": "basketball_nba", "NFL": "americanfootball_nfl"}
PLAYER_PROP_MARKETS = {
    "MLB": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis"],
    "NBA": ["player_points", "player_rebounds", "player_assists"],
    "NFL": ["player_pass_yds", "player_rush_yds", "player_receptions", "player_anytime_td"],
}

@st.cache_data
def load_statcast_files():
    hitters = None
    exit_velo = None
    for name in ["stats.csv", "stats (1).csv"]:
        p = Path(name)
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "barrel_batted_rate" in df.columns or "avg_best_speed" in df.columns:
                    sample = pd.to_numeric(df.get("avg_best_speed"), errors="coerce").mean()
                    if sample and sample > 88:
                        hitters = df
                        break
            except: pass
    for name in ["exit_velocity.csv", "exit_velocity (1).csv"]:
        p = Path(name)
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "avg_hit_speed" in df.columns:
                    sample = pd.to_numeric(df["avg_hit_speed"], errors="coerce").mean()
                    if sample and sample > 88:
                        exit_velo = df
                        break
            except: pass
    return hitters, exit_velo

def normalize_name(name):
    if not name: return ""
    name = str(name).lower().strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name

def find_player_metrics(player_name, hitters_df, exit_df):
    if hitters_df is None and exit_df is None:
        return None
    target = normalize_name(player_name)
    result = {"matched": None}
    source = hitters_df if hitters_df is not None else exit_df
    col = "last_name, first_name"
    for _, row in source.iterrows():
        savant = normalize_name(row.get(col, ""))
        if target in savant or savant in target or (target.split() and target.split()[-1] in savant):
            result["matched"] = savant
            result["barrel"] = row.get("barrel_batted_rate", row.get("brl_percent", "-"))
            result["hard_hit"] = row.get("hard_hit_percent", row.get("ev95percent", "-"))
            result["ev"] = row.get("avg_best_speed", row.get("avg_hit_speed", "-"))
            break
    return result if result.get("matched") else None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS odds_snapshots")
    c.execute("""CREATE TABLE odds_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, sport_key TEXT,
        event_id TEXT, commence_time TEXT, home_team TEXT, away_team TEXT,
        bookmaker TEXT, market TEXT, outcome TEXT, description TEXT,
        price REAL, point REAL, last_update TEXT)""")
    conn.commit()
    conn.close()

def save_odds_to_db(records, sport_key):
    if not records: return 0
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()
    rows = [(now, sport_key, r.get("event_id"), r.get("commence_time"), r.get("home_team"), r.get("away_team"),
             r.get("bookmaker"), r.get("market"), r.get("outcome"), r.get("description"),
             r.get("price"), r.get("point"), r.get("last_update")) for r in records]
    conn.executemany("INSERT INTO odds_snapshots VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return len(rows)

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key 🔑", type="password")
    return key

def is_preferred(book):
    if not book: return False
    return any(p in book.lower() for p in PREFERRED_BOOKS)

def format_odds(price):
    if price is None: return "-"
    try: return f"{int(price):+d}"
    except: return str(price)

def last_two_digits(price):
    try: return abs(int(price)) % 100
    except: return None

def fetch_events(api_key, sport_key):
    try:
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error: {e}")
        return []

def fetch_event_odds(api_key, sport_key, event_id, markets):
    params = {"apiKey": api_key, "regions": REGIONS, "markets": markets, "oddsFormat": "american"}
    try:
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events/{event_id}/odds", params=params, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def flatten_event_odds(data):
    if not data: return [], set()
    records, books = [], set()
    for book in data.get("bookmakers", []):
        books.add(book.get("key"))
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                records.append({
                    "event_id": data.get("id"), "commence_time": data.get("commence_time"),
                    "home_team": data.get("home_team"), "away_team": data.get("away_team"),
                    "bookmaker": book.get("key"), "market": market.get("key"),
                    "outcome": o.get("name"), "description": o.get("description"),
                    "price": o.get("price"), "point": o.get("point"),
                })
    return records, books

def flag_matching_digits(df):
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")]
    for (mkt, desc, pt), g in props.groupby(["market", "description", "point"], dropna=False):
        if len(g) < 2: continue
        prices = g["price"].dropna().tolist()
        books = g["bookmaker"].tolist()
        if len(set(prices)) == 1:
            flags.append({"player": desc, "odds": format_odds(prices[0]), "books": ", ".join(books), "reason": "exact match"})
        else:
            digits = defaultdict(list)
            for i, p in enumerate(prices):
                d = last_two_digits(p)
                if d is not None: digits[d].append(books[i])
            for d, bks in digits.items():
                if len(bks) >= 2:
                    flags.append({"player": desc, "odds": f"ends in {d:02d}", "books": ", ".join(bks), "reason": "matching digits"})
    return flags

def flag_priced(df, threshold=0.18):
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")]
    for (mkt, desc, pt), g in props.groupby(["market", "description", "point"], dropna=False):
        prices = g["price"].dropna().tolist()
        if len(prices) < 3: continue
        try: med = statistics.median(prices)
        except: continue
        for _, row in g.iterrows():
            if row["price"] is None: continue
            diff = (row["price"] - med) / abs(med) if med else 0
            if abs(diff) >= threshold:
                label = "underpriced" if row["price"] > med else "overpriced"
                flags.append({"player": desc, "book": row["bookmaker"], "odds": format_odds(row["price"]),
                              "median": format_odds(med), "diff": round(abs(diff)*100,1), "label": label})
    return flags

def fetch_probable_pitchers():
    today = date.today().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher", timeout=10)
        data = r.json()
        pitchers = {}
        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams = g.get("teams", {})
                away = teams.get("away", {}).get("team", {}).get("name", "")
                home = teams.get("home", {}).get("team", {}).get("name", "")
                away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "TBD")
                home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "TBD")
                pitchers[f"{away} @ {home}"] = {"away": away_p, "home": home_p}
        return pitchers
    except: return {}

def main():
    init_db()
    st.title("💖 Girl Magic Odds Tracker")

    hitters_df, exit_df = load_statcast_files()
    if hitters_df is not None: st.sidebar.success(f"Hitters: {len(hitters_df)}")
    if exit_df is not None: st.sidebar.success(f"Exit Velo: {len(exit_df)}")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add API key in Secrets")
        st.stop()

    with st.sidebar:
        st.header("Settings")
        sport = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport]
        props = st.multiselect("Props", PLAYER_PROP_MARKETS.get(sport, []), default=["batter_home_runs"] if sport=="MLB" else [])
        max_flags = st.slider("Max flags", 5, 20, 10)

    if st.button("Load Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key, sport_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games**")
        st.stop()

    rows = [{"id": e["id"], "Away": e.get("away_team"), "Home": e.get("home_team"),
             "Start": (e.get("commence_time") or "")[:16].replace("T"," ")} for e in events]
    st.dataframe(pd.DataFrame(rows)[["Away","Home","Start"]], use_container_width=True, hide_index=True)

    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in rows}
    chosen = st.multiselect("Select games", list(options.keys()))

    if st.button("Fetch Selected Games 💖", type="primary") and chosen:
        all_recs, all_books = [], set()
        prog = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(props))
            if data:
                recs, books = flatten_event_odds(data)
                all_recs.extend(recs)
                all_books.update(books)
            prog.progress((i+1)/len(chosen))

        if all_recs:
            df = pd.DataFrame(all_recs)
            df = df[df["outcome"].str.lower() == "over"]
            if "point" in df.columns:
                df = df.sort_values("point").groupby(["description","market","bookmaker"], dropna=False).first().reset_index()
            all_recs = df.to_dict("records")
            st.success(f"Saved {save_odds_to_db(all_recs, sport_key)} rows (Only 1 HR)")
            st.write("Books:", ", ".join(sorted(all_books)))
            pref = [b for b in all_books if is_preferred(b)]
            if pref: st.success("Main books: " + ", ".join(pref))
            else: st.warning("Main books missing")
            st.session_state["records"] = all_recs
            st.session_state["chosen"] = chosen
        else:
            st.warning("No odds returned")

    records = st.session_state.get("records", [])
    chosen = st.session_state.get("chosen", [])
    df = pd.DataFrame(records) if records else pd.DataFrame()
    pitchers = fetch_probable_pitchers()

    matching = flag_matching_digits(df)[:max_flags] if not df.empty else []
    priced = flag_priced(df)[:max_flags] if not df.empty else []
    under = [p for p in priced if p["label"]=="underpriced"]
    over = [p for p in priced if p["label"]=="overpriced"]

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Odds & Flags", "⚾ Batters", "🥎 Pitchers", "🚀 Petty's Launch List"])

    with tab1:
        st.subheader("Odds & Flags")
        if df.empty:
            st.info("Fetch games to see flags")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**👑 Queen of the Digits**")
                for m in matching:
                    st.markdown(f'<div class="flag-card"><b>{m["player"]}</b><br>{m["odds"]} • {m["books"]}</div>', unsafe_allow_html=True)
                if not matching: st.caption("None")
            with col2:
                st.markdown("**💎 Value Plays**")
                for u in under:
                    st.markdown(f'<div class="flag-card"><b>{u["player"]}</b><br>{u["book"]}: {u["odds"]} (med {u["median"]})</div>', unsafe_allow_html=True)
                if not under: st.caption("None")
            st.markdown("**😈 Overpriced**")
            for o in over:
                st.markdown(f'<div class="flag-card"><b>{o["player"]}</b><br>{o["book"]}: {o["odds"]}</div>', unsafe_allow_html=True)
            if not over: st.caption("None")

    with tab2:
        st.subheader("Batters")
        if not chosen:
            st.info("Fetch games first")
        else:
            for g in chosen:
                st.markdown(f'<div class="matchup-card"><b>{g}</b></div>', unsafe_allow_html=True)
                if not df.empty:
                    bats = df[((df["away_team"]+" @ "+df["home_team"])==g) & df["description"].notna()]["description"].unique()
                    for b in sorted(bats)[:12]:
                        m = find_player_metrics(b, hitters_df, exit_df)
                        if m:
                            st.markdown(f'<div class="player-card"><b>{b}</b> → {m["matched"]}<br>EV {m.get("ev","-")} | HH {m.get("hard_hit","-")}% | Barrel {m.get("barrel","-")}%</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="player-card"><b>{b}</b><br><small>No match</small></div>', unsafe_allow_html=True)

    with tab3:
        st.subheader("Pitchers of the Day")
        if not chosen:
            st.info("Fetch games first")
        else:
            for g in chosen:
                info = pitchers.get(g, {"away":"TBD","home":"TBD"})
                st.markdown(f'<div class="matchup-card"><b>{g}</b><br>Away SP: <b>{info["away"]}</b><br>Home SP: <b>{info["home"]}</b></div>', unsafe_allow_html=True)

    with tab4:
        st.subheader("🚀 Petty's Launch List (Hitters Only)")
        if hitters_df is None and exit_df is None:
            st.info("Upload hitter CSVs to power this")
        else:
            source = hitters_df if hitters_df is not None else exit_df
            cands = []
            for _, row in source.iterrows():
                name = row.get("last_name, first_name", "")
                try:
                    ev = float(row.get("avg_best_speed", row.get("avg_hit_speed", 0)) or 0)
                    hh = float(row.get("hard_hit_percent", row.get("ev95percent", 0)) or 0)
                    brl = float(row.get("barrel_batted_rate", row.get("brl_percent", 0)) or 0)
                    score = ev*0.4 + hh*0.35 + brl*0.25
                    cands.append({"name": name, "ev": round(ev,1), "hh": round(hh,1), "brl": round(brl,1), "score": round(score,1)})
                except: continue
            cands = sorted(cands, key=lambda x: x["score"], reverse=True)[:20]
            for i, c in enumerate(cands, 1):
                note = "EV NUCLEAR" if c["ev"] >= 92 else ("Barrel monster" if c["brl"] >= 12 else "")
                st.markdown(f'<div class="launch-card"><b>{i}. {c["name"]}</b><br>{c["ev"]} EV | {c["hh"]} HH% | {c["brl"]} Barrel%<br><small>{note}</small></div>', unsafe_allow_html=True)

    st.caption("💖 Girl Magic • Clean 4-tab version")

if __name__ == "__main__":
    main()
