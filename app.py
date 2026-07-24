"""
Girl Magic Odds ✨
Boss Bitch • HBIC • Me & My Girls We Rolling
ONLY 0.5 (1 HR) lines — no 2+/3+
"""

import streamlit as st
import pandas as pd
import requests
from collections import defaultdict
import statistics
from datetime import datetime, timezone, timedelta

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
        background: linear-gradient(165deg, #0a0410 0%, #160a22 40%, #1f0b30 100%);
        color: #fce7f3;
        font-family: 'Inter', sans-serif;
    }

    h1 {
        font-family: 'Playfair Display', serif !important;
        font-weight: 900 !important;
        background: linear-gradient(90deg, #f9a8d4, #e879f9, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.6rem !important;
        margin-bottom: 2px !important;
        letter-spacing: -0.5px;
    }

    .subtitle {
        color: #f9a8d4;
        font-size: 0.92rem;
        font-weight: 600;
        letter-spacing: 1.6px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .tagline {
        color: #e9d5ff;
        font-size: 0.88rem;
        font-style: italic;
        margin-bottom: 16px;
        opacity: 0.95;
    }

    .how-to {
        background: linear-gradient(135deg, #1a0f28 0%, #2a1040 100%);
        border: 1px solid #f472b6;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 16px;
        font-size: 0.88rem;
        line-height: 1.5;
        box-shadow: 0 0 18px rgba(244, 114, 182, 0.12);
        position: relative;
        overflow: hidden;
    }
    .how-to::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 4px; height: 100%;
        background: linear-gradient(180deg, #f472b6, #c084fc);
    }
    .how-to b { color: #f9a8d4; }

    .warning-box {
        background: #3b0764;
        border: 2px solid #f472b6;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 14px;
        font-size: 0.95rem;
    }

    .info-box {
        background: #1a0f28;
        border: 1px solid #a855f7;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 12px;
        font-size: 0.9rem;
    }

    .stButton > button {
        background: linear-gradient(90deg, #db2777, #9333ea) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.55rem 1.3rem !important;
        box-shadow: 0 3px 14px rgba(219, 39, 119, 0.45);
    }

    .petty-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }
    .petty-box {
        flex: 1;
        min-width: 100px;
        background: #1a0f28;
        border: 1px solid #f472b6;
        border-radius: 12px;
        padding: 12px 8px;
        text-align: center;
        box-shadow: 0 0 12px rgba(244, 114, 182, 0.15);
    }
    .petty-num {
        font-size: 1.55rem;
        font-weight: 800;
        color: #f9a8d4;
        line-height: 1.1;
    }
    .petty-label {
        font-size: 0.68rem;
        color: #e9d5ff;
        margin-top: 4px;
        letter-spacing: 0.4px;
    }

    .card {
        background: linear-gradient(155deg, #1a0f28, #251438);
        border: 1px solid #f472b6;
        border-radius: 12px;
        padding: 9px 12px;
        margin: 0;
        color: #fdf2f8;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        position: relative;
        height: 100%;
        font-size: 0.93rem;
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
        background: linear-gradient(155deg, #0c2418, #143d28) !important;
        border: 1px solid #34d399 !important;
        box-shadow: 0 0 16px rgba(52, 211, 153, 0.28);
    }
    .skip {
        background: #14101c !important;
        border: 1px solid #4b5563 !important;
        opacity: 0.78;
    }

    .tag {
        display: inline-block;
        background: #3b0764;
        color: #f9a8d4;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 10px;
        margin: 2px 3px 2px 0;
        border: 1px solid #a855f7;
    }
    .tag-green { background: #064e3b; color: #6ee7b7; border-color: #34d399; }

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

    .meter { display: flex; gap: 3px; margin: 4px 0 6px 0; }
    .meter-bar {
        height: 6px; width: 18px; border-radius: 3px; background: #374151;
    }
    .meter-bar.filled-high { background: linear-gradient(90deg, #f472b6, #c026d3); }
    .meter-bar.filled-strong { background: linear-gradient(90deg, #e879f9, #a855f7); }
    .meter-bar.filled-medium { background: linear-gradient(90deg, #c084fc, #7c3aed); }
    .meter-bar.filled-low { background: #6b7280; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        background: #1a0f28;
        border-radius: 8px;
        color: #f9a8d4;
        font-weight: 600;
        padding: 7px 10px;
        font-size: 0.82rem;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #db2777, #9333ea) !important;
        color: white !important;
    }

    .footer {
        text-align: center;
        color: #f9a8d4;
        font-size: 0.95rem;
        margin-top: 36px;
        letter-spacing: 1.1px;
        opacity: 0.9;
        padding-bottom: 20px;
    }
    .grid-card { margin-bottom: 7px; }

    .gloss-card {
        background: linear-gradient(155deg, #1a0f28, #251438);
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
    "hardrockbet", "caesars"
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

def clean_name(name):
    name = str(name).strip()
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
    parts = name.split()
    if parts and parts[-1].lower().rstrip(".") in suffixes:
        parts = parts[:-1]
    return " ".join(parts)

def get_initials(name):
    name = clean_name(name)
    parts = name.split()
    if len(parts) < 2:
        return None, None
    return parts[0][0].upper(), parts[-1][0].upper()

def now_az():
    az = timezone(timedelta(hours=-7))
    return datetime.now(az).strftime("%I:%M %p")

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
                pt = o.get("point")
                if pt is None or abs(float(pt) - 0.5) > 0.01:
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
                if ou is None or abs(float(ou) - 0.5) > 0.01:
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

    if "presence_history" not in st.session_state:
        st.session_state["presence_history"] = []
    current_presence = set()
    for _, r in df.iterrows():
        current_presence.add((r["player"], r["book"]))
    st.session_state["presence_history"].append(current_presence)
    st.session_state["presence_history"] = st.session_state["presence_history"][-12:]

    hist = st.session_state["presence_history"]
    if len(hist) >= 2:
        early = set()
        for snap in hist[:max(1, len(hist)//3)]:
            early |= snap
        latest = hist[-1]
        previous = hist[-2] if len(hist) >= 2 else set()

        for player, book in latest - previous:
            results.append({
                "type": "late", "label": player,
                "reason": f"Just appeared on {book}",
                "event": "", "css": "hist", "methods": ["Just Appeared"]
            })
            flagged.add(player)
            methods_map[player].append("Just Appeared")

        for player, book in latest - early:
            if (player, book) in previous:
                continue
            results.append({
                "type": "late", "label": player,
                "reason": f"Added late on {book} (was missing earlier today)",
                "event": "", "css": "hist", "methods": ["Added Late"]
            })
            flagged.add(player)
            methods_map[player].append("Added Late")

        for player, book in previous - latest:
            results.append({
                "type": "late", "label": player,
                "reason": f"Gone missing from {book}",
                "event": "", "css": "hist", "methods": ["Gone Missing"]
            })
            flagged.add(player)
            methods_map[player].append("Gone Missing")

    if "price_history" not in st.session_state:
        st.session_state["price_history"] = []
    snap = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}
    st.session_state["price_history"].append(snap)
    st.session_state["price_history"] = st.session_state["price_history"][-8:]

    stayed = defaultdict(int)
    phist = st.session_state["price_history"]
    if len(phist) >= 2:
        for i in range(1, len(phist)):
            for key in phist[i]:
                if key in phist[i-1] and phist[i-1][key] == phist[i][key]:
                    stayed[key[0]] += 1

    for _, row in df.iterrows():
        if row["book"] == "draftkings" and last_two(row["price"]) == 10:
            results.append({"type": "dk", "label": row["player"],
                "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                "event": row["event"], "css": "dk", "methods": ["DK 10"]})
            flagged.add(row["player"])
            methods_map[row["player"]].append("DK 10")

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

    for _, row in df.iterrows():
        if row["book"] == "fanduel":
            price = abs(int(row["price"])) if row["price"] else 0
            last = last_two(row["price"])
            if price >= 400 and last in (10, 20, 30, 60, 70, 90):
                results.append({"type": "fd", "label": row["player"],
                    "reason": f"FanDuel ≥ +400 ends in {last:02d} → {format_odds(row['price'])}",
                    "event": row["event"], "css": "fd", "methods": ["FD Pattern"]})
                flagged.add(row["player"])
                methods_map[row["player"]].append("FD Pattern")

    for p, c in stayed.items():
        if c >= 2:
            lab = f"Stayed {c} times" if c >= 3 else "Stayed the same"
            results.append({"type": "signal", "label": p,
                "reason": "Price stayed the same across fetches",
                "event": "", "css": "signal", "methods": [lab]})
            flagged.add(p)
            methods_map[p].append(lab)

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
        if method_count < 1:
            continue
        is_bet = (method_count >= METHODS_MIN) and (edge >= EDGE_MIN)
        conf, bars, level, css = get_confidence(meths, edge, is_bet)
        pri = 0
        if "Last one left" in meths: pri += 30
        if any("Stayed" in m and "times" in m for m in meths): pri += 20
        if "Stayed in the group" in meths: pri += 10
        if "Same on 3+ books" in meths: pri += 8
        if "Just Appeared" in meths or "Added Late" in meths: pri += 6
        pri += method_count * 5 + min(edge / 10, 15)
        if is_bet:
            why = f"{method_count} methods hit + price is clearly better. This is the one."
        elif method_count >= METHODS_MIN:
            why = f"{method_count} methods hit, but the price isn’t better enough yet."
        else:
            why = "Has a method, but needs at least 2 methods + real edge to bet."
        ev_board.append({
            "player": player, "best_price": best, "best_book": best_book,
            "median": med, "edge": edge, "is_bet": is_bet, "why": why,
            "methods": meths, "priority": pri, "bars": bars,
            "level": level, "css": css, "method_count": method_count
        })
    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["priority"]))

    CORE_METHODS = {
        "DK 10", "FD Pattern", "Exact Match", "MGM Exact",
        "Match 25", "Match 50", "Match 75",
        "Last one left", "Stayed in the group"
    }
    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])
    strong = set()
    for p, ms in methods_map.items():
        core_hits = [m for m in set(ms) if m in CORE_METHODS or m.startswith("MGM ") or m.startswith("Match ") or m.startswith("Stayed 3")]
        if len(core_hits) >= 2:
            strong.add(p)
    players = list(strong)

    def diff_team(a, b):
        return len(pev[a] & pev[b]) == 0

    init_map = defaultdict(list)
    for p in players:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    for k, names in init_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                tag = "same team" if not diff_team(a, b) else "different teams"
                results.append({"type": "same_init", "label": f"{a} + {b}",
                    "reason": f"Same initials {k} ({tag})", "event": "", "css": "name", "methods": ["Same Init"]})

    for i, a in enumerate(players):
        _, l1 = get_initials(a)
        if not l1: continue
        for b in players[i+1:]:
            f2, _ = get_initials(b)
            if f2 and l1 == f2:
                tag = "same team" if not diff_team(a, b) else "different teams"
                results.append({"type": "cross", "label": f"{a} + {b}",
                    "reason": f"Cross initials ({l1}) ({tag})", "event": "", "css": "name", "methods": ["Cross Init"]})

    last_map = defaultdict(list)
    for p in players:
        parts = clean_name(p).split()
        if len(parts) >= 2:
            last_map[parts[-1].lower()].append(p)
    for last, names in last_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                tag = "same team" if not diff_team(a, b) else "different teams"
                results.append({"type": "last", "label": f"{a} + {b}",
                    "reason": f"Same last name ({last.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same Last"]})

    first_map = defaultdict(list)
    for p in players:
        parts = clean_name(p).split()
        if parts:
            first_map[parts[0].lower()].append(p)
    for first, names in first_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                tag = "same team" if not diff_team(a, b) else "different teams"
                results.append({"type": "first", "label": f"{a} + {b}",
                    "reason": f"Same first name ({first.title()}) ({tag})", "event": "", "css": "name", "methods": ["Same First"]})

    return results, ev_board

def main():
    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch • HBIC • Me & My Girls We Rolling</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Where odds intuition meets Girl Magic.</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="how-to">
        👑 <b>The Code</b> → BET THIS only when <b>2+ methods</b> hit <b>and</b> edge ≥ 60<br>
        🎯 <b>Market</b> → Over 0.5 HR only (1 homer) — no 2+ / 3+ lines<br>
        💜 <b>Books</b> → FanDuel • DraftKings • BetMGM • Hard Rock • Caesars
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
            st.session_state["last_fetch_time"] = now_az()
            st.success(f"Loaded {len(df)} props (0.5 HR only) • {st.session_state['last_fetch_time']} AZ")
        else:
            st.warning("No 0.5 HR odds returned.")

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

    counts = {
        "dk": len([r for r in results if r["type"] == "dk"]),
        "mgm": len([r for r in results if r["type"] == "mgm"]),
        "match": len([r for r in results if r["type"] == "match"]),
        "fd": len([r for r in results if r["type"] == "fd"]),
        "name": len([r for r in results if r["type"] in ("same_init", "cross", "last", "first")]),
        "late": len([r for r in results if r["type"] == "late"]),
        "bets": len([e for e in ev_board if e["is_bet"]])
    }

    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box">
            <div class="petty-num">{counts['bets']}</div>
            <div class="petty-label">🟢 BET THIS</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['dk']}</div>
            <div class="petty-label">🎯 DK 10s</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['mgm']}</div>
            <div class="petty-label">🎰 MGM Groups</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['match']}</div>
            <div class="petty-label">🤝 Exact Matches</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['fd']}</div>
            <div class="petty-label">💙 FD Patterns</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['name']}</div>
            <div class="petty-label">💅 Name Magic</div>
        </div>
        <div class="petty-box">
            <div class="petty-num">{counts['late']}</div>
            <div class="petty-label">👻 Late Adds</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "🐝 +EV Board", "🎯 DK 10s", "🎰 MGM", "🤝 Exact", "⭐ MGM Exact",
        "🔢 Digits", "💙 FanDuel", "📈 Signals", "⏳ Movement",
        "👻 Late Adds", "💅 Initials", "🔄 Cross", "👩‍👧 Last Name", "👯 First Name", "📖 Glossary"
    ])

    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 We Cracked The Code — Boss Bitch Picks</div>', unsafe_allow_html=True)
        st.write("**Green = 2+ methods + real edge.** Only 0.5 HR (1 homer) lines. Only players with methods appear.")
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
    show(tabs[2], "mgm", "🎰 BetMGM Magic — Same Team Only", "Pairs & groups. Look for Stayed in the group / Last one left.")
    show(tabs[3], "match", "🤝 Exact Match — Books Agree", "Same exact price across books.")
    show(tabs[4], "mgm_exact", "⭐ MGM Exact — Locked In", "Same exact price on BetMGM for multiple guys.")
    show(tabs[5], "digit", "🔢 Matching Digits — 25 / 50 / 75", "Same player showing those endings on different books.")
    show(tabs[6], "fd", "💙 FanDuel Patterns — High Heat", "FanDuel ≥ +400 ending in 10 / 20 / 30 / 60 / 70 / 90.")
    show(tabs[7], "signal", "📈 Signals — Something’s Up", "Stayed the same • Same on 3+ books • Way different.")
    show(tabs[8], "hist", "⏳ Price Movement — Watch The Line", "Price moved since the last pull.")
    show(tabs[9], "late", "👻 Late Adds / Missing — Watch Who Shows Up",
         "Just Appeared = new on a book this pull. Added Late = missing earlier, now here. Gone Missing = was there, now gone.")
    show(tabs[10], "same_init", "💅 Same Initials — Name Magic", "Only when both already have 2+ real book methods. Jr. is ignored.")
    show(tabs[11], "cross", "🔄 Cross Initials — Connected", "Only when both already have 2+ real book methods. Jr. is ignored.")
    show(tabs[12], "last", "👩‍👧 Same Last Name — Family Ties", "Only when both already have 2+ real book methods. Jr. is ignored.")
    show(tabs[13], "first", "👯 Same First Name — Twinsies", "Only when both already have 2+ real book methods.")

    with tabs[14]:
        st.markdown('<div class="queen-banner">📖 The Code — What Everything Means</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="gloss-card">
            <b>🟢 BET THIS</b><br>
            At least <b>2 different methods</b> hit <b>and</b> the best price is clearly better than the rest of the books (edge of 60 or more).<br>
            These are the only ones we actually take. Everything else is noise. Only 0.5 HR (1 homer) lines.
        </div>
        <div class="gloss-card">
            <b>⚪ SKIP</b><br>
            Has one or more methods, but not enough of them — or the price isn’t better enough yet.<br>
            We pass. No forcing it.
        </div>
        <div class="gloss-card">
            <b>🎯 DK 10</b><br>
            DraftKings price ends in 10 (example: +110, +210, +310, +410, +510).<br>
            One of our strongest single-book tells. No team requirement.
        </div>
        <div class="gloss-card">
            <b>🎰 MGM 00 / 25 / 50 / 75</b><br>
            BetMGM prices ending in 00, 25, 50, or 75 on the <b>same team</b>.<br>
            We look for pairs first (2 players), then groups of three if no pair exists.
        </div>
        <div class="gloss-card">
            <b>Stayed in the group</b><br>
            This player is still inside the same BetMGM pair or group after multiple pulls.<br>
            The book keeps putting them there on purpose.
        </div>
        <div class="gloss-card">
            <b>Stayed 3 times / Stayed 4 times</b><br>
            Showed up in that same MGM spot on 3+ different fetches.<br>
            Even stronger than a one-time group.
        </div>
        <div class="gloss-card">
            <b>Last one left</b><br>
            Started in a bigger MGM group and is the only one still standing.<br>
            One of the strongest signals we track.
        </div>
        <div class="gloss-card">
            <b>⭐ MGM Exact</b><br>
            Two or more players on BetMGM have the <b>exact same price</b> (same team).<br>
            Different from the classic endings — this is the full number matching.
        </div>
        <div class="gloss-card">
            <b>🤝 Exact Match</b><br>
            Two or more books have the exact same price on the same player.<br>
            When books agree that hard, we pay attention.
        </div>
        <div class="gloss-card">
            <b>🔢 Match 25 / Match 50 / Match 75</b><br>
            The same player shows a 25, 50, or 75 ending on more than one book.<br>
            Different books using the same “template” number.
        </div>
        <div class="gloss-card">
            <b>💙 FD Pattern</b><br>
            FanDuel price is +400 or higher and ends in 10, 20, 30, 60, 70, or 90.<br>
            These longer-shot patterns are ones we watch closely.
        </div>
        <div class="gloss-card">
            <b>Same on 3+ books</b><br>
            Three or more books have the identical price on this player.<br>
            Strong agreement across the board.
        </div>
        <div class="gloss-card">
            <b>Way different</b><br>
            One book is an outlier — 150+ away from the middle of the other books.<br>
            Something is off on that book.
        </div>
        <div class="gloss-card">
            <b>Stayed the same</b><br>
            This player’s price did not move across multiple fetches.<br>
            The line is stuck.
        </div>
        <div class="gloss-card">
            <b>Price moved</b><br>
            The line went up or down since the last pull.<br>
            Direction matters — we note both.
        </div>
        <div class="gloss-card">
            <b>Just Appeared</b><br>
            Player is on a book right now but was not on the previous pull.<br>
            New to the board this fetch.
        </div>
        <div class="gloss-card">
            <b>Added Late</b><br>
            Was missing earlier in the day and just showed up on a book.<br>
            Late add — pay attention.
        </div>
        <div class="gloss-card">
            <b>Gone Missing</b><br>
            Was on a book earlier and disappeared on the latest pull.<br>
            Worth noting when it happens.
        </div>
        <div class="gloss-card">
            <b>💅 Same Init</b><br>
            Two players share the same first letter + same last letter (example: Marcus Morris & Matt McLain = MM).<br>
            Only counts when both already have 2+ real book methods. Prefer different teams. Jr. is ignored.
        </div>
        <div class="gloss-card">
            <b>🔄 Cross Init</b><br>
            One player’s last initial matches the other player’s first initial.<br>
            Only counts when both already have 2+ real book methods. Prefer different teams.
        </div>
        <div class="gloss-card">
            <b>👩‍👧 Same Last</b><br>
            Two players share the exact same last name.<br>
            Only counts when both already have 2+ real book methods.
        </div>
        <div class="gloss-card">
            <b>👯 Same First</b><br>
            Two players share the exact same first name.<br>
            Only counts when both already have 2+ real book methods.
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

    st.markdown('<div class="footer">👑 Girl Magic • Where intuition meets odds analytics.<br>Boss Bitch • HBIC • Me & My Girls We Rolling</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
