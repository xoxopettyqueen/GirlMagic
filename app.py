"""
Girl Magic Odds ✨
Boss Bitch • HBIC • Me & My Girls We Rolling
Tighter cards • Clearer +EV language
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict
import statistics
from datetime import datetime

st.set_page_config(
    page_title="Girl Magic Odds ✨",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background: linear-gradient(165deg, #0c0414 0%, #1a0a28 45%, #2a0b3d 100%);
        color: #fce7f3;
        font-family: 'Inter', sans-serif;
    }

    h1 {
        font-family: 'Playfair Display', serif !important;
        font-weight: 900 !important;
        background: linear-gradient(90deg, #f9a8d4, #e879f9, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.6rem !important;
        margin-bottom: 0 !important;
    }

    .subtitle {
        color: #f9a8d4;
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: -4px;
        margin-bottom: 18px;
    }

    .how-to {
        background: #1c0f2b;
        border: 1px solid #f472b6;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 18px;
        font-size: 0.9rem;
        line-height: 1.45;
    }

    .stButton > button {
        background: linear-gradient(90deg, #db2777, #9333ea) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 15px rgba(219, 39, 119, 0.4);
    }

    .card {
        background: linear-gradient(155deg, #1c0f2b, #27143a);
        border: 1px solid #f472b6;
        border-radius: 14px;
        padding: 12px 16px;
        margin: 0;
        color: #fdf2f8;
        box-shadow: 0 6px 18px rgba(0,0,0,0.3);
        position: relative;
        height: 100%;
    }

    .card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 5px; height: 100%;
        border-radius: 14px 0 0 14px;
    }

    .dk::before { background: #00a3e0; }
    .mgm::before { background: #c4a35a; }
    .match::before { background: #f472b6; }
    .digit::before { background: #a855f7; }
    .fd::before { background: #1493ff; }
    .name::before { background: #f9a8d4; }
    .signal::before { background: #34d399; }
    .hist::before { background: #fbbf24; }

    .bet {
        background: linear-gradient(155deg, #0d2818, #163d28) !important;
        border: 1px solid #34d399 !important;
        box-shadow: 0 0 18px rgba(52, 211, 153, 0.25);
    }
    .bet::before { background: #34d399; }

    .skip {
        background: #16101f !important;
        border: 1px solid #4b5563 !important;
        opacity: 0.75;
    }
    .skip::before { background: #6b7280; }

    .tag {
        display: inline-block;
        background: #3b0764;
        color: #f9a8d4;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 12px;
        margin: 2px 3px 2px 0;
        border: 1px solid #a855f7;
    }

    .tag-green {
        background: #064e3b;
        color: #6ee7b7;
        border: 1px solid #34d399;
    }

    .queen-banner {
        display: inline-block;
        background: linear-gradient(90deg, #db2777, #9333ea);
        color: white;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 20px;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] {
        background: #1c0f2b;
        border-radius: 10px;
        color: #f9a8d4;
        font-weight: 600;
        padding: 8px 12px;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #db2777, #9333ea) !important;
        color: white !important;
    }

    .footer {
        text-align: center;
        color: #f9a8d4;
        font-size: 0.9rem;
        margin-top: 40px;
        letter-spacing: 1px;
        opacity: 0.85;
    }

    .grid-card {
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key", type="password")
    return key

def format_odds(p):
    try: return f"{int(p):+d}"
    except: return str(p)

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def get_initials(name):
    parts = str(name).strip().split()
    if len(parts) < 2: return None, None
    return parts[0][0].upper(), parts[-1][0].upper()

def fetch_events(api_key):
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(str(e))
        return []

def fetch_odds(api_key, event_id):
    params = {
        "apiKey": api_key,
        "regions": REGIONS,
        "markets": "batter_home_runs",
        "oddsFormat": "american"
    }
    try:
        r = requests.get(f"{API_BASE}/sports/baseball_mlb/events/{event_id}/odds", params=params, timeout=20)
        if r.status_code != 200: return None
        return r.json()
    except:
        return None

def flatten(data):
    if not data: return []
    rows = []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over": continue
                rows.append({
                    "event": event,
                    "book": book.get("key", ""),
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": o.get("point"),
                })
    return rows

def run_flags(df, previous_df=None):
    if df.empty: return [], []

    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []
    flagged_players = set()
    player_methods = defaultdict(list)

    # DraftKings Ends in 10
    for _, row in df.iterrows():
        if "draftkings" in str(row["book"]).lower():
            if last_two(row["price"]) == 10:
                results.append({"type": "dk", "label": row["player"], "reason": f"DK ends in 10 → {format_odds(row['price'])}", "event": row["event"], "css": "dk", "methods": ["DK 10"]})
                flagged_players.add(row["player"])
                player_methods[row["player"]].append("DK 10")

    # BetMGM Classic Endings
    mgm_df = df[df["book"].str.lower().str.contains("betmgm|mgm", na=False)].copy()
    for event, event_group in mgm_df.groupby("event"):
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append(row["player"])
        for d, players in ending_groups.items():
            names = sorted(set(players))
            if len(names) >= 2:
                results.append({"type": "mgm", "label": " + ".join(names), "reason": f"MGM {'Pair' if len(names)==2 else 'Group'} ends in {d:02d}", "event": event, "css": "mgm", "methods": [f"MGM {d:02d}"]})
                for n in names:
                    flagged_players.add(n)
                    player_methods[n].append(f"MGM {d:02d}")

    # Exact Matching Odds
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(set(prices)) == 1:
            results.append({"type": "match", "label": player, "reason": f"Exact match {format_odds(prices[0])} → {', '.join(books)}", "event": group["event"].iloc[0], "css": "match", "methods": ["Exact Match"]})
            flagged_players.add(player)
            player_methods[player].append("Exact Match")

    # MGM Exact Match
    for event, event_group in mgm_df.groupby("event"):
        for price, price_group in event_group.groupby("price"):
            players = sorted(price_group["player"].unique().tolist())
            if len(players) >= 2:
                results.append({"type": "mgm_exact", "label": " + ".join(players), "reason": f"MGM Exact {format_odds(price)} ({len(players)} players)", "event": event, "css": "mgm", "methods": ["MGM Exact"]})
                for p in players:
                    flagged_players.add(p)
                    player_methods[p].append("MGM Exact")

    # Matching 25/50/75
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2: continue
        digits = defaultdict(list)
        for _, row in group.iterrows():
            d = last_two(row["price"])
            if d in (25, 50, 75):
                digits[d].append(row["book"])
        for d, bks in digits.items():
            if len(set(bks)) >= 2:
                results.append({"type": "digit", "label": player, "reason": f"Matching {d}s → {', '.join(set(bks))}", "event": group["event"].iloc[0], "css": "digit", "methods": [f"Match {d}"]})
                flagged_players.add(player)
                player_methods[player].append(f"Match {d}")

    # FanDuel Patterns
    for _, row in df.iterrows():
        if "fanduel" in str(row["book"]).lower():
            price = abs(int(row["price"])) if row["price"] else 0
            last = last_two(row["price"])
            if price >= 500 and last in (10, 30, 60, 70, 90):
                results.append({"type": "fd", "label": row["player"], "reason": f"FD ≥+500 ends in {last:02d} → {format_odds(row['price'])}", "event": row["event"], "css": "fd", "methods": ["FD Pattern"]})
                flagged_players.add(row["player"])
                player_methods[row["player"]].append("FD Pattern")

    # Line Signals
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(prices) < 3: continue
        if len(set(prices)) == 1:
            results.append({"type": "signal", "label": player, "reason": f"Stuck {format_odds(prices[0])} on {len(prices)} books", "event": group["event"].iloc[0], "css": "signal", "methods": ["Stuck"]})
            flagged_players.add(player)
            player_methods[player].append("Stuck")
        try:
            med = statistics.median(prices)
            for i, pr in enumerate(prices):
                if abs(pr - med) >= 150:
                    results.append({"type": "signal", "label": player, "reason": f"Wide on {books[i]}", "event": group["event"].iloc[0], "css": "signal", "methods": ["Wide"]})
                    flagged_players.add(player)
                    player_methods[player].append("Wide")
        except:
            pass

    # Historical
    if previous_df is not None and not previous_df.empty:
        prev_lookup = {(row["player"], row["book"]): row["price"] for _, row in previous_df.iterrows()}
        for _, row in df.iterrows():
            key = (row["player"], row["book"])
            if key in prev_lookup:
                old, new = prev_lookup[key], row["price"]
                if old is not None and new is not None and old != new:
                    direction = "↑" if new > old else "↓"
                    results.append({"type": "hist", "label": row["player"], "reason": f"{row['book']}: {format_odds(old)} → {format_odds(new)} {direction}", "event": row["event"], "css": "hist", "methods": ["Moved"]})
                    flagged_players.add(row["player"])
                    player_methods[row["player"]].append("Moved")

    # +EV Board
    ev_board = []
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(prices) < 2: continue

        best_price = max(prices)
        best_book = books[prices.index(best_price)]
        try:
            median = statistics.median(prices)
        except:
            median = best_price

        edge = best_price - median
        has_edge = edge >= 40
        has_method = player in flagged_players
        methods = list(set(player_methods.get(player, [])))
        is_bet = has_edge and has_method

        if is_bet:
            why = "Has one of our methods AND the price is better than most books"
        elif has_method:
            why = "Has a method but the price is not better than most books"
        elif has_edge:
            why = "Price looks better but none of our methods hit"
        else:
            why = "No method + price is not better than most books"

        ev_board.append({
            "player": player,
            "best_price": best_price,
            "best_book": best_book,
            "median": median,
            "edge": edge,
            "books": ", ".join(books),
            "event": group["event"].iloc[0],
            "is_bet": is_bet,
            "why": why,
            "methods": methods
        })

    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["edge"]))

    # Name patterns
    player_events = defaultdict(set)
    for _, row in df.iterrows():
        player_events[row["player"]].add(row["event"])
    players = list(df["player"].dropna().unique())

    def is_different_teams(p1, p2):
        return len(player_events[p1] & player_events[p2]) == 0

    def both_flagged(p1, p2):
        return p1 in flagged_players and p2 in flagged_players

    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l: init_map[f + l].append(p)
    for k, names in init_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "diff teams"
                    results.append({"type": "same_init", "label": f"{p1} + {p2}", "reason": f"Same initials {k} ({tag})", "event": "", "css": "name", "methods": ["Same Init"]})

    for i, p1 in enumerate(players):
        _, l1 = get_initials(p1)
        if not l1: continue
        for p2 in players[i+1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2 and both_flagged(p1, p2):
                same = not is_different_teams(p1, p2)
                tag = "same team" if same else "diff teams"
                results.append({"type": "cross", "label": f"{p1} + {p2}", "reason": f"Cross ({l1}) ({tag})", "event": "", "css": "name", "methods": ["Cross Init"]})

    last_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if len(parts) >= 2: last_map[parts[-1].lower()].append(p)
    for last, names in last_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "diff teams"
                    results.append({"type": "last", "label": f"{p1} + {p2}", "reason": f"Same last ({last.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same Last"]})

    first_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if parts: first_map[parts[0].lower()].append(p)
    for first, names in first_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i+1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "diff teams"
                    results.append({"type": "first", "label": f"{p1} + {p2}", "reason": f"Same first ({first.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same First"]})

    return results, ev_board

def main():
    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch • HBIC • Me & My Girls We Rolling</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="how-to">
        <b>Quick start:</b> Load Games → Select games → Fetch Odds → Green cards = the ones we like
    </div>
    """, unsafe_allow_html=True)

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Secrets")
        st.stop()

    if st.button("① Load Games", type="primary"):
        st.session_state["events"] = fetch_events(api_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** to start")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("② Select games", list(options.keys()))

    if st.button("③ Fetch Odds", type="primary") and chosen:
        all_rows = []
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds(api_key, options[label])
            all_rows.extend(flatten(data))
            progress.progress((i + 1) / len(chosen))
        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["last_fetch_time"] = datetime.now().strftime("%I:%M %p")
            st.success(f"Loaded {len(df)} props • {st.session_state['last_fetch_time']}")
        else:
            st.warning("No odds returned")

    odds = st.session_state.get("odds", [])
    previous = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(previous) if previous else None
    results, ev_board = run_flags(df, prev_df) if not df.empty else ([], [])

    tabs = st.tabs([
        "🐝 +EV Board",
        "🎯 DK 10s",
        "🎰 MGM",
        "🤝 Exact",
        "⭐ MGM Exact",
        "🔢 Digits",
        "💙 FanDuel",
        "📈 Signals",
        "⏳ Movement",
        "💅 Initials",
        "🔄 Cross",
        "👩‍👧 Last Name",
        "👯 First Name",
        "📖 Glossary"
    ])

    # ========== +EV BOARD ==========
    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 Boss Bitch Picks</div>', unsafe_allow_html=True)
        st.write("**Green = we like it.** **Gray = we skip it.** That’s it.")

        if not ev_board:
            st.info("Fetch some games first")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(ev_board):
                col = cols[idx % 2]
                with col:
                    tags_html = "".join([f'<span class="tag tag-green">{m}</span>' for m in item["methods"][:3]])
                    if not item["methods"]:
                        tags_html = '<span class="tag">No methods</span>'

                    if item["is_bet"]:
                        st.markdown(f'''
                        <div class="card bet grid-card">
                            <b>🟢 BET THIS</b> — <b>{item["player"]}</b><br>
                            Best: {format_odds(item["best_price"])} on {item["best_book"]}<br>
                            Most books: {format_odds(item["median"])}<br>
                            {tags_html}<br>
                            <small>{item["why"]}</small>
                        </div>''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="card skip grid-card">
                            <b>⚪ SKIP</b> — <b>{item["player"]}</b><br>
                            Best: {format_odds(item["best_price"])} on {item["best_book"]}<br>
                            Most books: {format_odds(item["median"])}<br>
                            {tags_html}<br>
                            <small>{item["why"]}</small>
                        </div>''', unsafe_allow_html=True)

    def show_tab(tab, typ, banner, explain):
        with tab:
            st.markdown(f'<div class="queen-banner">{banner}</div>', unsafe_allow_html=True)
            st.caption(explain)
            items = [r for r in results if r["type"] == typ]
            if not items:
                st.info("None right now")
                return

            cols = st.columns(2)
            for idx, r in enumerate(items):
                col = cols[idx % 2]
                with col:
                    methods = r.get("methods", [])
                    tags = "".join([f'<span class="tag">{m}</span>' for m in methods])
                    st.markdown(f'''
                    <div class="card {r["css"]} grid-card">
                        <b>{r["label"]}</b><br>
                        {r["reason"]}<br>
                        {tags}
                        <br><small>{r.get("event","")}</small>
                    </div>''', unsafe_allow_html=True)

    show_tab(tabs[1], "dk", "🎯 DraftKings Ends in 10", "DK prices ending in 10 (+210, +310, etc.)")
    show_tab(tabs[2], "mgm", "🎰 BetMGM Classic", "Two+ players same team with MGM 00/25/50/75 endings")
    show_tab(tabs[3], "match", "🤝 Exact Matching Odds", "Same exact price on the same player across books")
    show_tab(tabs[4], "mgm_exact", "⭐ MGM Exact Match", "Same exact price on BetMGM for multiple players")
    show_tab(tabs[5], "digit", "🔢 Matching 25/50/75", "Same player has 25/50/75 endings on different books")
    show_tab(tabs[6], "fd", "💙 FanDuel Patterns", "FanDuel +500+ ending in 10/30/60/70/90")
    show_tab(tabs[7], "signal", "📈 Line Signals", "Stuck numbers or one book way off the others")
    show_tab(tabs[8], "hist", "⏳ Price Movement", "Price changed since last fetch")
    show_tab(tabs[9], "same_init", "💅 Same Initials", "Same first + last initial (already has a method)")
    show_tab(tabs[10], "cross", "🔄 Cross Initials", "Last initial of one = first initial of another")
    show_tab(tabs[11], "last", "👩‍👧 Same Last Name", "Players sharing a last name")
    show_tab(tabs[12], "first", "👯 Same First Name", "Players sharing a first name")

    with tabs[13]:
        st.markdown('<div class="queen-banner">📖 Glossary</div>', unsafe_allow_html=True)
        st.markdown("""
### Black & white rules

**🟢 BET THIS**  
Two things must be true at the same time:
1. At least one of our Girl Magic methods hit
2. The best price is clearly better than what most other books are offering

**⚪ SKIP**  
Anything that does not meet both of the rules above.

That’s the whole system.

---

### What the methods mean

- **DK 10** → DraftKings price ends in 10  
- **MGM 00 / 25 / 50 / 75** → BetMGM classic endings (pairs or groups)  
- **Exact Match** → Same exact price on different books  
- **MGM Exact** → Same exact price on BetMGM for multiple players  
- **Matching Digits** → Same player shows 25/50/75 on more than one book  
- **FD Pattern** → FanDuel price is +500 or higher and ends in 10, 30, 60, 70 or 90  
- **Stuck** → Same price showing on 3 or more books  
- **Wide** → One book is way different from the rest  
- **Name patterns** → Matching initials or names (only shown when a method already hit)

The little colored tags on every card tell you exactly which methods fired.
        """)

    st.markdown('<div class="footer">👑 Girl Magic • Boss Bitch • HBIC • Me & My Girls We Rolling</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
