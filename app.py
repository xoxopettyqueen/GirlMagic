"""
Girl Magic Odds ✨ — FULL FIX
- Book aliases: williamhill_us → caesars, hardrockbet_oh → hardrockbet
- Keeps Hard Rock + Caesars when DK/FD/MGM missing from Odds API
- Debug: books seen vs kept (no more fake "games are live")
- Pregame lock · Results + Undo · methods tabs
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
.stApp{background:linear-gradient(165deg,#0a0410,#160a22 40%,#1f0b30);color:#fce7f3;font-family:Inter,sans-serif}
h1{font-family:'Playfair Display',serif!important;font-weight:900!important;background:linear-gradient(90deg,#f9a8d4,#e879f9,#c084fc,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2.5rem!important}
.subtitle{color:#f9a8d4;font-size:.9rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.tagline{color:#e9d5ff;font-size:.88rem;font-style:italic;margin-bottom:14px}
.how-to{background:linear-gradient(135deg,#1a0f28,#2a1040);border:1px solid #f472b6;border-radius:14px;padding:12px 16px;margin-bottom:14px;font-size:.86rem;position:relative}
.how-to::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:linear-gradient(180deg,#f472b6,#c084fc)}
.how-to b{color:#f9a8d4}
.warning-box{background:#3b0764;border:2px solid #f472b6;border-radius:12px;padding:10px 14px;margin-bottom:12px;font-size:.9rem}
.info-box{background:#1a0f28;border:1px solid #a855f7;border-radius:12px;padding:10px 14px;margin-bottom:10px;font-size:.88rem}
.debug-box{background:#0f172a;border:1px solid #64748b;border-radius:12px;padding:10px 14px;margin-bottom:12px;font-size:.8rem;color:#cbd5e1;font-family:ui-monospace,monospace}
.stButton>button{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important}
.petty-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.petty-box{flex:1;min-width:68px;background:#1a0f28;border:1px solid #f472b6;border-radius:12px;padding:8px 6px;text-align:center}
.petty-num{font-size:1.25rem;font-weight:800;color:#f9a8d4}
.petty-label{font-size:.55rem;color:#e9d5ff;margin-top:3px}
.card{background:linear-gradient(155deg,#1a0f28,#251438);border:1px solid #f472b6;border-radius:12px;padding:10px 12px;color:#fdf2f8;position:relative;font-size:.92rem;margin-bottom:7px}
.card::before{content:'';position:absolute;top:0;left:0;width:4px;height:100%;border-radius:12px 0 0 12px;background:#f472b6}
.bet{background:linear-gradient(155deg,#0c2418,#143d28)!important;border-color:#34d399!important}
.skip{background:#14101c!important;border-color:#4b5563!important;opacity:.85}
.score-pill{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-weight:800;font-size:.9rem;padding:2px 10px;border-radius:12px;margin-left:6px}
.tag{display:inline-block;background:#3b0764;color:#f9a8d4;font-size:.68rem;font-weight:700;padding:2px 7px;border-radius:10px;margin:2px 3px 2px 0;border:1px solid #a855f7}
.tag-dk{background:#064e3b;color:#6ee7b7;border-color:#34d399}
.tag-mgm{background:#422006;color:#fcd34d;border-color:#f59e0b}
.tag-fd{background:#1e3a5f;color:#93c5fd;border-color:#3b82f6}
.tag-match{background:#4c1d95;color:#e9d5ff;border-color:#a855f7}
.tag-strong{background:#14532d;color:#bbf7d0;border-color:#22c55e}
.tag-b365{background:#14532d;color:#86efac;border-color:#22c55e}
.queen-banner{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-size:.75rem;font-weight:700;padding:5px 12px;border-radius:16px;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px}
.stTabs [data-baseweb=tab]{background:#1a0f28;border-radius:8px;color:#f9a8d4;font-weight:600;font-size:.76rem;padding:6px 8px}
.stTabs [aria-selected=true]{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important}
.footer{text-align:center;color:#f9a8d4;margin-top:28px;opacity:.9;padding-bottom:16px}
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

# Normalize API keys → our keys
BOOK_ALIASES = {
    "williamhill_us": "caesars",      # Caesars
    "hardrockbet_oh": "hardrockbet",
    "hardrockbet_nj": "hardrockbet",
    "caesars_oh": "caesars",
    "betmgm_nj": "betmgm",
    "betmgm_az": "betmgm",
}

# Books we KEEP after normalize (core + backups when DK/FD/MGM missing)
PREFERRED = {
    "fanduel", "draftkings", "betmgm", "bet365", "bet365_au",
    "hardrockbet", "caesars",
}

CORE_BOOKS = {
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
    "betmgm": "BetMGM",
    "bet365": "Bet365",
}

LATE_BOOKS = {"fanduel", "draftkings", "betmgm", "hardrockbet", "caesars"}
EDGE_MIN = 60
METHODS_MIN = 2
OUTLIER_GAP = 150
REFRESH_MINUTES = 30
NAME_METHODS_MIN = 3
NAME_MAX_PAIRS = 50
FD_MIN = 500
PENDING_PAGE = 40

PERSONAL_STRONG = {
    "DK 10", "FD Pattern", "FD 600", "Exact Match", "MGM Exact",
    "Match 25", "Match 50", "Match 75",
    "B365 850", "B365 Match 25", "B365 Match 50", "B365 Match 75",
    "B365 > HardRock", "Last one left", "Multi-book Shorten", "Same on 3+ books",
}
NOISE_METHODS = {
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup",
    "In lineup · missing books", "Price moved", "Multi-book Lengthen",
    "Shortening", "Lengthening", "Stayed the same", "Way different",
}

def normalize_book(key):
    k = str(key or "").lower().strip()
    if "bet365" in k:
        return "bet365"
    return BOOK_ALIASES.get(k, k)

def is_bet365(book):
    return "bet365" in str(book).lower() or str(book).lower() == "365"

def is_hardrock(book):
    return "hardrock" in str(book).lower()

def is_core_method(m):
    if m in NOISE_METHODS:
        return False
    if m.startswith(("Shortening (", "Lengthening (", "FADE", "FD under", "Outlier", "Stuck", "Same ending")):
        return False
    return True

def count_core_methods(meths):
    return len([m for m in set(meths) if is_core_method(m)])

def has_personal_strong(meths):
    return any(m in PERSONAL_STRONG or m.startswith("Match ") or m.startswith("B365") for m in meths)

def has_dk_or_mgm(meths):
    for m in meths:
        if m == "DK 10" or m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m:
            return True
    return False

def method_tag_class(m):
    m = str(m)
    if m == "DK 10" or m.startswith("DK"):
        return "tag-dk"
    if m.startswith("MGM") or "Stayed in group" in m or m == "Last one left":
        return "tag-mgm"
    if m.startswith("FD"):
        return "tag-fd"
    if m.startswith("B365"):
        return "tag-b365"
    if m in ("Exact Match", "MGM Exact") or m.startswith("Match "):
        return "tag-match"
    if "Multi-book Shorten" in m or m == "Same on 3+ books":
        return "tag-strong"
    return ""

def render_method_tags(methods, limit=6):
    return "".join(f'<span class="tag {method_tag_class(m)}">{m}</span>' for m in list(methods)[:limit])

def girl_magic_score(core_count, edge, methods):
    method_pts = min(core_count, 5) * 10
    edge_pts = min(40, max(0, int((edge / 180) * 40)))
    bonus = 0
    if "Last one left" in methods:
        bonus += 5
    if any("Stayed in group" in m or m == "Stayed in the group" for m in methods):
        bonus += 3
    if "Multi-book Shorten" in methods:
        bonus += 3
    if "Same on 3+ books" in methods:
        bonus += 2
    return min(100, method_pts + edge_pts + min(10, bonus))

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
    b = normalize_book(b)
    labels = {
        "betmgm": "MGM", "draftkings": "DK", "fanduel": "FD", "bet365": "365",
        "hardrockbet": "HardRock", "caesars": "Caesars",
    }
    return labels.get(b, (b or "—").title())

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

# ── pregame lock ─────────────────────────────────────────────
def load_pregame():
    if not os.path.exists(PREGAME_FILE):
        return {}
    try:
        with open(PREGAME_FILE) as f:
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
        book = normalize_book(r["book"])
        price = r["price"]
        event = r.get("event") or ""
        if player not in lock:
            lock[player] = {"date": today, "event": event, "books": {}, "locked_at": ts, "updated_at": ts}
        entry = lock[player]
        if event:
            entry["event"] = event
        entry["date"], entry["updated_at"] = today, ts
        entry.setdefault("books", {})
        entry["books"][book] = {"price": int(price) if price is not None else None, "ending": last_two(price), "seen_at": ts}
        if book == "betmgm":
            entry["mgm_price"] = int(price) if price is not None else entry.get("mgm_price")
            entry["mgm_ending"] = last_two(price)
    save_pregame(lock)
    st.session_state["pregame_lock"] = lock
    return lock

def get_locked(player):
    lock = st.session_state.get("pregame_lock") or load_pregame()
    return lock.get(clean_name(player)) or lock.get(player) or {}

def locked_price_str(player):
    books = (get_locked(player).get("books") or {})
    parts = [f"{book_label(b)} {format_odds(info.get('price'))}" for b, info in sorted(books.items()) if info.get("price") is not None]
    return " · ".join(parts)

# ── results ──────────────────────────────────────────────────
def load_results():
    if not os.path.exists(RESULTS_FILE):
        return []
    try:
        with open(RESULTS_FILE) as f:
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
        save_results([x for x in load_results() if x.get("id") != row_id])
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
        locked = get_locked(item["player"])
        rows.append({
            "id": f"{today}_{item['player']}_{int(item['score'])}",
            "date": today, "time": now_az(), "player": item["player"],
            "score": item["score"], "edge": int(item["edge"]),
            "best_price": item.get("best_price"), "best_book": item.get("best_book", ""),
            "ending": last_two(item.get("best_price")),
            "mgm_locked": locked.get("mgm_price"), "mgm_ending": locked.get("mgm_ending"),
            "methods": item["methods"], "core": item.get("method_count", 0),
            "result": "PENDING", "source": "take_it", "logged_at": now_utc_iso(),
        })
        added += 1
    if added:
        save_results(rows)
    return added

def log_manual_hr(player, price, book):
    player = clean_name(player)
    if not player:
        return False, "Need player name"
    if (price is None or str(price).strip() == ""):
        locked = get_locked(player)
        books = locked.get("books") or {}
        bkey = normalize_book(book)
        if bkey in books and books[bkey].get("price") is not None:
            price = books[bkey]["price"]
        elif bkey == "betmgm":
            price = locked.get("mgm_price")
    try:
        price = int(str(price).replace("+", "").replace(",", "").strip())
    except Exception:
        return False, "Need price (or lock for that book)"
    book = normalize_book(book or "untagged")
    rows = load_results()
    rid = f"hr_{today_az()}_{player}_{price}_{book}_{len(rows)}"
    rows.append({
        "id": rid, "date": today_az(), "time": now_az(), "player": player,
        "best_price": price, "best_book": book, "ending": last_two(price),
        "methods": ["Manual HR log"], "result": "HIT", "source": "manual_hr",
        "logged_at": now_utc_iso(),
    })
    save_results(rows)
    return True, f"Logged {player} {format_odds(price)} {book_label(book)}"

def pending_sort_key(r):
    return (r.get("date") or "", r.get("time") or "", r.get("logged_at") or "", r.get("player") or "")

# ── history (light) ──────────────────────────────────────────
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return
    try:
        with open(HISTORY_FILE) as f:
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

# ── fetch (FIXED) ────────────────────────────────────────────
def fetch_events_oddsapi(api_key):
    try:
        r = requests.get(f"{ODDS_API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Events error: {e}")
        return []

def fetch_odds_oddsapi(api_key, event_id):
    """Return (data_or_None, status, err_snip, raw_book_keys)."""
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/baseball_mlb/events/{event_id}/odds",
            params={
                "apiKey": api_key,
                "regions": REGIONS,
                "markets": "batter_home_runs",
                "oddsFormat": "american",
            },
            timeout=25,
        )
        raw_keys = []
        if r.status_code == 200:
            data = r.json()
            for b in data.get("bookmakers") or []:
                raw_keys.append(b.get("key", ""))
            return data, r.status_code, "", raw_keys
        return None, r.status_code, (r.text or "")[:180], []
    except Exception as e:
        return None, 0, str(e)[:180], []

def flatten_oddsapi(data):
    """Parse props. Normalize book keys. Keep PREFERRED after alias."""
    if not data:
        return [], set(), set()
    rows = []
    found_raw = set()
    found_kept = set()
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers") or []:
        raw = (book.get("key") or "").lower()
        found_raw.add(raw)
        bk = normalize_book(raw)
        if bk not in PREFERRED:
            continue
        found_kept.add(bk)
        for market in book.get("markets") or []:
            if market.get("key") != "batter_home_runs":
                continue
            for o in market.get("outcomes") or []:
                if str(o.get("name", "")).lower() != "over":
                    continue
                pt = o.get("point")
                if pt is None:
                    continue
                try:
                    if abs(float(pt) - 0.5) > 0.01:
                        continue
                except Exception:
                    continue
                player = o.get("description")
                price = o.get("price")
                if not player or price is None:
                    continue
                rows.append({
                    "event": event, "book": bk, "player": player,
                    "price": int(price), "point": 0.5, "team": "", "source": "oddsapi",
                })
    return rows, found_raw, found_kept

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(
            f"{SGO_BASE}/events",
            params={"apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 30},
            timeout=30,
        )
        if r.status_code != 200:
            return rows, found, f"SGO HTTP {r.status_code}"
        for ev in (r.json().get("data") or []):
            if ev.get("status", {}).get("started"):
                continue
            teams = ev.get("teams") or {}
            home = (teams.get("home") or {}).get("names", {}).get("long", "Home")
            away = (teams.get("away") or {}).get("names", {}).get("long", "Away")
            event_name = f"{away} @ {home}"
            players_map = ev.get("players") or {}
            for odd_id, odd_data in (ev.get("odds") or {}).items():
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
                for bk, bd in (odd_data.get("byBookmaker") or {}).items():
                    if not bd.get("available", True):
                        continue
                    b = normalize_book(bk)
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
                        "event": event_name, "book": b, "player": pname,
                        "price": price, "point": 0.5, "team": team, "source": "sgo",
                    })
        return rows, found, ""
    except Exception as e:
        return rows, found, str(e)[:120]

def merge_odds(rows_a, rows_b):
    combined = rows_a + rows_b
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
    """Fetch + diagnostics so empty board is explainable."""
    all_rows = []
    all_raw, all_kept = set(), set()
    per_game = []
    errors = []

    for label in chosen_labels:
        eid = options.get(label)
        if not eid:
            errors.append(f"No event id for {label}")
            continue
        data, status, err, raw_keys = fetch_odds_oddsapi(odds_key, eid)
        if status != 200:
            errors.append(f"{label}: HTTP {status} {err}")
            per_game.append({"game": label, "status": status, "raw": [], "kept_rows": 0})
            continue
        rows, found_raw, found_kept = flatten_oddsapi(data)
        all_rows.extend(rows)
        all_raw |= found_raw
        all_kept |= found_kept
        per_game.append({
            "game": label, "status": 200,
            "raw": sorted(found_raw), "kept_rows": len(rows),
        })

    sgo_rows, sgo_found, sgo_err = fetch_sgo_hr_props(sgo_key)
    all_rows.extend(sgo_rows)
    all_kept |= sgo_found
    if sgo_err:
        errors.append(sgo_err)

    df = merge_odds(
        [r for r in all_rows if r.get("source") == "oddsapi"],
        [r for r in all_rows if r.get("source") == "sgo"],
    )
    if chosen_labels and not df.empty and "event" in df.columns:
        mask = df["event"].apply(lambda e: event_matches_chosen(e, chosen_labels))
        df = df[mask].copy()

    debug = {
        "oddsapi_rows": len([r for r in all_rows if r.get("source") == "oddsapi"]),
        "sgo_rows": len(sgo_rows),
        "merged_rows": 0 if df is None or df.empty else len(df),
        "raw_books": sorted(all_raw),
        "kept_books": sorted(all_kept),
        "core_present": sorted([b for b in ("fanduel", "draftkings", "betmgm", "bet365") if b in all_kept]),
        "per_game": per_game,
        "errors": errors,
    }
    return df, all_kept, debug

# ── flags (core methods) ─────────────────────────────────────
def run_flags(df, record_history=True, selected_events=None):
    if df is None or df.empty:
        return [], [], []

    if "team" not in df.columns:
        df["team"] = ""
    df["book"] = df["book"].apply(normalize_book)
    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()

    results, methods_map = [], defaultdict(list)
    all_players = set(df["player"].unique())
    selected = set(selected_events) if selected_events else set(df["event"].unique())
    team_map = {r["player"]: r["team"] for _, r in df.iterrows() if r.get("team")}
    lineup_names = st.session_state.get("lineup_names", set())

    for k in ("presence_history", "price_history", "mgm_history"):
        if k not in st.session_state:
            st.session_state[k] = []

    current_presence = {(r["player"], r["book"], r["event"]) for _, r in df.iterrows() if r["book"] in LATE_BOOKS}
    current_prices = {(r["player"], r["book"]): r["price"] for _, r in df.iterrows()}
    if record_history:
        st.session_state["presence_history"] = (st.session_state["presence_history"] + [current_presence])[-12:]
        st.session_state["price_history"] = (st.session_state["price_history"] + [current_prices])[-8:]

    # DK 10
    for _, row in df.iterrows():
        if row["book"] == "draftkings" and last_two(row["price"]) == 10:
            results.append({"type": "dk", "label": row["player"], "reason": f"DK ends in 10 → {format_odds(row['price'])}", "event": row["event"], "methods": ["DK 10"]})
            methods_map[row["player"]].append("DK 10")

    # MGM groups same team
    mgm = df[df["book"] == "betmgm"].copy()
    current_mgm = []
    group_cols = ["event", "team"] if mgm["team"].astype(str).str.len().gt(0).any() else ["event"]
    if not mgm.empty:
        for keys, g in mgm.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            event, team = keys[0], (keys[1] if len(keys) > 1 else "")
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in (0, 25, 50, 75):
                    ends[d].append(r["player"])
            for d, ps in ends.items():
                names = sorted(set(ps))
                if len(names) < 2:
                    continue
                current_mgm.append({"event": event, "ending": d, "team": team or "", "players": frozenset(names)})
                kind = "pair" if len(names) == 2 else f"group of {len(names)}"
                tnote = f" · {team}" if team else ""
                meth = [f"MGM {d:02d}"]
                results.append({"type": "mgm", "label": " + ".join(names), "reason": f"MGM {kind} ends in {d:02d}{tnote}", "event": event, "methods": meth})
                for n in names:
                    methods_map[n].extend(meth)
                if d in (25, 50, 75) and len(names) in (2, 3):
                    results.append({"type": "digit", "label": " + ".join(names), "reason": f"Digit {kind} ends in {d}{tnote}", "event": event, "methods": [f"Match {d}"]})
                    for n in names:
                        methods_map[n].append(f"Match {d}")

    if record_history:
        st.session_state["mgm_history"] = (st.session_state["mgm_history"] + [current_mgm])[-8:]

    # MGM exact same price same team
    if not mgm.empty:
        for keys, g in mgm.groupby(group_cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            event, team = keys[0], (keys[1] if len(keys) > 1 else "")
            for price, pg in g.groupby("price"):
                names = sorted(pg["player"].unique())
                if len(names) >= 2:
                    results.append({"type": "mgm_exact", "label": " + ".join(names), "reason": f"MGM Exact {format_odds(price)} ({len(names)})", "event": event, "methods": ["MGM Exact"]})
                    for n in names:
                        methods_map[n].append("MGM Exact")

    # Exact match any books
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        prices = g["price"].dropna().tolist()
        if len(set(prices)) == 1:
            results.append({"type": "match", "label": player, "reason": f"Exact {format_odds(prices[0])} → {', '.join(g['book'])}", "event": g['event'].iloc[0], "methods": ["Exact Match"]})
            methods_map[player].append("Exact Match")

    # FD patterns (need DK or MGM method)
    for _, row in df.iterrows():
        if row["book"] != "fanduel":
            continue
        player = row["player"]
        if not has_dk_or_mgm(methods_map.get(player, [])):
            continue
        price = abs(int(row["price"]))
        last = last_two(row["price"])
        if price == 600:
            results.append({"type": "fd", "label": player, "reason": f"FD +600 · {format_odds(row['price'])}", "event": row["event"], "methods": ["FD 600"]})
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in (10, 20, 30, 60, 70, 90):
            results.append({"type": "fd", "label": player, "reason": f"FD ≥+{FD_MIN} ends {last:02d} · {format_odds(row['price'])}", "event": row["event"], "methods": ["FD Pattern"]})
            methods_map[player].append("FD Pattern")

    # B365
    for _, row in df.iterrows():
        if row["book"] != "bet365":
            continue
        price = abs(int(row["price"]))
        if price == 850 or price % 1000 == 850:
            results.append({"type": "b365", "label": row["player"], "reason": f"B365 850 · {format_odds(row['price'])}", "event": row["event"], "methods": ["B365 850"]})
            methods_map[row["player"]].append("B365 850")

    # Board
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
        meths = list(set(methods_map.get(player, [])))
        core_count = count_core_methods(meths)
        if core_count < METHODS_MIN:
            continue
        is_bet = edge >= EDGE_MIN
        display = [m for m in meths if is_core_method(m)]
        score = girl_magic_score(core_count, edge, display)
        why = f"Score {score}/100 · {core_count} core · edge {int(edge)}"
        ev_board.append({
            "player": player, "best_price": best, "best_book": best_book,
            "median": med, "edge": edge, "is_bet": is_bet, "why": why,
            "methods": display, "score": score, "method_count": core_count,
            "team": team_map.get(player, ""), "events": list(player_events.get(player, [])),
        })
    ev_board = sorted(ev_board, key=lambda x: (not x["is_bet"], -x["score"], -x["edge"]))

    if record_history:
        st.session_state["prev_ev"] = {
            i["player"]: {"methods": i["methods"], "edge": i["edge"], "is_bet": i["is_bet"],
                          "method_count": i["method_count"], "score": i["score"], "events": i.get("events", [])}
            for i in ev_board
        }
        save_history(prev_ev=st.session_state["prev_ev"])

    # Name magic (tight)
    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])

    def different_teams(a, b):
        ta, tb = team_map.get(a, ""), team_map.get(b, "")
        if ta and tb:
            return ta != tb
        return len(pev[a] & pev[b]) == 0

    pool = [p for p, ms in methods_map.items() if count_core_methods(ms) >= NAME_METHODS_MIN and has_personal_strong(ms)]
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
                    results.append({"type": "same_init", "label": f"{a} + {b}", "reason": f"Same initials {k}", "event": "", "methods": ["Same Init"]})
                    n += 1

    return results, ev_board, []

def fetch_rotowire_lineups():
    if not HAS_BS4:
        return set(), "Install beautifulsoup4"
    try:
        r = requests.get(ROTOWIRE_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        if r.status_code != 200:
            return set(), f"HTTP {r.status_code}"
        soup = BeautifulSoup(r.content, "html.parser")
        names = set()
        for el in soup.select("div.lineup__player a, li.lineup__player a"):
            t = el.get_text(strip=True)
            if t and len(t.split()) >= 2:
                names.add(clean_name(t))
        return names, f"RotoWire · {len(names)} names"
    except Exception as e:
        return set(), str(e)

# ── main ─────────────────────────────────────────────────────
def main():
    if "history_loaded" not in st.session_state:
        load_history()
        st.session_state["pregame_lock"] = load_pregame()
        st.session_state["history_loaded"] = True
    if "pending_page" not in st.session_state:
        st.session_state["pending_page"] = 0

    if HAS_AUTOREFRESH:
        refresh_count = st_autorefresh(interval=REFRESH_MINUTES * 60 * 1000, key="ar")
    else:
        refresh_count = 0

    st.markdown("<h1>👑 Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Boss Bitch · HBIC · Me & My Girls</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Where odds intuition meets Petty precision.</p>', unsafe_allow_html=True)

    lock_n = len(st.session_state.get("pregame_lock") or {})
    st.markdown(f'<div class="how-to">🔒 Pregame lock: <b>{lock_n}</b> players · aliases fix Caesars (<code>williamhill_us</code>) · Hard Rock kept when DK/FD/MGM missing from API</div>', unsafe_allow_html=True)

    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add ODDS_API_KEY")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("① Load Games", type="primary"):
            st.session_state["events"] = fetch_events_oddsapi(odds_key)
    with c2:
        if st.button("📋 Lineups"):
            names, msg = fetch_rotowire_lineups()
            st.session_state["lineup_names"] = names
            st.session_state["lineup_msg"] = msg

    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games**")
        st.stop()

    options = {f"{e.get('away_team')} @ {e.get('home_team')}": e["id"] for e in events}
    default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
    chosen = st.multiselect("② Select games", list(options.keys()), default=default_sel)
    st.session_state["selected_games"] = chosen

    manual = st.button("③ Fetch Odds", type="primary")
    if "last_rc" not in st.session_state:
        st.session_state["last_rc"] = refresh_count
    auto = HAS_AUTOREFRESH and refresh_count != st.session_state["last_rc"] and bool(chosen)
    if auto:
        st.session_state["last_rc"] = refresh_count

    if (manual or auto) and chosen:
        with st.spinner("Fetching…"):
            df, found, debug = do_fetch(odds_key, sgo_key, chosen, options)
        st.session_state["fetch_debug"] = debug
        st.session_state["found_books"] = sorted(found)
        if df is not None and not df.empty:
            update_pregame_lock(df)
            st.session_state["previous_odds"] = st.session_state.get("odds", [])
            st.session_state["odds"] = df.to_dict("records")
            st.session_state["last_selected"] = list(chosen)
            st.session_state["new_fetch"] = True
            st.success(f"Loaded **{len(df)}** props · books kept: {', '.join(sorted(found)) or 'none'}")
        else:
            st.session_state["odds"] = []
            st.warning("No preferred-book HR props after filter — see debug below.")

    # DEBUG STRIP — always show after a fetch attempt
    dbg = st.session_state.get("fetch_debug")
    if dbg:
        raw = ", ".join(dbg.get("raw_books") or []) or "(none)"
        kept = ", ".join(dbg.get("kept_books") or []) or "(none)"
        core = ", ".join(dbg.get("core_present") or []) or "NONE — API did not return DK/FD/MGM/365"
        st.markdown(
            f'<div class="debug-box">'
            f'<b>Fetch debug</b><br>'
            f"OddsAPI rows: {dbg.get('oddsapi_rows', 0)} · SGO rows: {dbg.get('sgo_rows', 0)} · "
            f"Merged: {dbg.get('merged_rows', 0)}<br>"
            f"<b>API books seen (raw):</b> {raw}<br>"
            f"<b>Kept after preferred+alias:</b> {kept}<br>"
            f"<b>Core (DK/FD/MGM/365):</b> {core}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if dbg.get("errors"):
            st.caption("Notes: " + " · ".join(dbg["errors"][:5]))
        if dbg.get("raw_books") and not dbg.get("kept_books"):
            st.markdown(
                '<div class="warning-box">⚠️ API returned books, but <b>none matched preferred</b> '
                "after alias. Raw list is above — we need those keys in PREFERRED/BOOK_ALIASES.</div>",
                unsafe_allow_html=True,
            )
        if dbg.get("raw_books") and "draftkings" not in dbg.get("kept_books", []) and "fanduel" not in dbg.get("kept_books", []):
            st.info(
                "The Odds API often omits DK/FD/MGM for some events even when the websites show them. "
                "Hard Rock + Caesars (`williamhill_us`) are kept so the board is not blank. "
                "SGO is still used for core books when available."
            )

    odds = st.session_state.get("odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, _ = run_flags(df, record_history=new_fetch, selected_events=selected_events) if not df.empty else ([], [], [])

    if ev_board:
        log_bet_this(ev_board)

    if not df.empty:
        st.markdown(
            f'<div class="info-box"><b>Props in board:</b> {len(df)} · '
            f'<b>Books:</b> {", ".join(sorted(df["book"].unique()))}</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.get("fetch_debug"):
        st.markdown(
            '<div class="warning-box">No HR props in the board. '
            "This is <b>not</b> because games are live — check debug (API books vs preferred filter).</div>",
            unsafe_allow_html=True,
        )

    bets = len([e for e in ev_board if e["is_bet"]])
    st.markdown(
        f'<div class="petty-row">'
        f'<div class="petty-box"><div class="petty-num">{bets}</div><div class="petty-label">TAKE IT</div></div>'
        f'<div class="petty-box"><div class="petty-num">{len(ev_board)}</div><div class="petty-label">BOARD</div></div>'
        f'<div class="petty-box"><div class="petty-num">{len(df) if not df.empty else 0}</div><div class="petty-label">PROPS</div></div>'
        f'<div class="petty-box"><div class="petty-num">{lock_n}</div><div class="petty-label">LOCKED</div></div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    tabs = st.tabs([
        "👑 Board", "🎯 DK 10s", "🎰 MGM", "🤝 Exact", "⭐ MGM Exact",
        "🔢 Digits", "💙 FD", "💚 B365", "🔒 Lock", "📊 Results", "📖 Glossary",
    ])

    with tabs[0]:
        st.markdown('<div class="queen-banner">👑 The Board</div>', unsafe_allow_html=True)
        if not ev_board:
            st.info("Need 2+ books on a player + 2 core methods for board rows. Props can still show in other tabs once loaded.")
        else:
            cols = st.columns(2)
            for i, item in enumerate(ev_board):
                with cols[i % 2]:
                    cls = "bet" if item["is_bet"] else "skip"
                    lab = "🟢 TAKE IT" if item["is_bet"] else "⚪ PASS"
                    st.markdown(
                        f'<div class="card {cls}"><b>{lab}</b> — <b>{item["player"]}</b>'
                        f'<span class="score-pill">{item["score"]}</span><br>'
                        f'Best {format_odds(item["best_price"])} {book_label(item["best_book"])} · '
                        f'med {format_odds(item["median"])} · edge {int(item["edge"])}<br>'
                        f'{render_method_tags(item["methods"])}<br><small>{item["why"]}</small></div>',
                        unsafe_allow_html=True,
                    )

    def show(tab, typ, title):
        with tab:
            st.markdown(f'<div class="queen-banner">{title}</div>', unsafe_allow_html=True)
            items = [r for r in results if r["type"] == typ]
            if not items:
                st.info("None")
                return
            cols = st.columns(2)
            for i, r in enumerate(items):
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}<br>{render_method_tags(r.get("methods", []))}</div>',
                        unsafe_allow_html=True,
                    )

    show(tabs[1], "dk", "🎯 DK 10s")
    show(tabs[2], "mgm", "🎰 MGM")
    show(tabs[3], "match", "🤝 Exact")
    show(tabs[4], "mgm_exact", "⭐ MGM Exact")
    show(tabs[5], "digit", "🔢 Digits")
    show(tabs[6], "fd", "💙 FanDuel")
    show(tabs[7], "b365", "💚 Bet365")

    with tabs[8]:
        st.markdown('<div class="queen-banner">🔒 Pregame Lock</div>', unsafe_allow_html=True)
        lock = st.session_state.get("pregame_lock") or load_pregame()
        if not lock:
            st.info("Fetch while pregame to build lock")
        else:
            q = st.text_input("Filter", key="lq")
            cols = st.columns(2)
            n = 0
            for player, entry in sorted(lock.items()):
                if q and q.lower() not in player.lower():
                    continue
                lines = [f"{book_label(b)} {format_odds(info.get('price'))}" for b, info in sorted((entry.get("books") or {}).items()) if info.get("price") is not None]
                if not lines:
                    continue
                with cols[n % 2]:
                    st.markdown(f'<div class="card"><b>{player}</b><br>{" · ".join(lines)}</div>', unsafe_allow_html=True)
                n += 1

    with tabs[9]:
        st.markdown('<div class="queen-banner">📊 Results</div>', unsafe_allow_html=True)
        st.caption("Wrong HIT → ↩️ Undo under Recent graded")
        lc1, lc2, lc3, lc4 = st.columns([2, 1, 1, 1])
        with lc1:
            hr_p = st.text_input("Player", key="hrp")
        with lc2:
            hr_pr = st.text_input("Price", key="hrpr")
        with lc3:
            hr_b = st.selectbox("Book", ["betmgm", "draftkings", "fanduel", "hardrockbet", "caesars", "bet365", "untagged"], key="hrb")
        with lc4:
            st.write("")
            if st.button("Log HIT"):
                ok, msg = log_manual_hr(hr_p, hr_pr, hr_b)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

        rows = load_results()
        today_only = st.checkbox("Today only", True)
        view = [r for r in rows if r.get("date") == today_az()] if today_only else rows
        pending = sorted([r for r in view if r.get("result") == "PENDING"], key=pending_sort_key)
        done = [r for r in view if r.get("result") in ("HIT", "MISS")]
        st.write(f"Pending **{len(pending)}** · Hits **{sum(1 for r in done if r['result']=='HIT')}** · Misses **{sum(1 for r in done if r['result']=='MISS')}**")

        page = st.session_state.get("pending_page", 0)
        max_page = max(0, (len(pending) - 1) // PENDING_PAGE) if pending else 0
        page = min(page, max_page)
        start, end = page * PENDING_PAGE, min(page * PENDING_PAGE + PENDING_PAGE, len(pending))
        n1, n2, _ = st.columns([1, 1, 4])
        with n1:
            if st.button("← Prev", disabled=page <= 0):
                st.session_state["pending_page"] = page - 1
                st.rerun()
        with n2:
            if st.button("Next →", disabled=page >= max_page):
                st.session_state["pending_page"] = page + 1
                st.rerun()
        st.caption(f"Showing {start+1 if pending else 0}–{end} of {len(pending)} (oldest first)")

        for r in pending[start:end]:
            rid = r["id"]
            st.markdown(f"**{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}")
            a, b, _ = st.columns([1, 1, 4])
            with a:
                if st.button("🟢 HIT", key=f"h{rid}"):
                    set_result_status(rid, "HIT")
                    st.rerun()
            with b:
                if st.button("🔴 MISS", key=f"m{rid}"):
                    set_result_status(rid, "MISS")
                    st.rerun()

        st.markdown("#### Recent graded")
        for r in reversed(done[-30:]):
            rid = r["id"]
            icon = "🟢" if r["result"] == "HIT" else "🔴"
            st.markdown(f"{icon} **{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}")
            if st.button("↩️ Undo", key=f"u{rid}"):
                undo_result(rid, r.get("source"))
                st.rerun()

    with tabs[10]:
        st.markdown('<div class="queen-banner">📖 Glossary</div>', unsafe_allow_html=True)
        st.markdown("""
**Fetch fix:** Caesars in the API is `williamhill_us` → we map to `caesars`.  
Hard Rock is kept when DK/FD/MGM are missing from The Odds API.  

**TAKE IT** = 2+ core methods + edge ≥ 60.  
**DK 10 / MGM pairs / Exact / FD patterns / B365** = core methods.  
**Lock** = last pregame prices, never wiped when live feed drops books.  
**Debug box** = raw API books vs what we keep — use it when the board is empty.
        """)

    st.markdown('<div class="footer">👑 Girl Magic · Me & My Girls</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
