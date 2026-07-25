"""
Girl Magic Odds ✨
Boss Bitch · HBIC · Me & My Girls We Rolling

Tabs: Board | Odds Tricks (sub) | Name Magic (sub) | Results | Glossary
What's Going Today: book color-coded chips
Results: no raw HTML · Undo · oldest-first pages
Pregame lock · full glossary
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
import re
from collections import defaultdict, Counter
import statistics
from datetime import datetime, timezone, timedelta

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

st.set_page_config(page_title="Girl Magic Odds ✨", page_icon="👑", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background: linear-gradient(165deg, #0a0410 0%, #160a22 40%, #1f0b30 100%); color: #fce7f3; font-family: 'Inter', sans-serif; }
    h1 { font-family: 'Playfair Display', serif !important; font-weight: 900 !important; background: linear-gradient(90deg, #f9a8d4, #e879f9, #c084fc, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.6rem !important; margin-bottom: 2px !important; }
    .subtitle { color: #f9a8d4; font-size: 0.92rem; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase; margin-bottom: 4px; }
    .tagline { color: #e9d5ff; font-size: 0.88rem; font-style: italic; margin-bottom: 16px; opacity: 0.95; }
    .how-to { background: linear-gradient(135deg, #1a0f28 0%, #2a1040 100%); border: 1px solid #f472b6; border-radius: 14px; padding: 14px 18px; margin-bottom: 16px; font-size: 0.88rem; line-height: 1.5; position: relative; overflow: hidden; }
    .how-to::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: linear-gradient(180deg, #f472b6, #c084fc); }
    .how-to b { color: #f9a8d4; }
    .warning-box { background: #3b0764; border: 2px solid #f472b6; border-radius: 12px; padding: 12px 16px; margin-bottom: 14px; font-size: 0.95rem; }
    .info-box { background: #1a0f28; border: 1px solid #a855f7; border-radius: 12px; padding: 10px 14px; margin-bottom: 12px; font-size: 0.9rem; }
    .stButton > button { background: linear-gradient(90deg, #db2777, #9333ea) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; padding: 0.55rem 1.3rem !important; }
    .petty-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
    .petty-box { flex: 1; min-width: 70px; background: #1a0f28; border: 1px solid #f472b6; border-radius: 12px; padding: 10px 6px; text-align: center; }
    .petty-num { font-size: 1.35rem; font-weight: 800; color: #f9a8d4; line-height: 1.1; }
    .petty-label { font-size: 0.58rem; color: #e9d5ff; margin-top: 4px; }
    .trends-today { background: linear-gradient(135deg, #2a1040 0%, #1a0f28 50%, #3b0764 100%); border: 1px solid #c084fc; border-radius: 16px; padding: 14px 18px; margin-bottom: 18px; }
    .trends-today-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
    .trends-today-title { color: #f9a8d4; font-weight: 800; font-size: 0.95rem; }
    .trends-today-sub { color: #e9d5ff; font-size: 0.72rem; opacity: 0.9; }
    .trends-chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .trend-chip { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 7px 14px; font-size: 0.8rem; font-weight: 800; color: #fff; border: 2px solid transparent; }
    .chip-mgm { background: #422006; border-color: #f59e0b; color: #fcd34d; }
    .chip-dk { background: #064e3b; border-color: #34d399; color: #6ee7b7; }
    .chip-fd { background: #1e3a5f; border-color: #3b82f6; color: #93c5fd; }
    .chip-365 { background: #14532d; border-color: #22c55e; color: #86efac; }
    .chip-hr { background: #7f1d1d; border-color: #f87171; color: #fecaca; }
    .chip-other { background: #3b0764; border-color: #a855f7; color: #e9d5ff; }
    .chip-count { font-weight: 900; margin-left: 4px; }
    .card { background: linear-gradient(155deg, #1a0f28, #251438); border: 1px solid #f472b6; border-radius: 12px; padding: 10px 12px; margin: 0; color: #fdf2f8; position: relative; height: 100%; font-size: 0.93rem; }
    .card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; border-radius: 12px 0 0 12px; background: #f472b6; }
    .bet { background: linear-gradient(155deg, #0c2418, #143d28) !important; border: 1px solid #34d399 !important; }
    .skip { background: #14101c !important; border: 1px solid #4b5563 !important; opacity: 0.8; }
    .good-card { border-color: #34d399 !important; }
    .fade-card { border-color: #f87171 !important; opacity: 0.9; }
    .up-card { border-color: #f87171 !important; }
    .down-card { border-color: #34d399 !important; }
    .score-pill { display: inline-block; background: linear-gradient(90deg, #db2777, #9333ea); color: white; font-weight: 800; font-size: 0.95rem; padding: 2px 10px; border-radius: 12px; margin-left: 6px; }
    .tag { display: inline-block; background: #3b0764; color: #f9a8d4; font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 10px; margin: 2px 3px 2px 0; border: 1px solid #a855f7; }
    .tag-dk { background: #064e3b; color: #6ee7b7; border-color: #34d399; }
    .tag-mgm { background: #422006; color: #fcd34d; border-color: #f59e0b; }
    .tag-fd { background: #1e3a5f; color: #93c5fd; border-color: #3b82f6; }
    .tag-match { background: #4c1d95; color: #e9d5ff; border-color: #a855f7; }
    .tag-signal { background: #831843; color: #fbcfe8; border-color: #f472b6; }
    .tag-strong { background: #14532d; color: #bbf7d0; border-color: #22c55e; font-weight: 800; }
    .tag-b365 { background: #14532d; color: #86efac; border-color: #22c55e; }
    .tag-red { background: #450a0a; color: #fca5a5; border-color: #f87171; }
    .queen-banner { display: inline-block; background: linear-gradient(90deg, #db2777, #9333ea); color: white; font-size: 0.78rem; font-weight: 700; padding: 5px 14px; border-radius: 16px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; }
    .meter { display: flex; gap: 3px; margin: 4px 0 6px 0; }
    .meter-bar { height: 6px; width: 18px; border-radius: 3px; background: #374151; }
    .meter-bar.filled-high { background: linear-gradient(90deg, #f472b6, #c026d3); }
    .meter-bar.filled-strong { background: linear-gradient(90deg, #e879f9, #a855f7); }
    .meter-bar.filled-medium { background: linear-gradient(90deg, #c084fc, #7c3aed); }
    .meter-bar.filled-low { background: #6b7280; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { background: #1a0f28; border-radius: 8px; color: #f9a8d4; font-weight: 600; padding: 7px 10px; font-size: 0.8rem; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #db2777, #9333ea) !important; color: white !important; }
    .footer { text-align: center; color: #f9a8d4; font-size: 0.95rem; margin-top: 36px; opacity: 0.9; padding-bottom: 20px; }
    .grid-card { margin-bottom: 7px; }
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
REGIONS = "us,us2"
HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"

PREFERRED = {
    "fanduel", "draftkings", "betmgm", "hardrockbet", "caesars",
    "bet365", "bet365_au",
}
CORE_BOOKS = {
    "fanduel": "FanDuel", "draftkings": "DraftKings",
    "betmgm": "BetMGM", "bet365": "Bet365",
}
LATE_BOOKS = {"fanduel", "draftkings", "betmgm"}

EDGE_MIN = 60
METHODS_MIN = 2
OUTLIER_GAP = 150
REFRESH_MINUTES = 30
NAME_METHODS_MIN = 3
NAME_MAX_PAIRS = 50
BIG_MOVE = 100
MOVE_MIN = 40
FD_MIN = 500
MOVE_PRICE_MIN = 500
PENDING_PAGE = 40

PERSONAL_STRONG = {
    "DK 10", "FD Pattern", "FD 600", "Exact Match", "MGM Exact",
    "Match 25", "Match 50", "Match 75",
    "B365 850", "B365 Match 25", "B365 Match 50", "B365 Match 75",
    "B365 > HardRock", "Last one left", "Multi-book Shorten", "Same on 3+ books",
}
NOISE_METHODS = {
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup",
    "In lineup · missing books", "Multi-book Stuck", "Price moved",
    "Stayed the same", "Way different", "Shortening", "Lengthening",
    "Multi-book Lengthen",
}

def is_bet365(book):
    b = str(book).lower()
    return "bet365" in b or b == "365"

def is_hardrock(book):
    return "hardrock" in str(book).lower()

def is_core_method(m):
    if m in NOISE_METHODS: return False
    if m.startswith("Shortening (") or m.startswith("Lengthening ("): return False
    if m.startswith("Stayed ") and "times" in m and "group" not in m.lower(): return False
    if m.startswith("FADE") or m.startswith("FD under"): return False
    if m.startswith("Outlier") or m.startswith("Stuck") or m.startswith("Same ending"): return False
    return True

def count_core_methods(meths):
    return len([m for m in set(meths) if is_core_method(m)])

def has_personal_strong(meths):
    return any(m in PERSONAL_STRONG or m.startswith("Match ") or m.startswith("B365") for m in meths)

def has_dk_or_mgm(meths):
    for m in meths:
        if m == "DK 10": return True
        if m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m:
            return True
    return False

def method_tag_class(m):
    m = str(m)
    if m == "DK 10" or m.startswith("DK"): return "tag-dk"
    if m.startswith("MGM") or m == "Last one left" or m == "Stayed in the group" or "Stayed in group" in m:
        return "tag-mgm"
    if m.startswith("FD"): return "tag-fd"
    if m.startswith("B365"): return "tag-b365"
    if m in ("Exact Match", "MGM Exact") or m.startswith("Match "): return "tag-match"
    if "Multi-book Shorten" in m or m == "Same on 3+ books": return "tag-strong"
    if m.startswith("Same ending") or m.startswith("Outlier") or m.startswith("Stuck"): return "tag-signal"
    if m == "Not in lineup": return "tag-red"
    return ""

def render_method_tags(methods, limit=6):
    return "".join(f'<span class="tag {method_tag_class(m)}">{m}</span>' for m in list(methods)[:limit])

def girl_magic_score(core_count, edge, methods):
    method_pts = min(core_count, 5) * 10
    edge_pts = min(40, max(0, int((edge / 180) * 40)))
    bonus = 0
    if "Last one left" in methods: bonus += 5
    if any("Stayed in group" in m or m == "Stayed in the group" for m in methods): bonus += 3
    if "Multi-book Shorten" in methods: bonus += 3
    if "Same on 3+ books" in methods: bonus += 2
    if "FD 600" in methods: bonus += 2
    if "B365 850" in methods: bonus += 2
    if "B365 > HardRock" in methods: bonus += 2
    return min(100, method_pts + edge_pts + min(10, bonus))

def get_odds_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("The Odds API Key", type="password", key="odds_key")
    return key

def get_sgo_key():
    return st.secrets.get("SGO_API_KEY", "d5422e23cc05702bf95197f6a98ec8ce")

def format_odds(p):
    try: return f"{int(p):+d}"
    except: return str(p)

def last_two(p):
    try: return abs(int(p)) % 100
    except: return None

def book_label(b):
    b = str(b or "").lower()
    if "betmgm" in b or b == "mgm": return "MGM"
    if "draftkings" in b or b == "dk": return "DK"
    if "fanduel" in b or b == "fd": return "FD"
    if "bet365" in b or b == "365": return "365"
    if "hardrock" in b: return "HardRock"
    if "caesars" in b: return "Caesars"
    if b in ("untagged", "unknown", "—", ""): return "Untagged"
    return b.title() if b else "Untagged"

def chip_class_for_book(bl):
    bl = str(bl).upper()
    if "MGM" in bl: return "chip-mgm"
    if bl in ("DK", "DRAFTKINGS"): return "chip-dk"
    if bl in ("FD", "FANDUEL"): return "chip-fd"
    if "365" in bl: return "chip-365"
    if "HARD" in bl: return "chip-hr"
    return "chip-other"

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
    if len(parts) < 2: return None, None
    return parts[0][0].upper(), parts[-1][0].upper()

def clean_team(tid):
    if not tid: return ""
    return str(tid).replace("_MLB", "").replace("_", " ").strip()

def now_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%I:%M %p")

def today_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def smart_best(prices, books):
    if not prices: return None, None
    paired = sorted(zip(prices, books), key=lambda x: x[0], reverse=True)
    best_p, best_b = paired[0]
    if len(paired) >= 2 and best_p - paired[1][0] >= OUTLIER_GAP:
        return paired[1][0], paired[1][1]
    return best_p, best_b

def get_confidence(score, is_bet):
    if not is_bet: return "Skip", 1, "low"
    if score >= 85: return "High", 5, "high"
    if score >= 70: return "Strong", 4, "strong"
    if score >= 55: return "Medium", 3, "medium"
    return "Low", 2, "low"

def make_meter(bars, level):
    html = '<div class="meter">'
    for i in range(5):
        filled = f"filled-{level}" if i < bars else ""
        html += f'<div class="meter-bar {filled}"></div>'
    return html + '</div>'

def event_matches_chosen(ev, chosen):
    if not chosen: return True
    if ev in chosen: return True
    ev_l = str(ev).lower()
    for c in chosen:
        c_l = str(c).lower()
        parts_c = [p.strip() for p in c_l.split("@")]
        parts_e = [p.strip() for p in ev_l.split("@")]
        if len(parts_c) == 2 and parts_c[0] in ev_l and parts_c[1] in ev_l: return True
        if len(parts_e) == 2 and parts_e[0] in c_l and parts_e[1] in c_l: return True
    return False

def name_in_lineup(player, lineup_names):
    if not lineup_names: return None
    cn = clean_name(player)
    if cn in lineup_names: return True
    parts = cn.split()
    if len(parts) >= 2:
        last, fi = parts[-1].lower(), parts[0][0].lower()
        for ln in lineup_names:
            lp = ln.split()
            if len(lp) >= 2 and lp[-1].lower() == last and lp[0][0].lower() == fi:
                return True
    return False

def load_pregame():
    if not os.path.exists(PREGAME_FILE):
        return {}
    try:
        with open(PREGAME_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_pregame(data):
    try:
        with open(PREGAME_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def update_pregame_lock(df):
    if df is None or df.empty:
        return load_pregame()
    lock = load_pregame()
    today = today_az()
    ts = now_utc_iso()
    for _, r in df.iterrows():
        player = clean_name(r["player"])
        book = r["book"]
        if is_bet365(book):
            book = "bet365"
        price = r["price"]
        event = r.get("event") or ""
        if player not in lock:
            lock[player] = {"date": today, "event": event, "books": {}, "locked_at": ts, "updated_at": ts}
        entry = lock[player]
        if event:
            entry["event"] = event
        entry["date"] = today
        entry["updated_at"] = ts
        entry.setdefault("books", {})
        entry["books"][book] = {
            "price": int(price) if price is not None else None,
            "ending": last_two(price),
            "seen_at": ts,
        }
        if "betmgm" in book or book == "mgm":
            entry["mgm_price"] = int(price) if price is not None else entry.get("mgm_price")
            entry["mgm_ending"] = last_two(price)
    save_pregame(lock)
    st.session_state["pregame_lock"] = lock
    return lock

def get_locked(player):
    lock = st.session_state.get("pregame_lock") or load_pregame()
    return lock.get(clean_name(player)) or lock.get(player) or {}

def locked_price_str(player):
    entry = get_locked(player)
    books = entry.get("books") or {}
    if not books:
        return ""
    parts = []
    for b, info in sorted(books.items()):
        p = info.get("price")
        if p is not None:
            parts.append(f"{book_label(b)} {format_odds(p)}")
    return " · ".join(parts)

def load_history():
    if not os.path.exists(HISTORY_FILE): return
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        saved_at = data.get("saved_at")
        if saved_at:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(saved_at)
            if age > timedelta(hours=HISTORY_MAX_AGE_HOURS): return
        pr = []
        for snap in data.get("presence_history", []):
            s = set()
            for item in snap:
                if len(item) >= 3: s.add((item[0], item[1], item[2]))
                elif len(item) == 2: s.add((item[0], item[1], ""))
            pr.append(s)
        st.session_state["presence_history"] = pr[-12:]
        ph = [{tuple(k.split("||", 1)): v for k, v in snap.items()} for snap in data.get("price_history", [])]
        st.session_state["price_history"] = ph[-8:]
        mh = []
        for snap in data.get("mgm_history", []):
            mh.append([{"event": g["event"], "ending": g["ending"], "team": g.get("team", ""), "players": frozenset(g["players"])} for g in snap])
        st.session_state["mgm_history"] = mh[-8:]
        if "prev_ev" in data:
            st.session_state["prev_ev"] = data["prev_ev"]
    except Exception:
        pass

def save_history(prev_ev=None):
    try:
        ph = [{f"{a}||{b}": v for (a, b), v in snap.items()} for snap in st.session_state.get("price_history", [])]
        pr = [[[a, b, e] for (a, b, e) in snap] for snap in st.session_state.get("presence_history", [])]
        mh = [[{"event": g["event"], "ending": g["ending"], "team": g.get("team", ""), "players": list(g["players"])} for g in snap]
              for snap in st.session_state.get("mgm_history", [])]
        payload = {"saved_at": now_utc_iso(), "price_history": ph, "presence_history": pr, "mgm_history": mh}
        if prev_ev is not None:
            payload["prev_ev"] = prev_ev
        elif "prev_ev" in st.session_state:
            payload["prev_ev"] = st.session_state["prev_ev"]
        with open(HISTORY_FILE, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass

def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    try:
        with open(RESULTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_results(rows):
    try:
        with open(RESULTS_FILE, "w") as f:
            json.dump(rows, f, indent=2)
    except Exception:
        pass

def set_result_status(row_id, status):
    rows = load_results()
    for row in rows:
        if row.get("id") == row_id:
            row["result"] = status
            if status == "HIT" and row.get("ending") is None and row.get("best_price") is not None:
                row["ending"] = last_two(row["best_price"])
            save_results(rows)
            return True
    return False

def undo_result(row_id, source):
    if source == "manual_hr":
        rows = [x for x in load_results() if x.get("id") != row_id]
        save_results(rows)
        return True
    return set_result_status(row_id, "PENDING")

def log_bet_this(ev_board):
    rows = load_results()
    today = today_az()
    added = 0
    for item in ev_board:
        if not item.get("is_bet"):
            continue
        if any(r.get("date") == today and r.get("player") == item["player"] and r.get("source") != "manual_hr" for r in rows):
            continue
        price = item.get("best_price")
        book = item.get("best_book", "")
        locked = get_locked(item["player"])
        ending = last_two(price)
        rows.append({
            "id": f"{today}_{item['player']}_{int(item['score'])}",
            "date": today, "time": now_az(), "player": item["player"],
            "score": item["score"], "edge": int(item["edge"]),
            "best_price": price, "best_book": book,
            "ending": ending, "mgm_locked": locked.get("mgm_price"),
            "mgm_ending": locked.get("mgm_ending"),
            "locked_books": locked.get("books"),
            "methods": item["methods"], "core": item.get("method_count", 0),
            "result": "PENDING", "source": "take_it",
            "logged_at": now_utc_iso(),
        })
        added += 1
    if added:
        save_results(rows)
    return added

def log_manual_hr(player, price, book):
    rows = load_results()
    today = today_az()
    player = clean_name(player)
    if not player:
        return False, "Need a player name"
    if (price is None or str(price).strip() == "") and book:
        locked = get_locked(player)
        books = locked.get("books") or {}
        bkey = book.lower()
        if bkey in books and books[bkey].get("price") is not None:
            price = books[bkey]["price"]
        elif "betmgm" in bkey or bkey == "mgm":
            price = locked.get("mgm_price")
    try:
        price = int(str(price).replace("+", "").replace(",", "").strip())
    except Exception:
        return False, "Need a valid price (or locked pregame for that book)"
    book = (book or "untagged").strip().lower()
    ending = last_two(price)
    rid = f"hr_{today}_{player}_{price}_{book}_{len(rows)}"
    rows.append({
        "id": rid, "date": today, "time": now_az(), "player": player,
        "score": None, "edge": None, "best_price": price, "best_book": book,
        "ending": ending, "methods": ["Manual HR log"], "core": 0,
        "result": "HIT", "source": "manual_hr", "logged_at": now_utc_iso(),
    })
    save_results(rows)
    return True, f"Logged {player} {format_odds(price)} {book_label(book)} ends {ending:02d}"

def pending_sort_key(r):
    return (r.get("date") or "", r.get("time") or "", r.get("logged_at") or "", r.get("player") or "")

def build_whats_going_today(rows):
    today = today_az()
    todays = [r for r in rows if r.get("date") == today]
    hits = [r for r in todays if r.get("result") == "HIT"]
    graded = [r for r in todays if r.get("result") in ("HIT", "MISS")]
    n_hits, n_graded = len(hits), len(graded)
    book_ending = Counter()
    for r in hits:
        price = r.get("best_price")
        book = r.get("best_book") or ""
        ending = r.get("ending")
        if ending is None and price is not None:
            ending = last_two(price)
        if ending is None and r.get("mgm_ending") is not None:
            ending = r["mgm_ending"]
            book = book or "betmgm"
        if ending is None:
            continue
        ending = int(ending)
        bl = book_label(book)
        book_ending[(bl, ending)] += 1
    chips = []
    for (bl, end), cnt in sorted(book_ending.items(), key=lambda x: (-x[1], x[0], x[1])):
        chips.append((bl, end, cnt))
    return n_hits, n_graded, chips[:12]

def render_whats_going_today():
    rows = load_results()
    n_hits, n_graded, chips = build_whats_going_today(rows)
    if chips:
        parts = []
        for bl, end, cnt in chips:
            cls = chip_class_for_book(bl)
            parts.append(
                f'<span class="trend-chip {cls}">{bl} {end:02d}'
                f'<span class="chip-count"> · {cnt} HR</span></span>'
            )
        chips_html = "".join(parts)
    else:
        chips_html = '<span class="trend-chip chip-other">No HITs yet — grade PENDING or Log a HR</span>'
    st.markdown(f"""
    <div class="trends-today">
        <div class="trends-today-header">
            <div class="trends-today-title">🔥 What's Going Today</div>
            <div class="trends-today-sub">{n_hits} HR{"s" if n_hits != 1 else ""} of {n_graded} graded · book-coded · not predictive</div>
        </div>
        <div class="trends-chips">{chips_html}</div>
    </div>
    """, unsafe_allow_html=True)

def fetch_rotowire_lineups():
    if not HAS_BS4:
        return set(), "Install beautifulsoup4"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        r = requests.get(ROTOWIRE_URL, headers=headers, timeout=25)
        if r.status_code != 200:
            return set(), f"RotoWire HTTP {r.status_code}"
        soup = BeautifulSoup(r.content, "html.parser")
        names = set()
        for el in soup.select("div.lineup__player a, li.lineup__player a"):
            t = el.get_text(strip=True)
            if t and len(t.split()) >= 2:
                names.add(clean_name(t))
        if len(names) < 15:
            for box in soup.select("div.lineup__box, div.lineup"):
                for a in box.find_all("a", href=True):
                    href = a.get("href") or ""
                    if "player" not in href.lower() and "baseball" not in href.lower():
                        continue
                    t = a.get_text(strip=True)
                    if t and len(t.split()) >= 2 and not re.search(r"\d", t):
                        names.add(clean_name(t))
        return names, f"RotoWire · {len(names)} lineup names"
    except Exception as e:
        return set(), f"RotoWire error: {e}"

def fetch_events_oddsapi(api_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Odds API events error: {e}")
        return []

def fetch_odds_oddsapi(api_key, event_id):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/baseball_mlb/events/{event_id}/odds",
            params={"apiKey": api_key, "regions": REGIONS, "markets": "batter_home_runs", "oddsFormat": "american"},
            timeout=20,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def flatten_oddsapi(data):
    if not data: return [], set()
    rows, found = [], set()
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        bk = book.get("key", "").lower()
        found.add(bk)
        if bk not in PREFERRED: continue
        for market in book.get("markets", []):
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over": continue
                pt = o.get("point")
                if pt is None or abs(float(pt) - 0.5) > 0.01: continue
                rows.append({
                    "event": event, "book": bk, "player": o.get("description"),
                    "price": o.get("price"), "point": 0.5, "team": "", "source": "oddsapi",
                })
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(f"{SGO_BASE}/events", params={
            "apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 25
        }, timeout=25)
        if r.status_code != 200: return rows, found
        for ev in r.json().get("data", []):
            if ev.get("status", {}).get("started"): continue
            teams = ev.get("teams", {})
            home = teams.get("home", {}).get("names", {}).get("long", "Home")
            away = teams.get("away", {}).get("names", {}).get("long", "Away")
            event_name = f"{away} @ {home}"
            players_map = ev.get("players", {})
            for odd_id, odd_data in ev.get("odds", {}).items():
                if "batting_homeRuns" not in odd_id: continue
                if "ou-over" not in odd_id and "-over" not in odd_id: continue
                ou = odd_data.get("bookOverUnder") or odd_data.get("fairOverUnder")
                if ou is None or abs(float(ou) - 0.5) > 0.01: continue
                pid = odd_data.get("playerID") or odd_data.get("statEntityID")
                if not pid or pid not in players_map: continue
                pdata = players_map[pid]
                pname = pdata.get("name")
                if not pname: continue
                team = clean_team(pdata.get("teamID") or "")
                for bk, bd in odd_data.get("byBookmaker", {}).items():
                    if not bd.get("available", True): continue
                    b = bk.lower()
                    if is_bet365(b): b = "bet365"
                    if b not in PREFERRED: continue
                    price = bd.get("odds")
                    if price is None: continue
                    try: price = int(str(price).replace("+", ""))
                    except Exception: continue
                    found.add(b)
                    rows.append({
                        "event": event_name, "book": b, "player": pname,
                        "price": price, "point": 0.5, "team": team, "source": "sgo",
                    })
    except Exception as e:
        st.warning(f"SGO note: {e}")
    return rows, found

def merge_odds(a, b):
    combined = a + b
    if not combined: return pd.DataFrame()
    df = pd.DataFrame(combined)
    df["priority"] = df["source"].map({"oddsapi": 0, "sgo": 1})
    df = df.sort_values(["player", "book", "priority"])
    team_map = {}
    for _, r in df.iterrows():
        if r.get("team"):
            team_map[r["player"]] = r["team"]
    df["team"] = df.apply(lambda r: r["team"] if r.get("team") else team_map.get(r["player"], ""), axis=1)
    df = df.drop_duplicates(subset=["player", "book"], keep="first")
    return df.drop(columns=["priority", "source"], errors="ignore")

def do_fetch(odds_key, sgo_key, chosen_labels, options):
    all_rows, all_found = [], set()
    for label in chosen_labels:
        eid = options.get(label)
        if not eid: continue
        data = fetch_odds_oddsapi(odds_key, eid)
        rows, found = flatten_oddsapi(data)
        all_rows.extend(rows)
        all_found.update(found)
    sgo_rows, sgo_found = fetch_sgo_hr_props(sgo_key)
    all_rows.extend(sgo_rows)
    all_found.update(sgo_found)
    if not all_rows:
        return None, set()
    df = merge_odds(
        [r for r in all_rows if r.get("source") == "oddsapi"],
        [r for r in all_rows if r.get("source") == "sgo"],
    )
    if chosen_labels and not df.empty and "event" in df.columns:
        mask = df["event"].apply(lambda e: event_matches_chosen(e, chosen_labels))
        df = df[mask].copy()
    found = (all_found & PREFERRED) | {x for x in all_found if is_bet365(x)}
    return df, found

def build_team_map(df):
    tm = {}
    for _, r in df.iterrows():
        if r.get("team"):
            tm[r["player"]] = r["team"]
    return tm

def run_flags(df, previous_df=None, record_history=True, selected_events=None):
    if df.empty: return [], [], []

    if "team" not in df.columns:
        df["team"] = ""
    df["book"] = df["book"].apply(lambda b: "bet365" if is_bet365(b) else b)
    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results, methods_map = [], defaultdict(list)
    all_players_now = set(df["player"].unique())
    selected = set(selected_events) if selected_events else set(df["event"].unique())
    signal_bucket = defaultdict(list)
    signal_methods = defaultdict(set)
    team_map = build_team_map(df)
    lineup_names = st.session_state.get("lineup_names", set())

    for k in ("presence_history", "price_history", "mgm_history"):
        if k not in st.session_state:
            st.session_state[k] = []

    current_presence = {(r["player"], r["book"], r["event"]) for _, r in df.iterrows() if r["book"] in LATE_BOOKS}
    current_prices = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}

    if record_history:
        st.session_state["presence_history"].append(current_presence)
        st.session_state["presence_history"] = st.session_state["presence_history"][-12:]
        st.session_state["price_history"].append(current_prices)
        st.session_state["price_history"] = st.session_state["price_history"][-8:]

    hist = st.session_state["presence_history"]
    phist = st.session_state["price_history"]

    if len(hist) >= 2:
        def norm(snap):
            out = set()
            for item in snap:
                if len(item) == 3: out.add(item)
                elif len(item) == 2: out.add((item[0], item[1], ""))
            return out

        def scoped(snap):
            s = set()
            for p, b, e in norm(snap):
                if e and selected and not event_matches_chosen(e, selected): continue
                if not e and selected: continue
                s.add((p, b, e))
            return s

        latest, previous = scoped(hist[-1]), scoped(hist[-2])
        early = set()
        for snap in hist[:max(1, len(hist)//3)]:
            early |= scoped(snap)

        late_bucket = {}

        def add_late(player, book, event, kind):
            if player not in late_bucket:
                late_bucket[player] = {"kind": kind, "books": [], "event": event}
            pri = {"Gone Missing": 3, "Just Appeared": 2, "Added Late": 1}
            if pri.get(kind, 0) >= pri.get(late_bucket[player]["kind"], 0):
                late_bucket[player]["kind"] = kind
            late_bucket[player]["books"].append(book)
            if event:
                late_bucket[player]["event"] = event

        for player, book, event in latest - previous:
            add_late(player, book, event, "Just Appeared")
        for player, book, event in latest - early:
            if (player, book, event) in previous: continue
            add_late(player, book, event, "Added Late")
        for player, book, event in previous - latest:
            add_late(player, book, event, "Gone Missing")

        for player, info in sorted(late_bucket.items()):
            books = sorted(set(info["books"]))
            kind = info["kind"]
            lock_note = locked_price_str(player)
            reason = f"{kind} · {', '.join(books)}"
            if lock_note and kind == "Gone Missing":
                reason += f" | 🔒 {lock_note}"
            results.append({
                "type": "late", "label": player, "reason": reason,
                "event": info.get("event", ""), "css": "hist", "methods": [kind],
            })
            methods_map[player].append(kind)

    if lineup_names:
        by_player_books = defaultdict(set)
        for _, r in df.iterrows():
            by_player_books[r["player"]].add(r["book"])
        for player in sorted(all_players_now):
            status = name_in_lineup(player, lineup_names)
            if status is False:
                results.append({
                    "type": "late", "label": player,
                    "reason": "On books but NOT in RotoWire lineup — likely not playing",
                    "event": "", "css": "hist", "methods": ["Not in lineup"],
                })
                methods_map[player].append("Not in lineup")
            elif status is True:
                miss = [b for b in ("draftkings", "fanduel", "betmgm") if b not in by_player_books[player]]
                if miss:
                    results.append({
                        "type": "late", "label": player,
                        "reason": f"In lineup · missing props on {', '.join(miss)}",
                        "event": "", "css": "hist", "methods": ["In lineup · missing books"],
                    })
                    methods_map[player].append("In lineup · missing books")

    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap: continue
            prev_price = prev_snap[key]
            delta = curr_price - prev_price
            if delta >= BIG_MOVE:
                results.append({
                    "type": "trend", "trend_kind": "fade", "label": player,
                    "reason": f"Shot way up on {book}: {format_odds(prev_price)} → {format_odds(curr_price)} (+{int(delta)})",
                    "event": "", "css": "hist", "methods": ["FADE · Shot way up"], "gap": abs(int(delta)),
                })
            elif delta <= -BIG_MOVE:
                results.append({
                    "type": "trend", "trend_kind": "fade", "label": player,
                    "reason": f"Dropped >100 on {book}: {format_odds(prev_price)} → {format_odds(curr_price)} ({int(delta)})",
                    "event": "", "css": "hist", "methods": ["FADE · Drop >100"], "gap": abs(int(delta)),
                })

    for player, g in df.groupby("player"):
        by_book = {r["book"]: r["price"] for _, r in g.iterrows()}
        fd = by_book.get("fanduel")
        mgm_price = None
        for k, v in by_book.items():
            if "betmgm" in k or k == "mgm":
                mgm_price = v
                break
        b365 = by_book.get("bet365")
        hr = None
        for k, v in by_book.items():
            if is_hardrock(k):
                hr = v
                break
        others = [v for b, v in by_book.items() if b != "fanduel"]
        if fd is not None and mgm_price is not None:
            gap = mgm_price - fd
            if 10 <= gap <= 100:
                results.append({
                    "type": "trend", "trend_kind": "good", "label": player,
                    "reason": f"FD under MGM by {int(gap)} pts · FD {format_odds(fd)} · MGM {format_odds(mgm_price)}",
                    "event": "", "css": "hist", "methods": ["FD under MGM"], "gap": int(gap),
                })
        if fd is not None and others and fd > max(others):
            results.append({
                "type": "trend", "trend_kind": "fade", "label": player,
                "reason": f"FD highest of all books · FD {format_odds(fd)} · others max {format_odds(max(others))}",
                "event": "", "css": "hist", "methods": ["FADE · FD highest"], "gap": 0,
            })
        if b365 is not None and hr is not None and b365 > hr:
            gap_hr = int(b365 - hr)
            results.append({
                "type": "trend", "trend_kind": "good", "label": player,
                "reason": f"Bet365 higher than HardRock by {gap_hr} pts · 365 {format_odds(b365)} · HR {format_odds(hr)}",
                "event": "", "css": "hist", "methods": ["B365 > HardRock"], "gap": gap_hr,
            })
            methods_map[player].append("B365 > HardRock")

    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        player_up, player_down = defaultdict(list), defaultdict(list)
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap: continue
            prev_price = prev_snap[key]
            if abs(prev_price) < MOVE_PRICE_MIN and abs(curr_price) < MOVE_PRICE_MIN: continue
            delta = curr_price - prev_price
            if abs(delta) < MOVE_MIN: continue
            line = f"{book}: {format_odds(prev_price)} → {format_odds(curr_price)} ({int(abs(delta))} pts)"
            (player_up if delta > 0 else player_down)[player].append(line)
        for player, moves in sorted(player_up.items()):
            results.append({"type": "hist", "move_dir": "up", "label": player,
                "reason": " | ".join(moves), "event": "", "css": "hist", "methods": ["Price moved"]})
            methods_map[player].append("Price moved")
        for player, moves in sorted(player_down.items()):
            results.append({"type": "hist", "move_dir": "down", "label": player,
                "reason": " | ".join(moves), "event": "", "css": "hist", "methods": ["Price moved"]})
            methods_map[player].append("Price moved")

    for _, row in df.iterrows():
        if row["book"] == "draftkings" and last_two(row["price"]) == 10:
            results.append({"type": "dk", "label": row["player"],
                "reason": f"DraftKings ends in 10 → {format_odds(row['price'])}",
                "event": row["event"], "css": "dk", "methods": ["DK 10"]})
            methods_map[row["player"]].append("DK 10")

    for _, row in df.iterrows():
        if row["book"] != "bet365": continue
        price = abs(int(row["price"])) if row["price"] is not None else 0
        if price == 850 or price % 1000 == 850:
            results.append({"type": "b365", "label": row["player"],
                "reason": f"Bet365 850s → {format_odds(row['price'])}",
                "event": row["event"], "css": "b365", "methods": ["B365 850"]})
            methods_map[row["player"]].append("B365 850")

    b365_df = df[df["book"] == "bet365"].copy()
    if not b365_df.empty:
        group_cols = ["event", "team"] if b365_df["team"].astype(str).str.len().gt(0).any() else ["event"]
        for keys, g in b365_df.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            event = keys[0]
            team = keys[1] if len(keys) > 1 else ""
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in (25, 50, 75):
                    ends[d].append(r["player"])
            for d, ps in ends.items():
                names = sorted(set(ps))
                if len(names) not in (2, 3): continue
                kind = "pair" if len(names) == 2 else "group of 3"
                tnote = f" · {team}" if team else " · same team"
                meth = f"B365 Match {d}"
                results.append({"type": "b365", "label": " + ".join(names),
                    "reason": f"Bet365 {kind} ends in {d}{tnote}",
                    "event": event, "css": "b365", "methods": [meth]})
                for n in names: methods_map[n].append(meth)

    mgm = df[df["book"].str.contains("betmgm|mgm", case=False, na=False)].copy()
    current_mgm = []
    if not mgm.empty and mgm["team"].astype(str).str.len().gt(0).any():
        for (event, team), g in mgm.groupby(["event", "team"], dropna=False):
            team = team if isinstance(team, str) else ""
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in (0, 25, 50, 75):
                    ends[d].append(r["player"])
            for d, ps in ends.items():
                if len(set(ps)) >= 2:
                    current_mgm.append({"event": event, "ending": d, "team": team, "players": frozenset(ps)})
    else:
        for event, g in mgm.groupby("event"):
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in (0, 25, 50, 75):
                    ends[d].append(r["player"])
            for d, ps in ends.items():
                if len(set(ps)) >= 2:
                    current_mgm.append({"event": event, "ending": d, "team": "", "players": frozenset(ps)})

    if record_history:
        st.session_state["mgm_history"].append(current_mgm)
        st.session_state["mgm_history"] = st.session_state["mgm_history"][-8:]

    mgm_stayed, survivor = defaultdict(int), set()
    h = st.session_state["mgm_history"]
    if len(h) >= 2:
        for snap in h:
            seen = set()
            for g in snap: seen.update(g["players"])
            for p in seen: mgm_stayed[p] += 1
        early = set()
        for g in h[0]:
            if len(g["players"]) >= 3: early.update(g["players"])
        late = set()
        for g in h[-1]: late.update(g["players"])
        survivor = early & late

    for grp in current_mgm:
        names = sorted(grp["players"])
        if len(names) < 2: continue
        d = grp["ending"]
        team = grp.get("team") or ""
        meth, extra = [f"MGM {d:02d}"], []
        for n in names:
            c = mgm_stayed.get(n, 0)
            if c >= 3:
                meth.append(f"Stayed in group {c}x"); extra.append(f"Stayed in group {c}x")
            elif c >= 2:
                meth.append("Stayed in the group"); extra.append("Stayed in the group")
            if n in survivor:
                meth.append("Last one left"); extra.append("Last one left")
        kind = "pair" if len(names) == 2 else f"group of {len(names)}"
        team_note = f" · {team}" if team else ""
        reason = f"MGM {kind} ends in {d:02d}{team_note}"
        if extra: reason += " · " + " + ".join(set(extra))
        results.append({"type": "mgm", "label": " + ".join(names),
            "reason": reason, "event": grp["event"], "css": "mgm", "methods": list(set(meth))})
        for n in names: methods_map[n].extend(meth)

    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2: continue
        prices = g["price"].dropna().tolist()
        if len(set(prices)) == 1:
            results.append({"type": "match", "label": player,
                "reason": f"Exact match {format_odds(prices[0])} → {', '.join(g['book'])}",
                "event": g["event"].iloc[0], "css": "match", "methods": ["Exact Match"]})
            methods_map[player].append("Exact Match")

    for (event, team), g in mgm.groupby(["event", "team"], dropna=False):
        for price, pg in g.groupby("price"):
            names = sorted(pg["player"].unique())
            if len(names) >= 2:
                tnote = f" · {team}" if team else ""
                results.append({"type": "mgm_exact", "label": " + ".join(names),
                    "reason": f"MGM Exact {format_odds(price)} ({len(names)} players){tnote}",
                    "event": event, "css": "mgm", "methods": ["MGM Exact"]})
                for n in names: methods_map[n].append("MGM Exact")

    for (event, team), g in mgm.groupby(["event", "team"], dropna=False):
        ends = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in (25, 50, 75):
                ends[d].append(r["player"])
        for d, ps in ends.items():
            names = sorted(set(ps))
            if len(names) not in (2, 3): continue
            kind = "pair" if len(names) == 2 else "group of 3"
            tnote = f" · {team}" if team else " · same team"
            results.append({"type": "digit", "label": " + ".join(names),
                "reason": f"Digit {kind} ends in {d}{tnote}",
                "event": event, "css": "digit", "methods": [f"Match {d}"]})
            for n in names: methods_map[n].append(f"Match {d}")

    for _, row in df.iterrows():
        if row["book"] != "fanduel": continue
        player = row["player"]
        if not has_dk_or_mgm(methods_map.get(player, [])): continue
        price = abs(int(row["price"])) if row["price"] else 0
        last = last_two(row["price"])
        if price == 600:
            results.append({"type": "fd", "label": player,
                "reason": f"FanDuel exact +600 (has DK/MGM) → {format_odds(row['price'])}",
                "event": row["event"], "css": "fd", "methods": ["FD 600"]})
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in (10, 20, 30, 60, 70, 90):
            results.append({"type": "fd", "label": player,
                "reason": f"FanDuel ≥ +{FD_MIN} ends in {last:02d} (has DK/MGM) → {format_odds(row['price'])}",
                "event": row["event"], "css": "fd", "methods": ["FD Pattern"]})
            methods_map[player].append("FD Pattern")

    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 2: continue
        if len(prices) >= 3 and len(set(prices)) == 1:
            signal_bucket[player].append(f"Same price on {len(prices)} books → {format_odds(prices[0])}")
            signal_methods[player].add("Same on 3+ books")
            methods_map[player].append("Same on 3+ books")
        dig_books = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in (25, 50, 75):
                dig_books[d].append(r["book"])
        for d, bks in dig_books.items():
            if len(set(bks)) >= 3:
                signal_bucket[player].append(f"Same ending {d} on {len(set(bks))} books")
                signal_methods[player].add(f"Same ending {d}")
                methods_map[player].append(f"Same ending {d}")
        if len(prices) >= 3:
            for i, (p, b) in enumerate(zip(prices, books)):
                rest = prices[:i] + prices[i+1:]
                try: med_rest = statistics.median(rest)
                except Exception: continue
                if p - med_rest >= OUTLIER_GAP:
                    signal_bucket[player].append(f"One higher: {b} at {format_odds(p)} · pack {format_odds(med_rest)}")
                    signal_methods[player].add("Outlier higher")
                    methods_map[player].append("Outlier higher")

    if len(phist) >= 3:
        for key in phist[-1].keys():
            player, book = key
            if player not in all_players_now: continue
            vals = [snap[key] for snap in phist[-4:] if key in snap]
            if len(vals) >= 3 and len(set(vals)) == 1:
                signal_bucket[player].append(f"Stuck on {book} at {format_odds(vals[0])} across {len(vals)} snaps")
                signal_methods[player].add("Stuck price")
                methods_map[player].append("Stuck price")

    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        up_by, down_by = defaultdict(list), defaultdict(list)
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap: continue
            delta = curr_price - prev_snap[key]
            if abs(delta) < MOVE_MIN: continue
            if delta > 0: up_by[player].append(book)
            else: down_by[player].append(book)
        for player, books in up_by.items():
            if len(books) >= 2:
                signal_bucket[player].append(f"Multi-book lengthen on {', '.join(books)}")
                signal_methods[player].add("Multi-book Lengthen")
                methods_map[player].append("Multi-book Lengthen")
        for player, books in down_by.items():
            if len(books) >= 2:
                signal_bucket[player].append(f"Multi-book shorten on {', '.join(books)}")
                signal_methods[player].add("Multi-book Shorten")
                methods_map[player].append("Multi-book Shorten")

    for player in sorted(signal_bucket.keys()):
        results.append({
            "type": "signal", "label": player,
            "reason": " | ".join(signal_bucket[player]),
            "event": "", "css": "signal", "methods": list(signal_methods[player]),
        })

    ev_board = []
    player_events = defaultdict(set)
    for _, r in df.iterrows():
        player_events[r["player"]].add(r["event"])

    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if lineup_names and name_in_lineup(player, lineup_names) is False:
            continue
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 2: continue
        best, best_book = smart_best(prices, books)
        if best is None: continue
        try: med = statistics.median(prices)
        except Exception: med = best
        edge = best - med
        meths = list(set(methods_map.get(player, [])))
        core_count = count_core_methods(meths)
        if core_count < METHODS_MIN: continue
        is_bet = edge >= EDGE_MIN
        display_meths = [m for m in meths if is_core_method(m)]
        score = girl_magic_score(core_count, edge, display_meths)
        conf, bars, level = get_confidence(score, is_bet)
        why = (f"Score {score}/100 · {core_count} core · Edge pts {int(edge)}. This is the one."
               if is_bet else
               f"Score {score}/100 · {core_count} core · Edge pts {int(edge)} (need {EDGE_MIN}+).")
        ev_board.append({
            "player": player, "best_price": best, "best_book": best_book,
            "median": med, "edge": edge, "is_bet": is_bet, "why": why,
            "methods": display_meths, "score": score, "bars": bars,
            "level": level, "method_count": core_count,
            "team": team_map.get(player, ""),
            "events": list(player_events.get(player, [])),
        })
    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["score"], -x["edge"]))

    current_ev = {
        item["player"]: {
            "methods": item["methods"], "edge": item["edge"],
            "is_bet": item["is_bet"], "method_count": item["method_count"], "score": item["score"],
            "events": item.get("events", []),
        } for item in ev_board
    }

    prev_ev = st.session_state.get("prev_ev", {})
    prev_scope = set()
    if previous_df is not None and not previous_df.empty and "event" in previous_df.columns:
        prev_scope = set(
            previous_df[previous_df["event"].apply(lambda e: event_matches_chosen(e, selected))]["player"]
        )
    elif previous_df is not None and not previous_df.empty:
        prev_scope = set(previous_df["player"])

    fallen = []
    for player, old in prev_ev.items():
        if player in current_ev:
            continue
        old_events = old.get("events") or []
        if selected and old_events:
            if not any(event_matches_chosen(e, selected) for e in old_events):
                continue
        elif selected and prev_scope and player not in prev_scope and player not in all_players_now:
            continue
        elif selected and not old_events and player not in all_players_now and player not in prev_scope:
            continue

        now_meths = list(set(methods_map.get(player, [])))
        now_core = count_core_methods(now_meths)
        n_books = len(df[df["player"] == player]) if player in all_players_now else 0
        reasons = []
        lock_note = locked_price_str(player)
        if lineup_names and name_in_lineup(player, lineup_names) is False:
            reasons.append("Not in lineup")
        if player not in all_players_now:
            reasons.append("Line gone from live feed (often MGM after first pitch)")
            if lock_note:
                reasons.append(f"🔒 {lock_note}")
        elif n_books < 2:
            reasons.append("Only 1 book left")
        elif now_core < METHODS_MIN:
            reasons.append(f"Lost core methods ({now_core} left)")
            lost = set(old.get("methods", [])) - set(m for m in now_meths if is_core_method(m))
            if lost: reasons.append("Lost: " + ", ".join(list(lost)[:4]))
        else:
            reasons.append("Dropped under filters")
        if old.get("is_bet"): reasons.insert(0, "Was BET THIS")
        fallen.append({
            "type": "fallen", "label": player, "reason": " · ".join(reasons),
            "event": "", "css": "hist",
            "methods": ["Fallen Off"] + (["Was BET THIS"] if old.get("is_bet") else []),
            "old_methods": old.get("methods", []), "old_edge": old.get("edge", 0),
            "old_score": old.get("score", 0),
        })
        results.append(fallen[-1])

    if record_history:
        st.session_state["prev_ev"] = current_ev
        save_history(prev_ev=current_ev)

    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])

    def different_teams(a, b):
        ta, tb = team_map.get(a, ""), team_map.get(b, "")
        if ta and tb: return ta != tb
        return len(pev[a] & pev[b]) == 0

    pool = [p for p, ms in methods_map.items()
            if count_core_methods(ms) >= NAME_METHODS_MIN and has_personal_strong(ms)]
    if lineup_names:
        pool = [p for p in pool if name_in_lineup(p, lineup_names) is not False]

    init_map = defaultdict(list)
    for p in pool:
        f, l = get_initials(p)
        if f and l: init_map[f + l].append(p)
    init_pairs = []
    for k, names in init_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if different_teams(a, b): init_pairs.append((a, b, k))
    for a, b, k in sorted(init_pairs, key=lambda x: (x[2], x[0], x[1]))[:NAME_MAX_PAIRS]:
        results.append({"type": "same_init", "label": f"{a} + {b}",
            "reason": f"Same initials {k} (different teams)", "event": "", "css": "name", "methods": ["Same Init"]})

    double_pool = [(p, get_initials(p)[0]) for p in pool if get_initials(p)[0] and get_initials(p)[0] == get_initials(p)[1]]
    double_pairs = []
    for i, (a, la) in enumerate(double_pool):
        for b, lb in double_pool[i+1:]:
            if different_teams(a, b):
                double_pairs.append((a, b, la + lb))
    for a, b, k in sorted(double_pairs, key=lambda x: (x[2], x[0], x[1]))[:NAME_MAX_PAIRS]:
        results.append({"type": "double_init", "label": f"{a} + {b}",
            "reason": "Double initials (different teams)", "event": "", "css": "name", "methods": ["Double Init"]})

    cross_pairs = []
    for i, a in enumerate(pool):
        _, l1 = get_initials(a)
        if not l1: continue
        for b in pool[i+1:]:
            f2, _ = get_initials(b)
            if f2 and l1 == f2 and different_teams(a, b):
                cross_pairs.append((a, b, l1))
    for a, b, letter in sorted(cross_pairs, key=lambda x: (x[2], x[0], x[1]))[:NAME_MAX_PAIRS]:
        results.append({"type": "cross", "label": f"{a} + {b}",
            "reason": f"Cross initials ({letter}) (different teams)", "event": "", "css": "name", "methods": ["Cross Init"]})

    last_map = defaultdict(list)
    for p in pool:
        parts = clean_name(p).split()
        if len(parts) >= 2: last_map[parts[-1].lower()].append(p)
    last_pairs = []
    for last, names in last_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if different_teams(a, b): last_pairs.append((a, b, last))
    for a, b, last in sorted(last_pairs, key=lambda x: (x[2], x[0], x[1]))[:NAME_MAX_PAIRS]:
        results.append({"type": "last", "label": f"{a} + {b}",
            "reason": f"Same last name ({last.title()}) (different teams)", "event": "", "css": "name", "methods": ["Same Last"]})

    first_map = defaultdict(list)
    for p in pool:
        parts = clean_name(p).split()
        if parts: first_map[parts[0].lower()].append(p)
    first_pairs = []
    for first, names in first_map.items():
        for i, a in enumerate(names):
            for b in names[i+1:]:
                if different_teams(a, b): first_pairs.append((a, b, first))
    for a, b, first in sorted(first_pairs, key=lambda x: (x[2], x[0], x[1]))[:NAME_MAX_PAIRS]:
        results.append({"type": "first", "label": f"{a} + {b}",
            "reason": f"Same first name ({first.title()}) (different teams)", "event": "", "css": "name", "methods": ["Same First"]})

    return results, ev_board, fallen

def render_card_grid(items):
    if not items:
        st.info("None right now.")
        return
    cols = st.columns(2)
    for idx, r in enumerate(items):
        with cols[idx % 2]:
            tags = render_method_tags(r.get("methods", []))
            st.markdown(
                f'<div class="card grid-card"><b>{r["label"]}</b><br>{r["reason"]}<br>{tags}</div>',
                unsafe_allow_html=True,
            )

def main():
    if "history_loaded" not in st.session_state:
        load_history()
        st.session_state["pregame_lock"] = load_pregame()
        st.session_state["history_loaded"] = True
    if "pending_page" not in st.session_state:
        st.session_state["pending_page"] = 0

    if HAS_AUTOREFRESH:
        refresh_count = st_autorefresh(interval=REFRESH_MINUTES * 60 * 1000, key="odds_refresh")
    else:
        refresh_count = 0

    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch · HBIC · Me & My Girls We Rolling</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Where odds intuition meets Petty precision.</p>', unsafe_allow_html=True)

    lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
    hist_n = len(st.session_state.get("price_history", []))
    lu_n = len(st.session_state.get("lineup_names", set()))
    st.markdown(f"""
    <div class="how-to">
        🔒 <b>Pregame lock</b> keeps last prices when MGM vanishes · locked: <b>{lock_n}</b><br>
        📊 Results: grade all PENDING · ↩️ Undo · Log a HR<br>
        snaps: <b>{hist_n}</b> · lineup: <b>{lu_n}</b>
    </div>
    """, unsafe_allow_html=True)

    render_whats_going_today()

    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add your The Odds API key.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("① Load Games", type="primary"):
            st.session_state["events"] = fetch_events_oddsapi(odds_key)
    with c2:
        if st.button("📋 Refresh RotoWire Lineups"):
            with st.spinner("Pulling free RotoWire lineups…"):
                names, msg = fetch_rotowire_lineups()
                st.session_state["lineup_names"] = names
                st.session_state["lineup_msg"] = msg
            if names: st.success(msg)
            else: st.warning(msg or "No lineup names")

    if st.session_state.get("lineup_msg") and st.session_state.get("lineup_names"):
        st.caption(f"Lineups: {st.session_state['lineup_msg']}")

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games**.")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
    chosen = st.multiselect("② Select games", list(options.keys()), default=default_sel)
    st.session_state["selected_games"] = chosen

    manual_fetch = st.button("③ Fetch Odds", type="primary")
    if "last_refresh_count" not in st.session_state:
        st.session_state["last_refresh_count"] = refresh_count
    auto_fetch = HAS_AUTOREFRESH and refresh_count != st.session_state["last_refresh_count"] and bool(chosen)
    if auto_fetch:
        st.session_state["last_refresh_count"] = refresh_count

    if (manual_fetch or auto_fetch) and chosen:
        with st.spinner("Fetching odds…" if manual_fetch else "Auto-refresh…"):
            df, found = do_fetch(odds_key, sgo_key, chosen, options)
        if df is not None and not df.empty:
            update_pregame_lock(df)
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["found_books"] = sorted(found)
            st.session_state["last_fetch_time"] = now_az()
            st.session_state["last_selected"] = list(chosen)
            st.session_state["new_fetch"] = True
            st.success(f"Loaded {len(df)} props · lock: {len(st.session_state.get('pregame_lock', {}))} players")
        else:
            st.warning("No 0.5 HR odds. Lock unchanged.")

    found = st.session_state.get("found_books", [])
    if found:
        has_365 = any(is_bet365(b) or b == "bet365" for b in found)
        missing = [CORE_BOOKS[b] for b in CORE_BOOKS if b not in found and not (b == "bet365" and has_365)]
        st.markdown(f'<div class="info-box"><b>Books in use:</b> {", ".join(found)}</div>', unsafe_allow_html=True)
        if missing:
            st.markdown(f'<div class="warning-box">⚠️ <b>Still missing:</b> {", ".join(missing)}</div>', unsafe_allow_html=True)

    odds = st.session_state.get("odds", [])
    prev = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(prev) if prev else None
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, fallen = (
        run_flags(df, prev_df, record_history=new_fetch, selected_events=selected_events)
        if not df.empty else ([], [], [])
    )

    if ev_board:
        log_bet_this(ev_board)

    trend_good = sorted(
        [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "good"],
        key=lambda r: r.get("gap", 0), reverse=True,
    )
    trend_fade = [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "fade"]
    fd_under = [r for r in trend_good if "FD under MGM" in r.get("methods", [])]
    b365_hr = [r for r in trend_good if "B365 > HardRock" in r.get("methods", [])]

    counts = {
        "mgm": len([r for r in results if r["type"] == "mgm"]),
        "fd": len([r for r in results if r["type"] == "fd"]),
        "late": len([r for r in results if r["type"] == "late"]),
        "fallen": len(fallen),
        "bets": len([e for e in ev_board if e["is_bet"]]),
        "lock": len(st.session_state.get("pregame_lock") or {}),
    }

    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box"><div class="petty-num">{counts['bets']}</div><div class="petty-label">🟢 TAKE IT</div></div>
        <div class="petty-box"><div class="petty-num">{counts['mgm']}</div><div class="petty-label">🎰 MGM</div></div>
        <div class="petty-box"><div class="petty-num">{counts['fd']}</div><div class="petty-label">💙 FD</div></div>
        <div class="petty-box"><div class="petty-num">{counts['late']}</div><div class="petty-label">👻 Late</div></div>
        <div class="petty-box"><div class="petty-num">{counts['fallen']}</div><div class="petty-label">💀 Fallen</div></div>
        <div class="petty-box"><div class="petty-num">{counts['lock']}</div><div class="petty-label">🔒 Locked</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5 TOP TABS ──────────────────────────────────────────
    tab_board, tab_tricks, tab_names, tab_results, tab_gloss = st.tabs([
        "👑 The Board",
        "✨ Odds Tricks",
        "💅 Name Magic",
        "📊 Results",
        "📖 Glossary",
    ])

    # ── BOARD ───────────────────────────────────────────────
    with tab_board:
        st.markdown('<div class="queen-banner">👑 The Board</div>', unsafe_allow_html=True)
        if not lu_n:
            st.caption("Refresh RotoWire so non-starters don’t clog The Board.")
        if not ev_board:
            st.info("Select games and fetch.")
        else:
            cols = st.columns(2)
            for idx, item in enumerate(ev_board):
                with cols[idx % 2]:
                    tags = render_method_tags(item["methods"])
                    meter = make_meter(item["bars"], item["level"])
                    cls = "bet" if item["is_bet"] else "skip"
                    label = "🟢 TAKE IT" if item["is_bet"] else "⚪ PASS"
                    team = item.get("team") or ""
                    team_line = f" · {team}" if team else ""
                    st.markdown(f'''
                    <div class="card {cls} grid-card">
                        <b>{label}</b> — <b>{item["player"]}</b>{team_line}
                        <span class="score-pill">{item["score"]}</span><br>
                        {meter}
                        Best: {format_odds(item["best_price"])} on {item["best_book"]}<br>
                        Most books: {format_odds(item["median"])}<br>
                        <b>Edge pts:</b> {int(item["edge"])} · <b>Core:</b> {item.get("method_count", 0)}<br>
                        {tags}<br><small>{item["why"]}</small>
                    </div>''', unsafe_allow_html=True)

    # ── ODDS TRICKS (sub-tabs) ───────────────────────────────
    with tab_tricks:
        st.markdown('<div class="queen-banner">✨ Odds Tricks</div>', unsafe_allow_html=True)
        st.caption("Gold = MGM · Green = DK · Blue = FD · Bright green = 365")
        sub = st.tabs([
            "🎯 DK 10s", "🎰 MGM", "🤝 Exact", "⭐ MGM Exact", "🔢 Digits",
            "💙 FanDuel", "💚 Bet365", "📈 Signals", "⏳ Movement", "📉 Trends",
            "👻 Late", "💀 Fallen", "🔒 Lock",
        ])
        with sub[0]:
            st.caption("DraftKings prices ending in 10.")
            render_card_grid([r for r in results if r["type"] == "dk"])
        with sub[1]:
            st.caption("Same-team pairs/groups · 00/25/50/75.")
            render_card_grid([r for r in results if r["type"] == "mgm"])
        with sub[2]:
            st.caption("Same price across books.")
            render_card_grid([r for r in results if r["type"] == "match"])
        with sub[3]:
            st.caption("Exact same MGM price, same team.")
            render_card_grid([r for r in results if r["type"] == "mgm_exact"])
        with sub[4]:
            st.caption("Pairs/groups of 3 · same team · 25/50/75.")
            render_card_grid([r for r in results if r["type"] == "digit"])
        with sub[5]:
            st.caption(f"≥ +{FD_MIN} or +600 with DK/MGM.")
            render_card_grid([r for r in results if r["type"] == "fd"])
        with sub[6]:
            st.caption("850s · pairs 25/50/75 (no 00).")
            render_card_grid([r for r in results if r["type"] == "b365"])
        with sub[7]:
            st.caption("Multi-book Lengthen = noise.")
            render_card_grid([r for r in results if r["type"] == "signal"])
        with sub[8]:
            ups = [r for r in results if r["type"] == "hist" and r.get("move_dir") == "up"]
            downs = [r for r in results if r["type"] == "hist" and r.get("move_dir") == "down"]
            col_up, col_down = st.columns(2)
            with col_up:
                st.markdown("#### 🔴 UP")
                if not ups: st.info("None.")
                else:
                    for r in ups:
                        st.markdown(f'<div class="card up-card grid-card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            with col_down:
                st.markdown("#### 🟢 DOWN")
                if not downs: st.info("None.")
                else:
                    for r in downs:
                        st.markdown(f'<div class="card down-card grid-card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
        with sub[9]:
            st.markdown("#### 💚 FD under MGM")
            if not fd_under: st.info("None.")
            else:
                cols = st.columns(2)
                for idx, r in enumerate(fd_under):
                    with cols[idx % 2]:
                        st.markdown(f'<div class="card good-card grid-card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            st.markdown("#### 💚 Bet365 > HardRock")
            if not b365_hr: st.info("None.")
            else:
                cols = st.columns(2)
                for idx, r in enumerate(b365_hr):
                    with cols[idx % 2]:
                        st.markdown(f'<div class="card good-card grid-card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            st.markdown("#### 🔴 Fade")
            if not trend_fade: st.info("None.")
            else:
                cols = st.columns(2)
                for idx, r in enumerate(trend_fade):
                    with cols[idx % 2]:
                        st.markdown(f'<div class="card fade-card grid-card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
        with sub[10]:
            st.caption("Gone Missing shows 🔒 last pregame when available.")
            render_card_grid([r for r in results if r["type"] == "late"])
        with sub[11]:
            st.caption("Often = live feed dropped MGM. Lock keeps prices.")
            if not fallen: st.info("None.")
            else:
                cols = st.columns(2)
                for idx, r in enumerate(fallen):
                    with cols[idx % 2]:
                        st.markdown(f'<div class="card grid-card"><b>{r["label"]}</b> · was {r.get("old_score", 0)}<br>{r["reason"]}</div>', unsafe_allow_html=True)
        with sub[12]:
            st.caption("Merge-only. MGM gone after live → numbers stay.")
            lock = st.session_state.get("pregame_lock") or load_pregame()
            if not lock:
                st.info("Fetch while pregame to build lock.")
            else:
                items = sorted(lock.items(), key=lambda x: x[0])
                st.write(f"**{len(items)}** players locked")
                q = st.text_input("Filter player", key="lock_filter")
                cols = st.columns(2)
                shown = 0
                for player, entry in items:
                    if q and q.lower() not in player.lower():
                        continue
                    books = entry.get("books") or {}
                    lines = []
                    for b, info in sorted(books.items()):
                        p = info.get("price")
                        if p is not None:
                            end = info.get("ending")
                            end_s = f" ends {int(end):02d}" if end is not None else ""
                            lines.append(f"{book_label(b)} {format_odds(p)}{end_s}")
                    if not lines:
                        continue
                    with cols[shown % 2]:
                        ev = entry.get("event") or ""
                        st.markdown(
                            f'<div class="card grid-card"><b>{player}</b>'
                            f'{(" · " + ev) if ev else ""}<br>' + "<br>".join(lines) + "</div>",
                            unsafe_allow_html=True,
                        )
                    shown += 1
                if shown == 0:
                    st.info("No matches.")

    # ── NAME MAGIC (sub-tabs) ───────────────────────────────
    with tab_names:
        st.markdown('<div class="queen-banner">💅 Name Magic</div>', unsafe_allow_html=True)
        st.caption(f"Both need {NAME_METHODS_MIN}+ core + personal strong · different teams · max {NAME_MAX_PAIRS}")
        nsub = st.tabs(["💅 Same Init", "✨ Double Init", "🔄 Cross", "👩‍👧 Last Name", "👯 First Name"])
        with nsub[0]:
            render_card_grid([r for r in results if r["type"] == "same_init"])
        with nsub[1]:
            render_card_grid([r for r in results if r["type"] == "double_init"])
        with nsub[2]:
            render_card_grid([r for r in results if r["type"] == "cross"])
        with nsub[3]:
            render_card_grid([r for r in results if r["type"] == "last"])
        with nsub[4]:
            render_card_grid([r for r in results if r["type"] == "first"])

    # ── RESULTS (no raw HTML) ───────────────────────────────
    with tab_results:
        st.markdown('<div class="queen-banner">📊 Results Tracker</div>', unsafe_allow_html=True)
        st.caption("Wrong HIT? Recent graded → ↩️ Undo (TAKE IT → PENDING · manual HR deleted).")

        st.markdown("#### ⚡ Log a HR")
        lc1, lc2, lc3, lc4 = st.columns([2, 1, 1, 1])
        with lc1:
            hr_player = st.text_input("Player", placeholder="Paul Goldschmidt", key="hr_player")
        with lc2:
            hr_price = st.text_input("Price (blank = lock)", placeholder="475", key="hr_price")
        with lc3:
            hr_book = st.selectbox(
                "Book",
                ["betmgm", "bet365", "draftkings", "fanduel", "hardrockbet", "caesars", "untagged"],
                key="hr_book",
            )
        with lc4:
            st.write("")
            st.write("")
            if st.button("Log HIT", type="primary"):
                ok, msg = log_manual_hr(hr_player, hr_price, hr_book)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        rows = load_results()
        today_only = st.checkbox("Today only", value=True, key="res_today")
        rows_view = [r for r in rows if r.get("date") == today_az()] if today_only else rows

        pending = sorted(
            [r for r in rows_view if r.get("result") == "PENDING"],
            key=pending_sort_key,
        )
        done = [r for r in rows_view if r.get("result") in ("HIT", "MISS")]
        hits = sum(1 for r in done if r["result"] == "HIT")
        misses = sum(1 for r in done if r["result"] == "MISS")
        total_done = hits + misses
        rate = (hits / total_done * 100) if total_done else 0

        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{len(pending)}</div><div class="petty-label">⏳ PENDING</div></div>
            <div class="petty-box"><div class="petty-num">{hits}</div><div class="petty-label">🟢 HITS</div></div>
            <div class="petty-box"><div class="petty-num">{misses}</div><div class="petty-label">🔴 MISSES</div></div>
            <div class="petty-box"><div class="petty-num">{rate:.0f}%</div><div class="petty-label">HIT RATE</div></div>
        </div>
        """, unsafe_allow_html=True)

        method_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in done:
            for m in r.get("methods", []):
                if m == "Manual HR log": continue
                if r["result"] == "HIT": method_stats[m]["hit"] += 1
                else: method_stats[m]["miss"] += 1
        if method_stats:
            st.markdown("#### Method hit rates")
            lines = []
            for m, s in sorted(method_stats.items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
                t = s["hit"] + s["miss"]
                pct = s["hit"] / t * 100 if t else 0
                lines.append(f"**{m}**: {s['hit']}/{t} ({pct:.0f}%)")
            st.markdown(" · ".join(lines))

        total_p = len(pending)
        page = st.session_state.get("pending_page", 0)
        max_page = max(0, (total_p - 1) // PENDING_PAGE) if total_p else 0
        if page > max_page:
            page = 0
            st.session_state["pending_page"] = 0
        start = page * PENDING_PAGE
        end = min(start + PENDING_PAGE, total_p)
        slice_p = pending[start:end]

        st.markdown(f"#### Pending — **{start + 1 if total_p else 0}–{end} of {total_p}** (oldest first)")

        nav1, nav2, _ = st.columns([1, 1, 4])
        with nav1:
            if st.button("← Prev", disabled=page <= 0):
                st.session_state["pending_page"] = max(0, page - 1)
                st.rerun()
        with nav2:
            if st.button("Next →", disabled=page >= max_page):
                st.session_state["pending_page"] = min(max_page, page + 1)
                st.rerun()

        if not slice_p:
            st.info("No pending in this filter.")
        else:
            for r in slice_p:
                rid = r["id"]
                endg = r.get("ending")
                end_s = f" · ends {int(endg):02d}" if endg is not None else ""
                mgm_l = r.get("mgm_locked")
                mgm_s = f" · 🔒 MGM {format_odds(mgm_l)}" if mgm_l is not None else ""
                lock_s = locked_price_str(r["player"])
                st.markdown(
                    f"**{r['player']}** · {format_odds(r.get('best_price'))} "
                    f"{book_label(r.get('best_book'))}{end_s}{mgm_s} · score {r.get('score')} · {r.get('time', '')}"
                )
                if lock_s:
                    st.caption(f"🔒 {lock_s}")
                meths = r.get("methods") or []
                if meths:
                    st.caption(", ".join(meths[:6]))
                c1, c2, _ = st.columns([1, 1, 4])
                with c1:
                    if st.button("🟢 HIT", key=f"hit_{rid}"):
                        set_result_status(rid, "HIT")
                        st.rerun()
                with c2:
                    if st.button("🔴 MISS", key=f"miss_{rid}"):
                        set_result_status(rid, "MISS")
                        st.rerun()

        st.markdown("#### Recent graded / logged HRs")
        st.caption("↩️ Undo = TAKE IT → PENDING · manual HR deleted")
        if not done:
            st.info("None yet.")
        else:
            for r in reversed(done[-40:]):
                rid = r["id"]
                icon = "🟢" if r["result"] == "HIT" else "🔴"
                endg = r.get("ending")
                end_s = f" ends {int(endg):02d}" if endg is not None else ""
                src = " · manual" if r.get("source") == "manual_hr" else ""
                st.markdown(
                    f"{icon} **{r['player']}** · {format_odds(r.get('best_price'))} "
                    f"{book_label(r.get('best_book'))}{end_s}{src}"
                )
                u1, u2, u3, _ = st.columns([1, 1, 1, 3])
                with u1:
                    if st.button("↩️ Undo", key=f"undo_{rid}"):
                        undo_result(rid, r.get("source"))
                        st.rerun()
                with u2:
                    if r.get("result") != "HIT" and st.button("🟢 HIT", key=f"fix_hit_{rid}"):
                        set_result_status(rid, "HIT")
                        st.rerun()
                with u3:
                    if r.get("result") != "MISS" and st.button("🔴 MISS", key=f"fix_miss_{rid}"):
                        set_result_status(rid, "MISS")
                        st.rerun()

    # ── GLOSSARY (full, not stripped) ───────────────────────
    with tab_gloss:
        st.markdown('<div class="queen-banner">📖 The Code</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="how-to">
            <b>New here?</b> MLB Over 0.5 HR props · book patterns only.
            Expand each section. Gold = MGM · Green = DK · Blue = FD · Bright green = 365.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 1. The Board")
        with st.expander("🟢 TAKE IT vs ⚪ PASS", expanded=True):
            st.markdown("""
**TAKE IT** needs all of these:

- **2 or more core methods** (see section 2)
- **Edge pts ≥ 60**
- Over **0.5 HR** only (never 1.5 / 2.5)
- In RotoWire lineup when lineups are loaded

**PASS** = has 2+ core methods but edge is under 60.

**Score 0–100** ranks the board (methods + edge + bonuses like Last one left).
            """)
        with st.expander("📊 Edge pts"):
            st.markdown("""
**Edge pts** = best price minus the median across books.

- Outliers that are **150+** away from the pack are ignored for “best”
- You need **60 or more** edge pts for TAKE IT
- This is *not* a bankroll EV calculator — it is a gap score between books
            """)

        st.markdown("### 2. Core methods (count toward the 2+)")
        with st.expander("🎯 DraftKings 10s"):
            st.markdown("""
Flag any **DraftKings** pregame prop whose American odds **end in 10**  
(examples: +110, +210, +310, +410, +510).

No team requirement. Solo flag.
            """)
        with st.expander("🎰 BetMGM Classic Endings"):
            st.markdown("""
**Same team only.**

Valid endings: **00, 25, 50, 75**.

- **Pair (primary):** two players on the same team with the **same** ending
- **Group of three (fallback):** three on the same team sharing one ending when no pair exists

**Sticky / survivor (strong):**

- **Stayed in the group** / **Stayed in group Nx** = still in the same MGM ending group across fetches
- **Last one left** = was in an early group of 3+ and is still present later — often the one that hits
            """)
        with st.expander("💚 Bet365"):
            st.markdown("""
When the API returns Bet365:

- **B365 850** — prices that are 850 (or end in 850)
- **B365 Match 25 / 50 / 75** — same-team pairs or groups of 3 (like MGM, **no 00**)
- **B365 > HardRock** — Bet365 priced higher than Hard Rock on the same player
- Exact Match also includes 365 when prices line up
            """)
        with st.expander("🤝 Exact Match · ⭐ MGM Exact · 🔢 Digits"):
            st.markdown("""
**Exact Match** — same American price on 2+ books for the same player.

**MGM Exact** — two or more players on the **same team** with the **exact same** MGM price.

**Digits** — MGM same-team **pairs or groups of three** with endings **25, 50, or 75** only  
(not random 40s/60s).
            """)
        with st.expander("💙 FanDuel patterns"):
            st.markdown(f"""
Only if the player **already has** a DK or MGM core method:

- FanDuel **≥ +{FD_MIN}** ending in **10, 20, 30, 60, 70, or 90**
- Or exact **+600**

FanDuel alone does not count.
            """)
        with st.expander("📈 Signals"):
            st.markdown("""
**Counts as core when strong:**

- **Same on 3+ books**
- **Multi-book Shorten** (price dropping on 2+ books)

**Noise (does not count toward 2+):**

- **Multi-book Lengthen** (we do **not** like lengthening on multiple books)
- Single-book stuck / single outlier higher alone
            """)

        st.markdown("### 3. Noise (does NOT count toward 2+)")
        with st.expander("What is ignored for TAKE IT gating"):
            st.markdown("""
- Just Appeared / Added Late / Gone Missing  
- Not in lineup / In lineup · missing books  
- Price moved (single book)  
- FADE tags (shot way up, drop >100, FD highest)  
- FD under MGM (support trend only)  
- Multi-book Lengthen  
- Outlier / Stuck / Same ending chips that are not core
            """)

        st.markdown("### 4. Lock · Late · Fallen · Lineups")
        with st.expander("🔒 Pregame lock", expanded=True):
            st.markdown("""
Every **Fetch** **merges** player → book → price into `girl_magic_pregame.json`.

When a game goes live and **MGM (or any book) disappears from the API**, those rows are **not deleted**.

- **Gone Missing / Fallen** show 🔒 last pregame prices  
- **Log a HR** can leave price blank and pull from the lock for that book  
- Tab: **Odds Tricks → 🔒 Lock**
            """)
        with st.expander("👻 Late · 💀 Fallen · 📋 RotoWire"):
            st.markdown("""
**Late** — one card per player (Just Appeared / Added Late / Gone Missing), scoped to selected games.

**Fallen Off** — was on The Board, then left for this selection (often live feed / lost core methods).

**RotoWire** — free public lineups. Non-starters are filtered off The Board when loaded.  
Refresh the lineup button after lineup posts.
            """)

        st.markdown("### 5. Name Magic")
        with st.expander("Initials & names"):
            st.markdown(f"""
Only pairs where **both** players have:

- **{NAME_METHODS_MIN}+ core methods**
- At least one **personal strong** method (DK 10, MGM group/exact, FD pattern, B365, etc.)
- **Different teams** preferred (same team rare)

Types: Same Init · Double Init · Cross Init · Same Last · Same First  

Capped at **{NAME_MAX_PAIRS}** pairs per type. Jr. / Sr. ignored in names.
            """)

        st.markdown("### 6. Results · What's Going Today")
        with st.expander("📊 How to grade + Undo", expanded=True):
            st.markdown("""
**PENDING never deletes when a game goes live.**

- List is **oldest first**
- Use **Next →** until every pick has HIT or MISS
- **↩️ Undo** on Recent graded: TAKE IT grade → PENDING · manual HR log → deleted

**Log a HR** = anyone who went yard (even if never TAKE IT). Blank price uses 🔒 lock.

**What's Going Today** (top banner) = today’s HIT counts by **book + ending**  
(MGM 75, DK 10, 365 00, etc.). Color-coded by book. **Descriptive only — not a prediction.**
            """)

        st.markdown("### 7. First-timers")
        with st.expander("How to run a slate"):
            st.markdown(f"""
1. **Load Games** → select games → **Fetch Odds** (builds 🔒 while pregame)  
2. **Refresh RotoWire**  
3. **The Board** → TAKE IT rows  
4. **Odds Tricks** / **Name Magic** sub-tabs for deep dive  
5. After live: **Results** → grade **all** PENDING pages · **Undo** mistakes · **Log a HR** from lock  

Auto-refresh about every **{REFRESH_MINUTES}** minutes when the tab stays open.
            """)

    st.markdown(
        '<div class="footer">👑 Girl Magic · Boss Bitch · HBIC · Me & My Girls We Rolling</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
