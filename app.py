"""
Girl Magic Odds ✨
Boss Bitch • HBIC • Me & My Girls We Rolling

v3 — stricter cracker + tracker
- Bet365 shelved
- Core methods only: FD / DK / MGM
- Board: best per game · team · method (hard caps)
- Auto-fetch on timer (no babysitting)
- Pregame lock · Undo · Results paging
- Method & book hit-rate tracker (with n)
- Method-EV + simple Kelly on TAKE IT (when n is enough)
- Auto grade: stub for later (box scores)
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

st.set_page_config(
    page_title="Girl Magic Odds ✨",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background: linear-gradient(165deg, #0a0410 0%, #160a22 40%, #1f0b30 100%); color: #fce7f3; font-family: 'Inter', sans-serif; }
    h1 { font-family: 'Playfair Display', serif !important; font-weight: 900 !important;
         background: linear-gradient(90deg, #f9a8d4, #e879f9, #c084fc, #f472b6);
         -webkit-background-clip: text; -webkit-text-fill-color: transparent;
         font-size: 2.5rem !important; margin-bottom: 2px !important; }
    .subtitle { color: #f9a8d4; font-size: 0.9rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }
    .tagline { color: #e9d5ff; font-size: 0.85rem; font-style: italic; margin-bottom: 14px; opacity: 0.95; }
    .how-to { background: linear-gradient(135deg, #1a0f28 0%, #2a1040 100%); border: 1px solid #f472b6;
              border-radius: 14px; padding: 12px 16px; margin-bottom: 14px; font-size: 0.85rem; line-height: 1.45; }
    .how-to b { color: #f9a8d4; }
    .info-box { background: #1a0f28; border: 1px solid #a855f7; border-radius: 12px; padding: 10px 14px; margin-bottom: 10px; font-size: 0.88rem; }
    .warning-box { background: #3b0764; border: 2px solid #f472b6; border-radius: 12px; padding: 10px 14px; margin-bottom: 10px; font-size: 0.9rem; }
    .stButton > button { background: linear-gradient(90deg, #db2777, #9333ea) !important; color: white !important;
                         border: none !important; border-radius: 10px !important; font-weight: 700 !important; }
    .petty-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .petty-box { flex: 1; min-width: 68px; background: #1a0f28; border: 1px solid #f472b6; border-radius: 12px;
                 padding: 10px 6px; text-align: center; }
    .petty-num { font-size: 1.3rem; font-weight: 800; color: #f9a8d4; }
    .petty-label { font-size: 0.55rem; color: #e9d5ff; margin-top: 3px; }
    .rate-chip { display: inline-block; background: #1a0f28; border: 1px solid #a855f7; border-radius: 12px;
                 padding: 8px 12px; margin: 4px; text-align: center; min-width: 72px; }
    .rate-pct { font-size: 1.1rem; font-weight: 800; color: #f9a8d4; }
    .rate-name { font-size: 0.65rem; color: #e9d5ff; }
    .rate-n { font-size: 0.6rem; color: #c084fc; }
    .card { background: linear-gradient(155deg, #1a0f28, #251438); border: 1px solid #f472b6; border-radius: 12px;
            padding: 10px 12px; color: #fdf2f8; position: relative; font-size: 0.9rem; margin-bottom: 8px; }
    .card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
                    border-radius: 12px 0 0 12px; background: #f472b6; }
    .bet { background: linear-gradient(155deg, #0c2418, #143d28) !important; border-color: #34d399 !important; }
    .skip { background: #14101c !important; border-color: #4b5563 !important; opacity: 0.85; }
    .score-pill { display: inline-block; background: linear-gradient(90deg, #db2777, #9333ea); color: white;
                  font-weight: 800; font-size: 0.9rem; padding: 2px 10px; border-radius: 12px; margin-left: 6px; }
    .tag { display: inline-block; background: #3b0764; color: #f9a8d4; font-size: 0.68rem; font-weight: 700;
           padding: 2px 8px; border-radius: 10px; margin: 2px 3px 2px 0; border: 1px solid #a855f7; }
    .tag-dk { background: #064e3b; color: #6ee7b7; border-color: #34d399; }
    .tag-mgm { background: #422006; color: #fcd34d; border-color: #f59e0b; }
    .tag-fd { background: #1e3a5f; color: #93c5fd; border-color: #3b82f6; }
    .tag-match { background: #4c1d95; color: #e9d5ff; border-color: #a855f7; }
    .tag-strong { background: #14532d; color: #bbf7d0; border-color: #22c55e; font-weight: 800; }
    .queen-banner { display: inline-block; background: linear-gradient(90deg, #db2777, #9333ea); color: white;
                    font-size: 0.75rem; font-weight: 700; padding: 5px 14px; border-radius: 16px;
                    letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; }
    .meter { display: flex; gap: 3px; margin: 4px 0 6px 0; }
    .meter-bar { height: 6px; width: 16px; border-radius: 3px; background: #374151; }
    .meter-bar.filled-high { background: linear-gradient(90deg, #f472b6, #c026d3); }
    .meter-bar.filled-strong { background: linear-gradient(90deg, #e879f9, #a855f7); }
    .meter-bar.filled-medium { background: linear-gradient(90deg, #c084fc, #7c3aed); }
    .meter-bar.filled-low { background: #6b7280; }
    .stTabs [data-baseweb="tab"] { background: #1a0f28; border-radius: 8px; color: #f9a8d4; font-weight: 600;
                                   padding: 6px 8px; font-size: 0.75rem; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #db2777, #9333ea) !important; color: white !important; }
    .footer { text-align: center; color: #f9a8d4; font-size: 0.9rem; margin-top: 28px; opacity: 0.9; padding-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ── constants ────────────────────────────────────────────────
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
REGIONS = "us,us2"
HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"

# Books we pull (Bet365 shelved from methods — still ok if API returns it, we ignore tricks)
PREFERRED = {"fanduel", "draftkings", "betmgm", "hardrockbet", "caesars"}
CORE_BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM"}
LATE_BOOKS = {"fanduel", "draftkings", "betmgm"}

EDGE_MIN = 60
METHODS_MIN = 2
OUTLIER_GAP = 150
REFRESH_MINUTES = 20
FD_MIN = 400
MOVE_PRICE_MIN = 500
MOVE_MIN = 40
BIG_MOVE = 100
PENDING_PAGE = 40
KELLY_MIN_N = 12          # need this many graded plays for a method before Kelly shows
BOARD_MAX_PER_TEAM = 2
BOARD_MAX_PER_GAME = 6

PERSONAL_STRONG = {
    "DK 10", "DK FD-style", "FD Pattern", "FD 600",
    "Exact Match", "MGM Exact",
    "Match 00", "Match 25", "Match 50", "Match 75",
    "MGM 00", "MGM 25", "MGM 50", "MGM 75",
    "Last one left", "Stayed in the group", "Multi-book Shorten", "Same on 3+ books",
    "Multi-book method",
}
NOISE_METHODS = {
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup",
    "In lineup · missing books", "Price moved", "Multi-book Lengthen",
    "FADE · Shot way up", "FADE · Drop >100", "FADE · FD highest",
    "FD under MGM", "Shortening", "Lengthening", "Stuck price", "Outlier higher",
}

FD_ENDINGS = (10, 20, 30, 60, 70, 90)
MGM_ENDINGS = (0, 25, 50, 75)

# ── helpers ──────────────────────────────────────────────────
def is_core_method(m):
    if m in NOISE_METHODS:
        return False
    if m.startswith("FADE") or m.startswith("FD under"):
        return False
    if m.startswith("Stayed ") and "group" not in m.lower():
        return False
    if m.startswith("Outlier") or m.startswith("Stuck") or m.startswith("Same ending"):
        return False
    if m.startswith("Shortening") or m.startswith("Lengthening"):
        return False
    return True

def count_core_methods(meths):
    return len([m for m in set(meths) if is_core_method(m)])

def has_personal_strong(meths):
    return any(
        m in PERSONAL_STRONG or m.startswith("Match ") or m.startswith("MGM ")
        for m in meths
    )

def has_dk_or_mgm(meths):
    for m in meths:
        if m in ("DK 10", "DK FD-style"):
            return True
        if m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m:
            return True
        if m.startswith("Match "):
            return True
    return False

def method_tag_class(m):
    m = str(m)
    if m.startswith("DK"):
        return "tag-dk"
    if m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m:
        return "tag-mgm"
    if m.startswith("FD"):
        return "tag-fd"
    if m in ("Exact Match", "MGM Exact") or m.startswith("Match "):
        return "tag-match"
    if "Multi-book" in m or m == "Same on 3+ books" or m == "Multi-book method":
        return "tag-strong"
    return ""

def render_method_tags(methods, limit=6):
    return "".join(
        f'<span class="tag {method_tag_class(m)}">{m}</span>'
        for m in list(methods)[:limit]
    )

def girl_magic_score(core_count, edge, methods):
    method_pts = min(core_count, 5) * 10
    edge_pts = min(40, max(0, int((edge / 180) * 40)))
    bonus = 0
    if "Last one left" in methods:
        bonus += 5
    if any("Stayed in group" in m or m == "Stayed in the group" for m in methods):
        bonus += 3
    if "Multi-book method" in methods or "Multi-book Shorten" in methods:
        bonus += 4
    if "Same on 3+ books" in methods:
        bonus += 2
    if "FD 600" in methods:
        bonus += 2
    return min(100, method_pts + edge_pts + min(12, bonus))

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
    except Exception:
        return str(p)

def last_two(p):
    try:
        return abs(int(p)) % 100
    except Exception:
        return None

def book_label(b):
    b = str(b or "").lower()
    if "betmgm" in b or b == "mgm":
        return "MGM"
    if "draftkings" in b or b == "dk":
        return "DK"
    if "fanduel" in b or b == "fd":
        return "FD"
    if "hardrock" in b:
        return "HardRock"
    if "caesars" in b:
        return "Caesars"
    if b in ("untagged", "unknown", "—", ""):
        return "Untagged"
    return b.title() if b else "Untagged"

def clean_name(name):
    name = str(name).strip()
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
    parts = name.split()
    if parts and parts[-1].lower().rstrip(".") in suffixes:
        parts = parts[:-1]
    return " ".join(parts)

def clean_team(tid):
    if not tid:
        return ""
    return str(tid).replace("_MLB", "").replace("_", " ").strip()

def now_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%I:%M %p")

def today_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def smart_best(prices, books):
    if not prices:
        return None, None
    paired = sorted(zip(prices, books), key=lambda x: x[0], reverse=True)
    best_p, best_b = paired[0]
    if len(paired) >= 2 and best_p - paired[1][0] >= OUTLIER_GAP:
        return paired[1][0], paired[1][1]
    return best_p, best_b

def get_confidence(score, is_bet):
    if not is_bet:
        return "Skip", 1, "low"
    if score >= 85:
        return "High", 5, "high"
    if score >= 70:
        return "Strong", 4, "strong"
    if score >= 55:
        return "Medium", 3, "medium"
    return "Low", 2, "low"

def make_meter(bars, level):
    html = '<div class="meter">'
    for i in range(5):
        filled = f"filled-{level}" if i < bars else ""
        html += f'<div class="meter-bar {filled}"></div>'
    return html + "</div>"

def event_matches_chosen(ev, chosen):
    if not chosen:
        return True
    if ev in chosen:
        return True
    ev_l = str(ev).lower()
    for c in chosen:
        c_l = str(c).lower()
        parts_c = [p.strip() for p in c_l.split("@")]
        if len(parts_c) == 2 and parts_c[0] in ev_l and parts_c[1] in ev_l:
            return True
    return False

def name_in_lineup(player, lineup_names):
    if not lineup_names:
        return None
    cn = clean_name(player)
    if cn in lineup_names:
        return True
    parts = cn.split()
    if len(parts) >= 2:
        last, fi = parts[-1].lower(), parts[0][0].lower()
        for ln in lineup_names:
            lp = ln.split()
            if len(lp) >= 2 and lp[-1].lower() == last and lp[0][0].lower() == fi:
                return True
    return False

def american_to_decimal(american):
    try:
        a = int(american)
    except Exception:
        return None
    if a > 0:
        return 1 + a / 100.0
    return 1 + 100.0 / abs(a)

def implied_prob(american):
    dec = american_to_decimal(american)
    if not dec:
        return None
    return 1.0 / dec

def kelly_fraction(p_win, american):
    """Fractional Kelly using method hit rate as p. Returns f in 0..1 or None."""
    if p_win is None or p_win <= 0 or p_win >= 1:
        return None
    try:
        a = int(american)
    except Exception:
        return None
    if a > 0:
        b = a / 100.0
    else:
        b = 100.0 / abs(a)
    q = 1 - p_win
    f = (b * p_win - q) / b
    if f <= 0:
        return 0.0
    return min(0.25, f)  # quarter-Kelly cap for safety

# ── pregame lock ─────────────────────────────────────────────
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
    today, ts = today_az(), now_utc_iso()
    for _, r in df.iterrows():
        player = clean_name(r["player"])
        book = str(r["book"]).lower()
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
    parts = []
    for b, info in sorted(books.items()):
        p = info.get("price")
        if p is not None:
            parts.append(f"{book_label(b)} {format_odds(p)}")
    return " · ".join(parts)

# ── history / results ────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        saved_at = data.get("saved_at")
        if saved_at:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(saved_at)
            if age > timedelta(hours=HISTORY_MAX_AGE_HOURS):
                return
        pr = []
        for snap in data.get("presence_history", []):
            s = set()
            for item in snap:
                if len(item) >= 3:
                    s.add((item[0], item[1], item[2]))
                elif len(item) == 2:
                    s.add((item[0], item[1], ""))
            pr.append(s)
        st.session_state["presence_history"] = pr[-12:]
        ph = [{tuple(k.split("||", 1)): v for k, v in snap.items()} for snap in data.get("price_history", [])]
        st.session_state["price_history"] = ph[-8:]
        mh = []
        for snap in data.get("mgm_history", []):
            mh.append([
                {"event": g["event"], "ending": g["ending"], "team": g.get("team", ""), "players": frozenset(g["players"])}
                for g in snap
            ])
        st.session_state["mgm_history"] = mh[-8:]
        if "prev_ev" in data:
            st.session_state["prev_ev"] = data["prev_ev"]
    except Exception:
        pass

def save_history(prev_ev=None):
    try:
        ph = [{f"{a}||{b}": v for (a, b), v in snap.items()} for snap in st.session_state.get("price_history", [])]
        pr = [[[a, b, e] for (a, b, e) in snap] for snap in st.session_state.get("presence_history", [])]
        mh = [
            [{"event": g["event"], "ending": g["ending"], "team": g.get("team", ""), "players": list(g["players"])} for g in snap]
            for snap in st.session_state.get("mgm_history", [])
        ]
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
        if any(
            r.get("date") == today and r.get("player") == item["player"] and r.get("source") != "manual_hr"
            for r in rows
        ):
            continue
        locked = get_locked(item["player"])
        price = item.get("best_price")
        rows.append({
            "id": f"{today}_{item['player']}_{int(item['score'])}",
            "date": today,
            "time": now_az(),
            "player": item["player"],
            "score": item["score"],
            "edge": int(item["edge"]),
            "best_price": price,
            "best_book": item.get("best_book", ""),
            "ending": last_two(price),
            "mgm_locked": locked.get("mgm_price"),
            "mgm_ending": locked.get("mgm_ending"),
            "methods": item["methods"],
            "core": item.get("method_count", 0),
            "result": "PENDING",
            "source": "take_it",
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
        return False, "Need a valid price (or lock)"
    book = (book or "untagged").strip().lower()
    ending = last_two(price)
    rid = f"hr_{today}_{player}_{price}_{book}_{len(rows)}"
    rows.append({
        "id": rid,
        "date": today,
        "time": now_az(),
        "player": player,
        "score": None,
        "edge": None,
        "best_price": price,
        "best_book": book,
        "ending": ending,
        "methods": ["Manual HR log"],
        "core": 0,
        "result": "HIT",
        "source": "manual_hr",
        "logged_at": now_utc_iso(),
    })
    save_results(rows)
    return True, f"Logged {player} {format_odds(price)} {book_label(book)} ends {ending:02d}"

def pending_sort_key(r):
    return (r.get("date") or "", r.get("time") or "", r.get("logged_at") or "", r.get("player") or "")

def build_tracker_stats(rows):
    """Method + best-book hit rates with n. Untagged skipped for books."""
    done = [r for r in rows if r.get("result") in ("HIT", "MISS") and r.get("source") != "manual_hr"]
    method_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    book_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    ending_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    for r in done:
        is_hit = r["result"] == "HIT"
        for m in r.get("methods") or []:
            if m == "Manual HR log" or m in NOISE_METHODS:
                continue
            if is_hit:
                method_stats[m]["hit"] += 1
            else:
                method_stats[m]["miss"] += 1
        bb = book_label(r.get("best_book"))
        if bb != "Untagged":
            if is_hit:
                book_stats[bb]["hit"] += 1
            else:
                book_stats[bb]["miss"] += 1
        end = r.get("ending")
        if end is None and r.get("best_price") is not None:
            end = last_two(r["best_price"])
        if end is not None:
            key = f"{int(end):02d}"
            if is_hit:
                ending_stats[key]["hit"] += 1
            else:
                ending_stats[key]["miss"] += 1
    return method_stats, book_stats, ending_stats

def method_hit_rate(method_stats, method_name):
    s = method_stats.get(method_name)
    if not s:
        return None, 0
    t = s["hit"] + s["miss"]
    if t == 0:
        return None, 0
    return s["hit"] / t, t

def best_method_rate_for_player(methods, method_stats):
    """Pick the strongest method rate among this player's core methods."""
    best_p, best_n, best_m = None, 0, None
    for m in methods:
        if not is_core_method(m):
            continue
        p, n = method_hit_rate(method_stats, m)
        if p is None:
            continue
        if best_p is None or p > best_p or (p == best_p and n > best_n):
            best_p, best_n, best_m = p, n, m
    return best_p, best_n, best_m

# ── APIs ─────────────────────────────────────────────────────
def fetch_rotowire_lineups():
    if not HAS_BS4:
        return set(), "Install beautifulsoup4"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
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
                    if "player" not in href.lower():
                        continue
                    t = a.get_text(strip=True)
                    if t and len(t.split()) >= 2 and not re.search(r"\d", t):
                        names.add(clean_name(t))
        return names, f"RotoWire · {len(names)} names"
    except Exception as e:
        return set(), f"RotoWire error: {e}"

def fetch_events_oddsapi(api_key):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/baseball_mlb/events",
            params={"apiKey": api_key},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Odds API events error: {e}")
        return []

def fetch_odds_oddsapi(api_key, event_id):
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/baseball_mlb/events/{event_id}/odds",
            params={
                "apiKey": api_key,
                "regions": REGIONS,
                "markets": "batter_home_runs",
                "oddsFormat": "american",
            },
            timeout=20,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
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
                    "event": event,
                    "book": bk,
                    "player": o.get("description"),
                    "price": o.get("price"),
                    "point": 0.5,
                    "team": "",
                    "source": "oddsapi",
                })
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(
            f"{SGO_BASE}/events",
            params={"apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 25},
            timeout=25,
        )
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
                pdata = players_map[pid]
                pname = pdata.get("name")
                if not pname:
                    continue
                team = clean_team(pdata.get("teamID") or "")
                for bk, bd in odd_data.get("byBookmaker", {}).items():
                    if not bd.get("available", True):
                        continue
                    b = bk.lower()
                    if "bet365" in b:
                        continue  # shelved
                    if b not in PREFERRED:
                        continue
                    price = bd.get("odds")
                    if price is None:
                        continue
                    try:
                        price = int(str(price).replace("+", ""))
                    except Exception:
                        continue
                    found.add(b)
                    rows.append({
                        "event": event_name,
                        "book": b,
                        "player": pname,
                        "price": price,
                        "point": 0.5,
                        "team": team,
                        "source": "sgo",
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
        if not eid:
            continue
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
    found = all_found & PREFERRED
    return df, found

def build_team_map(df):
    tm = {}
    for _, r in df.iterrows():
        if r.get("team"):
            tm[r["player"]] = r["team"]
    return tm

# ── flags (core methods only) ────────────────────────────────
def run_flags(df, previous_df=None, record_history=True, selected_events=None):
    if df.empty:
        return [], [], []

    if "team" not in df.columns:
        df["team"] = ""
    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results, methods_map = [], defaultdict(list)
    all_players_now = set(df["player"].unique())
    selected = set(selected_events) if selected_events else set(df["event"].unique())
    team_map = build_team_map(df)
    lineup_names = st.session_state.get("lineup_names", set())
    signal_bucket = defaultdict(list)
    signal_methods = defaultdict(set)

    for k in ("presence_history", "price_history", "mgm_history"):
        if k not in st.session_state:
            st.session_state[k] = []

    current_presence = {
        (r["player"], r["book"], r["event"])
        for _, r in df.iterrows()
        if r["book"] in LATE_BOOKS
    }
    current_prices = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}

    if record_history:
        st.session_state["presence_history"].append(current_presence)
        st.session_state["presence_history"] = st.session_state["presence_history"][-12:]
        st.session_state["price_history"].append(current_prices)
        st.session_state["price_history"] = st.session_state["price_history"][-8:]

    hist = st.session_state["presence_history"]
    phist = st.session_state["price_history"]

    # Late / gone (with lock note)
    if len(hist) >= 2:
        def norm(snap):
            out = set()
            for item in snap:
                if len(item) == 3:
                    out.add(item)
                elif len(item) == 2:
                    out.add((item[0], item[1], ""))
            return out

        def scoped(snap):
            s = set()
            for p, b, e in norm(snap):
                if e and selected and not event_matches_chosen(e, selected):
                    continue
                if not e and selected:
                    continue
                s.add((p, b, e))
            return s

        latest, previous = scoped(hist[-1]), scoped(hist[-2])
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
        for player, book, event in previous - latest:
            add_late(player, book, event, "Gone Missing")

        for player, info in sorted(late_bucket.items()):
            books = sorted(set(info["books"]))
            kind = info["kind"]
            lock_note = locked_price_str(player)
            reason = f"{kind} · {', '.join(books)}"
            if lock_note and kind == "Gone Missing":
                reason += f"<br>🔒 last pregame: {lock_note}"
            results.append({
                "type": "late",
                "label": player,
                "reason": reason,
                "event": info.get("event", ""),
                "methods": [kind],
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
                    "type": "late",
                    "label": player,
                    "reason": "⚠️ On books but NOT in RotoWire lineup",
                    "event": "",
                    "methods": ["Not in lineup"],
                })
                methods_map[player].append("Not in lineup")

    # Movement (500+)
    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        player_up, player_down = defaultdict(list), defaultdict(list)
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap:
                continue
            prev_price = prev_snap[key]
            if abs(prev_price) < MOVE_PRICE_MIN and abs(curr_price) < MOVE_PRICE_MIN:
                continue
            delta = curr_price - prev_price
            if abs(delta) < MOVE_MIN:
                continue
            line = f"{book}: {format_odds(prev_price)} → {format_odds(curr_price)} ({int(abs(delta))} pts)"
            (player_up if delta > 0 else player_down)[player].append(line)
            if delta >= BIG_MOVE:
                results.append({
                    "type": "trend",
                    "trend_kind": "fade",
                    "label": player,
                    "reason": f"🔴 Shot way up on {book}: {format_odds(prev_price)} → {format_odds(curr_price)}",
                    "methods": ["FADE · Shot way up"],
                    "gap": abs(int(delta)),
                })
            elif delta <= -BIG_MOVE:
                results.append({
                    "type": "trend",
                    "trend_kind": "fade",
                    "label": player,
                    "reason": f"🔴 Dropped >100 on {book}: {format_odds(prev_price)} → {format_odds(curr_price)}",
                    "methods": ["FADE · Drop >100"],
                    "gap": abs(int(delta)),
                })
        for player, moves in sorted(player_up.items()):
            results.append({
                "type": "hist",
                "move_dir": "up",
                "label": player,
                "reason": "<br>".join(moves),
                "methods": ["Price moved"],
            })
        for player, moves in sorted(player_down.items()):
            results.append({
                "type": "hist",
                "move_dir": "down",
                "label": player,
                "reason": "<br>".join(moves),
                "methods": ["Price moved"],
            })

    # FD under MGM (tracked support, not core)
    for player, g in df.groupby("player"):
        by_book = {r["book"]: r["price"] for _, r in g.iterrows()}
        fd = by_book.get("fanduel")
        mgm_price = next((v for k, v in by_book.items() if "betmgm" in k or k == "mgm"), None)
        others = [v for b, v in by_book.items() if b != "fanduel"]
        if fd is not None and mgm_price is not None:
            gap = mgm_price - fd
            if 10 <= gap <= 100:
                results.append({
                    "type": "trend",
                    "trend_kind": "good",
                    "label": player,
                    "reason": f"💚 FD under MGM by {int(gap)} · FD {format_odds(fd)} · MGM {format_odds(mgm_price)}",
                    "methods": ["FD under MGM"],
                    "gap": int(gap),
                })
        if fd is not None and others and fd > max(others):
            results.append({
                "type": "trend",
                "trend_kind": "fade",
                "label": player,
                "reason": f"🔴 FD highest of all · FD {format_odds(fd)}",
                "methods": ["FADE · FD highest"],
                "gap": 0,
            })

    # DK 10 + DK FD-style endings
    for _, row in df.iterrows():
        if row["book"] != "draftkings":
            continue
        d = last_two(row["price"])
        if d == 10:
            results.append({
                "type": "dk",
                "label": row["player"],
                "reason": f"DK ends in 10 → {format_odds(row['price'])}",
                "event": row["event"],
                "methods": ["DK 10"],
            })
            methods_map[row["player"]].append("DK 10")
        elif d in FD_ENDINGS:
            results.append({
                "type": "dk",
                "label": row["player"],
                "reason": f"DK FD-style ends in {d:02d} → {format_odds(row['price'])}",
                "event": row["event"],
                "methods": ["DK FD-style"],
            })
            methods_map[row["player"]].append("DK FD-style")

    # MGM groups
    mgm = df[df["book"].str.contains("betmgm|mgm", case=False, na=False)].copy()
    current_mgm = []
    group_key = ["event", "team"] if mgm["team"].astype(str).str.len().gt(0).any() else ["event"]
    if not mgm.empty:
        for keys, g in mgm.groupby(group_key, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            event = keys[0]
            team = keys[1] if len(keys) > 1 else ""
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in MGM_ENDINGS:
                    ends[d].append(r["player"])
            for d, ps in ends.items():
                names = sorted(set(ps))
                if len(names) < 2:
                    continue
                current_mgm.append({
                    "event": event,
                    "ending": d,
                    "team": team if isinstance(team, str) else "",
                    "players": frozenset(names),
                })

    if record_history:
        st.session_state["mgm_history"].append(current_mgm)
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

    for grp in current_mgm:
        names = sorted(grp["players"])
        if len(names) not in (2, 3) and len(names) < 2:
            continue
        # prefer pairs; allow group of 3; if >3 still show but tag as group
        d = grp["ending"]
        team = grp.get("team") or ""
        meth = [f"MGM {d:02d}", f"Match {d:02d}" if d != 0 else "Match 00"]
        extra = []
        for n in names:
            c = mgm_stayed.get(n, 0)
            if c >= 2:
                meth.append("Stayed in the group")
                extra.append("Stayed in the group")
            if n in survivor:
                meth.append("Last one left")
                extra.append("Last one left")
        kind = "pair" if len(names) == 2 else f"group of {len(names)}"
        tnote = f" · {team}" if team else " · same team"
        reason = f"MGM {kind} ends in {d:02d}{tnote}"
        if extra:
            reason += " • " + " + ".join(sorted(set(extra)))
        results.append({
            "type": "mgm",
            "label": " + ".join(names),
            "reason": reason,
            "event": grp["event"],
            "methods": list(set(meth)),
        })
        for n in names:
            methods_map[n].extend(meth)

        # digits tab uses same
        if len(names) in (2, 3) and d in (25, 50, 75, 0):
            results.append({
                "type": "digit",
                "label": " + ".join(names),
                "reason": f"Digit {kind} ends in {d:02d}{tnote}",
                "event": grp["event"],
                "methods": [f"Match {d:02d}" if d != 0 else "Match 00"],
            })

    # MGM exact same price
    if not mgm.empty:
        gk = ["event", "team"] if mgm["team"].astype(str).str.len().gt(0).any() else ["event"]
        for keys, g in mgm.groupby(gk, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            event = keys[0]
            team = keys[1] if len(keys) > 1 else ""
            for price, pg in g.groupby("price"):
                names = sorted(pg["player"].unique())
                if len(names) >= 2:
                    tnote = f" · {team}" if team else ""
                    results.append({
                        "type": "mgm_exact",
                        "label": " + ".join(names),
                        "reason": f"MGM Exact {format_odds(price)} ({len(names)}){tnote}",
                        "event": event,
                        "methods": ["MGM Exact"],
                    })
                    for n in names:
                        methods_map[n].append("MGM Exact")

    # Exact match any books
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        prices = g["price"].dropna().tolist()
        if len(set(prices)) == 1:
            results.append({
                "type": "match",
                "label": player,
                "reason": f"Exact match {format_odds(prices[0])} → {', '.join(g['book'])}",
                "event": g["event"].iloc[0],
                "methods": ["Exact Match"],
            })
            methods_map[player].append("Exact Match")

    # FanDuel patterns (only with DK or MGM)
    for _, row in df.iterrows():
        if row["book"] != "fanduel":
            continue
        player = row["player"]
        if not has_dk_or_mgm(methods_map.get(player, [])):
            continue
        price = abs(int(row["price"])) if row["price"] else 0
        last = last_two(row["price"])
        if price == 600:
            results.append({
                "type": "fd",
                "label": player,
                "reason": f"FD +600 chalk (has DK/MGM) → {format_odds(row['price'])}",
                "event": row["event"],
                "methods": ["FD 600"],
            })
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in FD_ENDINGS:
            results.append({
                "type": "fd",
                "label": player,
                "reason": f"FD ≥ +{FD_MIN} ends {last:02d} (has DK/MGM) → {format_odds(row['price'])}",
                "event": row["event"],
                "methods": ["FD Pattern"],
            })
            methods_map[player].append("FD Pattern")

    # Multi-book method boost
    for player, ms in list(methods_map.items()):
        core = [m for m in set(ms) if is_core_method(m)]
        books_hit = set()
        for m in core:
            if m.startswith("DK"):
                books_hit.add("dk")
            if m.startswith("MGM") or m.startswith("Match ") or m == "MGM Exact":
                books_hit.add("mgm")
            if m.startswith("FD"):
                books_hit.add("fd")
        if len(books_hit) >= 2:
            methods_map[player].append("Multi-book method")
            signal_bucket[player].append(f"Methods on {len(books_hit)} books")
            signal_methods[player].add("Multi-book method")

    # Multi-book shorten (core-ish)
    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        down_by = defaultdict(list)
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap:
                continue
            delta = curr_price - prev_snap[key]
            if delta <= -MOVE_MIN:
                down_by[player].append(book)
        for player, books in down_by.items():
            if len(books) >= 2:
                methods_map[player].append("Multi-book Shorten")
                signal_bucket[player].append(f"Shorten on {', '.join(books)}")
                signal_methods[player].add("Multi-book Shorten")

    for player in sorted(signal_bucket.keys()):
        results.append({
            "type": "signal",
            "label": player,
            "reason": "<br>".join(signal_bucket[player]),
            "methods": list(signal_methods[player]),
        })

    # Board candidates
    player_events = defaultdict(set)
    for _, r in df.iterrows():
        player_events[r["player"]].add(r["event"])

    ev_board = []
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if lineup_names and name_in_lineup(player, lineup_names) is False:
            continue
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 2:
            continue
        best, best_book = smart_best(prices, books)
        if best is None:
            continue
        try:
            med = statistics.median(prices)
        except Exception:
            med = best
        edge = best - med
        meths = list(set(methods_map.get(player, [])))
        core_count = count_core_methods(meths)
        if core_count < METHODS_MIN:
            continue
        is_bet = edge >= EDGE_MIN
        display_meths = [m for m in meths if is_core_method(m)]
        score = girl_magic_score(core_count, edge, display_meths)
        conf, bars, level = get_confidence(score, is_bet)
        why = (
            f"Score {score}/100 · {core_count} core · edge {int(edge)}."
            if is_bet
            else f"Score {score}/100 · {core_count} core · edge {int(edge)} (need {EDGE_MIN}+)."
        )
        ev_board.append({
            "player": player,
            "best_price": best,
            "best_book": best_book,
            "median": med,
            "edge": edge,
            "is_bet": is_bet,
            "why": why,
            "methods": display_meths,
            "score": score,
            "bars": bars,
            "level": level,
            "method_count": core_count,
            "team": team_map.get(player, ""),
            "events": list(player_events.get(player, [])),
            "event": next(iter(player_events.get(player, [])), ""),
        })

    # Strict board: best per team / game
    ev_board = tighten_board(ev_board)

    current_ev = {
        item["player"]: {
            "methods": item["methods"],
            "edge": item["edge"],
            "is_bet": item["is_bet"],
            "method_count": item["method_count"],
            "score": item["score"],
            "events": item.get("events", []),
        }
        for item in ev_board
    }

    prev_ev = st.session_state.get("prev_ev", {})
    fallen = []
    for player, old in prev_ev.items():
        if player in current_ev:
            continue
        old_events = old.get("events") or []
        if selected and old_events and not any(event_matches_chosen(e, selected) for e in old_events):
            continue
        lock_note = locked_price_str(player)
        reasons = []
        if player not in all_players_now:
            reasons.append("Left live feed (often MGM after first pitch)")
            if lock_note:
                reasons.append(f"🔒 {lock_note}")
        else:
            reasons.append("Dropped under strict filters")
        if old.get("is_bet"):
            reasons.insert(0, "Was TAKE IT")
        fallen.append({
            "type": "fallen",
            "label": player,
            "reason": " · ".join(reasons),
            "methods": ["Fallen Off"],
            "old_score": old.get("score", 0),
        })
        results.append(fallen[-1])

    if record_history:
        st.session_state["prev_ev"] = current_ev
        save_history(prev_ev=current_ev)

    return results, ev_board, fallen

def tighten_board(ev_board):
    """Max per team / per game; multi-method and higher score first."""
    if not ev_board:
        return []
    ranked = sorted(
        ev_board,
        key=lambda x: (
            not x["is_bet"],
            -x["method_count"],
            -x["score"],
            -x["edge"],
        ),
    )
    per_team = defaultdict(int)
    per_game = defaultdict(int)
    out = []
    for item in ranked:
        team = item.get("team") or "UNK"
        game = item.get("event") or (item.get("events") or ["UNK"])[0]
        if per_team[team] >= BOARD_MAX_PER_TEAM:
            continue
        if per_game[game] >= BOARD_MAX_PER_GAME:
            continue
        # prefer multi-method for TAKE IT slots
        if item["is_bet"] and item["method_count"] < METHODS_MIN:
            continue
        out.append(item)
        per_team[team] += 1
        per_game[game] += 1
    return out

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
    st.markdown('<p class="subtitle">Boss Bitch • HBIC • Me & My Girls We Rolling</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Where odds intuition meets Petty precision.</p>', unsafe_allow_html=True)

    lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
    st.markdown(f"""
    <div class="how-to">
        <b>Auto-fetch</b> every {REFRESH_MINUTES} min · <b>Bet365 shelved</b> · Board capped per team/game<br>
        🔒 Pregame lock: <b>{lock_n}</b> · Tracker + Kelly when n≥{KELLY_MIN_N} · Auto-grade <i>coming later</i>
    </div>
    """, unsafe_allow_html=True)

    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add The Odds API key.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("① Load Games", type="primary"):
            st.session_state["events"] = fetch_events_oddsapi(odds_key)
    with c2:
        if st.button("📋 Lineups"):
            with st.spinner("RotoWire…"):
                names, msg = fetch_rotowire_lineups()
                st.session_state["lineup_names"] = names
                st.session_state["lineup_msg"] = msg
            st.success(msg) if names else st.warning(msg)
    with c3:
        auto_lineups = st.checkbox("Auto lineups on fetch", value=True)

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** once. After that, odds auto-refresh.")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
    chosen = st.multiselect("② Games (leave all selected for full slate)", list(options.keys()), default=default_sel or list(options.keys())[:8])
    st.session_state["selected_games"] = chosen

    manual_fetch = st.button("③ Fetch now", type="primary")
    if "last_refresh_count" not in st.session_state:
        st.session_state["last_refresh_count"] = refresh_count
    auto_fetch = HAS_AUTOREFRESH and refresh_count != st.session_state["last_refresh_count"] and bool(chosen)
    # also auto-fetch once if we have games but no odds yet
    first_load = bool(chosen) and not st.session_state.get("odds") and st.session_state.get("auto_once") is not False
    if auto_fetch:
        st.session_state["last_refresh_count"] = refresh_count
    if first_load:
        st.session_state["auto_once"] = False
        auto_fetch = True

    if (manual_fetch or auto_fetch) and chosen:
        with st.spinner("Fetching…"):
            if auto_lineups or not st.session_state.get("lineup_names"):
                names, msg = fetch_rotowire_lineups()
                if names:
                    st.session_state["lineup_names"] = names
                    st.session_state["lineup_msg"] = msg
            df, found = do_fetch(odds_key, sgo_key, chosen, options)
        if df is not None and not df.empty:
            update_pregame_lock(df)
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["found_books"] = sorted(found)
            st.session_state["last_selected"] = list(chosen)
            st.session_state["new_fetch"] = True
            st.session_state["last_fetch_time"] = now_az()
            st.success(f"Loaded {len(df)} props · {now_az()} AZ · lock {len(st.session_state.get('pregame_lock', {}))}")
        else:
            st.warning("No 0.5 HR odds this pull.")

    if st.session_state.get("last_fetch_time"):
        st.caption(f"Last fetch: {st.session_state['last_fetch_time']} AZ · next auto ~{REFRESH_MINUTES} min")

    found = st.session_state.get("found_books", [])
    if found:
        missing = [CORE_BOOKS[b] for b in CORE_BOOKS if b not in found]
        st.markdown(f'<div class="info-box"><b>Books:</b> {", ".join(found)}</div>', unsafe_allow_html=True)
        if missing:
            st.markdown(f'<div class="warning-box">⚠️ Missing: {", ".join(missing)}</div>', unsafe_allow_html=True)

    odds = st.session_state.get("odds", [])
    prev = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(prev) if prev else None
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, fallen = (
        run_flags(df, prev_df, record_history=new_fetch, selected_events=selected_events)
        if not df.empty
        else ([], [], [])
    )
    if ev_board:
        log_bet_this(ev_board)

    method_stats, book_stats, ending_stats = build_tracker_stats(load_results())

    # attach Kelly / method EV to board items
    for item in ev_board:
        p, n, mname = best_method_rate_for_player(item["methods"], method_stats)
        item["method_p"] = p
        item["method_n"] = n
        item["method_rate_name"] = mname
        if p is not None and n >= KELLY_MIN_N:
            item["kelly"] = kelly_fraction(p, item["best_price"])
            market_p = implied_prob(item["best_price"])
            item["method_ev"] = (p * (american_to_decimal(item["best_price"]) - 1) - (1 - p)) if market_p else None
        else:
            item["kelly"] = None
            item["method_ev"] = None

    take_n = len([e for e in ev_board if e["is_bet"]])
    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box"><div class="petty-num">{take_n}</div><div class="petty-label">🟢 TAKE IT</div></div>
        <div class="petty-box"><div class="petty-num">{len([r for r in results if r['type']=='mgm'])}</div><div class="petty-label">🎰 MGM</div></div>
        <div class="petty-box"><div class="petty-num">{len([r for r in results if r['type']=='dk'])}</div><div class="petty-label">🎯 DK</div></div>
        <div class="petty-box"><div class="petty-num">{len([r for r in results if r['type']=='fd'])}</div><div class="petty-label">💙 FD</div></div>
        <div class="petty-box"><div class="petty-num">{len(fallen)}</div><div class="petty-label">💀 Fallen</div></div>
        <div class="petty-box"><div class="petty-num">{len(st.session_state.get('pregame_lock') or {})}</div><div class="petty-label">🔒 Lock</div></div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs([
        "👑 Board", "🎯 DK", "🎰 MGM", "🔢 Digits", "💙 FD", "🤝 Exact",
        "📈 Signals", "⏳ Moves", "📉 Trends", "👻 Late", "💀 Fallen", "🔒 Lock",
        "📡 Tracker", "📊 Results", "📖 Code",
    ])

    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 Strict Board</div>', unsafe_allow_html=True)
        st.caption(f"Max {BOARD_MAX_PER_TEAM}/team · {BOARD_MAX_PER_GAME}/game · 2+ core methods · edge ≥ {EDGE_MIN}")
        if not ev_board:
            st.info("No strict TAKE IT / PASS candidates. Fetch while pregame.")
        else:
            # group by game
            by_game = defaultdict(list)
            for item in ev_board:
                g = item.get("event") or "Game"
                by_game[g].append(item)
            for game, items in by_game.items():
                st.markdown(f"**{game}**")
                cols = st.columns(2)
                for idx, item in enumerate(items):
                    with cols[idx % 2]:
                        tags = render_method_tags(item["methods"])
                        meter = make_meter(item["bars"], item["level"])
                        cls = "bet" if item["is_bet"] else "skip"
                        label = "🟢 TAKE IT" if item["is_bet"] else "⚪ PASS"
                        kelly_s = ""
                        if item.get("kelly") is not None:
                            kelly_s = f"<br><b>Kelly</b> ~{item['kelly']*100:.1f}% bank · method {item.get('method_rate_name')} ({item.get('method_n')} plays)"
                        elif item.get("method_n"):
                            kelly_s = f"<br><small>Method rate n={item['method_n']} (need {KELLY_MIN_N} for Kelly)</small>"
                        ev_s = ""
                        if item.get("method_ev") is not None:
                            ev_s = f" · method EV/u {item['method_ev']:+.2f}"
                        team = item.get("team") or ""
                        st.markdown(f"""
                        <div class="card {cls}">
                            <b>{label}</b> — <b>{item['player']}</b>{(' · '+team) if team else ''}
                            <span class="score-pill">{item['score']}</span><br>
                            {meter}
                            Best {format_odds(item['best_price'])} on {book_label(item['best_book'])}
                            · consensus {format_odds(item['median'])}
                            · edge <b>{int(item['edge'])}</b>{ev_s}<br>
                            {tags}{kelly_s}<br><small>{item['why']}</small>
                        </div>
                        """, unsafe_allow_html=True)

    def show(tab, typ, banner, explain):
        with tab:
            st.markdown(f'<div class="queen-banner">{banner}</div>', unsafe_allow_html=True)
            st.caption(explain)
            items = [r for r in results if r["type"] == typ]
            if not items:
                st.info("None.")
                return
            cols = st.columns(2)
            for idx, r in enumerate(items[:40]):
                with cols[idx % 2]:
                    tags = render_method_tags(r.get("methods", []))
                    st.markdown(
                        f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}<br>{tags}</div>',
                        unsafe_allow_html=True,
                    )

    show(tabs[1], "dk", "🎯 DraftKings", "Ends in 10 · FD-style endings tracked separately")
    show(tabs[2], "mgm", "🎰 BetMGM", "Same-team 00/25/50/75 pairs & groups")
    show(tabs[3], "digit", "🔢 Digits", "Pairs / groups of 3 only")
    show(tabs[4], "fd", "💙 FanDuel", f"≥+{FD_MIN} endings 10/20/30/60/70/90 or +600 · needs DK/MGM")
    show(tabs[5], "match", "🤝 Exact", "Same price across books")
    show(tabs[6], "signal", "📈 Signals", "Multi-book method / shorten")

    with tabs[7]:
        st.markdown('<div class="queen-banner">⏳ Moves (500+ only)</div>', unsafe_allow_html=True)
        ups = [r for r in results if r["type"] == "hist" and r.get("move_dir") == "up"]
        downs = [r for r in results if r["type"] == "hist" and r.get("move_dir") == "down"]
        a, b = st.columns(2)
        with a:
            st.markdown("#### 🔴 UP")
            for r in ups[:20]:
                st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            if not ups:
                st.info("None")
        with b:
            st.markdown("#### 🟢 DOWN")
            for r in downs[:20]:
                st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            if not downs:
                st.info("None")

    with tabs[8]:
        st.markdown('<div class="queen-banner">📉 Trends</div>', unsafe_allow_html=True)
        good = sorted(
            [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "good"],
            key=lambda r: r.get("gap", 0),
            reverse=True,
        )
        fade = [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "fade"]
        st.markdown("#### 💚 FD under MGM")
        for r in good[:15]:
            st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
        if not good:
            st.info("None")
        st.markdown("#### 🔴 Fade")
        for r in fade[:15]:
            st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
        if not fade:
            st.info("None")

    show(tabs[9], "late", "👻 Late / Gone", "🔒 shows last pregame when MGM vanishes")
    with tabs[10]:
        st.markdown('<div class="queen-banner">💀 Fallen</div>', unsafe_allow_html=True)
        if not fallen:
            st.info("None")
        else:
            for r in fallen[:30]:
                st.markdown(
                    f'<div class="card"><b>{r["label"]}</b> · was {r.get("old_score", 0)}<br>{r["reason"]}</div>',
                    unsafe_allow_html=True,
                )

    with tabs[11]:
        st.markdown('<div class="queen-banner">🔒 Pregame Lock</div>', unsafe_allow_html=True)
        lock = st.session_state.get("pregame_lock") or load_pregame()
        if not lock:
            st.info("Fetch pregame to build lock.")
        else:
            q = st.text_input("Filter", key="lock_q")
            cols = st.columns(2)
            i = 0
            for player, entry in sorted(lock.items()):
                if q and q.lower() not in player.lower():
                    continue
                lines = [
                    f"{book_label(b)} {format_odds(info['price'])}"
                    for b, info in sorted((entry.get("books") or {}).items())
                    if info.get("price") is not None
                ]
                if not lines:
                    continue
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="card"><b>{player}</b><br>' + "<br>".join(lines) + "</div>",
                        unsafe_allow_html=True,
                    )
                i += 1

    # Tracker
    with tabs[12]:
        st.markdown('<div class="queen-banner">📡 Tracker — what actually hits</div>', unsafe_allow_html=True)
        st.caption("From graded TAKE ITs only · n = sample size · ignore tiny n")
        st.markdown("#### By method")
        if not method_stats:
            st.info("Grade some PENDING plays first.")
        else:
            chips = []
            for m, s in sorted(
                method_stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                pct = 100 * s["hit"] / t if t else 0
                chips.append(
                    f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{m}</div><div class="rate-n">{s["hit"]}H / {s["miss"]}M · {t}</div></div>'
                )
            st.markdown("".join(chips), unsafe_allow_html=True)
        st.markdown("#### By best book")
        if not book_stats:
            st.info("No book data yet.")
        else:
            chips = []
            for b, s in sorted(
                book_stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                pct = 100 * s["hit"] / t if t else 0
                chips.append(
                    f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{b}</div><div class="rate-n">{s["hit"]}H / {s["miss"]}M · {t}</div></div>'
                )
            st.markdown("".join(chips), unsafe_allow_html=True)
        st.markdown("#### By ending digits")
        if ending_stats:
            chips = []
            for end, s in sorted(
                ending_stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                pct = 100 * s["hit"] / t if t else 0
                chips.append(
                    f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">ends {end}</div><div class="rate-n">{s["hit"]}H / {s["miss"]}M · {t}</div></div>'
                )
            st.markdown("".join(chips), unsafe_allow_html=True)
        st.info("🤖 Auto-grade from box scores = next phase. For now grade PENDING (or Undo mistakes).")

    # Results
    with tabs[13]:
        st.markdown('<div class="queen-banner">📊 Results</div>', unsafe_allow_html=True)
        st.caption("↩️ Undo wrong HIT/MISS · Log HR for non–TAKE IT dingers")

        st.markdown("#### Log a HR")
        a, b, c, d = st.columns([2, 1, 1, 1])
        with a:
            hr_p = st.text_input("Player", key="hr_p")
        with b:
            hr_price = st.text_input("Price (blank=lock)", key="hr_pr")
        with c:
            hr_book = st.selectbox("Book", ["betmgm", "draftkings", "fanduel", "hardrockbet", "caesars", "untagged"], key="hr_b")
        with d:
            st.write("")
            st.write("")
            if st.button("Log HIT"):
                ok, msg = log_manual_hr(hr_p, hr_price, hr_book)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

        rows = load_results()
        today_only = st.checkbox("Today only", value=True)
        rows_view = [r for r in rows if r.get("date") == today_az()] if today_only else rows
        pending = sorted([r for r in rows_view if r.get("result") == "PENDING"], key=pending_sort_key)
        done = [r for r in rows_view if r.get("result") in ("HIT", "MISS")]
        hits = sum(1 for r in done if r["result"] == "HIT")
        misses = sum(1 for r in done if r["result"] == "MISS")
        rate = 100 * hits / (hits + misses) if (hits + misses) else 0

        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{len(pending)}</div><div class="petty-label">PENDING</div></div>
            <div class="petty-box"><div class="petty-num">{hits}</div><div class="petty-label">HITS</div></div>
            <div class="petty-box"><div class="petty-num">{misses}</div><div class="petty-label">MISSES</div></div>
            <div class="petty-box"><div class="petty-num">{rate:.0f}%</div><div class="petty-label">RATE</div></div>
        </div>
        """, unsafe_allow_html=True)

        total_p = len(pending)
        page = st.session_state.get("pending_page", 0)
        max_page = max(0, (total_p - 1) // PENDING_PAGE) if total_p else 0
        page = min(page, max_page)
        st.session_state["pending_page"] = page
        start, end = page * PENDING_PAGE, min((page + 1) * PENDING_PAGE, total_p)
        st.markdown(f"**Pending {start+1 if total_p else 0}–{end} of {total_p}** (oldest first)")
        n1, n2, _ = st.columns([1, 1, 4])
        with n1:
            if st.button("← Prev", disabled=page <= 0):
                st.session_state["pending_page"] = page - 1
                st.rerun()
        with n2:
            if st.button("Next →", disabled=page >= max_page):
                st.session_state["pending_page"] = page + 1
                st.rerun()

        for r in pending[start:end]:
            rid = r["id"]
            endg = r.get("ending")
            end_s = f" ends {int(endg):02d}" if endg is not None else ""
            lock_s = locked_price_str(r["player"])
            st.markdown(
                f"**{r['player']}** · {format_odds(r.get('best_price'))} "
                f"{book_label(r.get('best_book'))}{end_s} · score {r.get('score')}"
            )
            if lock_s:
                st.caption(f"🔒 {lock_s}")
            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("🟢 HIT", key=f"hit_{rid}"):
                    set_result_status(rid, "HIT")
                    st.rerun()
            with c2:
                if st.button("🔴 MISS", key=f"miss_{rid}"):
                    set_result_status(rid, "MISS")
                    st.rerun()

        st.markdown("#### Graded — ↩️ Undo")
        for r in reversed(done[-40:]):
            rid = r["id"]
            icon = "🟢" if r["result"] == "HIT" else "🔴"
            endg = r.get("ending")
            end_s = f" ends {int(endg):02d}" if endg is not None else ""
            st.markdown(
                f"{icon} **{r['player']}** · {format_odds(r.get('best_price'))} "
                f"{book_label(r.get('best_book'))}{end_s}"
            )
            u1, u2, u3, _ = st.columns([1, 1, 1, 3])
            with u1:
                if st.button("↩️ Undo", key=f"undo_{rid}"):
                    undo_result(rid, r.get("source"))
                    st.rerun()
            with u2:
                if r.get("result") != "HIT" and st.button("🟢 HIT", key=f"fh_{rid}"):
                    set_result_status(rid, "HIT")
                    st.rerun()
            with u3:
                if r.get("result") != "MISS" and st.button("🔴 MISS", key=f"fm_{rid}"):
                    set_result_status(rid, "MISS")
                    st.rerun()

    with tabs[14]:
        st.markdown('<div class="queen-banner">📖 The Code</div>', unsafe_allow_html=True)
        with st.expander("Board rules", expanded=True):
            st.markdown(f"""
- **TAKE IT** = ≥{METHODS_MIN} core methods · edge ≥ {EDGE_MIN} · Over **0.5 HR** · in lineup when RotoWire loaded  
- Cap **{BOARD_MAX_PER_TEAM}/team** · **{BOARD_MAX_PER_GAME}/game**  
- **Bet365 shelved** until the plan has it  
- **Kelly / method EV** only when that method has ≥{KELLY_MIN_N} graded plays  
            """)
        with st.expander("Core methods"):
            st.markdown("""
**DK** — ends in **10**; **DK FD-style** = 10/20/30/60/70/90 on DK (tracked separately)  

**MGM** — same team · **00 / 25 / 50 / 75** · pair, exact same last-two, or group of 3 · **Stayed in group / Last one left**  

**FD** — ≥ threshold endings **10/20/30/60/70/90** or **+600** · only if player also has DK or MGM  

**Exact / Multi-book method** — same price or methods on 2+ of DK/MGM/FD  
            """)
        with st.expander("Noise (not core)"):
            st.markdown("Late tags · Not in lineup · FD under MGM (support only) · FADE spikes · single-book moves · Multi-book Lengthen")
        with st.expander("Lock · Results · Tracker"):
            st.markdown("""
**Lock** = last pregame prices; never wiped when MGM drops after first pitch.  

**Results** = grade all PENDING (page through) · **Undo** wrong grades.  

**Tracker** = method / book / ending hit rates with **n**.  

**Auto-grade** = next phase (box scores).  
            """)

    st.markdown(
        '<div class="footer">👑 Girl Magic • Boss Bitch • HBIC • Me & My Girls We Rolling</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
