"""
Girl Magic Odds Tracker ✨
Full fixed version – tabs restored + flag system
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
    .alert-card { background: linear-gradient(90deg, #831843, #4c1d95); border: 2px solid #f472b6; border-radius: 12px; padding: 14px 18px; margin: 10px 0; }
    .matchup-card { background: #2d1b3d; border: 1px solid #c084fc; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

PREFERRED_BOOKS = [
    "fanduel", "draftkings", "betmgm", "williamhill_us",
    "betrivers", "fanatics", "espnbet", "hardrockbet", "ballybet", "bet365"
]

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
    c.executemany("INSERT INTO odds_snapshots VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
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
        st.error(f"Events error: {e}")
        return []

def fetch_event_odds(api_key, sport_key, event_id, markets):
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": markets,
        "oddsFormat": "american",
        "dateFormat": "iso"
    }
    try:
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events/{event_id}/odds", params=params, timeout=25)
        if r.status_code != 200:
            st.warning(f"API status {r.status_code}: {r.text[:200]}")
            return None
        return r.json()
    except Exception as e:
        st.warning(f"Odds fetch error: {e}")
        return None

def flatten_event_odds(event_data):
    if not event_data: return []
    records = []
    books_found = set()
    for book in event_data.get("bookmakers", []):
        books_found.add(book.get("key"))
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
    return records, books_found

# ---------- FLAG FUNCTIONS ----------
def flag_matching_digits(df):
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")].copy()
    if props.empty: return flags

    for (market, desc, point), group in props.groupby(["market", "description", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["bookmaker"].tolist()
        if len(prices) < 2: continue

        if len(set(prices)) == 1:
            flags.append({
                "player": desc, "market": market, "line": point,
                "books": ", ".join(books), "odds": format_odds(prices[0]),
                "reason": "exact matching odds"
            })
            continue

        digits = [last_two_digits(p) for p in prices]
        digit_counts = defaultdict(list)
        for i, d in enumerate(digits):
            if d is not None:
                digit_counts[d].append(books[i])
        for d, bks in digit_counts.items():
            if len(bks) >= 2:
                flags.append({
                    "player": desc, "market": market, "line": point,
                    "books": ", ".join(bks), "odds": f"ends in {d:02d}",
                    "reason": "matching last two digits"
                })
    return flags

def flag_over_under_priced(df, threshold=0.18):
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")].copy()
    if props.empty: return flags

    for (market, desc, point), group in props.groupby(["market", "description", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        if len(prices) < 3: continue
        try:
            median = statistics.median(prices)
        except: continue

        for _, row in group.iterrows():
            if row["price"] is None: continue
            diff = (row["price"] - median) / abs(median) if median != 0 else 0
            if abs(diff) >= threshold:
                if row["price"] > 0:
                    label = "underpriced" if row["price"] > median else "overpriced"
                else:
                    label = "overpriced" if row["price"] > median else "underpriced"
                flags.append({
                    "player": desc, "book": row["bookmaker"],
                    "odds": format_odds(row["price"]), "median": format_odds(median),
                    "diff_pct": round(abs(diff)*100, 1), "label": label,
                    "market": market, "line": point
                })
    return flags

def flag_out_of_place(df, line_threshold=1.0, odds_threshold=150):
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")].copy()
    if props.empty: return flags

    for (market, desc), group in props.groupby(["market", "description"]):
        if len(group) < 3: continue
        points = group["point"].dropna().tolist()
        prices = group["price"].dropna().tolist()

        if points and len(set(points)) > 1:
            try:
                med_point = statistics.median(points)
                for _, row in group.iterrows():
                    if row["point"] is not None and abs(row["point"] - med_point) >= line_threshold:
                        flags.append({
                            "player": desc, "market": market,
                            "outlier_book": row["bookmaker"],
                            "outlier_value": f"line {row['point']}",
                            "group_value": f"median {med_point}",
                            "reason": "out-of-place line"
                        })
            except: pass

        if prices and len(set(prices)) > 1:
            try:
                med_price = statistics.median(prices)
                for _, row in group.iterrows():
                    if row["price"] is not None and abs(row["price"] - med_price) >= odds_threshold:
                        flags.append({
                            "player": desc, "market": market,
                            "outlier_book": row["bookmaker"],
                            "outlier_value": format_odds(row["price"]),
                            "group_value": format_odds(med_price),
                            "reason": "out-of-place odds"
                        })
            except: pass
    return flags

def main():
    init_db()
    st.title("💖 Girl Magic Odds Tracker ✨")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Manage app → Secrets")
        st.stop()

    with st.sidebar:
        st.header("✨ Settings")
        sport_name = st.selectbox("Sport", list(SPORTS.keys()))
        sport_key = SPORTS[sport_name]
        prop_list = PLAYER_PROP_MARKETS.get(sport_name, [])
        selected_props = st.multiselect("Props", prop_list, default=["batter_home_runs"] if "batter_home_runs" in prop_list else prop_list[:2])
        max_items = st.slider("Max flags per section", 5, 30, 12)

    if st.button("Load Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key, sport_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** first")
        st.stop()

    game_rows = [{"id": e["id"], "Away": e.get("away_team"), "Home": e.get("home_team"),
                  "Start": (e.get("commence_time") or "")[:16].replace("T", " ")} for e in events]
    st.dataframe(pd.DataFrame(game_rows)[["Away", "Home", "Start"]], use_container_width=True, hide_index=True)

    options = {f"{r['Away']} @ {r['Home']}": r["id"] for r in game_rows}
    chosen = st.multiselect("Select games", list(options.keys()))

    if st.button("Fetch Selected Games 💖", type="primary") and chosen:
        all_records = []
        all_books = set()
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(selected_props))
            if data:
                recs, books = flatten_event_odds(data)
                all_records.extend(recs)
                all_books.update(books)
            progress.progress((i + 1) / len(chosen))

        if all_records:
            st.success(f"Saved {save_odds_to_db(all_records, sport_key)} rows")
            st.write(f"**Books returned by API:** {', '.join(sorted(all_books)) if all_books else 'none'}")
            preferred = [b for b in all_books if is_preferred(b)]
            if preferred:
                st.success(f"Preferred books found: {', '.join(preferred)}")
            else:
                st.warning("None of the preferred books returned for these props")
            st.session_state["last_records"] = all_records
            st.session_state["chosen_games"] = chosen
        else:
            st.warning("No odds returned from The Odds API for the selected games/markets. Try different games or check if the props are open.")

    records = st.session_state.get("last_records", [])
    chosen_games = st.session_state.get("chosen_games", [])

    # ===================== TABS =====================
    tab1, tab2, tab3 = st.tabs(["🎯 Odds + Tricks", "⚾ Batters + Pitchers", "🚀 Petty's Launch List"])

    with tab1:
        st.subheader("Odds + Flag System")
        if not records:
            st.info("Fetch some games first")
        else:
            df = pd.DataFrame(records)

            matching = flag_matching_digits(df)[:max_items]
            priced = flag_over_under_priced(df)[:max_items]
            suspicious = flag_out_of_place(df)[:max_items]

            overpriced = [p for p in priced if p["label"] == "overpriced"]
            underpriced = [p for p in priced if p["label"] == "underpriced"]

            st.markdown(f'<div class="alert-card"><b>Petty Alerts</b><br>'
                        f'{len(matching)} matching digits • {len(underpriced)} underpriced • '
                        f'{len(overpriced)} overpriced • {len(suspicious)} suspicious</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 👑 Queen of the Digits")
                if matching:
                    for m in matching:
                        st.markdown(f'<div class="flag-card"><b>{m["player"]}</b><br>{m["odds"]} • {m["books"]}<br><small>{m["reason"]}</small></div>', unsafe_allow_html=True)
                else:
                    st.caption("No matching digit patterns")

                st.markdown("### 💎 Girl Magic Value Plays")
                if underpriced:
                    for u in underpriced:
                        st.markdown(f'<div class="flag-card"><b>{u["player"]}</b><br>{u["book"]}: {u["odds"]} (med {u["median"]}) +{u["diff_pct"]}%</div>', unsafe_allow_html=True)
                else:
                    st.caption("No underpriced plays")

            with col2:
                st.markdown("### 🕵️ Book Shenanigans")
                if suspicious:
                    for s in suspicious:
                        st.markdown(f'<div class="flag-card"><b>{s["player"]}</b><br>{s["outlier_book"]} → {s["outlier_value"]} vs {s["group_value"]}</div>', unsafe_allow_html=True)
                else:
                    st.caption("No major disagreements")

                st.markdown("### 😈 Overpriced Kings")
                if overpriced:
                    for o in overpriced:
                        st.markdown(f'<div class="flag-card"><b>{o["player"]}</b><br>{o["book"]}: {o["odds"]} (med {o["median"]})</div>', unsafe_allow_html=True)
                else:
                    st.caption("No overpriced kings")

            st.markdown("---")
            st.write("**Raw odds table**")
            show = df[["home_team", "away_team", "bookmaker", "market", "description", "price", "point"]].copy()
            show["price"] = show["price"].apply(format_odds)
            st.dataframe(show, use_container_width=True, height=300)

    with tab2:
        st.subheader("Batters + Pitchers")
        st.info("This tab will show matchup + Statcast metrics once odds are loaded and CSVs are present.")
        if chosen_games:
            for g in chosen_games:
                st.markdown(f'<div class="matchup-card"><b>{g}</b></div>', unsafe_allow_html=True)

    with tab3:
        st.subheader("🚀 Petty's Launch List")
        st.info("Ranked HR candidates will appear here once your Statcast CSVs are loaded in the repo.")

    st.caption("💖 Girl Magic • Tabs restored • Flag system active")

if __name__ == "__main__":
    main()
