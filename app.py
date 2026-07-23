"""
Girl Magic Odds Model ✨
Pure odds tricks + Girl Math flags only
MLB focused • Clean • Simple
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict
import statistics

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435, #1c0d24); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important;
    }
    .magic-card {
        background: #2a1435; border: 1px solid #f472b6; border-radius: 12px;
        padding: 14px 18px; margin: 10px 0; color: #fdf2f8;
    }
    .score-badge { color: #f9a8d4; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"
PREFERRED_BOOKS = ["fanduel", "draftkings", "betmgm", "bet365", "williamhill_us"]  # Caesars = williamhill_us

MARKETS = [
    "batter_home_runs", "batter_hits", "batter_total_bases",
    "batter_rbis", "batter_runs_scored", "batter_strikeouts"
]

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key 🔑", type="password")
    return key

def is_preferred(book):
    if not book: return False
    return any(p in book.lower() for p in PREFERRED_BOOKS)

def format_odds(p):
    if p is None: return "-"
    try: return f"{int(p):+d}"
    except: return str(p)

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def get_initials(name):
    parts = str(name).strip().split()
    if not parts: return None, None
    first = parts[0][0].upper() if parts[0] else None
    last = parts[-1][0].upper() if len(parts) > 1 else None
    return first, last

def fetch_events(api_key):
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Events error: {e}")
        return []

def fetch_odds(api_key, event_id, markets):
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": ",".join(markets),
        "oddsFormat": "american"
    }
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events/{event_id}/odds", params=params, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except: return None

def flatten(data):
    if not data: return []
    rows = []
    for book in data.get("bookmakers", []):
        if not is_preferred(book.get("key")): continue
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over": continue  # only Overs
                rows.append({
                    "home": data.get("home_team"),
                    "away": data.get("away_team"),
                    "book": book.get("key"),
                    "market": market.get("key"),
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": o.get("point"),
                })
    return rows

# ============================================================
# GIRL MATH FLAG ENGINE
# ============================================================
def run_girl_math(df):
    if df.empty: return []

    scores = defaultdict(lambda: {"score": 0, "reasons": [], "players": set(), "matchup": ""})

    # Only lowest line (Over 0.5 / 1)
    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "market", "book"], dropna=False).first().reset_index()

    # --- Digit flags ---
    for _, row in df.iterrows():
        p = row["player"]
        price = row["price"]
        book = row["book"].lower()
        matchup = f"{row['away']} @ {row['home']}"
        last = last_two(price)

        # BetMGM 25/50/75
        if "betmgm" in book or "mgm" in book:
            if last in (25, 50, 75):
                scores[p]["score"] += 3
                scores[p]["reasons"].append(f"BetMGM ends in {last}")
                scores[p]["players"].add(p)
                scores[p]["matchup"] = matchup

        # DraftKings ends in 10
        if "draftkings" in book or "dk" in book:
            if last == 10:
                scores[p]["score"] += 3
                scores[p]["reasons"].append("DraftKings ends in 10")
                scores[p]["players"].add(p)
                scores[p]["matchup"] = matchup

        # Bet365 +850
        if "bet365" in book:
            try:
                if abs(int(price)) == 850:
                    scores[p]["score"] += 3
                    scores[p]["reasons"].append("Bet365 +850 Club")
                    scores[p]["players"].add(p)
                    scores[p]["matchup"] = matchup
            except: pass

    # --- Exact match + matching digits across books ---
    for (market, player, point), group in df.groupby(["market", "player", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        matchup = f"{group['away'].iloc[0]} @ {group['home'].iloc[0]}"

        if len(set(prices)) == 1:
            key = player
            scores[key]["score"] += 5
            scores[key]["reasons"].append(f"Exact match {format_odds(prices[0])} across {', '.join(books)}")
            scores[key]["players"].add(player)
            scores[key]["matchup"] = matchup
        else:
            digits = defaultdict(list)
            for i, pr in enumerate(prices):
                d = last_two(pr)
                if d is not None: digits[d].append(books[i])
            for d, bks in digits.items():
                if len(bks) >= 2:
                    scores[player]["score"] += 4
                    scores[player]["reasons"].append(f"Matching digit tier ({d:02d}) – {', '.join(bks)}")
                    scores[player]["players"].add(player)
                    scores[player]["matchup"] = matchup

    # --- Over/Under priced ---
    for (market, player, point), group in df.groupby(["market", "player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        if len(prices) < 3: continue
        try: med = statistics.median(prices)
        except: continue
        for _, row in group.iterrows():
            if row["price"] is None: continue
            diff = row["price"] - med
            if abs(diff) >= 100:
                label = "Underpriced" if diff > 0 else "Overpriced"
                scores[player]["score"] += 2
                scores[player]["reasons"].append(f"{label} on {row['book']} ({format_odds(row['price'])} vs med {format_odds(med)})")
                scores[player]["players"].add(player)
                scores[player]["matchup"] = f"{row['away']} @ {row['home']}"

    # --- Name / Initial patterns ---
    for market, group in df.groupby("market"):
        players = list(group["player"].dropna().unique())
        matchup = f"{group['away'].iloc[0]} @ {group['home'].iloc[0]}" if len(group) else ""

        # Same initials
        init_map = defaultdict(list)
        for p in players:
            f, l = get_initials(p)
            if f and l: init_map[f+l].append(p)
        for k, names in init_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 3
                scores[key]["reasons"].append(f"Same initials {k}")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

        # Cross / opposite initials
        for i, p1 in enumerate(players):
            f1, l1 = get_initials(p1)
            if not f1 or not l1: continue
            for p2 in players[i+1:]:
                f2, l2 = get_initials(p2)
                if not f2 or not l2: continue
                if l1 == f2 or f1 == l2:
                    key = " + ".join(sorted([p1, p2]))
                    scores[key]["score"] += 3
                    scores[key]["reasons"].append(f"Cross initial ({l1}↔{f2})")
                    scores[key]["players"].update([p1, p2])
                    scores[key]["matchup"] = matchup

        # Same last name
        last_map = defaultdict(list)
        for p in players:
            parts = str(p).split()
            if len(parts) >= 2:
                last_map[parts[-1].lower()].append(p)
        for last, names in last_map.items():
            if len(names) >= 2:
                key = " + ".join(sorted(names))
                scores[key]["score"] += 2
                scores[key]["reasons"].append(f"Same last name ({last.title()})")
                scores[key]["players"].update(names)
                scores[key]["matchup"] = matchup

    # Build final list
    results = []
    for key, data in scores.items():
        if data["score"] <= 0: continue
        is_pair = " + " in key
        final_score = data["score"] + (2 if is_pair else 0)
        results.append({
            "label": key,
            "score": final_score,
            "reasons": list(set(data["reasons"])),
            "matchup": data["matchup"],
            "is_pair": is_pair
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)

# ============================================================
# APP
# ============================================================
def main():
    st.title("💖 Girl Magic Odds Model")
    st.caption("Pure odds tricks • Digit flags • Girl Math only")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Manage app → Secrets")
        st.stop()

    with st.sidebar:
        st.header("Settings")
        selected_markets = st.multiselect("Markets", MARKETS, default=["batter_home_runs"])
        max_show = st.slider("Max results", 5, 30, 15)

    if st.button("Load MLB Games 💫", type="primary"):
        st.session_state["events"] = fetch_events(api_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load MLB Games**")
        st.stop()

    game_opts = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("Select games", list(game_opts.keys()))

    if st.button("Fetch Odds 💖", type="primary") and chosen:
        all_rows = []
        prog = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds(api_key, game_opts[label], selected_markets)
            all_rows.extend(flatten(data))
            prog.progress((i+1)/len(chosen))
        if all_rows:
            st.success(f"Loaded {len(all_rows)} odds rows from preferred books")
            st.session_state["odds"] = all_rows
        else:
            st.warning("No odds returned from preferred books")

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["💅 Odds Magic", "📊 Girl Math Flags", "👑 Queen of the Digits"])

    results = run_girl_math(df) if not df.empty else []

    with tab1:
        st.subheader("💅 Odds Magic Overview")
        if not results:
            st.info("Fetch some games to see magic")
        else:
            for r in results[:max_show]:
                reasons = " • ".join(r["reasons"][:4])
                st.markdown(
                    f'<div class="magic-card">'
                    f'<b>{r["label"]}</b> <span class="score-badge">Score {r["score"]}</span><br>'
                    f'<small>{r["matchup"]}</small><br>{reasons}'
                    f'</div>', unsafe_allow_html=True
                )

    with tab2:
        st.subheader("📊 All Girl Math Flags")
        if not results:
            st.info("No flags yet")
        else:
            for r in results:
                st.markdown(
                    f'<div class="magic-card">'
                    f'<b>{r["label"]}</b> — Score {r["score"]}<br>'
                    f'{ " • ".join(r["reasons"]) }'
                    f'</div>', unsafe_allow_html=True
                )

    with tab3:
        st.subheader("👑 Queen of the Digits")
        digit_flags = [r for r in results if any("digit" in x.lower() or "ends in" in x.lower() or "850" in x or "exact match" in x.lower() for x in r["reasons"])]
        if not digit_flags:
            st.info("No digit patterns found")
        else:
            for r in digit_flags:
                st.markdown(
                    f'<div class="magic-card">'
                    f'<b>{r["label"]}</b><br>{ " • ".join(r["reasons"]) }'
                    f'</div>', unsafe_allow_html=True
                )

    st.caption("💖 Girl Magic • Odds tricks only • No clutter")

if __name__ == "__main__":
    main()
