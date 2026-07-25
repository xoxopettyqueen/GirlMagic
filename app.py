"""
Girl Magic Odds ✨ — full app (no mirrors)

PAIR first (MGM/365 same team) · TRIO only if no pair
🔥 HOT = pair/trio + FD + DK10/Was/DK FD-style
🟢 TAKE = live pair/trio · not faded · ≥+400 · not HardRock-best
⚪ PASS = no primary · HardRock best · fade ±150 · price too low

Digits = MGM + Bet365 only · No Caesars
📋 Cheat Sheet · mobile-safe board order (row-by-row)
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
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
.stApp{background:linear-gradient(165deg,#0a0410 0%,#160a22 40%,#1f0b30 100%);color:#fce7f3;font-family:'Inter',sans-serif}
h1{font-family:'Playfair Display',serif!important;font-weight:900!important;background:linear-gradient(90deg,#f9a8d4,#e879f9,#c084fc,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.4rem!important;margin-bottom:2px!important}
.subtitle{color:#f9a8d4;font-size:.9rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px}
.tagline{color:#e9d5ff;font-size:.85rem;font-style:italic;margin-bottom:14px;opacity:.95}
.how-to{background:linear-gradient(135deg,#1a0f28,#2a1040);border:1px solid #f472b6;border-radius:14px;padding:12px 16px;margin-bottom:14px;font-size:.85rem;line-height:1.45;position:relative}
.how-to::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:linear-gradient(180deg,#f472b6,#c084fc)}
.how-to b{color:#f9a8d4}
.info-box{background:#1a0f28;border:1px solid #a855f7;border-radius:12px;padding:8px 12px;margin-bottom:10px;font-size:.85rem}
.stButton>button{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important;padding:.5rem 1.1rem!important}
.petty-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.petty-box{flex:1;min-width:58px;background:#1a0f28;border:1px solid #f472b6;border-radius:12px;padding:8px 6px;text-align:center}
.petty-num{font-size:1.2rem;font-weight:800;color:#f9a8d4;line-height:1.1}
.petty-label{font-size:.52rem;color:#e9d5ff;margin-top:3px}
.trends-today{background:linear-gradient(135deg,#2a1040,#1a0f28 50%,#3b0764);border:1px solid #c084fc;border-radius:16px;padding:12px 16px;margin-bottom:16px}
.trends-today-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.trends-today-title{color:#f9a8d4;font-weight:800;font-size:.92rem}
.trends-today-sub{color:#e9d5ff;font-size:.7rem;opacity:.9}
.trends-chips{display:flex;flex-wrap:wrap;gap:7px}
.trend-chip{display:inline-flex;align-items:center;border-radius:999px;padding:6px 12px;font-size:.76rem;font-weight:800;border:2px solid transparent}
.chip-mgm{background:#422006;border-color:#f59e0b;color:#fcd34d}
.chip-dk{background:#064e3b;border-color:#34d399;color:#6ee7b7}
.chip-fd{background:#1e3a5f;border-color:#3b82f6;color:#93c5fd}
.chip-365{background:#14532d;border-color:#22c55e;color:#86efac}
.chip-hr{background:#7f1d1d;border-color:#f87171;color:#fecaca}
.chip-other{background:#3b0764;border-color:#a855f7;color:#e9d5ff}
.chip-count{font-weight:900;margin-left:4px}
.card{background:linear-gradient(155deg,#1a0f28,#251438);border:1px solid #f472b6;border-radius:12px;padding:9px 11px;color:#fdf2f8;position:relative;font-size:.88rem;margin-bottom:6px}
.card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;border-radius:12px 0 0 12px;background:#f472b6}
.bet{background:linear-gradient(155deg,#0c2418,#143d28)!important;border:1px solid #34d399!important}
.hot{background:linear-gradient(155deg,#3b0764,#7c2d12)!important;border:1px solid #fb923c!important}
.skip{background:#14101c!important;border:1px solid #4b5563!important;opacity:.85}
.fade-card{border-color:#f87171!important;opacity:.9}
.score-pill{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-weight:800;font-size:.85rem;padding:2px 9px;border-radius:12px;margin-left:5px}
.tag{display:inline-block;background:#3b0764;color:#f9a8d4;font-size:.65rem;font-weight:700;padding:2px 7px;border-radius:10px;margin:2px 2px 2px 0;border:1px solid #a855f7}
.tag-dk{background:#064e3b;color:#6ee7b7;border-color:#34d399}
.tag-mgm{background:#422006;color:#fcd34d;border-color:#f59e0b}
.tag-fd{background:#1e3a5f;color:#93c5fd;border-color:#3b82f6}
.tag-match{background:#4c1d95;color:#e9d5ff;border-color:#a855f7}
.tag-strong{background:#14532d;color:#bbf7d0;border-color:#22c55e}
.tag-b365{background:#14532d;color:#86efac;border-color:#22c55e}
.tag-fade{background:#450a0a;color:#fca5a5;border-color:#f87171}
.tag-hot{background:#7c2d12;color:#fdba74;border-color:#fb923c}
.queen-banner{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-size:.72rem;font-weight:700;padding:4px 12px;border-radius:16px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
.meter{display:flex;gap:3px;margin:3px 0 5px}
.meter-bar{height:5px;width:16px;border-radius:3px;background:#374151}
.meter-bar.filled-high{background:linear-gradient(90deg,#f472b6,#c026d3)}
.meter-bar.filled-strong{background:linear-gradient(90deg,#e879f9,#a855f7)}
.meter-bar.filled-medium{background:linear-gradient(90deg,#c084fc,#7c3aed)}
.meter-bar.filled-low{background:#6b7280}
.stTabs [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{background:#1a0f28;border-radius:8px;color:#f9a8d4;font-weight:600;padding:6px 9px;font-size:.78rem}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important}
.footer{text-align:center;color:#f9a8d4;font-size:.9rem;margin-top:28px;opacity:.9;padding-bottom:16px}
.res-card{background:#1a0f28;border:1px solid #7c3aed;border-radius:10px;padding:8px 10px;margin-bottom:8px;font-size:.82rem}
@media (max-width:768px){
  .card{font-size:.82rem;padding:8px 10px}
  .petty-box{min-width:46%}
  .score-pill{font-size:.75rem}
}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
MLB_API = "https://statsapi.mlb.com/api/v1"
REGIONS = "us,us2"
MARKETS = "batter_home_runs"
HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"

PREFERRED = {"fanduel", "draftkings", "betmgm", "hardrockbet", "bet365", "bet365_au"}
BOOK_PRIORITY = ["betmgm", "draftkings", "fanduel", "bet365", "hardrockbet"]
ALLOWED_BEST_BOOKS = {"MGM", "DK", "FD", "HardRock"}

METHODS_MIN = 2
METHODS_STRONG = 3
OUTLIER_GAP = 150
BIG_MOVE = 150
PRICE_MIN_TAKE = 400
REFRESH_MINUTES = 30
NAME_METHODS_MIN = 3
NAME_MAX_PAIRS = 50
FD_MIN = 500
FD_STYLE_ENDS = (10, 20, 30, 60, 70, 90)
PENDING_PAGE = 20
MGM_STAY_SNAPS = 3

FD_METHODS = {"FD Pattern", "FD 600"}
DK_METHODS = {"DK 10", "Was DK 10", "DK FD-style"}
PAIR_TAGS = {"MGM Pair", "B365 Pair", "MGM Exact"}
TRIO_TAGS = {"MGM Trio", "B365 Trio"}
PERSONAL_STRONG = PAIR_TAGS | TRIO_TAGS | FD_METHODS | DK_METHODS | {
    "Exact Match", "B365 850", "B365 > HardRock", "Stayed in group", "Last one left",
    "🔥 HOT", "MGM 00", "MGM 25", "MGM 50", "MGM 75",
}
NOISE_METHODS = {
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup",
    "In lineup · missing books", "Price moved", "Shortening", "Lengthening",
    "Multi-book Lengthen", "Spike", "Dump", "FADE · Spike", "FADE · Dump",
    "HardRock best",
}


def is_bet365(book):
    b = str(book).lower()
    return "bet365" in b or b == "365"


def is_core_method(m):
    if m in NOISE_METHODS:
        return False
    if m.startswith("Shortening") or m.startswith("Lengthening") or m.startswith("FADE"):
        return False
    if m.startswith("Outlier") or m.startswith("Stuck"):
        return False
    if m.startswith("Stayed in group") and m != "Stayed in group":
        return False
    return True


def normalize_method(m):
    if str(m).startswith("Stayed in group") or m == "Stayed in the group":
        return "Stayed in group"
    return m


def count_core_methods(meths):
    cleaned = {normalize_method(m) for m in meths}
    return len([m for m in cleaned if is_core_method(m)])


def has_pair(meths):
    return bool({normalize_method(m) for m in meths} & PAIR_TAGS)


def has_trio(meths):
    return bool({normalize_method(m) for m in meths} & TRIO_TAGS)


def has_live_primary(meths):
    return has_pair(meths) or has_trio(meths)


def has_fd_heat(meths):
    return bool({normalize_method(m) for m in meths} & FD_METHODS)


def has_dk_support(meths):
    return bool({normalize_method(m) for m in meths} & {"DK 10", "Was DK 10", "DK FD-style"})


def has_personal_strong(meths):
    cleaned = {normalize_method(m) for m in meths}
    return any(m in PERSONAL_STRONG or m.startswith("MGM ") or m.startswith("B365") for m in cleaned)


def has_dk_or_mgm(meths):
    return has_dk_support(meths) or has_live_primary(meths)


def method_tag_class(m):
    m = normalize_method(str(m))
    if m == "🔥 HOT":
        return "tag-hot"
    if m in DK_METHODS or m.startswith("DK"):
        return "tag-dk"
    if m.startswith("MGM") or m in ("Last one left", "Stayed in group") or m in PAIR_TAGS | TRIO_TAGS:
        return "tag-mgm"
    if m.startswith("FD"):
        return "tag-fd"
    if m.startswith("B365"):
        return "tag-b365"
    if m in ("Exact Match", "MGM Exact"):
        return "tag-match"
    if m in ("Spike", "Dump", "HardRock best") or m.startswith("FADE"):
        return "tag-fade"
    return ""


def render_method_tags(methods, limit=10):
    seen = []
    for m in methods:
        nm = normalize_method(m)
        if nm not in seen:
            seen.append(nm)
    if "🔥 HOT" in seen:
        seen.remove("🔥 HOT")
        seen.insert(0, "🔥 HOT")
    return "".join(f'<span class="tag {method_tag_class(m)}">{m}</span>' for m in seen[:limit])


def girl_magic_score(core_count, edge, methods):
    methods = [normalize_method(m) for m in methods]
    method_pts = min(core_count, 5) * 8
    if core_count >= METHODS_STRONG:
        method_pts += 6
    bonus = 0
    if has_pair(methods):
        bonus += 20
    elif has_trio(methods):
        bonus += 12
    if "Last one left" in methods:
        bonus += 10
    if "Stayed in group" in methods:
        bonus += 8
    if "🔥 HOT" in methods:
        bonus += 16
    if "DK FD-style" in methods:
        bonus += 6
    if "Was DK 10" in methods:
        bonus += 5
    if "DK 10" in methods:
        bonus += 4
    edge_pts = min(15, max(0, int((max(0, edge) / 200) * 15)))
    if "Spike" in methods or "Dump" in methods or "HardRock best" in methods:
        bonus -= 15
    if any(str(m).startswith("FADE") for m in methods):
        bonus -= 10
    return max(0, min(100, method_pts + edge_pts + min(40, max(-20, bonus))))


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
    if "bet365" in b or b == "365":
        return "365"
    if "hardrock" in b:
        return "HardRock"
    if b in ("untagged", "unknown", "—", ""):
        return "Untagged"
    return b.title() if b else "Untagged"


def chip_class_for_book(bl):
    bl = str(bl).upper()
    if "MGM" in bl:
        return "chip-mgm"
    if bl in ("DK", "DRAFTKINGS"):
        return "chip-dk"
    if bl in ("FD", "FANDUEL"):
        return "chip-fd"
    if "365" in bl:
        return "chip-365"
    if "HARD" in bl:
        return "chip-hr"
    return "chip-other"


def clean_name(name):
    name = str(name).strip()
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
    parts = name.split()
    if parts and parts[-1].lower().rstrip(".") in suffixes:
        parts = parts[:-1]
    return " ".join(parts)


def names_match(a, b):
    ca = clean_name(a).lower().replace(".", "").replace("'", "")
    cb = clean_name(b).lower().replace(".", "").replace("'", "")
    if ca == cb:
        return True
    pa, pb = ca.split(), cb.split()
    if len(pa) >= 2 and len(pb) >= 2:
        if pa[-1] == pb[-1] and pa[0][0] == pb[0][0]:
            return True
        if pa[-1] == pb[-1] and (pa[0] in pb[0] or pb[0] in pa[0]):
            return True
    return False


def get_initials(name):
    name = clean_name(name)
    parts = name.split()
    if len(parts) < 2:
        return None, None
    return parts[0][0].upper(), parts[-1][0].upper()


def clean_team(tid):
    if not tid:
        return ""
    return str(tid).replace("_MLB", "").replace("_", " ").strip()


def now_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%I:%M %p")


def today_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")


def today_mlb():
    return datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def smart_best(prices, books):
    if not prices:
        return None, None
    paired = list(zip(prices, books))
    non_hr = [(p, b) for p, b in paired if "hardrock" not in str(b).lower()]
    use = non_hr if non_hr else paired
    use = sorted(use, key=lambda x: x[0], reverse=True)
    best_p, best_b = use[0]
    if len(use) >= 2 and best_p - use[1][0] >= OUTLIER_GAP:
        return use[1][0], use[1][1]
    return best_p, best_b


def is_hardrock_best(prices, books):
    if not prices:
        return False
    paired = sorted(zip(prices, books), key=lambda x: x[0], reverse=True)
    return "hardrock" in str(paired[0][1]).lower()


def get_confidence(score, is_bet, core_count, is_hot=False):
    if not is_bet:
        return "Skip", 1, "low"
    if is_hot or (core_count >= METHODS_STRONG and score >= 80):
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
    html += "</div>"
    return html


def event_matches_chosen(ev, chosen):
    if not chosen:
        return True
    if ev in chosen:
        return True
    ev_l = str(ev).lower()
    for c in chosen:
        parts_c = [p.strip() for p in str(c).lower().split("@")]
        if len(parts_c) == 2 and parts_c[0] in ev_l and parts_c[1] in ev_l:
            return True
    return False


def name_in_lineup(player, lineup_names):
    if not lineup_names:
        return None
    cn = clean_name(player)
    for ln in lineup_names:
        if names_match(cn, ln):
            return True
    parts = cn.split()
    if len(parts) >= 2:
        last, fi = parts[-1].lower(), parts[0][0].lower()
        for ln in lineup_names:
            lp = clean_name(ln).split()
            if len(lp) >= 2 and lp[-1].lower() == last and lp[0][0].lower() == fi:
                return True
    return False


def parse_cheat_sheet(text):
    if not text or not str(text).strip():
        return []
    raw = str(text).replace(",", "\n").replace(";", "\n")
    names, seen = [], set()
    for line in raw.splitlines():
        n = clean_name(line.strip())
        if not n or len(n) < 3:
            continue
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(n)
    return names


def check_cheat_sheet(sheet_names, methods_map, ev_board, source_label="Sheet"):
    board_by = {}
    for item in ev_board or []:
        board_by[clean_name(item["player"])] = item
    hits, misses = [], []
    for sheet_name in sheet_names:
        matched_key = None
        meths = []
        for k, ms in (methods_map or {}).items():
            if names_match(sheet_name, k):
                matched_key = clean_name(k)
                meths = list(dict.fromkeys(normalize_method(m) for m in ms))
                break
        if matched_key is None:
            for k in board_by:
                if names_match(sheet_name, k):
                    matched_key = k
                    break
        board = board_by.get(matched_key) if matched_key else None
        if board:
            meths = list(dict.fromkeys(meths + [normalize_method(m) for m in board.get("methods", [])]))
        primary = has_live_primary(meths) if meths else False
        has_signal = primary or bool(board and (board.get("is_bet") or board.get("is_hot"))) or count_core_methods(meths) >= 1
        entry = {
            "source": source_label,
            "sheet_name": sheet_name,
            "matched_as": matched_key or sheet_name,
            "methods": meths,
            "on_board": board is not None,
            "is_bet": bool(board and board.get("is_bet")),
            "is_hot": bool(board and board.get("is_hot")),
            "score": board.get("score") if board else None,
            "best_price": board.get("best_price") if board else None,
            "best_book": board.get("best_book") if board else None,
            "why": board.get("why") if board else "",
            "primary": primary,
        }
        if has_signal:
            hits.append(entry)
        else:
            misses.append(entry)
    hits.sort(key=lambda x: (not x["is_hot"], not x["is_bet"], not x["primary"], -(x["score"] or 0)))
    return hits, misses


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
        if "caesar" in str(book).lower():
            continue
        price = r["price"]
        event = r.get("event") or ""
        if player not in lock:
            lock[player] = {
                "date": today, "event": event, "books": {},
                "locked_at": ts, "updated_at": ts,
                "first_prices": {}, "last_prices": {},
            }
        entry = lock[player]
        if event:
            entry["event"] = event
        entry["date"] = today
        entry["updated_at"] = ts
        entry.setdefault("books", {})
        entry.setdefault("first_prices", {})
        entry.setdefault("last_prices", {})
        if book not in entry["first_prices"] and price is not None:
            entry["first_prices"][book] = int(price)
        if price is not None:
            entry["last_prices"][book] = int(price)
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
    cn = clean_name(player)
    if cn in lock:
        return lock[cn]
    for k, v in lock.items():
        if names_match(k, player):
            return v
    return {}


def movement_summary(player):
    entry = get_locked(player)
    first = entry.get("first_prices") or {}
    last = entry.get("last_prices") or {}
    best = None
    for b in BOOK_PRIORITY:
        if b in first and b in last:
            d = last[b] - first[b]
            best = (b, first[b], last[b], d)
            break
    if best is None:
        for b in first:
            if b in last:
                d = last[b] - first[b]
                best = (b, first[b], last[b], d)
                break
    if best is None:
        return "", 0
    b, f, l, d = best
    if d >= BIG_MOVE:
        return f"Spike {book_label(b)} {format_odds(f)}→{format_odds(l)}", d
    if d <= -BIG_MOVE:
        return f"Dump {book_label(b)} {format_odds(f)}→{format_odds(l)}", d
    if abs(d) >= 40:
        direction = "up" if d > 0 else "down"
        return f"{direction} {book_label(b)} {format_odds(f)}→{format_odds(l)}", d
    return "", d


def pick_lock_book_price(player):
    entry = get_locked(player)
    books = entry.get("books") or {}
    if not books:
        if entry.get("mgm_price") is not None:
            return "betmgm", entry["mgm_price"]
        return "untagged", None
    for b in BOOK_PRIORITY:
        if b in books and books[b].get("price") is not None:
            return b, books[b]["price"]
    for b, info in books.items():
        if info.get("price") is not None:
            return b, info["price"]
    return "untagged", None


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
            mv, delta = movement_summary(row.get("player", ""))
            if mv:
                row["movement"] = mv
                row["movement_delta"] = delta
            save_results(rows)
            return True
    return False


def undo_result(row_id, source):
    if source in ("manual_hr", "mlb_auto"):
        rows = [x for x in load_results() if x.get("id") != row_id]
        save_results(rows)
        return True
    return set_result_status(row_id, "PENDING")


def dedupe_pending(rows, today):
    best = {}
    others = []
    for r in rows:
        if r.get("date") == today and r.get("result") == "PENDING" and r.get("source") == "take_it":
            p = r.get("player")
            if p not in best or (r.get("score") or 0) > (best[p].get("score") or 0):
                best[p] = r
        else:
            others.append(r)
    return others + list(best.values())


def auto_mark_dnp():
    lineup = st.session_state.get("lineup_names") or set()
    if not lineup:
        return 0
    rows = load_results()
    today = today_az()
    n = 0
    for r in rows:
        if r.get("date") != today or r.get("result") != "PENDING" or r.get("source") != "take_it":
            continue
        if name_in_lineup(r.get("player", ""), lineup) is False:
            r["result"] = "DNP"
            n += 1
    if n:
        save_results(rows)
    return n


def bulk_miss_to_dnp(today_only=True):
    lineup = st.session_state.get("lineup_names") or set()
    if not lineup:
        return 0, "Load RotoWire first"
    rows = load_results()
    today = today_az()
    n = 0
    for r in rows:
        if r.get("result") != "MISS":
            continue
        if today_only and r.get("date") != today:
            continue
        if name_in_lineup(r.get("player", ""), lineup) is False:
            r["result"] = "DNP"
            n += 1
    if n:
        save_results(rows)
    return n, f"Converted {n} MISS → DNP"


def log_bet_this(ev_board):
    rows = load_results()
    today = today_az()
    lineup = st.session_state.get("lineup_names") or set()
    added = 0
    for item in ev_board:
        if not item.get("is_bet"):
            continue
        if lineup and name_in_lineup(item["player"], lineup) is False:
            continue
        if any(r.get("date") == today and r.get("player") == item["player"] and r.get("source") == "take_it" for r in rows):
            continue
        price = item.get("best_price")
        book = item.get("best_book", "")
        locked = get_locked(item["player"])
        mv, delta = movement_summary(item["player"])
        rows.append({
            "id": f"{today}_{item['player']}_{int(item['score'])}",
            "date": today, "time": now_az(), "player": item["player"],
            "score": item["score"], "edge": int(item["edge"]),
            "best_price": price, "best_book": book,
            "ending": last_two(price),
            "mgm_locked": locked.get("mgm_price"),
            "methods": [normalize_method(m) for m in item["methods"]],
            "core": item.get("method_count", 0),
            "is_hot": item.get("is_hot", False),
            "movement": mv, "movement_delta": delta,
            "result": "PENDING", "source": "take_it", "logged_at": now_utc_iso(),
        })
        added += 1
    rows = dedupe_pending(rows, today)
    if added:
        save_results(rows)
    return added


def log_manual_hr(player, price, book):
    rows = load_results()
    today = today_az()
    player = clean_name(player)
    if not player:
        return False, "Need a player name"
    if price is None or str(price).strip() == "":
        b, p = pick_lock_book_price(player)
        if p is not None:
            price = p
            if not book or book == "untagged":
                book = b
    try:
        price = int(str(price).replace("+", "").replace(",", "").strip())
    except Exception:
        return False, "Need a valid price (or lock)"
    book = (book or "untagged").strip().lower()
    mv, delta = movement_summary(player)
    rid = f"hr_{today}_{player}_{price}_{book}_{len(rows)}"
    rows.append({
        "id": rid, "date": today, "time": now_az(), "player": player,
        "score": None, "edge": None, "best_price": price, "best_book": book,
        "ending": last_two(price), "methods": ["Manual HR log"], "core": 0,
        "movement": mv, "movement_delta": delta,
        "result": "HIT", "source": "manual_hr", "logged_at": now_utc_iso(),
    })
    save_results(rows)
    return True, f"Logged {player} {format_odds(price)} {book_label(book)}"


def fetch_mlb_home_runs_today():
    date = today_mlb()
    hrs = []
    try:
        r = requests.get(f"{MLB_API}/schedule", params={"sportId": 1, "date": date}, timeout=20)
        if r.status_code != 200:
            return [], f"MLB schedule HTTP {r.status_code}"
        data = r.json()
        game_pks = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                status = (g.get("status") or {}).get("abstractGameState", "")
                if status in ("Live", "Final"):
                    game_pks.append(g.get("gamePk"))
        for pk in game_pks:
            try:
                fr = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live", timeout=15)
                if fr.status_code != 200:
                    continue
                feed = fr.json()
                away = feed.get("gameData", {}).get("teams", {}).get("away", {}).get("name", "")
                home = feed.get("gameData", {}).get("teams", {}).get("home", {}).get("name", "")
                game_label = f"{away} @ {home}"
                for play in feed.get("liveData", {}).get("plays", {}).get("allPlays", []):
                    result = play.get("result") or {}
                    et = (result.get("eventType") or "").lower()
                    ev = (result.get("event") or "").lower()
                    if et != "home_run" and "home run" not in ev:
                        continue
                    batter = (play.get("matchup") or {}).get("batter") or {}
                    name = batter.get("fullName") or ""
                    if name:
                        hrs.append({"player": clean_name(name), "game": game_label})
            except Exception:
                continue
    except Exception as e:
        return [], f"MLB error: {e}"
    seen, unique = set(), []
    for h in hrs:
        key = h["player"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)
    return unique, f"MLB · {len(unique)} HR(s) · {date}"


def already_logged_hr(rows, player, today):
    for r in rows:
        if r.get("date") != today or r.get("result") != "HIT":
            continue
        if names_match(r.get("player", ""), player):
            return True
    return False


def already_pending_take_it(rows, player, today):
    for r in rows:
        if r.get("date") != today or r.get("source") != "take_it":
            continue
        if names_match(r.get("player", ""), player):
            return r
    return None


def auto_log_mlb_hrs():
    hrs, msg = fetch_mlb_home_runs_today()
    if not hrs:
        return 0, 0, msg
    rows = load_results()
    today = today_az()
    auto_n, promote_n = 0, 0
    for h in hrs:
        player = h["player"]
        pend = already_pending_take_it(rows, player, today)
        if pend:
            if pend.get("result") == "PENDING":
                pend["result"] = "HIT"
                if pend.get("ending") is None and pend.get("best_price") is not None:
                    pend["ending"] = last_two(pend["best_price"])
                mv, delta = movement_summary(player)
                if mv:
                    pend["movement"] = mv
                    pend["movement_delta"] = delta
                promote_n += 1
            continue
        if already_logged_hr(rows, player, today):
            continue
        book, price = pick_lock_book_price(player)
        mv, delta = movement_summary(player)
        rid = f"mlb_{today}_{player}_{book}_{price}_{len(rows)}"
        rows.append({
            "id": rid, "date": today, "time": now_az(), "player": player,
            "score": None, "edge": None, "best_price": price, "best_book": book or "untagged",
            "ending": last_two(price) if price is not None else None,
            "methods": ["MLB auto HR"], "core": 0,
            "movement": mv, "movement_delta": delta,
            "result": "HIT", "source": "mlb_auto", "game": h.get("game", ""),
            "logged_at": now_utc_iso(),
        })
        auto_n += 1
    if auto_n or promote_n:
        save_results(rows)
    return auto_n, promote_n, msg


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
        if ending is None:
            continue
        book_ending[(book_label(book), int(ending))] += 1
    chips = [(bl, end, cnt) for (bl, end), cnt in sorted(book_ending.items(), key=lambda x: (-x[1], x[0]))]
    return n_hits, n_graded, chips[:12]


def render_whats_going_today():
    rows = load_results()
    n_hits, n_graded, chips = build_whats_going_today(rows)
    if chips:
        parts = [
            f'<span class="trend-chip {chip_class_for_book(bl)}">{bl} {end:02d}'
            f'<span class="chip-count"> · {cnt} HR</span></span>'
            for bl, end, cnt in chips
        ]
        chips_html = "".join(parts)
    else:
        chips_html = '<span class="trend-chip chip-other">No HITs yet — Sync MLB HRs</span>'
    st.markdown(f"""
    <div class="trends-today">
      <div class="trends-today-header">
        <div class="trends-today-title">🔥 What's Going Today</div>
        <div class="trends-today-sub">{n_hits} HR of {n_graded} graded (DNP excluded)</div>
      </div>
      <div class="trends-chips">{chips_html}</div>
    </div>
    """, unsafe_allow_html=True)


def fetch_rotowire_lineups():
    if not HAS_BS4:
        return set(), "Install beautifulsoup4"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
            params={"apiKey": api_key, "regions": REGIONS, "markets": MARKETS, "oddsFormat": "american"},
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
        if bk not in PREFERRED or "caesar" in bk:
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
                    "price": o.get("price"), "point": 0.5, "team": "", "source": "oddsapi",
                })
    return rows, found


def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(f"{SGO_BASE}/events", params={
            "apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 25
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
                pdata = players_map[pid]
                pname = pdata.get("name")
                if not pname:
                    continue
                team = clean_team(pdata.get("teamID") or "")
                for bk, bd in odd_data.get("byBookmaker", {}).items():
                    if not bd.get("available", True):
                        continue
                    b = bk.lower()
                    if is_bet365(b):
                        b = "bet365"
                    if "caesar" in b or b not in PREFERRED:
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
                        "event": event_name, "book": b, "player": pname,
                        "price": price, "point": 0.5, "team": team, "source": "sgo",
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
    found = (all_found & PREFERRED) | {x for x in all_found if is_bet365(x)}
    return df, found


def build_team_map(df):
    tm = {}
    for _, r in df.iterrows():
        if r.get("team"):
            tm[r["player"]] = r["team"]
    return tm


def detect_was_dk10(current_prices, price_history):
    if not price_history or len(price_history) < 2:
        return set()
    had_dk10 = set()
    for snap in price_history[:-1]:
        for (player, book), price in snap.items():
            if book == "draftkings" and last_two(price) == 10:
                had_dk10.add(player)
    still = set()
    for (player, book), price in current_prices.items():
        if book == "draftkings" and last_two(price) == 10:
            still.add(player)
    return had_dk10 - still


def detect_classic_groups(book_df, endings):
    groups = []
    if book_df.empty or not book_df["team"].astype(str).str.len().gt(0).any():
        return groups
    for (event, team), g in book_df.groupby(["event", "team"], dropna=False):
        if not team:
            continue
        ends = defaultdict(list)
        for _, r in g.iterrows():
            d = last_two(r["price"])
            if d in endings:
                ends[d].append(r["player"])
        for d, ps in ends.items():
            names = sorted(set(ps))
            if len(names) == 2:
                groups.append({"event": event, "ending": d, "team": team, "players": frozenset(names), "size": 2})
            elif len(names) == 3:
                groups.append({"event": event, "ending": d, "team": team, "players": frozenset(names), "size": 3})
    return groups


def run_flags(df, previous_df=None, record_history=True, selected_events=None):
    if df.empty:
        return [], [], {}
    if "team" not in df.columns:
        df["team"] = ""
    df["book"] = df["book"].apply(lambda b: "bet365" if is_bet365(b) else b)
    df = df[~df["book"].astype(str).str.contains("caesar", case=False, na=False)]
    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results, methods_map = [], defaultdict(list)
    team_map = build_team_map(df)
    lineup_names = st.session_state.get("lineup_names", set())
    spike_dump = {}

    for k in ("price_history", "mgm_history"):
        if k not in st.session_state:
            st.session_state[k] = []

    current_prices = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}
    if record_history:
        st.session_state["price_history"].append(current_prices)
        st.session_state["price_history"] = st.session_state["price_history"][-8:]

    for player in df["player"].unique():
        mv, delta = movement_summary(player)
        if abs(delta) >= BIG_MOVE:
            tag = "Spike" if delta > 0 else "Dump"
            spike_dump[player] = (tag, mv, delta)
            methods_map[player].append(tag)
            methods_map[player].append(f"FADE · {tag}")

    for _, row in df.iterrows():
        if row["book"] == "draftkings" and last_two(row["price"]) == 10:
            results.append({"type": "dk", "label": row["player"],
                "reason": f"DK ends in 10 → {format_odds(row['price'])}",
                "event": row["event"], "methods": ["DK 10"]})
            methods_map[row["player"]].append("DK 10")

    for _, row in df.iterrows():
        if row["book"] != "draftkings":
            continue
        price = abs(int(row["price"])) if row["price"] is not None else 0
        last = last_two(row["price"])
        if price >= FD_MIN and last in FD_STYLE_ENDS:
            results.append({"type": "dk", "label": row["player"],
                "reason": f"DK FD-style ≥+{FD_MIN} ends {last:02d} → {format_odds(row['price'])}",
                "event": row["event"], "methods": ["DK FD-style"]})
            methods_map[row["player"]].append("DK FD-style")

    was_dk10 = detect_was_dk10(current_prices, st.session_state.get("price_history", []))
    for player in was_dk10:
        results.append({"type": "dk_was", "label": player,
            "reason": "Was DK 10 earlier · counts toward HOT",
            "event": "", "methods": ["Was DK 10"]})
        methods_map[player].append("Was DK 10")

    mgm = df[df["book"].str.contains("betmgm|mgm", case=False, na=False)].copy()
    current_mgm = detect_classic_groups(mgm, (0, 25, 50, 75))

    if record_history:
        st.session_state["mgm_history"].append(current_mgm)
        st.session_state["mgm_history"] = st.session_state["mgm_history"][-8:]

    h = st.session_state["mgm_history"]
    stay_count = defaultdict(int)
    survivor = set()
    if len(h) >= 2:
        for snap in h:
            seen = set()
            for g in snap:
                seen.update(g["players"])
            for p in seen:
                stay_count[p] += 1
        early = set()
        for g in h[0]:
            if g.get("size") == 3 or len(g["players"]) == 3:
                early.update(g["players"])
        late = set()
        for g in h[-1]:
            late.update(g["players"])
        survivor = early & late

    for grp in current_mgm:
        names = sorted(grp["players"])
        d = grp["ending"]
        size = grp.get("size") or len(names)
        is_pair = size == 2
        kind = "pair" if is_pair else "trio (no pair)"
        meth = [f"MGM {d:02d}", "MGM Pair" if is_pair else "MGM Trio"]
        extra = []
        for name in names:
            if stay_count.get(name, 0) >= MGM_STAY_SNAPS:
                meth.append("Stayed in group")
                extra.append("Stayed in group")
            if name in survivor:
                meth.append("Last one left")
                extra.append("Last one left")
        meth = list(dict.fromkeys(meth))
        reason = f"MGM {kind} ends {d:02d} · {grp.get('team', '')}"
        reason += " · PAIR → TAKE" if is_pair else " · TRIO fallback → TAKE"
        if extra:
            reason += " · " + " + ".join(dict.fromkeys(extra))
        results.append({"type": "mgm", "label": " + ".join(names), "reason": reason,
                        "event": grp["event"], "methods": meth})
        for name in names:
            methods_map[name].extend(meth)

    if not mgm.empty and mgm["team"].astype(str).str.len().gt(0).any():
        for (event, team), g in mgm.groupby(["event", "team"], dropna=False):
            if not team:
                continue
            for price, pg in g.groupby("price"):
                names = sorted(pg["player"].unique())
                if len(names) != 2:
                    continue
                results.append({"type": "mgm_exact", "label": " + ".join(names),
                    "reason": f"MGM Exact {format_odds(price)} · {team} · PAIR",
                    "event": event, "methods": ["MGM Exact", "MGM Pair"]})
                for nm in names:
                    methods_map[nm].extend(["MGM Exact", "MGM Pair"])

    b365 = df[df["book"] == "bet365"].copy()
    for grp in detect_classic_groups(b365, (25, 50, 75)):
        names = sorted(grp["players"])
        d = grp["ending"]
        size = grp.get("size") or len(names)
        is_pair = size == 2
        meth = [f"B365 Match {d}", "B365 Pair" if is_pair else "B365 Trio"]
        reason = f"B365 {'pair' if is_pair else 'trio'} ends {d} · {grp.get('team', '')}"
        results.append({"type": "b365", "label": " + ".join(names), "reason": reason,
                        "event": grp["event"], "methods": meth})
        for nm in names:
            methods_map[nm].extend(meth)

    for _, row in df.iterrows():
        if row["book"] != "bet365":
            continue
        price = abs(int(row["price"])) if row["price"] is not None else 0
        if price == 850 or price % 1000 == 850:
            results.append({"type": "b365", "label": row["player"],
                "reason": f"B365 850 → {format_odds(row['price'])}",
                "event": row["event"], "methods": ["B365 850"]})
            methods_map[row["player"]].append("B365 850")

    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        books = set(g["book"])
        if "bet365" in books and "hardrockbet" in books:
            p365 = g[g["book"] == "bet365"]["price"].dropna()
            phr = g[g["book"] == "hardrockbet"]["price"].dropna()
            if not p365.empty and not phr.empty and int(p365.iloc[0]) > int(phr.iloc[0]):
                methods_map[player].append("B365 > HardRock")
                results.append({"type": "b365", "label": player,
                    "reason": f"B365 {format_odds(p365.iloc[0])} > HardRock {format_odds(phr.iloc[0])}",
                    "event": g["event"].iloc[0], "methods": ["B365 > HardRock"]})

    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        prices = g["price"].dropna().tolist()
        if len(set(prices)) == 1:
            results.append({"type": "match", "label": player,
                "reason": f"Exact {format_odds(prices[0])} → {', '.join(g['book'])}",
                "event": g["event"].iloc[0], "methods": ["Exact Match"]})
            methods_map[player].append("Exact Match")

    for _, row in df.iterrows():
        if row["book"] != "fanduel":
            continue
        player = row["player"]
        if not has_dk_or_mgm(methods_map.get(player, [])):
            continue
        price = abs(int(row["price"])) if row["price"] else 0
        last = last_two(row["price"])
        if price == 600:
            results.append({"type": "fd", "label": player,
                "reason": f"FD +600 → {format_odds(row['price'])}",
                "event": row["event"], "methods": ["FD 600"]})
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in FD_STYLE_ENDS:
            results.append({"type": "fd", "label": player,
                "reason": f"FD ≥+{FD_MIN} ends {last:02d} → {format_odds(row['price'])}",
                "event": row["event"], "methods": ["FD Pattern"]})
            methods_map[player].append("FD Pattern")

    ev_board = []
    player_events = defaultdict(set)
    for _, r in df.iterrows():
        player_events[r["player"]].add(r["event"])

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
        raw_meths = list(set(methods_map.get(player, [])))
        meths = list(dict.fromkeys(normalize_method(m) for m in raw_meths))

        primary = has_live_primary(meths)
        core_count = count_core_methods(meths)
        if not primary and core_count < METHODS_MIN:
            continue

        has_fade = player in spike_dump or "Spike" in meths or "Dump" in meths
        price_too_low = best is not None and int(best) < PRICE_MIN_TAKE
        hr_best = is_hardrock_best(prices, books)
        if hr_best:
            meths.append("HardRock best")

        is_hot = (
            primary and has_fd_heat(meths) and has_dk_support(meths)
            and not has_fade and not price_too_low and not hr_best
        )
        if is_hot and "🔥 HOT" not in meths:
            meths.insert(0, "🔥 HOT")

        is_bet = primary and not has_fade and not price_too_low and not hr_best

        display_meths = [
            m for m in meths
            if is_core_method(m) or m in (
                "Spike", "Dump", "🔥 HOT", "Was DK 10", "HardRock best",
                "Stayed in group", "Last one left", "DK FD-style",
            )
        ]
        score = girl_magic_score(core_count, edge, display_meths)
        _, bars, level = get_confidence(score, is_bet, core_count, is_hot=is_hot)
        mv_note = spike_dump.get(player, ("", "", 0))[1]

        why = f"Score {score}/100 · {core_count} core · Edge {int(edge)} (info)"
        if is_hot:
            why += " · 🔥 HOT"
        elif has_pair(meths):
            why += " · PAIR"
        elif has_trio(meths):
            why += " · TRIO fallback"
        else:
            why += " · no primary → PASS"
        if hr_best:
            why += " · PASS HardRock best"
            is_bet = False
            is_hot = False
        if price_too_low:
            why += f" · PASS price < +{PRICE_MIN_TAKE}"
            is_bet = False
            is_hot = False
        if has_fade:
            why += f" · FADE {mv_note}" if mv_note else " · FADE ±150"
            is_bet = False
            is_hot = False

        ev_board.append({
            "player": player, "best_price": best, "best_book": best_book,
            "median": med, "edge": edge, "is_bet": is_bet, "is_hot": is_hot,
            "why": why, "methods": display_meths, "score": score,
            "bars": bars, "level": level, "method_count": core_count,
            "team": team_map.get(player, ""),
            "events": list(player_events.get(player, [])), "movement": mv_note,
            "has_primary": primary, "is_pair": has_pair(meths),
        })

    def board_rank(x):
        if x.get("is_hot") and x.get("is_bet"):
            tier = 0
        elif x.get("is_bet"):
            tier = 1
        else:
            tier = 2
        return (tier, not x.get("is_pair"), -x.get("score", 0), -x.get("edge", 0))

    ev_board = sorted(ev_board, key=board_rank)

    if record_history:
        current_ev = {
            item["player"]: {
                "methods": item["methods"], "edge": item["edge"], "is_bet": item["is_bet"],
                "method_count": item["method_count"], "score": item["score"],
                "events": item.get("events", []),
            }
            for item in ev_board
        }
        st.session_state["prev_ev"] = current_ev
        save_history(prev_ev=current_ev)

    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])

    def different_teams(a, b):
        ta, tb = team_map.get(a, ""), team_map.get(b, "")
        if ta and tb:
            return ta != tb
        return len(pev[a] & pev[b]) == 0

    pool = [
        p for p, ms in methods_map.items()
        if count_core_methods(ms) >= NAME_METHODS_MIN and has_personal_strong(ms)
    ]
    if lineup_names:
        pool = [p for p in pool if name_in_lineup(p, lineup_names) is not False]

    init_map = defaultdict(list)
    for p in pool:
        f, l = get_initials(p)
        if f and l:
            init_map[f + l].append(p)
    n = 0
    for k, names in init_map.items():
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if different_teams(a, b) and n < NAME_MAX_PAIRS:
                    results.append({
                        "type": "same_init", "label": f"{a} + {b}",
                        "reason": f"Same initials {k}", "event": "", "methods": ["Same Init"],
                    })
                    n += 1

    return results, ev_board, dict(methods_map)


def render_card_grid(items):
    """Row-by-row so mobile keeps order."""
    if not items:
        st.info("None right now.")
        return
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(items):
                break
            r = items[i + j]
            with col:
                tags = render_method_tags(r.get("methods", []))
                st.markdown(
                    f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}<br>{tags}</div>',
                    unsafe_allow_html=True,
                )


def render_cheat_hits(hits, title):
    if not hits:
        st.info(f"No method hits on {title}.")
        return
    st.markdown(f"**{title} — {len(hits)} popping off**")
    for i in range(0, len(hits), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(hits):
                break
            e = hits[i + j]
            with col:
                if e["is_hot"]:
                    label, cls = "🔥 HOT", "hot"
                elif e["is_bet"]:
                    label, cls = "🟢 TAKE IT", "bet"
                elif e["primary"]:
                    label, cls = "🎰 PRIMARY", "bet"
                else:
                    label, cls = "✨ METHOD", "card"
                tags = render_method_tags(e["methods"], limit=8)
                price = format_odds(e["best_price"]) if e["best_price"] is not None else "—"
                book = e.get("best_book") or ""
                score = e["score"] if e["score"] is not None else "—"
                st.markdown(
                    f'<div class="card {cls}"><b>{label}</b> — <b>{e["matched_as"]}</b>'
                    f'<span class="score-pill">{score}</span><br>'
                    f'{price} {book}<br>{tags}</div>',
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
    st.markdown(
        f'<div class="how-to">'
        f'<b>PAIR first</b> · <b>TRIO</b> if no pair · '
        f'<b>🔥 HOT</b> = pair/trio + FD + DK · '
        f'<b>PASS</b> HardRock-best / fade / short price · '
        f'📋 Cheat Sheet · 🔒 {lock_n}'
        f'</div>',
        unsafe_allow_html=True,
    )
    render_whats_going_today()

    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add your The Odds API key.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("① Load Games", type="primary"):
            st.session_state["events"] = fetch_events_oddsapi(odds_key)
    with c2:
        if st.button("📋 RotoWire"):
            names, msg = fetch_rotowire_lineups()
            st.session_state["lineup_names"] = names
            st.session_state["lineup_msg"] = msg
            if names:
                st.success(msg)
                n_dnp = auto_mark_dnp()
                n_miss, _ = bulk_miss_to_dnp(today_only=True)
                bits = []
                if n_dnp:
                    bits.append(f"PENDING→DNP {n_dnp}")
                if n_miss:
                    bits.append(f"MISS→DNP {n_miss}")
                if bits:
                    st.info(" · ".join(bits))
            else:
                st.warning(msg or "No lineup names")
    with c3:
        if st.button("⚡ Sync MLB HRs", type="primary"):
            with st.spinner("Pulling MLB HRs…"):
                auto_n, promote_n, msg = auto_log_mlb_hrs()
            st.success(f"{msg} · auto {auto_n} · promoted {promote_n}")
            st.rerun()

    if st.session_state.get("lineup_msg") and st.session_state.get("lineup_names"):
        st.caption(st.session_state["lineup_msg"])

    if "last_hr_sync" not in st.session_state:
        st.session_state["last_hr_sync"] = -1
    if HAS_AUTOREFRESH and refresh_count != st.session_state["last_hr_sync"]:
        st.session_state["last_hr_sync"] = refresh_count
        try:
            auto_log_mlb_hrs()
            auto_mark_dnp()
        except Exception:
            pass

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games**.")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
    chosen = st.multiselect("② Select games", list(options.keys()), default=default_sel)
    st.session_state["selected_games"] = chosen

    manual_fetch = st.button("③ Fetch Odds", type="primary")
    if "last_odds_refresh" not in st.session_state:
        st.session_state["last_odds_refresh"] = -1
    auto_fetch = HAS_AUTOREFRESH and refresh_count != st.session_state["last_odds_refresh"] and bool(chosen)
    if auto_fetch:
        st.session_state["last_odds_refresh"] = refresh_count

    if (manual_fetch or auto_fetch) and chosen:
        with st.spinner("Fetching odds…"):
            df, found = do_fetch(odds_key, sgo_key, chosen, options)
        if df is not None and not df.empty:
            update_pregame_lock(df)
            if "odds" in st.session_state:
                st.session_state["previous_odds"] = st.session_state["odds"]
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["found_books"] = sorted(found)
            st.session_state["last_selected"] = list(chosen)
            st.session_state["new_fetch"] = True
            st.success(f"Loaded {len(df)} props")
            try:
                a, p, m = auto_log_mlb_hrs()
                if a or p:
                    st.info(f"MLB: {a} new · {p} promoted")
            except Exception:
                pass
            if st.session_state.get("lineup_names"):
                auto_mark_dnp()
        else:
            st.warning("No 0.5 HR odds.")

    found = st.session_state.get("found_books", [])
    if found:
        note = ""
        if "betmgm" not in found and not any("mgm" in x for x in found):
            note = " · <b>MGM missing</b>"
        st.markdown(f'<div class="info-box"><b>Books:</b> {", ".join(found)}{note}</div>', unsafe_allow_html=True)

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(st.session_state.get("previous_odds", []) or [])
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, methods_map = (
        run_flags(df, prev_df if not prev_df.empty else None, record_history=new_fetch, selected_events=selected_events)
        if not df.empty else ([], [], {})
    )
    st.session_state["methods_map"] = methods_map
    st.session_state["ev_board"] = ev_board
    if ev_board:
        log_bet_this(ev_board)

    all_rows = load_results()
    today_rows = [r for r in all_rows if r.get("date") == today_az()]
    hits_n = sum(1 for r in today_rows if r.get("result") == "HIT")
    misses_n = sum(1 for r in today_rows if r.get("result") == "MISS")
    graded_n = hits_n + misses_n
    hit_pct = int(hits_n / graded_n * 100) if graded_n else 0
    n_was_dk = len([r for r in results if r["type"] == "dk_was"])
    n_hot = len([e for e in ev_board if e.get("is_hot") and e.get("is_bet")])
    n_take = len([e for e in ev_board if e["is_bet"] and not e.get("is_hot")])
    n_pass = len([e for e in ev_board if not e["is_bet"]])
    n_pairs = len([r for r in results if r["type"] == "mgm" and "PAIR" in r.get("reason", "")])

    st.markdown(f"""
    <div class="petty-row">
      <div class="petty-box"><div class="petty-num">{n_hot}</div><div class="petty-label">🔥 HOT</div></div>
      <div class="petty-box"><div class="petty-num">{n_take}</div><div class="petty-label">🟢 TAKE IT</div></div>
      <div class="petty-box"><div class="petty-num">{n_pass}</div><div class="petty-label">⚪ PASS</div></div>
      <div class="petty-box"><div class="petty-num">{n_pairs}</div><div class="petty-label">🎰 MGM PAIRS</div></div>
      <div class="petty-box"><div class="petty-num">{n_was_dk}</div><div class="petty-label">📉 Was DK 10</div></div>
      <div class="petty-box"><div class="petty-num">{hit_pct}%</div><div class="petty-label">📈 HIT%</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab_board, tab_tricks, tab_names, tab_sheet, tab_results, tab_gloss = st.tabs([
        "👑 The Board", "✨ Odds Tricks", "💅 Name Magic",
        "📋 Cheat Sheet", "📊 Results", "📖 Glossary",
    ])

    with tab_board:
        st.markdown('<div class="queen-banner">👑 The Board</div>', unsafe_allow_html=True)
        st.caption("PAIR first · TRIO if no pair · HOT = pair/trio + FD + DK · HardRock best = PASS")
        if not ev_board:
            st.info("Select games and fetch.")
        else:
            # Row-by-row → mobile keeps HOT → TAKE → PASS order
            for i in range(0, len(ev_board), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j >= len(ev_board):
                        break
                    item = ev_board[i + j]
                    with col:
                        tags = render_method_tags(item["methods"])
                        meter = make_meter(item["bars"], item["level"])
                        cls = "bet" if item["is_bet"] else "skip"
                        if item.get("is_hot") and item["is_bet"]:
                            cls = "hot"
                        if "Spike" in item["methods"] or "Dump" in item["methods"] or "HardRock best" in item["methods"]:
                            cls = "skip fade-card"
                        if item.get("is_hot") and item["is_bet"]:
                            label = "🔥 HOT TAKE"
                        elif item["is_bet"]:
                            label = "🟢 TAKE IT"
                        else:
                            label = "⚪ PASS"
                        mv = item.get("movement") or ""
                        mv_line = f"<br><small>{mv}</small>" if mv else ""
                        st.markdown(f'''
                        <div class="card {cls}">
                          <b>{label}</b> — <b>{item["player"]}</b>
                          <span class="score-pill">{item["score"]}</span><br>{meter}
                          Best {format_odds(item["best_price"])} · {item["best_book"]}
                          · edge {int(item["edge"])} · core {item.get("method_count", 0)}<br>
                          {tags}{mv_line}<br><small>{item["why"]}</small>
                        </div>''', unsafe_allow_html=True)

    with tab_tricks:
        st.markdown('<div class="queen-banner">✨ Odds Tricks</div>', unsafe_allow_html=True)
        sub = st.tabs([
            "🎯 DK 10 / FD-style", "📉 Was DK 10", "🎰 MGM pairs/trios",
            "⭐ MGM Exact", "🤝 Exact", "💙 FD", "💚 365 pairs/trios", "🔒 Lock",
        ])
        with sub[0]:
            st.caption("DK ends-in-10 + DK priced like FD")
            render_card_grid([r for r in results if r["type"] == "dk"])
        with sub[1]:
            render_card_grid([r for r in results if r["type"] == "dk_was"])
        with sub[2]:
            st.caption("PAIR preferred · TRIO only when ending has exactly 3")
            render_card_grid([r for r in results if r["type"] == "mgm"])
        with sub[3]:
            render_card_grid([r for r in results if r["type"] == "mgm_exact"])
        with sub[4]:
            render_card_grid([r for r in results if r["type"] == "match"])
        with sub[5]:
            render_card_grid([r for r in results if r["type"] == "fd"])
        with sub[6]:
            st.caption("Same classic endings · 25/50/75 · pair then trio")
            render_card_grid([r for r in results if r["type"] == "b365"])
        with sub[7]:
            lock = st.session_state.get("pregame_lock") or load_pregame()
            if not lock:
                st.info("Fetch pregame to build lock.")
            else:
                q = st.text_input("Filter", key="lock_q")
                shown = 0
                for player, entry in sorted(lock.items()):
                    if q and q.lower() not in player.lower():
                        continue
                    books = entry.get("books") or {}
                    lines = [
                        f"{book_label(b)} {format_odds(info.get('price'))}"
                        for b, info in books.items() if info.get("price") is not None
                    ]
                    mv, _ = movement_summary(player)
                    extra = f" · {mv}" if mv else ""
                    if lines:
                        st.markdown(f"**{player}** — " + " · ".join(lines) + extra)
                        shown += 1
                    if shown >= 80:
                        break

    with tab_names:
        st.markdown('<div class="queen-banner">💅 Name Magic</div>', unsafe_allow_html=True)
        nsub = st.tabs(["Same Init", "Double", "Cross", "Last", "First"])
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

    with tab_sheet:
        st.markdown('<div class="queen-banner">📋 Cheat Sheet Check</div>', unsafe_allow_html=True)
        st.caption("Paste names (one per line). Shows who also hits our live methods.")

        col_a, col_b = st.columns(2)
        with col_a:
            my_text = st.text_area("💜 My cheat sheet", height=180, placeholder="One name per line", key="cheat_mine")
        with col_b:
            girls_text = st.text_area("💖 Girls’ cheat sheet", height=180, placeholder="One name per line", key="cheat_girls")

        show_misses = st.checkbox("Also show names with no method hits", value=False, key="cheat_show_miss")
        mm = st.session_state.get("methods_map") or methods_map or {}
        eb = st.session_state.get("ev_board") or ev_board or []

        if not mm and not eb:
            st.warning("Fetch odds first.")
        else:
            my_names = parse_cheat_sheet(my_text)
            girls_names = parse_cheat_sheet(girls_text)
            if my_names:
                hits, misses = check_cheat_sheet(my_names, mm, eb, "My sheet")
                render_cheat_hits(hits, "💜 My sheet")
                if show_misses and misses:
                    with st.expander(f"No method hit ({len(misses)})"):
                        st.write(", ".join(m["sheet_name"] for m in misses))
            if girls_names:
                hits, misses = check_cheat_sheet(girls_names, mm, eb, "Girls sheet")
                render_cheat_hits(hits, "💖 Girls’ sheet")
                if show_misses and misses:
                    with st.expander(f"Girls — no method hit ({len(misses)})"):
                        st.write(", ".join(m["sheet_name"] for m in misses))
            if my_names and girls_names:
                my_set = {n.lower() for n in my_names}
                both = [n for n in girls_names if n.lower() in my_set]
                if both:
                    st.markdown("**🤝 On both sheets**")
                    st.write(", ".join(both))
            if not my_names and not girls_names:
                st.info("Paste at least one name to check.")

    with tab_results:
        st.markdown('<div class="queen-banner">📊 Results</div>', unsafe_allow_html=True)
        top = st.columns([1, 1, 1, 1])
        with top[0]:
            if st.button("⚡ Sync MLB", key="sync_res"):
                with st.spinner("MLB…"):
                    a, p, m = auto_log_mlb_hrs()
                st.success(f"{m} · {a} new · {p} promoted")
                st.rerun()
        with top[1]:
            if st.button("📋 PENDING→DNP", key="mark_dnp"):
                n = auto_mark_dnp()
                st.success(f"PENDING → DNP: {n}")
                st.rerun()
        with top[2]:
            if st.button("🟡 MISS→DNP", key="miss_to_dnp"):
                n, msg = bulk_miss_to_dnp(today_only=True)
                st.success(msg) if n else st.warning(msg)
                st.rerun()
        with top[3]:
            today_only = st.checkbox("Today only", value=True, key="res_today")

        with st.expander("⚡ Manual Log", expanded=False):
            lc1, lc2, lc3, lc4 = st.columns([2, 1, 1, 1])
            with lc1:
                hr_player = st.text_input("Player", key="hr_player")
            with lc2:
                hr_price = st.text_input("Price", key="hr_price")
            with lc3:
                hr_book = st.selectbox(
                    "Book",
                    ["betmgm", "draftkings", "fanduel", "bet365", "hardrockbet", "untagged"],
                    key="hr_book",
                )
            with lc4:
                st.write("")
                st.write("")
                if st.button("Log HIT", key="manual_log"):
                    ok, msg = log_manual_hr(hr_player, hr_price, hr_book)
                    st.success(msg) if ok else st.error(msg)
                    if ok:
                        st.rerun()

        rows = load_results()
        rows_view = [r for r in rows if r.get("date") == today_az()] if today_only else rows
        pending = sorted([r for r in rows_view if r.get("result") == "PENDING"], key=pending_sort_key)
        done = [r for r in rows_view if r.get("result") in ("HIT", "MISS")]
        dnps = [r for r in rows_view if r.get("result") == "DNP"]
        hits = sum(1 for r in done if r["result"] == "HIT")
        misses = sum(1 for r in done if r["result"] == "MISS")
        rate = (hits / (hits + misses) * 100) if (hits + misses) else 0

        st.markdown(f"""
        <div class="petty-row">
          <div class="petty-box"><div class="petty-num">{len(pending)}</div><div class="petty-label">PENDING</div></div>
          <div class="petty-box"><div class="petty-num">{hits}</div><div class="petty-label">HITS</div></div>
          <div class="petty-box"><div class="petty-num">{misses}</div><div class="petty-label">MISSES</div></div>
          <div class="petty-box"><div class="petty-num">{rate:.0f}%</div><div class="petty-label">HIT%</div></div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("Hit rate by BEST book", expanded=True):
            st.caption("HIT/MISS · no Untagged/365/Caesars")
            graded_for_books = [r for r in rows_view if r.get("result") in ("HIT", "MISS")]
            book_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
            for r in graded_for_books:
                b = r.get("best_book") or "untagged"
                if is_bet365(b) or "caesar" in str(b).lower():
                    continue
                bl = book_label(b)
                if bl not in ALLOWED_BEST_BOOKS:
                    continue
                if r.get("result") == "HIT":
                    book_stats[bl]["hit"] += 1
                else:
                    book_stats[bl]["miss"] += 1
            if not book_stats:
                st.caption("Grade PENDING first.")
            else:
                ranked = sorted(
                    book_stats.items(),
                    key=lambda x: (-(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])), -(x[1]["hit"] + x[1]["miss"])),
                )
                cols = st.columns(min(4, max(1, len(ranked))))
                for i, (bl, s) in enumerate(ranked):
                    t = s["hit"] + s["miss"]
                    pct = int(s["hit"] / t * 100) if t else 0
                    with cols[i % len(cols)]:
                        st.markdown(
                            f'<div class="petty-box"><div class="petty-num">{pct}%</div>'
                            f'<div class="petty-label">{bl}</div>'
                            f'<div style="font-size:.65rem;color:#e9d5ff;margin-top:4px">{s["hit"]}H / {s["miss"]}M</div></div>',
                            unsafe_allow_html=True,
                        )

        total_p = len(pending)
        page = st.session_state.get("pending_page", 0)
        max_page = max(0, (total_p - 1) // PENDING_PAGE) if total_p else 0
        if page > max_page:
            page = 0
            st.session_state["pending_page"] = 0
        start, end = page * PENDING_PAGE, min(page * PENDING_PAGE + PENDING_PAGE, total_p)
        slice_p = pending[start:end]
        st.markdown(f"**Pending** {start + 1 if total_p else 0}–{end} of **{total_p}**")
        n1, n2, _ = st.columns([1, 1, 4])
        with n1:
            if st.button("← Prev", disabled=page <= 0, key="prev_p"):
                st.session_state["pending_page"] = max(0, page - 1)
                st.rerun()
        with n2:
            if st.button("Next →", disabled=page >= max_page, key="next_p"):
                st.session_state["pending_page"] = min(max_page, page + 1)
                st.rerun()

        if not slice_p:
            st.info("No pending.")
        else:
            left, right = st.columns(2)
            for idx, r in enumerate(slice_p):
                col = left if idx % 2 == 0 else right
                with col:
                    rid = r["id"]
                    endg = r.get("ending")
                    end_s = f" · {int(endg):02d}" if endg is not None else ""
                    meths = list(dict.fromkeys(normalize_method(m) for m in (r.get("methods") or [])))
                    tags = render_method_tags(meths, limit=8)
                    st.markdown(
                        f'<div class="res-card"><b>{r["player"]}</b> · '
                        f'{format_odds(r.get("best_price"))} {book_label(r.get("best_book"))}{end_s}'
                        f'<br>{tags}</div>',
                        unsafe_allow_html=True,
                    )
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("🟢", key=f"hit_{rid}"):
                            set_result_status(rid, "HIT")
                            st.rerun()
                    with b2:
                        if st.button("🔴", key=f"miss_{rid}"):
                            set_result_status(rid, "MISS")
                            st.rerun()
                    with b3:
                        if st.button("🟡", key=f"dnp_{rid}"):
                            set_result_status(rid, "DNP")
                            st.rerun()

        with st.expander(f"All graded ({len(done)})", expanded=True):
            if not done:
                st.caption("None yet.")
            else:
                for r in sorted(done, key=pending_sort_key):
                    rid = r["id"]
                    icon = "🟢" if r["result"] == "HIT" else "🔴"
                    meths = list(dict.fromkeys(normalize_method(m) for m in (r.get("methods") or [])))
                    tags = render_method_tags(meths, limit=10)
                    st.markdown(
                        f'<div class="res-card">{icon} <b>{r["player"]}</b> · '
                        f'{format_odds(r.get("best_price"))} {book_label(r.get("best_book"))}<br>{tags}</div>',
                        unsafe_allow_html=True,
                    )
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        if r.get("result") != "HIT" and st.button("🟢", key=f"g_hit_{rid}"):
                            set_result_status(rid, "HIT")
                            st.rerun()
                    with c2:
                        if r.get("result") != "MISS" and st.button("🔴", key=f"g_miss_{rid}"):
                            set_result_status(rid, "MISS")
                            st.rerun()
                    with c3:
                        if st.button("🟡", key=f"g_dnp_{rid}"):
                            set_result_status(rid, "DNP")
                            st.rerun()
                    with c4:
                        if st.button("↩️", key=f"g_undo_{rid}"):
                            undo_result(rid, r.get("source"))
                            st.rerun()

        with st.expander(f"DNP ({len(dnps)})", expanded=False):
            for r in sorted(dnps, key=lambda x: x.get("player") or ""):
                st.markdown(f"🟡 **{r.get('player')}** · was {format_odds(r.get('best_price'))}")

    with tab_gloss:
        st.markdown('<div class="queen-banner">📖 The Code</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="how-to">
            <b>Girl Magic in one breath:</b><br>
            Classic endings only on <b>MGM + Bet365</b> · same team.<br>
            <b>PAIR (exactly 2)</b> first. <b>TRIO (exactly 3)</b> only when that ending has no pair.<br>
            <b>🔥 HOT</b> = pair/trio + FanDuel pattern + DK 10 / Was DK 10 / DK FD-style.<br>
            <b>🟢 TAKE IT</b> = live pair/trio · not faded · price high enough · not HardRock-best.<br>
            <b>⚪ PASS</b> = no pair/trio · HardRock is best · big move (±150) · price too low.<br>
            <b>No Caesars.</b> Edge is info only.
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔥 HOT · 🟢 TAKE IT · ⚪ PASS", expanded=True):
            st.markdown(f"""
**PAIR** — exactly 2 · same team · same classic ending  
**TRIO** — exactly 3 · only when that ending is not a pair  

| Book | Endings |
|------|---------|
| **BetMGM** | 00 · 25 · 50 · 75 |
| **Bet365** | 25 · 50 · 75 |

**🔥 HOT** = pair/trio + FD + DK support · not faded · ≥ +{PRICE_MIN_TAKE} · not HardRock-best  

**🟢 TAKE IT** = live pair/trio · not faded · ≥ +{PRICE_MIN_TAKE} · not HardRock-best  

**⚪ PASS** = no primary · HardRock best · ±{BIG_MOVE} · short price  

**Board order on phone:** cards render row-by-row so HOT → TAKE → PASS stays in order.
            """)

        with st.expander("🎯 DK · 💙 FD · HardRock"):
            st.markdown(f"""
**DK 10** · **Was DK 10** · **DK FD-style** (≥ +{FD_MIN} ending like FD)  
**FD Pattern / FD 600**  
**HardRock best** → automatic **PASS**
            """)

        with st.expander("📋 Cheat Sheet"):
            st.markdown("Paste My sheet / Girls’ sheet → see who also hits live methods.")

        with st.expander("What we ignore"):
            st.markdown("- Caesars · digits on non-MGM/365 books · edge as a gate")

    st.markdown(
        '<div class="footer">👑 Girl Magic · Boss Bitch · HBIC · Me & My Girls</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
