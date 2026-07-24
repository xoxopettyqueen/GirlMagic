"""
Girl Magic Odds ✨
Boss Bitch • HBIC • Me & My Girls We Rolling
Pull ALL books from The Odds API + warn when core books are missing
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
        font-size: 2.4rem !important;
        margin-bottom: 0 !important;
    }

    .subtitle {
        color: #f9a8d4;
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: -4px;
        margin-bottom: 14px;
    }

    .how-to {
        background: #1c0f2b;
        border: 1px solid #f472b6;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 14px;
        font-size: 0.9rem;
        line-height: 1.4;
    }

    .warning-box {
        background: #3b0764;
        border: 2px solid #f472b6;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-size: 0.95rem;
        color: #fce7f3;
    }

    .info-box {
        background: #1c0f2b;
        border: 1px solid #a855f7;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 14px;
        font-size: 0.9rem;
    }

    .stButton > button {
        background: linear-gradient(90deg, #db2777, #9333ea) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1.3rem !important;
        box-shadow: 0 3px 12px rgba(219, 39, 119, 0.4);
        font-size: 0.95rem;
    }

    .card {
        background: linear-gradient(155deg, #1c0f2b, #27143a);
        border: 1px solid #f472b6;
        border-radius: 12px;
        padding: 8px 12px;
        margin: 0;
        color: #fdf2f8;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        position: relative;
        height: 100%;
        font-size: 0.95rem;
    }

    .card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px; height: 100%;
        border-radius: 12px 0 0 12px;
    }

    .high::before { background: linear-gradient(180deg, #f472b6, #c026d3); }
    .strong::before { background: linear-gradient(180deg, #e879f9, #a855f7); }
    .medium::before { background: linear-gradient(180deg, #c084fc, #7c3aed); }
    .low::before { background: #6b7280; }
    .skip-card::before { background: #4b5563; }

    .bet {
        background: linear-gradient(155deg, #0d2818, #163d28) !important;
        border: 1px solid #34d399 !important;
        box-shadow: 0 0 14px rgba(52, 211, 153, 0.25);
    }

    .skip {
        background: #16101f !important;
        border: 1px solid #4b5563 !important;
        opacity: 0.75;
    }

    .tag {
        display: inline-block;
        background: #3b0764;
        color: #f9a8d4;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 10px;
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
        font-size: 0.75rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 16px;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .meter {
        display: flex;
        gap: 3px;
        margin: 4px 0 6px 0;
    }

    .meter-bar {
        height: 6px;
        width: 18px;
        border-radius: 3px;
        background: #374151;
    }

    .meter-bar.filled-high { background: linear-gradient(90deg, #f472b6, #c026d3); }
    .meter-bar.filled-strong { background: linear-gradient(90deg, #e879f9, #a855f7); }
    .meter-bar.filled-medium { background: linear-gradient(90deg, #c084fc, #7c3aed); }
    .meter-bar.filled-low { background: #6b7280; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        background: #1c0f2b;
        border-radius: 8px;
        color: #f9a8d4;
        font-weight: 600;
        padding: 7px 11px;
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
        margin-top: 30px;
        letter-spacing: 1px;
        opacity: 0.85;
    }

    .grid-card {
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us,us2"

# Core books our methods need
CORE_BOOKS = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM"
}

def get_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("Odds API Key", type="password")
    return key

def format_odds(p):
    try:
        return f"{int(p):+d}"
    except:
        return str(p)

def last_two(p):
    try:
        return abs(int(p)) % 100
    except:
        return None

def get_initials(name):
    parts = str(name).strip().split()
    if len(parts) < 2:
        return None, None
    return parts[0][0].upper(), parts[-1][0].upper()

def get_confidence(methods, edge, is_bet):
    if not is_bet:
        return "Skip", 1, "low", "skip-card"

    score = 0
    if "Last one left" in methods:
        score += 4
    if any("Stayed" in m and "times" in m for m in methods):
        score += 3
    if "Stayed in the group" in methods:
        score += 2
    if "Same on 3+ books" in methods:
        score += 2
    score += min(len(methods), 3)
    score += 1 if edge >= 70 else 0

    if score >= 7:
        return "High", 5, "high", "high"
    elif score >= 5:
        return "Strong", 4, "strong", "strong"
    elif score >= 3:
        return "Medium", 3, "medium", "medium"
    else:
        return "Low", 2, "low", "low"

def make_meter(bars, level):
    html = '<div class="meter">'
    for i in range(5):
        if i < bars:
            html += f'<div class="meter-bar filled-{level}"></div>'
        else:
            html += '<div class="meter-bar"></div>'
    html += '</div>'
    return html

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
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

def flatten(data):
    """Pull EVERY book the API returns"""
    if not data:
        return [], set()
    rows = []
    found_books = set()
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        book_key = book.get("key", "").lower()
        found_books.add(book_key)
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over":
                    continue
                # Only keep the lowest line (0.5 HR)
                point = o.get("point")
                if point is not None and point > 0.5:
                    continue
                rows.append({
                    "event": event,
                    "book": book_key,
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": point,
                })
    return rows, found_books

def run_flags(df, previous_df=None):
    if df.empty:
        return [], []

    if "point" in df.columns:
        df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results = []
    flagged_players = set()
    player_methods = defaultdict(list)

    if "price_history" not in st.session_state:
        st.session_state["price_history"] = []

    current_snap = {}
    for _, row in df.iterrows():
        key = (row["player"], row["book"])
        current_snap[key] = row["price"]

    st.session_state["price_history"].append(current_snap)
    st.session_state["price_history"] = st.session_state["price_history"][-8:]

    stayed_count = defaultdict(int)
    history = st.session_state["price_history"]
    if len(history) >= 2:
        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]
            for key in curr:
                if key in prev and prev[key] == curr[key]:
                    stayed_count[key[0]] += 1

    # DraftKings Ends in 10
    for _, row in df.iterrows():
        if "draftkings" in str(row["book"]).lower():
            if last_two(row["price"]) == 10:
                results.append({
                    "type": "dk",
                    "label": row["player"],
                    "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "dk",
                    "methods": ["DK 10"]
                })
                flagged_players.add(row["player"])
                player_methods[row["player"]].append("DK 10")

    # BetMGM Classic (Same Team Only)
    mgm_df = df[df["book"].str.lower().str.contains("betmgm|mgm", na=False)].copy()

    if "mgm_history" not in st.session_state:
        st.session_state["mgm_history"] = []

    current_mgm_groups = []
    for event, event_group in mgm_df.groupby("event"):
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append(row["player"])
        for d, players in ending_groups.items():
            names = frozenset(players)
            if len(names) >= 2:
                current_mgm_groups.append({"event": event, "ending": d, "players": names})

    st.session_state["mgm_history"].append(current_mgm_groups)
    st.session_state["mgm_history"] = st.session_state["mgm_history"][-8:]

    mgm_stayed = defaultdict(int)
    mgm_survivor = set()
    mgm_hist = st.session_state["mgm_history"]
    if len(mgm_hist) >= 2:
        for snap in mgm_hist:
            seen = set()
            for g in snap:
                for p in g["players"]:
                    seen.add(p)
            for p in seen:
                mgm_stayed[p] += 1

        early = set()
        for g in mgm_hist[0]:
            if len(g["players"]) >= 3:
                early.update(g["players"])
        late = set()
        for g in mgm_hist[-1]:
            late.update(g["players"])
        mgm_survivor = early & late

    for event, event_group in mgm_df.groupby("event"):
        ending_groups = defaultdict(list)
        for _, row in event_group.iterrows():
            d = last_two(row["price"])
            if d in (0, 25, 50, 75):
                ending_groups[d].append(row["player"])

        for d, players in ending_groups.items():
            names = sorted(set(players))
            if len(names) >= 2:
                methods = [f"MGM {d:02d}"]
                extra = []
                for n in names:
                    cnt = mgm_stayed.get(n, 0)
                    if cnt >= 3:
                        methods.append(f"Stayed {cnt} times")
                        extra.append(f"Stayed {cnt} times")
                    elif cnt >= 2:
                        methods.append("Stayed in the group")
                        extra.append("Stayed in the group")
                    if n in mgm_survivor:
                        methods.append("Last one left")
                        extra.append("Last one left")

                reason = f"MGM {'pair' if len(names) == 2 else 'group of ' + str(len(names))} ends in {d:02d}"
                if extra:
                    reason += " • " + " + ".join(set(extra))

                results.append({
                    "type": "mgm",
                    "label": " + ".join(names),
                    "reason": reason,
                    "event": event,
                    "css": "mgm",
                    "methods": list(set(methods))
                })
                for n in names:
                    flagged_players.add(n)
                    player_methods[n].extend(methods)

    # Exact Matching Odds
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2:
            continue
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(set(prices)) == 1:
            results.append({
                "type": "match",
                "label": player,
                "reason": f"Exact match {format_odds(prices[0])} → {', '.join(books)}",
                "event": group["event"].iloc[0],
                "css": "match",
                "methods": ["Exact Match"]
            })
            flagged_players.add(player)
            player_methods[player].append("Exact Match")

    # MGM Exact Match
    for event, event_group in mgm_df.groupby("event"):
        for price, price_group in event_group.groupby("price"):
            players = sorted(price_group["player"].unique().tolist())
            if len(players) >= 2:
                results.append({
                    "type": "mgm_exact",
                    "label": " + ".join(players),
                    "reason": f"MGM Exact {format_odds(price)} ({len(players)} players)",
                    "event": event,
                    "css": "mgm",
                    "methods": ["MGM Exact"]
                })
                for p in players:
                    flagged_players.add(p)
                    player_methods[p].append("MGM Exact")

    # Matching 25/50/75
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        if len(group) < 2:
            continue
        digits = defaultdict(list)
        for _, row in group.iterrows():
            d = last_two(row["price"])
            if d in (25, 50, 75):
                digits[d].append(row["book"])
        for d, bks in digits.items():
            if len(set(bks)) >= 2:
                results.append({
                    "type": "digit",
                    "label": player,
                    "reason": f"Matching {d}s → {', '.join(set(bks))}",
                    "event": group["event"].iloc[0],
                    "css": "digit",
                    "methods": [f"Match {d}"]
                })
                flagged_players.add(player)
                player_methods[player].append(f"Match {d}")

    # FanDuel Patterns
    for _, row in df.iterrows():
        if "fanduel" in str(row["book"]).lower():
            price = abs(int(row["price"])) if row["price"] else 0
            last = last_two(row["price"])
            if price >= 500 and last in (10, 30, 60, 70, 90):
                results.append({
                    "type": "fd",
                    "label": row["player"],
                    "reason": f"FanDuel ≥ +500 ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"],
                    "css": "fd",
                    "methods": ["FD Pattern"]
                })
                flagged_players.add(row["player"])
                player_methods[row["player"]].append("FD Pattern")

    # General "Stayed the same"
    for player, cnt in stayed_count.items():
        if cnt >= 2:
            label = f"Stayed {cnt} times" if cnt >= 3 else "Stayed the same"
            results.append({
                "type": "signal",
                "label": player,
                "reason": "Price stayed the same across multiple fetches",
                "event": "",
                "css": "signal",
                "methods": [label]
            })
            flagged_players.add(player)
            player_methods[player].append(label)

    # Line Signals
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(prices) < 3:
            continue
        if len(set(prices)) == 1:
            results.append({
                "type": "signal",
                "label": player,
                "reason": f"Same price on {len(prices)} books",
                "event": group["event"].iloc[0],
                "css": "signal",
                "methods": ["Same on 3+ books"]
            })
            flagged_players.add(player)
            player_methods[player].append("Same on 3+ books")
        try:
            med = statistics.median(prices)
            for i, pr in enumerate(prices):
                if abs(pr - med) >= 150:
                    results.append({
                        "type": "signal",
                        "label": player,
                        "reason": f"One book is way different ({books[i]})",
                        "event": group["event"].iloc[0],
                        "css": "signal",
                        "methods": ["Way different"]
                    })
                    flagged_players.add(player)
                    player_methods[player].append("Way different")
        except:
            pass

    # Historical Movement
    if previous_df is not None and not previous_df.empty:
        prev_lookup = {(row["player"], row["book"]): row["price"] for _, row in previous_df.iterrows()}
        for _, row in df.iterrows():
            key = (row["player"], row["book"])
            if key in prev_lookup:
                old, new = prev_lookup[key], row["price"]
                if old is not None and new is not None and old != new:
                    direction = "went up" if new > old else "went down"
                    results.append({
                        "type": "hist",
                        "label": row["player"],
                        "reason": f"{row['book']}: {format_odds(old)} → {format_odds(new)} ({direction})",
                        "event": row["event"],
                        "css": "hist",
                        "methods": ["Price moved"]
                    })
                    flagged_players.add(row["player"])
                    player_methods[row["player"]].append("Price moved")

    # +EV Board (edge +50)
    ev_board = []
    for (player, point), group in df.groupby(["player", "point"], dropna=False):
        prices = group["price"].dropna().tolist()
        books = group["book"].tolist()
        if len(prices) < 2:
            continue

        best_price = max(prices)
        best_book = books[prices.index(best_price)]
        try:
            median = statistics.median(prices)
        except:
            median = best_price

        edge = best_price - median
        has_edge = edge >= 50
        has_method = player in flagged_players
        methods = list(set(player_methods.get(player, [])))
        is_bet = has_edge and has_method

        conf_label, bars, level, css = get_confidence(methods, edge, is_bet)

        priority = 0
        if "Last one left" in methods:
            priority += 30
        if any("Stayed" in m and "times" in m for m in methods):
            priority += 20
        if "Stayed in the group" in methods:
            priority += 10
        if "Same on 3+ books" in methods:
            priority += 8
        priority += len(methods)
        priority += min(edge / 10, 15)

        if is_bet:
            why = "Has one of our methods and the price is better than most books."
        elif has_method:
            why = "Has a method, but the price is not better than most books."
        elif has_edge:
            why = "Price looks better, but none of our methods hit."
        else:
            why = "No method and the price is not better than most books."

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
            "methods": methods,
            "priority": priority,
            "conf_label": conf_label,
            "bars": bars,
            "level": level,
            "css": css
        })

    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["priority"]))

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
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i + 1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "different teams"
                    results.append({
                        "type": "same_init",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same initials {k} ({tag})",
                        "event": "",
                        "css": "name",
                        "methods": ["Same Init"]
                    })

    for i, p1 in enumerate(players):
        _, l1 = get_initials(p1)
        if not l1:
            continue
        for p2 in players[i + 1:]:
            f2, _ = get_initials(p2)
            if f2 and l1 == f2 and both_flagged(p1, p2):
                same = not is_different_teams(p1, p2)
                tag = "same team" if same else "different teams"
                results.append({
                    "type": "cross",
                    "label": f"{p1} + {p2}",
                    "reason": f"Cross initials ({l1}) ({tag})",
                    "event": "",
                    "css": "name",
                    "methods": ["Cross Init"]
                })

    last_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if len(parts) >= 2:
            last_map[parts[-1].lower()].append(p)
    for last, names in last_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i + 1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "different teams"
                    results.append({
                        "type": "last",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same last name ({last.title()}) ({tag})",
                        "event": "",
                        "css": "name",
                        "methods": ["Same Last"]
                    })

    first_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if parts:
            first_map[parts[0].lower()].append(p)
    for first, names in first_map.items():
        for i, p1 in enumerate(names):
            for p2 in names[i + 1:]:
                if both_flagged(p1, p2):
                    same = not is_different_teams(p1, p2)
                    tag = "same team" if same else "different teams"
                    results.append({
                        "type": "first",
                        "label": f"{p1} + {p2}",
                        "reason": f"Same first name ({first.title()}) ({tag})",
                        "event": "",
                        "css": "name",
                        "methods": ["Same First"]
                    })

    return results, ev_board

def main():
    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch • HBIC • Me & My Girls We Rolling</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="how-to">
        <b>Quick start:</b> Load Games → Select games → Fetch Odds → Green cards = the ones we like.<br>
        <b>Tip:</b> Fetch a few times during the day so “Stayed in the group” and “Last one left” can appear.
    </div>
    """, unsafe_allow_html=True)

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your Odds API key in Secrets.")
        st.stop()

    if st.button("① Load Games", type="primary"):
        st.session_state["events"] = fetch_events(api_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** to start.")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("② Select games", list(options.keys()))

    if st.button("③ Fetch Odds", type="primary") and chosen:
        all_rows = []
        all_found_books = set()
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds(api_key, options[label])
            rows, found = flatten(data)
            all_rows.extend(rows)
            all_found_books.update(found)
            progress.progress((i + 1) / len(chosen))

        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["found_books"] = sorted(all_found_books)
            st.session_state["last_fetch_time"] = datetime.now().strftime("%I:%M %p")
            st.success(f"Loaded {len(df)} props • {st.session_state['last_fetch_time']}")
        else:
            st.warning("No odds returned.")

    # Show which books came back + warn about missing core books
    found_books = st.session_state.get("found_books", [])
    if found_books:
        missing_core = [CORE_BOOKS[b] for b in CORE_BOOKS if b not in found_books]
        present_core = [CORE_BOOKS[b] for b in CORE_BOOKS if b in found_books]

        st.markdown(f"""
        <div class="info-box">
            <b>Books returned this pull:</b> {', '.join(found_books)}
        </div>
        """, unsafe_allow_html=True)

        if missing_core:
            st.markdown(f"""
            <div class="warning-box">
                ⚠️ <b>Missing core books:</b> {', '.join(missing_core)}<br>
                Our main methods need FanDuel, DraftKings, and BetMGM.  
                Without them the flags will be incomplete.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"Core books present: {', '.join(present_core)}")

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

    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 Boss Bitch Picks</div>', unsafe_allow_html=True)
        st.write("**Green = we like it.** **Gray = we skip it.**")

        if not ev_board:
            st.info("Fetch some games first.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(ev_board):
                col = cols[idx % 2]
                with col:
                    tags_html = "".join([f'<span class="tag tag-green">{m}</span>' for m in item["methods"][:5]])
                    if not item["methods"]:
                        tags_html = '<span class="tag">No methods</span>'

                    meter = make_meter(item["bars"], item["level"])

                    if item["is_bet"]:
                        st.markdown(f'''
                        <div class="card bet grid-card {item["css"]}">
                            <b>🟢 BET THIS</b> — <b>{item["player"]}</b><br>
                            {meter}
                            Best: {format_odds(item["best_price"])} on {item["best_book"]}<br>
                            Most books: {format_odds(item["median"])}<br>
                            {tags_html}<br>
                            <small>{item["why"]}</small>
                        </div>''', unsafe_allow_html=True)
                    else:
                        st.markdown(f'''
                        <div class="card skip grid-card">
                            <b>⚪ SKIP</b> — <b>{item["player"]}</b><br>
                            {meter}
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
                st.info("None right now.")
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
                        <br><small>{r.get("event", "")}</small>
                    </div>''', unsafe_allow_html=True)

    show_tab(tabs[1], "dk", "🎯 DraftKings Ends in 10", "DraftKings prices ending in 10.")
    show_tab(tabs[2], "mgm", "🎰 BetMGM (Same Team Only)", "Same-team pairs and groups. Look for “Stayed in the group,” “Stayed 3 times,” and “Last one left.”")
    show_tab(tabs[3], "match", "🤝 Exact Matching Odds", "Same exact price across different books.")
    show_tab(tabs[4], "mgm_exact", "⭐ MGM Exact Match", "Same exact price on BetMGM for multiple players in the same game.")
    show_tab(tabs[5], "digit", "🔢 Matching 25/50/75", "Same player has 25, 50, or 75 endings on different books.")
    show_tab(tabs[6], "fd", "💙 FanDuel Patterns", "FanDuel prices of +500 or higher that end in 10, 30, 60, 70, or 90.")
    show_tab(tabs[7], "signal", "📈 Signals", "Stayed the same, Same on 3+ books, Way different.")
    show_tab(tabs[8], "hist", "⏳ Price Movement", "Price went up or down since the last fetch.")
    show_tab(tabs[9], "same_init", "💅 Same Initials", "Same first and last initial (only if a method already hit).")
    show_tab(tabs[10], "cross", "🔄 Cross Initials", "One player’s last initial matches another player’s first initial.")
    show_tab(tabs[11], "last", "👩‍👧 Same Last Name", "Players who share the same last name.")
    show_tab(tabs[12], "first", "👯 Same First Name", "Players who share the same first name.")

    with tabs[13]:
        st.markdown('<div class="queen-banner">📖 Glossary</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div class="card bet">
                <b>🟢 BET THIS</b><br>
                Has one of our methods <b>and</b> the price is better than most other books.
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class="card skip">
                <b>⚪ SKIP</b><br>
                Either no method hit, or the price is not better than most other books.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="queen-banner">MGM Clear Names</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="card mgm">
            <b>Stayed in the group</b> → Still in the same MGM pair or group<br>
            <b>Stayed 3 times</b> → Appeared in the group on three different fetches<br>
            <b>Last one left</b> → Started in a bigger group and is still there
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="queen-banner">All Methods</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="card">
            <span class="tag">DK 10</span> DraftKings ends in 10<br>
            <span class="tag">MGM 00/25/50/75</span> Same-team pairs or groups<br>
            <span class="tag">Exact Match</span> Same price on different books<br>
            <span class="tag">MGM Exact</span> Same price on BetMGM for multiple players<br>
            <span class="tag">Matching Digits</span> 25/50/75 across books<br>
            <span class="tag">FD Pattern</span> FanDuel +500 or higher with special endings<br>
            <span class="tag">Stayed the same</span> Price did not change across fetches<br>
            <span class="tag">Same on 3+ books</span> Exact same price on three or more books<br>
            <span class="tag">Way different</span> One book is much higher or lower than the rest<br>
            <span class="tag">Name patterns</span> Only shown when a method already hit
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="footer">👑 Girl Magic • Boss Bitch • HBIC • Me & My Girls We Rolling</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
