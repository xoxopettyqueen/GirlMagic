"""
Girl Magic Odds ✨
Boss Bitch • HBIC • Me & My Girls We Rolling
Rule: BET THIS = 2+ methods + edge ≥ 60
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
        font-size: 0.78rem;
        font-weight: 700;
        padding: 5px 14px;
        border-radius: 16px;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 10px;
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

    .grid-card { margin-bottom: 6px; }

    .gloss-card {
        background: linear-gradient(155deg, #1c0f2b, #27143a);
        border: 1px solid #a855f7;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
        font-size: 0.92rem;
        line-height: 1.45;
    }
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
REGIONS = "us,us2"

PREFERRED = {
    "fanduel", "draftkings", "betmgm",
    "hardrockbet", "williamhill_us", "caesars"
}

CORE_BOOKS = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM"
}

EDGE_MIN = 60
METHODS_MIN = 2

def get_odds_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("The Odds API Key", type="password", key="odds_key")
    return key

def get_sgo_key():
    return st.secrets.get("SGO_API_KEY", "d5422e23cc05702bf95197f6a98ec8ce")

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
    if "Last one left" in methods: score += 4
    if any("Stayed" in m and "times" in m for m in methods): score += 3
    if "Stayed in the group" in methods: score += 2
    if "Same on 3+ books" in methods: score += 2
    score += min(len(methods), 3)
    score += 1 if edge >= 80 else 0
    if score >= 7: return "High", 5, "high", "high"
    if score >= 5: return "Strong", 4, "strong", "strong"
    if score >= 3: return "Medium", 3, "medium", "medium"
    return "Low", 2, "low", "low"

def make_meter(bars, level):
    html = '<div class="meter">'
    for i in range(5):
        filled = f"filled-{level}" if i < bars else ""
        html += f'<div class="meter-bar {filled}"></div>'
    html += '</div>'
    return html

def fetch_events_oddsapi(api_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/baseball_mlb/events",
                         params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Odds API events error: {e}")
        return []

def fetch_odds_oddsapi(api_key, event_id):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/baseball_mlb/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": REGIONS,
                    "markets": "batter_home_runs", "oddsFormat": "american"}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def flatten_oddsapi(data):
    if not data:
        return [], set()
    rows, found = [], set()
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        bk = book.get("key", "").lower()
        found.add(bk)
        if bk not in PREFERRED:
            continue
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over":
                    continue
                if o.get("point") is not None and float(o["point"]) > 0.5:
                    continue
                rows.append({
                    "event": event, "book": bk, "player": o.get("description"),
                    "price": o.get("price"), "point": 0.5, "source": "oddsapi"
                })
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(f"{SGO_BASE}/events", params={
            "apiKey": sgo_key, "leagueID": "MLB",
            "oddsAvailable": "true", "limit": 25
        }, timeout=25)
        if r.status_code != 200:
            return rows, found
        for ev in r.json().get("data", []):
            if ev.get("status", {}).get("started"):
                continue
            teams = ev.get("teams", {})
            home = teams.get("home", {}).get("names", {}).get("long", "Home")
            away = teams.get("away", {}).get("names", {}).get("long", "Away")
            event_name = f"{away} @ {home}"
            players_map = ev.get("players", {})
            for odd_id, odd_data in ev.get("odds", {}).items():
                if "batting_homeRuns" not in odd_id:
                    continue
                if "ou-over" not in odd_id and "-over" not in odd_id:
                    continue
                ou = odd_data.get("bookOverUnder") or odd_data.get("fairOverUnder")
                if ou is not None and float(ou) > 0.5:
                    continue
                pid = odd_data.get("playerID") or odd_data.get("statEntityID")
                if not pid or pid not in players_map:
                    continue
                pname = players_map[pid].get("name")
                if not pname:
                    continue
                for bk, bd in odd_data.get("byBookmaker", {}).items():
                    if not bd.get("available", True):
                        continue
                    b = bk.lower()
                    if b not in PREFERRED:
                        continue
                    price = bd.get("odds")
                    if price is None:
                        continue
                    try:
                        price = int(str(price).replace("+", ""))
                    except:
                        continue
                    found.add(b)
                    rows.append({
                        "event": event_name, "book": b, "player": pname,
                        "price": price, "point": 0.5, "source": "sgo"
                    })
    except Exception as e:
        st.warning(f"SGO note: {e}")
    return rows, found

def merge_odds(a, b):
    combined = a + b
    if not combined:
        return pd.DataFrame()
    df = pd.DataFrame(combined)
    df["priority"] = df["source"].map({"oddsapi": 0, "sgo": 1})
    df = df.sort_values(["player", "book", "priority"]).drop_duplicates(
        subset=["player", "book"], keep="first")
    return df.drop(columns=["priority", "source"], errors="ignore")

def run_flags(df, previous_df=None):
    if df.empty:
        return [], []

    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
    results, flagged, methods_map = [], set(), defaultdict(list)

    if "price_history" not in st.session_state:
        st.session_state["price_history"] = []
    snap = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}
    st.session_state["price_history"].append(snap)
    st.session_state["price_history"] = st.session_state["price_history"][-8:]

    stayed = defaultdict(int)
    hist = st.session_state["price_history"]
    if len(hist) >= 2:
        for i in range(1, len(hist)):
            for key in hist[i]:
                if key in hist[i-1] and hist[i-1][key] == hist[i][key]:
                    stayed[key[0]] += 1

    # DK 10
    for _, row in df.iterrows():
        if row["book"] == "draftkings" and last_two(row["price"]) == 10:
            results.append({"type": "dk", "label": row["player"],
                "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                "event": row["event"], "css": "dk", "methods": ["DK 10"]})
            flagged.add(row["player"])
            methods_map[row["player"]].append("DK 10")

    # MGM
    mgm = df[df["book"].str.contains("betmgm|mgm", case=False, na=False)]
    if "mgm_history" not in st.session_state:
        st.session_state["mgm_history"] = []
    current = []
    for event, g in mgm.groupby("event"):
        ends = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in (0, 25, 50, 75):
                ends[d].append(r["player"])
        for d, ps in ends.items():
            if len(set(ps)) >= 2:
                current.append({"event": event, "ending": d, "players": frozenset(ps)})
    st.session_state["mgm_history"].append(current)
    st.session_state["mgm_history"] = st.session_state["mgm_history"][-8:]

    mgm_stayed, survivor = defaultdict(int), set()
    h = st.session_state["mgm_history"]
    if len(h) >= 2:
        for snap in h:
            seen = set()
            for g in snap:
                seen.update(g["players"])
            for p in seen:
                mgm_stayed[p] += 1
        early = set()
        for g in h[0]:
            if len(g["players"]) >= 3:
                early.update(g["players"])
        late = set()
        for g in h[-1]:
            late.update(g["players"])
        survivor = early & late

    for event, g in mgm.groupby("event"):
        ends = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in (0, 25, 50, 75):
                ends[d].append(r["player"])
        for d, ps in ends.items():
            names = sorted(set(ps))
            if len(names) < 2:
                continue
            meth, extra = [f"MGM {d:02d}"], []
            for n in names:
                c = mgm_stayed.get(n, 0)
                if c >= 3:
                    meth.append(f"Stayed {c} times")
                    extra.append(f"Stayed {c} times")
                elif c >= 2:
                    meth.append("Stayed in the group")
                    extra.append("Stayed in the group")
                if n in survivor:
                    meth.append("Last one left")
                    extra.append("Last one left")
            reason = f"MGM {'pair' if len(names)==2 else 'group of '+str(len(names))} ends in {d:02d}"
            if extra:
                reason += " • " + " + ".join(set(extra))
            results.append({"type": "mgm", "label": " + ".join(names),
                "reason": reason, "event": event, "css": "mgm", "methods": list(set(meth))})
            for n in names:
                flagged.add(n)
                methods_map[n].extend(meth)

    # Exact
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        prices = g["price"].dropna().tolist()
        if len(set(prices)) == 1:
            results.append({"type": "match", "label": player,
                "reason": f"Exact match {format_odds(prices[0])} → {', '.join(g['book'])}",
                "event": g["event"].iloc[0], "css": "match", "methods": ["Exact Match"]})
            flagged.add(player)
            methods_map[player].append("Exact Match")

    # MGM Exact
    for event, g in mgm.groupby("event"):
        for price, pg in g.groupby("price"):
            names = sorted(pg["player"].unique())
            if len(names) >= 2:
                results.append({"type": "mgm_exact", "label": " + ".join(names),
                    "reason": f"MGM Exact {format_odds(price)} ({len(names)} players)",
                    "event": event, "css": "mgm", "methods": ["MGM Exact"]})
                for n in names:
                    flagged.add(n)
                    methods_map[n].append("MGM Exact")

    # Digits
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        digs = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in (25, 50, 75):
                digs[d].append(r["book"])
        for d, bks in digs.items():
            if len(set(bks)) >= 2:
                results.append({"type": "digit", "label": player,
                    "reason": f"Matching {d}s → {', '.join(set(bks))}",
                    "event": g["event"].iloc[0], "css": "digit", "methods": [f"Match {d}"]})
                flagged.add(player)
                methods_map[player].append(f"Match {d}")

    # FanDuel
    for _, row in df.iterrows():
        if row["book"] == "fanduel":
            price = abs(int(row["price"])) if row["price"] else 0
            last = last_two(row["price"])
            if price >= 500 and last in (10, 30, 60, 70, 90):
                results.append({"type": "fd", "label": row["player"],
                    "reason": f"FanDuel ≥ +500 ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"], "css": "fd", "methods": ["FD Pattern"]})
                flagged.add(row["player"])
                methods_map[row["player"]].append("FD Pattern")

    # Stayed
    for p, c in stayed.items():
        if c >= 2:
            lab = f"Stayed {c} times" if c >= 3 else "Stayed the same"
            results.append({"type": "signal", "label": p,
                "reason": "Price stayed the same across fetches",
                "event": "", "css": "signal", "methods": [lab]})
            flagged.add(p)
            methods_map[p].append(lab)

    # Line signals
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 3:
            continue
        if len(set(prices)) == 1:
            results.append({"type": "signal", "label": player,
                "reason": f"Same price on {len(prices)} books",
                "event": g["event"].iloc[0], "css": "signal", "methods": ["Same on 3+ books"]})
            flagged.add(player)
            methods_map[player].append("Same on 3+ books")
        try:
            med = statistics.median(prices)
            for i, pr in enumerate(prices):
                if abs(pr - med) >= 150:
                    results.append({"type": "signal", "label": player,
                        "reason": f"One book is way different ({books[i]})",
                        "event": g["event"].iloc[0], "css": "signal", "methods": ["Way different"]})
                    flagged.add(player)
                    methods_map[player].append("Way different")
        except:
            pass

    # Movement
    if previous_df is not None and not previous_df.empty:
        prev = {(r["player"], r["book"]): r["price"] for _, r in previous_df.iterrows()}
        for _, row in df.iterrows():
            key = (row["player"], row["book"])
            if key in prev and prev[key] != row["price"]:
                direction = "went up" if row["price"] > prev[key] else "went down"
                results.append({"type": "hist", "label": row["player"],
                    "reason": f"{row['book']}: {format_odds(prev[key])} → {format_odds(row['price'])} ({direction})",
                    "event": row["event"], "css": "hist", "methods": ["Price moved"]})
                flagged.add(row["player"])
                methods_map[row["player"]].append("Price moved")

    # +EV — STRICT: 2+ methods AND edge ≥ 60
    ev_board = []
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 2:
            continue
        best = max(prices)
        best_book = books[prices.index(best)]
        try:
            med = statistics.median(prices)
        except:
            med = best
        edge = best - med
        meths = list(set(methods_map.get(player, [])))
        method_count = len(meths)

        is_bet = (method_count >= METHODS_MIN) and (edge >= EDGE_MIN)

        conf, bars, level, css = get_confidence(meths, edge, is_bet)
        pri = 0
        if "Last one left" in meths: pri += 30
        if any("Stayed" in m and "times" in m for m in meths): pri += 20
        if "Stayed in the group" in meths: pri += 10
        if "Same on 3+ books" in meths: pri += 8
        pri += method_count * 5 + min(edge / 10, 15)

        if is_bet:
            why = f"{method_count} methods hit + price is clearly better. This is the one."
        elif method_count >= METHODS_MIN:
            why = f"{method_count} methods hit, but the price isn’t better enough yet."
        elif edge >= EDGE_MIN:
            why = "Price looks better, but we need at least 2 methods."
        else:
            why = "Not enough methods and not enough edge."

        if method_count >= 1 or edge >= EDGE_MIN:
            ev_board.append({
                "player": player, "best_price": best, "best_book": best_book,
                "median": med, "edge": edge, "is_bet": is_bet, "why": why,
                "methods": meths, "priority": pri, "bars": bars,
                "level": level, "css": css, "method_count": method_count
            })

    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["priority"]))

    # Name patterns
    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])
    players = list(df["player"].dropna().unique())

    def diff_team(a, b):
        return len(pev[a] & pev[b]) == 0

    def both(a, b):
        return a in flagged and b in flagged

    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if both(a, b):
                    tag = "same team" if not diff_team(a, b) else "different teams"
                    results.append({"type": "same_init", "label": f"{a} + {b}",
                        "reason": f"Same initials {k} ({tag})", "event": "", "css": "name", "methods": ["Same Init"]})

    for i, a in enumerate(players):
        _, l1 = get_initials(a)
        if not l1:
            continue
        for b in players[i+1:]:
            f2, _ = get_initials(b)
            if f2 and l1 == f2 and both(a, b):
                tag = "same team" if not diff_team(a, b) else "different teams"
                results.append({"type": "cross", "label": f"{a} + {b}",
                    "reason": f"Cross initials ({l1}) ({tag})", "event": "", "css": "name", "methods": ["Cross Init"]})

    last_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if len(parts) >= 2:
            last_map[parts[-1].lower()].append(p)
    for last, names in last_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if both(a, b):
                    tag = "same team" if not diff_team(a, b) else "different teams"
                    results.append({"type": "last", "label": f"{a} + {b}",
                        "reason": f"Same last name ({last.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same Last"]})

    first_map = defaultdict(list)
    for p in players:
        parts = str(p).split()
        if parts:
            first_map[parts[0].lower()].append(p)
    for first, names in first_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if both(a, b):
                    tag = "same team" if not diff_team(a, b) else "different teams"
                    results.append({"type": "first", "label": f"{a} + {b}",
                        "reason": f"Same first name ({first.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same First"]})

    return results, ev_board

def main():
    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch • HBIC • Me & My Girls We Rolling</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="how-to">
        <b>The rule:</b> We only say <b>BET THIS</b> when <b>2 or more methods</b> hit <b>and</b> the price is clearly better (edge ≥ 60).<br>
        <b>Books:</b> FanDuel • DraftKings • BetMGM • Hard Rock • Caesars
    </div>
    """, unsafe_allow_html=True)

    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add your The Odds API key.")
        st.stop()

    if st.button("① Load Games", type="primary"):
        st.session_state["events"] = fetch_events_oddsapi(odds_key)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** to start.")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    chosen = st.multiselect("② Select games", list(options.keys()))

    if st.button("③ Fetch Odds", type="primary") and chosen:
        all_rows, all_found = [], set()
        progress = st.progress(0)
        for i, label in enumerate(chosen):
            data = fetch_odds_oddsapi(odds_key, options[label])
            rows, found = flatten_oddsapi(data)
            all_rows.extend(rows)
            all_found.update(found)
            progress.progress((i+1)/(len(chosen)+1))
        with st.spinner("Pulling Sports Game Odds backup…"):
            sgo_rows, sgo_found = fetch_sgo_hr_props(sgo_key)
            all_rows.extend(sgo_rows)
            all_found.update(sgo_found)
        progress.progress(1.0)

        if all_rows:
            df = merge_odds(
                [r for r in all_rows if r.get("source") == "oddsapi"],
                [r for r in all_rows if r.get("source") == "sgo"]
            )
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["found_books"] = sorted(all_found & PREFERRED)
            st.session_state["last_fetch_time"] = datetime.now().strftime("%I:%M %p")
            st.success(f"Loaded {len(df)} props • {st.session_state['last_fetch_time']}")
        else:
            st.warning("No odds returned.")

    found = st.session_state.get("found_books", [])
    if found:
        missing = [CORE_BOOKS[b] for b in CORE_BOOKS if b not in found]
        st.markdown(f'<div class="info-box"><b>Books in use:</b> {", ".join(found)}</div>', unsafe_allow_html=True)
        if missing:
            st.markdown(f'''
            <div class="warning-box">
                ⚠️ <b>Still missing:</b> {", ".join(missing)}<br>
                MGM usually drops later (often morning). Methods that need it will light up when it appears.
            </div>''', unsafe_allow_html=True)

    odds = st.session_state.get("odds", [])
    prev = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(prev) if prev else None
    results, ev_board = run_flags(df, prev_df) if not df.empty else ([], [])

    tabs = st.tabs([
        "🐝 +EV Board", "🎯 DK 10s", "🎰 MGM", "🤝 Exact", "⭐ MGM Exact",
        "🔢 Digits", "💙 FanDuel", "📈 Signals", "⏳ Movement",
        "💅 Initials", "🔄 Cross", "👩‍👧 Last Name", "👯 First Name", "📖 Glossary"
    ])

    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 I Cracked The Code — Boss Bitch Picks</div>', unsafe_allow_html=True)
        st.write("**Green = 2+ methods + real edge.** Everything else is skip.")
        if not ev_board:
            st.info("Fetch some games first.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(ev_board):
                with cols[idx % 2]:
                    tags = "".join(f'<span class="tag tag-green">{m}</span>' for m in item["methods"][:5]) or '<span class="tag">No methods</span>'
                    meter = make_meter(item["bars"], item["level"])
                    cls = "bet" if item["is_bet"] else "skip"
                    label = "🟢 BET THIS" if item["is_bet"] else "⚪ SKIP"
                    st.markdown(f'''
                    <div class="card {cls} grid-card {item["css"]}">
                        <b>{label}</b> — <b>{item["player"]}</b><br>{meter}
                        Best: {format_odds(item["best_price"])} on {item["best_book"]}<br>
                        Most books: {format_odds(item["median"])}<br>
                        Methods: {item.get("method_count", 0)}<br>
                        {tags}<br><small>{item["why"]}</small>
                    </div>''', unsafe_allow_html=True)

    def show(tab, typ, banner, explain):
        with tab:
            st.markdown(f'<div class="queen-banner">{banner}</div>', unsafe_allow_html=True)
            st.caption(explain)
            items = [r for r in results if r["type"] == typ]
            if not items:
                st.info("None right now.")
                return
            cols = st.columns(2)
            for idx, r in enumerate(items):
                with cols[idx % 2]:
                    tags = "".join(f'<span class="tag">{m}</span>' for m in r.get("methods", []))
                    st.markdown(f'''
                    <div class="card {r["css"]} grid-card">
                        <b>{r["label"]}</b><br>{r["reason"]}<br>{tags}
                        <br><small>{r.get("event","")}</small>
                    </div>''', unsafe_allow_html=True)

    show(tabs[1], "dk", "🎯 DraftKings 10s — I See You", "DK prices ending in 10.")
    show(tabs[2], "mgm", "🎰 BetMGM Magic — Same Team Only", "Pairs & groups. Look for Stayed in the group / Last one left. Usually posts in the morning.")
    show(tabs[3], "match", "🤝 Exact Match — Books Agree", "Same exact price across books.")
    show(tabs[4], "mgm_exact", "⭐ MGM Exact — Locked In", "Same exact price on BetMGM for multiple guys.")
    show(tabs[5], "digit", "🔢 Matching Digits — 25 / 50 / 75", "Same player showing those endings on different books.")
    show(tabs[6], "fd", "💙 FanDuel Patterns — High Heat", "FanDuel ≥ +500 ending in 10 / 30 / 60 / 70 / 90.")
    show(tabs[7], "signal", "📈 Signals — Something’s Up", "Stayed the same • Same on 3+ books • Way different.")
    show(tabs[8], "hist", "⏳ Price Movement — Watch The Line", "Price moved since the last pull.")
    show(tabs[9], "same_init", "💅 Same Initials — Name Magic", "Same first + last initial (only when a method already hit).")
    show(tabs[10], "cross", "🔄 Cross Initials — Connected", "One player’s last initial matches another’s first.")
    show(tabs[11], "last", "👩‍👧 Same Last Name — Family Ties", "Shared last name.")
    show(tabs[12], "first", "👯 Same First Name — Twinsies", "Shared first name.")

    with tabs[13]:
        st.markdown('<div class="queen-banner">📖 The Code — What Everything Means</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="gloss-card">
            <b>🟢 BET THIS</b><br>
            Needs <b>2 or more methods</b> <b>and</b> the price is clearly better than most books (edge of 60 or more).<br>
            These are the only ones we actually take. Everything else is noise.
        </div>

        <div class="gloss-card">
            <b>⚪ SKIP</b><br>
            Less than 2 methods, or the price isn’t better enough yet.<br>
            We pass. No forcing it.
        </div>

        <div class="gloss-card">
            <b>🎯 DraftKings Ends in 10</b><br>
            Any DraftKings home-run price that ends in 10 (like +110, +210, +310, +410, +510).<br>
            This is one of our strongest book-specific tells.
        </div>

        <div class="gloss-card">
            <b>🎰 BetMGM Classic Endings (00 / 25 / 50 / 75)</b><br>
            BetMGM loves these endings. We look for:<br>
            • <b>Pairs</b> — two players on the same team with the same ending<br>
            • <b>Groups of three</b> — three players on the same team with the same ending<br>
            Pairs always beat groups. Same team only.
        </div>

        <div class="gloss-card">
            <b>Stayed in the group</b><br>
            This player is still inside the same BetMGM pair or group after multiple pulls.<br>
            The book is keeping him there on purpose.
        </div>

        <div class="gloss-card">
            <b>Stayed 3 times</b><br>
            Showed up in that same spot on three different fetches.<br>
            Even stronger. The books keep locking him in.
        </div>

        <div class="gloss-card">
            <b>Last one left</b><br>
            Started in a bigger MGM group and is the only one still standing.<br>
            This is one of the strongest signals we track.
        </div>

        <div class="gloss-card">
            <b>🤝 Exact Match</b><br>
            Two or more books have the exact same price on the same player.<br>
            When books agree that hard, we pay attention.
        </div>

        <div class="gloss-card">
            <b>⭐ MGM Exact</b><br>
            Multiple players on BetMGM have the exact same price.<br>
            Same-team only. Strong grouping signal.
        </div>

        <div class="gloss-card">
            <b>🔢 Matching Digits (25 / 50 / 75)</b><br>
            The same player shows a 25, 50, or 75 ending on more than one book.<br>
            Different books using the same “template” number.
        </div>

        <div class="gloss-card">
            <b>💙 FanDuel Patterns</b><br>
            FanDuel prices that are +500 or higher and end in 10, 30, 60, 70, or 90.<br>
            These long-shot patterns are ones we watch closely.
        </div>

        <div class="gloss-card">
            <b>📈 Signals</b><br>
            • <b>Stayed the same</b> — price didn’t move across pulls<br>
            • <b>Same on 3+ books</b> — three or more books have the identical price<br>
            • <b>Way different</b> — one book is an outlier (150+ away from the middle)
        </div>

        <div class="gloss-card">
            <b>⏳ Price Movement</b><br>
            The line moved up or down since the last time we pulled.<br>
            Direction matters. We note both.
        </div>

        <div class="gloss-card">
            <b>💅 Same Initials</b><br>
            Two players share the same first letter and same last letter (example: Marcus Morris & Matt McLain = MM).<br>
            Only counts when other methods already hit. Prefer different teams.
        </div>

        <div class="gloss-card">
            <b>🔄 Cross Initials</b><br>
            One player’s last initial matches the other player’s first initial.<br>
            Only counts when other methods already hit. Prefer different teams.
        </div>

        <div class="gloss-card">
            <b>👩‍👧 Same Last Name</b><br>
            Two players share the exact same last name.<br>
            Only counts when other methods already hit.
        </div>

        <div class="gloss-card">
            <b>👯 Same First Name</b><br>
            Two players share the exact same first name.<br>
            Only counts when other methods already hit.
        </div>

        <div class="gloss-card">
            <b>Confidence Meter</b><br>
            The little bars under each card.<br>
            More filled bars = stronger mix of methods + edge.<br>
            Levels: High / Strong / Medium / Low.
        </div>

        <div class="gloss-card">
            <b>Edge</b><br>
            How much better the best price is compared to the middle of the books.<br>
            We require edge of 60 or higher before we will say BET THIS.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="footer">👑 Girl Magic • Boss Bitch • HBIC • Me & My Girls We Rolling</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
