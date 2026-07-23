"""
Girl Magic Odds Tracker ✨
Upgraded with full flag system + branded sections
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
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

# Expanded to the main US books you want
PREFERRED_BOOKS = [
    "fanduel", "draftkings", "betmgm", "williamhill_us",
    "betrivers", "fanatics", "espnbet", "hardrockbet", "ballybet"
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
        r = requests.get(f"{API_BASE}/sports/{sport_key}/events/{event_id}/odds", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Odds error: {e}")
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

# ============================================================
# FLAG LOGIC (modular)
# ============================================================

def flag_matching_digits(df):
    """Queen of the Digits – matching last two digits or exact odds"""
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")].copy()
    if props.empty: return flags

    for (market, desc, point), group in props.groupby(["market", "description", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["bookmaker"].tolist()
        if len(prices) < 2: continue

        # Exact match
        if len(set(prices)) == 1:
            flags.append({
                "player": desc,
                "market": market,
                "line": point,
                "books": ", ".join(books),
                "odds": format_odds(prices[0]),
                "reason": "exact matching odds"
            })
            continue

        # Last two digits
        digits = [last_two_digits(p) for p in prices]
        digit_counts = defaultdict(list)
        for i, d in enumerate(digits):
            if d is not None:
                digit_counts[d].append(books[i])
        for d, bks in digit_counts.items():
            if len(bks) >= 2:
                flags.append({
                    "player": desc,
                    "market": market,
                    "line": point,
                    "books": ", ".join(bks),
                    "odds": f"ends in {d:02d}",
                    "reason": "matching last two digits"
                })
    return flags

def flag_over_under_priced(df, threshold=0.18):
    """Overpriced Kings / Underpriced Princes"""
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
                label = "overpriced" if row["price"] < median else "underpriced"  # shorter = overpriced for underdogs
                # For positive odds, higher number = longer odds = underpriced
                if row["price"] > 0:
                    label = "underpriced" if row["price"] > median else "overpriced"
                else:
                    label = "overpriced" if row["price"] > median else "underpriced"  # less negative = shorter

                flags.append({
                    "player": desc,
                    "book": row["bookmaker"],
                    "odds": format_odds(row["price"]),
                    "median": format_odds(median),
                    "diff_pct": round(abs(diff) * 100, 1),
                    "label": label,
                    "market": market,
                    "line": point
                })
    return flags

def flag_out_of_place(df, line_threshold=1.0, odds_threshold=150):
    """Suspicious Props – one book clearly off"""
    flags = []
    props = df[df["description"].notna() & (df["description"] != "")].copy()
    if props.empty: return flags

    for (market, desc), group in props.groupby(["market", "description"]):
        if len(group) < 3: continue
        points = group["point"].dropna().tolist()
        prices = group["price"].dropna().tolist()

        # Line disagreement
        if points and len(set(points)) > 1:
            try:
                med_point = statistics.median(points)
                for _, row in group.iterrows():
                    if row["point"] is not None and abs(row["point"] - med_point) >= line_threshold:
                        flags.append({
                            "player": desc,
                            "market": market,
                            "outlier_book": row["bookmaker"],
                            "outlier_value": f"line {row['point']}",
                            "group_value": f"median {med_point}",
                            "reason": "out-of-place line"
                        })
            except: pass

        # Odds disagreement
        if prices and len(set(prices)) > 1:
            try:
                med_price = statistics.median(prices)
                for _, row in group.iterrows():
                    if row["price"] is not None and abs(row["price"] - med_price) >= odds_threshold:
                        flags.append({
                            "player": desc,
                            "market": market,
                            "outlier_book": row["bookmaker"],
                            "outlier_value": format_odds(row["price"]),
                            "group_value": format_odds(med_price),
                            "reason": "out-of-place odds"
                        })
            except: pass
    return flags

def flag_book_disagreements(df):
    """Book Shenanigans Detector"""
    return flag_out_of_place(df)  # reuses the same logic for now

# ============================================================
# MAIN APP
# ============================================================

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
        selected_props = st.multiselect("Props", prop_list, default=prop_list[:2] if prop_list else [])
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
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_event_odds(api_key, sport_key, options[label], ",".join(selected_props))
            all_records.extend(flatten_event_odds(data))
            progress.progress((i + 1) / len(chosen))
        if all_records:
            st.success(f"Saved {save_odds_to_db(all_records, sport_key)} rows")
            preferred = sorted(set(r["bookmaker"] for r in all_records if is_preferred(r.get("bookmaker"))))
            all_books = sorted(set(r["bookmaker"] for r in all_records))
            st.write(f"**Books returned:** {', '.join(all_books)}")
            if preferred:
                st.success(f"Preferred books found: {', '.join(preferred)}")
            else:
                st.warning("None of the preferred US books returned for these props")
            st.session_state["last_records"] = all_records
        else:
            st.warning("No odds returned")

    records = st.session_state.get("last_records", [])
    if not records:
        st.info("Fetch some games to see flags")
        st.stop()

    df = pd.DataFrame(records)
    # Keep only preferred books for cleaner flags
    df = df[df["bookmaker"].apply(is_preferred)]

    # Run all flaggers
    matching = flag_matching_digits(df)[:max_items]
    priced = flag_over_under_priced(df)[:max_items]
    suspicious = flag_out_of_place(df)[:max_items]
    disagreements = flag_book_disagreements(df)[:max_items]

    overpriced = [p for p in priced if p["label"] == "overpriced"]
    underpriced = [p for p in priced if p["label"] == "underpriced"]

    # ---------- SECTIONS ----------
    st.markdown("---")
    st.header("🚨 Petty Alerts")
    total_flags = len(matching) + len(overpriced) + len(underpriced) + len(suspicious)
    st.markdown(f'<div class="alert-card"><b>{total_flags} total flags found</b><br>'
                f'{len(matching)} matching digits • {len(underpriced)} underpriced • '
                f'{len(overpriced)} overpriced • {len(suspicious)} suspicious</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👑 Queen of the Digits")
        if matching:
            for m in matching:
                st.markdown(f'<div class="flag-card"><b>{m["player"]}</b> ({m["market"]})<br>'
                            f'{m["odds"]} • {m["books"]}<br><small>{m["reason"]}</small></div>', unsafe_allow_html=True)
        else:
            st.caption("No matching digit patterns right now")

        st.subheader("💎 Girl Magic Value Plays")
        if underpriced:
            for u in underpriced:
                st.markdown(f'<div class="flag-card"><b>{u["player"]}</b><br>'
                            f'{u["book"]}: {u["odds"]} (median {u["median"]}) • +{u["diff_pct"]}%<br>'
                            f'<small>Underpriced Prince</small></div>', unsafe_allow_html=True)
        else:
            st.caption("No underpriced plays found")

    with col2:
        st.subheader("🕵️ Book Shenanigans Detector")
        if disagreements:
            for d in disagreements:
                st.markdown(f'<div class="flag-card"><b>{d["player"]}</b> ({d["market"]})<br>'
                            f'Outlier: {d["outlier_book"]} → {d["outlier_value"]}<br>'
                            f'Group: {d["group_value"]}<br><small>{d["reason"]}</small></div>', unsafe_allow_html=True)
        else:
            st.caption("No major book disagreements")

        st.subheader("😈 Overpriced Kings")
        if overpriced:
            for o in overpriced:
                st.markdown(f'<div class="flag-card"><b>{o["player"]}</b><br>'
                            f'{o["book"]}: {o["odds"]} (median {o["median"]}) • {o["diff_pct"]}% shorter<br>'
                            f'<small>Overpriced</small></div>', unsafe_allow_html=True)
        else:
            st.caption("No overpriced kings")

    st.subheader("👁️ Suspicious Props")
    if suspicious:
        for s in suspicious:
            st.markdown(f'<div class="flag-card"><b>{s["player"]}</b> ({s["market"]})<br>'
                        f'{s["outlier_book"]} is out of place → {s["outlier_value"]} vs {s["group_value"]}<br>'
                        f'<small>{s["reason"]}</small></div>', unsafe_allow_html=True)
    else:
        st.caption("No suspicious props detected")

    st.markdown("---")
    st.caption("💖 Girl Magic • Petty Alerts • Queen of the Digits • Book Shenanigans")

if __name__ == "__main__":
    main()
