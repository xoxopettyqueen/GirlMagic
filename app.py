"""
Girl Magic Odds ✨
- GitHub-backed results + lock + movement history (survives Streamlit sleep/wipe)
- No Digits tab (folded into MGM)
- MGM: pairs + groups of 3 + Exact 2-3 only
- One card per player on every method tab
- +EV language (no Kelly) · Tracker Multi-book · What's Going Today
- Auto-grade (stronger name match) · MLB HRs on banner · lock · undo · strict board
"""

import streamlit as st
import pandas as pd
import requests
import json
import os
import base64
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
.stApp{background:#0b0612;color:#fce7f3;font-family:'Inter',sans-serif}
/* medium width - not full bleed, not phone-narrow on desktop */
.main .block-container,
[data-testid="stMainBlockContainer"],
.block-container{
  max-width:1240px!important;
  width:100%!important;
  padding-left:1.25rem!important;
  padding-right:1.25rem!important;
  margin-left:auto!important;
  margin-right:auto!important;
}
@media (max-width:640px){
  .main .block-container,[data-testid="stMainBlockContainer"]{padding:0.65rem 0.75rem!important}
  h1{font-size:1.65rem!important}
}
div[role="radiogroup"]{flex-wrap:wrap!important;gap:4px!important;margin:6px 0 12px!important}
div[role="radiogroup"] label{
  background:#16101f!important;border:1px solid #2a2038!important;border-radius:999px!important;
  padding:6px 12px!important;font-size:0.72rem!important;color:#c4b5d6!important;
}
div[role="radiogroup"] label:has(input:checked),
div[role="radiogroup"] [data-checked="true"]{
  background:#2a1040!important;border-color:#ec4899!important;color:#fff!important;
}

h1{font-family:'Playfair Display',serif!important;font-weight:900!important;color:#f8f4ff!important;-webkit-text-fill-color:#f8f4ff!important;background:none!important;font-size:2.35rem!important;margin:2px 0 4px!important}
.kicker{color:#f9a8d4;font-size:.68rem;font-weight:700;letter-spacing:2.2px;text-transform:uppercase;margin:0}
.subtitle{color:#f9a8d4;font-size:.9rem;font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.tagline{color:#c4b5d6;font-size:.88rem;font-style:italic;margin:0 0 12px;opacity:.95}
.how-to{background:#16101f;border:1px solid #2a2038;border-radius:999px;padding:8px 16px;margin-bottom:14px;font-size:.78rem;line-height:1.4;color:#d8c8ea}
.how-to b{color:#f9a8d4}
.info-box{background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:12px 14px;margin-bottom:10px;font-size:.82rem;color:#d8c8ea}
.warning-box{background:#16101f;border:1px solid #4c1d95;border-radius:16px;padding:10px 14px;margin-bottom:10px;font-size:.82rem;color:#e9d5ff}
.stButton>button{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important}
.petty-row{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 16px}
.petty-box{flex:1;min-width:88px;background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:14px 8px;text-align:center}
.petty-num{font-size:1.7rem;font-weight:800;color:#f472b6;line-height:1}
.petty-label{font-size:.62rem;color:#c4b5d6;margin-top:6px;letter-spacing:.8px;text-transform:uppercase}
.rate-chip{display:inline-block;background:#1a0f28;border:1px solid #a855f7;border-radius:12px;padding:8px 12px;margin:4px;text-align:center;min-width:72px;vertical-align:top}
.rate-chip.beat{border:2px solid #34d399;background:linear-gradient(155deg,#0c2418,#1a0f28);box-shadow:0 0 0 1px rgba(52,211,153,.25)}
.rate-chip.beat .rate-pct{color:#6ee7b7}
.rate-beat{font-size:.55rem;color:#34d399;font-weight:700;margin-top:2px}
.rate-pct{font-size:1.1rem;font-weight:800;color:#f9a8d4}
.rate-name{font-size:.65rem;color:#e9d5ff}
.rate-n{font-size:.6rem;color:#c084fc}
.card{background:#16101f;border:1px solid #2a2038;border-radius:18px;padding:12px 14px;color:#fdf2f8;position:relative;font-size:.88rem;margin-bottom:10px}
.card::before{display:none}
.bet{background:#0d1c18!important;border-color:#1d4a3a!important}
.skip{background:#16101f!important;border-color:#2a2038!important;opacity:1}
.watch-card{background:#141018!important;border-color:#2a2038!important}
.score-pill{display:inline-block;background:#ec4899;color:#fff;font-weight:800;font-size:.72rem;padding:3px 9px;border-radius:999px;float:right}
.card-kicker{font-size:.62rem;letter-spacing:1.2px;text-transform:uppercase;color:#f9a8d4;font-weight:700;margin-bottom:4px}
.card-name{font-size:1.05rem;font-weight:800;color:#fff;margin:0}
.card-meta{font-size:.72rem;color:#9ca3af;margin:2px 0 6px}
.card-line{font-size:.86rem;color:#e5e7eb;margin:1px 0}
.card-foot{font-size:.68rem;color:#9ca3af;margin-top:8px}
.tag{display:inline-block;background:#1b1226;color:#e9d5ff;font-size:.62rem;font-weight:700;padding:3px 8px;border-radius:999px;margin:2px 3px 2px 0;border:1px solid #3b0764}
.tag-dk{background:#064e3b;color:#6ee7b7;border-color:#34d399}
.tag-mgm{background:#422006;color:#fcd34d;border-color:#f59e0b}
.tag-fd{background:#1e3a5f;color:#93c5fd;border-color:#3b82f6}
.tag-match{background:#4c1d95;color:#e9d5ff;border-color:#a855f7}
.tag-strong{background:#14532d;color:#bbf7d0;border-color:#22c55e;font-weight:800}
.queen-banner{display:inline-block;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-size:.75rem;font-weight:700;padding:5px 14px;border-radius:16px;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px}
.meter{display:flex;gap:3px;margin:4px 0 6px}
.meter-bar{height:6px;width:16px;border-radius:3px;background:#374151}
.meter-bar.filled-high{background:linear-gradient(90deg,#f472b6,#c026d3)}
.meter-bar.filled-strong{background:linear-gradient(90deg,#e879f9,#a855f7)}
.meter-bar.filled-medium{background:linear-gradient(90deg,#c084fc,#7c3aed)}
.meter-bar.filled-low{background:#6b7280}
.stTabs [data-baseweb="tab"]{background:#1a0f28;border-radius:8px;color:#f9a8d4;font-weight:600;padding:6px 8px;font-size:.75rem}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#db2777,#9333ea)!important;color:#fff!important}
.footer{text-align:center;color:#f9a8d4;font-size:.9rem;margin-top:28px;opacity:.9;padding-bottom:16px}
.glossary-block{background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:14px 16px;margin-bottom:12px;font-size:.88rem;line-height:1.55}
.glossary-block h4{color:#f9a8d4;margin:0 0 8px 0;font-size:1rem}
.glossary-block b{color:#fbcfe8}
.trends-today{background:#16101f;border:1px solid #2a2038;border-radius:18px;padding:14px 16px;margin-bottom:12px}
.trends-today-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.trends-today-title{color:#f9a8d4;font-weight:800;font-size:.95rem}
.trends-today-sub{color:#e9d5ff;font-size:.72rem;opacity:.9}
.trends-chips{display:flex;flex-wrap:wrap;gap:8px}
.trend-chip{display:inline-flex;align-items:center;gap:6px;background:rgba(0,0,0,.35);border:1px solid #a855f7;border-radius:999px;padding:6px 12px;font-size:.78rem;font-weight:700;color:#fce7f3}
.trend-chip.hot{border-color:#f472b6;background:rgba(219,39,119,.25)}
.trend-chip .chip-count{color:#f9a8d4;font-weight:900}
/* keep game picker from eating the whole page */
div[data-baseweb="select"]{max-width:100%}
div[data-baseweb="select"] span{font-size:0.78rem!important}
.stMultiSelect{max-width:920px}
.stMultiSelect [data-baseweb="tag"]{max-width:160px}
.games-hint{color:#e9d5ff;font-size:.8rem;margin:4px 0 8px}
.shop-wrap{overflow-x:auto;margin:8px 0 16px}
.shop-table{width:100%;border-collapse:separate;border-spacing:0 6px;font-size:.78rem}
.shop-table th{color:#c4b5d6;font-weight:700;text-align:center;padding:4px 6px;font-size:.62rem;letter-spacing:.6px;text-transform:uppercase}
.shop-table td{background:#16101f;padding:8px 8px;text-align:center;border-top:1px solid #2a2038;border-bottom:1px solid #2a2038}
.shop-table td:first-child{text-align:left;border-radius:12px 0 0 12px;border-left:1px solid #2a2038}
.shop-table td:last-child{border-radius:0 12px 12px 0;border-right:1px solid #2a2038}
.shop-name{font-weight:800;color:#fff;font-size:.86rem}
.shop-game{color:#9ca3af;font-size:.65rem}
.shop-best{color:#6ee7b7;font-weight:800}
.shop-short{color:#f87171;font-weight:700}
.shop-take{color:#34d399;font-weight:800}
.shop-dont{color:#fb7185;font-weight:800}
.shop-lean{color:#fbbf24;font-weight:800}
.shop-mkt{color:#c4b5d6;font-weight:700}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
MLB_STATS = "https://statsapi.mlb.com/api/v1"
REGIONS = "us,us2"
HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"
PREFERRED = {"fanduel", "draftkings", "betmgm", "hardrockbet", "caesars"}
CORE_BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM"}
VALUE_BOOKS = {"draftkings", "fanduel", "hardrockbet"}
VALUE_BOOK_LABELS = {"DK", "FD", "HardRock"}
# Odds API uses different keys for the same books — map only
BOOK_ALIASES = {
    "williamhill_us": "caesars",
    "hardrockbet_oh": "hardrockbet",
    "hardrockbet_nj": "hardrockbet",
}

def normalize_book(key):
    k = str(key or "").lower().strip()
    if "bet365" in k:
        return "bet365"
    return BOOK_ALIASES.get(k, k)
LATE_BOOKS = {"fanduel", "draftkings", "betmgm"}
# ── Board gates (re-eval Tracker 2026-08-25) ─────────────────
# Baseline TAKE IT ~11% (n=256). Promote 25s / Exact / multi-book / FD combos.
# Demote 50s from priority (10% / 9% on TAKE). DK 10 = core only (6% on TAKE alone).
EDGE_MIN = 80
EDGE_SOFT = 40  # heavy stacks that still include a PRIORITY method
METHODS_MIN = 2
NAME_METHODS_MIN = 3
NAME_MAX_PAIRS = 50
OUTLIER_GAP = 150
BOOK_CLUSTER_GAP = 50  # max spread across focus books to count as 'tight'
REFRESH_MINUTES = 20
FD_MIN = 400
MOVE_PRICE_MIN = 500
# 0.5 HR Over sanity — reject absurd API longshots (not real pregame 1HR prices)
MAX_HR_AMERICAN = 2500
# Never show / lock / tag these players (name match, Jr. stripped)
PLAYER_BLOCKLIST = {
    "chandler simpson",
}
MOVE_MIN = 40
BIG_MOVE = 100
PENDING_PAGE = 40
EV_MIN_N = 12
BOARD_MAX_PER_TEAM = 3
BOARD_MAX_PER_GAME = 4

# PRIORITY = must have ≥1 to unlock TAKE IT (Tracker 9/03 volume)
PRIORITY_METHODS = {
    "Match 25", "MGM 25",
    "DK 10",
    "FD 600",
    "Multi-book method",
    "FD+MGM classic",
    "MGM Exact",
}
# PREMIUM = counts as core (still need ≥1 PRIORITY + edge for TAKE IT)
TAKE_IT_STRONG = {
    "Match 25", "MGM 25",
    "DK 10",
    "FD 600", "FD Pattern",
    "Multi-book method",
    "FD+MGM classic",
    "MGM Exact",
    "Multi-book Shorten",
    "Match 50", "MGM 50",
}
# SUPPORT = tagged / WATCH / Tracker only — never core, never unlocks alone
SUPPORT_ONLY = {
    "Books tight", "Exact Match", "All books same",
    "DK FD-style", "Same on 3+ books",
    "Match 75", "MGM 75",
    "Match 00", "MGM 00",
    "Stayed in the group",
    "Last one left",
}
TRACKER_MIN_N = 25  # hide thin samples on Tracker (n < 25)
# Name magic can still use a slightly wider set
PERSONAL_STRONG = {
    "DK 10", "FD 600", "FD Pattern", "Multi-book Shorten",
    "Match 50", "MGM 50", "Match 25", "MGM 25",
    "Match 75", "MGM 75", "MGM Exact", "Stayed in the group",
    "DK FD-style", "Exact Match", "Books tight",
    "Multi-book method", "Same on 3+ books", "All books same",
}
NOISE_METHODS = {
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup", "In lineup · missing books",
    "Price moved", "Multi-book Lengthen", "FADE · Shot way up", "FADE · Drop >100", "FADE · FD highest",
    "FD under MGM", "Shortening", "Lengthening", "Stuck price", "Outlier higher",
    "HOT", "HardRock highest", "MLB auto HR", "Was DK 10", "Manual HR log",
}
TRACKER_BLOCKLIST = {
    "HOT", "HardRock highest", "MLB auto HR", "Was DK 10", "Manual HR log",
    "Just Appeared", "Added Late", "Gone Missing", "Not in lineup", "Price moved",
    "FADE · Shot way up", "FADE · Drop >100", "FADE · FD highest", "FD under MGM",
    "Multi-book Lengthen", "Stuck price", "Outlier higher",
}
TRACKER_ALWAYS = {
    "Multi-book method", "Stayed in the group", "Last one left", "MGM Exact", "DK 10",
    "FD Pattern", "FD 600", "Exact Match", "Match 00", "Match 25", "Match 50", "Match 75",
    "MGM 00", "MGM 25", "MGM 50", "MGM 75", "DK FD-style", "Multi-book Shorten",
    "All books same", "Books tight", "FD+MGM classic",
}
FD_ENDINGS = (10, 20, 30, 60, 70, 90)
MGM_ENDINGS = (0, 25, 50, 75)

def is_core_method(m):
    """Premium only — support/noise do not inflate core_count."""
    m = normalize_method_name(m)
    if m in NOISE_METHODS or m in SUPPORT_ONLY:
        return False
    if m.startswith("FADE") or m.startswith("FD under"):
        return False
    if m.startswith("Outlier") or m.startswith("Stuck") or m.startswith("Same ending"):
        return False
    if m.startswith("Shortening") or m.startswith("Lengthening"):
        return False
    if m in TAKE_IT_STRONG:
        return True
    return False

def normalize_method_name(m):
    m = str(m)
    if m.startswith("Stayed in group") or m == "Stayed in the group":
        return "Stayed in the group"
    return m

def count_core_methods(meths):
    return len({normalize_method_name(m) for m in meths if is_core_method(m)})

def has_priority_method(methods):
    """Step 1+3: TAKE IT requires ≥1 priority tag from tracker winners."""
    ms = {normalize_method_name(m) for m in (methods or [])}
    return bool(ms & PRIORITY_METHODS)

def strong_method_families(methods):
    """PREMIUM tags only form families (priority subset drives unlock)."""
    ms = {normalize_method_name(m) for m in (methods or [])}
    families = set()
    for m in ms:
        if m not in TAKE_IT_STRONG:
            continue
        if m in ("Match 25", "MGM 25"):
            families.add("mgm_25")  # 8/25: strongest ending signal
        elif m in ("Match 50", "MGM 50"):
            families.add("mgm_50")
        elif m == "MGM Exact":
            families.add("mgm_exact")
        elif m == "DK 10":
            families.add("dk_10")
        elif m in ("FD 600", "FD Pattern"):
            families.add("fd")
        elif m == "FD+MGM classic":
            families.add("fd_mgm")
        elif m in ("Multi-book method", "Multi-book Shorten"):
            families.add("multi_book")
        else:
            families.add(m)
    return families


def qualifies_take_it(core_count, methods, edge=0):
    """TAKE IT (Tracker re-eval 2026-08-25):
    1 PRIORITY (≥1): Match/MGM 25 · FD Pattern/600 · Multi-book method · FD+MGM classic · MGM Exact
    2 Core (≥2 premium): priority set + DK 10 + Multi-book Shorten + Match/MGM 50
    3 Demoted from priority: 50s · DK 10 alone · Multi-book Shorten alone
    4 Support only: 75s · 00s · Stayed · Last one left · Exact/tight
    5 Edge ≥ 80 (or ≥40 with 3+ core + priority + 2 families)
    """
    ms = {normalize_method_name(m) for m in (methods or [])}
    if not (ms & PRIORITY_METHODS):
        return False
    fams = strong_method_families(methods)
    n = len(fams)
    # Primary: 2+ core · 1+ priority · edge ≥ 80
    if core_count >= METHODS_MIN and edge >= EDGE_MIN:
        return True
    # Heavy stack soft edge — still requires priority
    if core_count >= 3 and n >= 2 and edge >= EDGE_SOFT:
        return True
    return False

def has_dk_or_mgm(meths):
    for m in meths:
        if m in ("DK 10", "DK FD-style"): return True
        if m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m: return True
        if m.startswith("Match "): return True
    return False

def is_dk_family(m):
    m = str(m)
    return m in ("DK 10", "DK FD-style") or m.startswith("DK ")

def is_mgm_family(m):
    m = str(m)
    if m.startswith("MGM"): return True
    if m in ("Last one left", "Stayed in the group") or "Stayed in group" in m: return True
    if m.startswith("Match "): return True
    return False

def is_fd_family(m):
    m = str(m)
    return m.startswith("FD") or m in ("FD Pattern", "FD 600")

def has_dk_mgm_fd(meths):
    """Trifecta: DK + MGM + FD tags. Score bonus only — does NOT gate TAKE IT."""
    ms = list(meths or [])
    return (
        any(is_dk_family(m) for m in ms)
        and any(is_mgm_family(m) for m in ms)
        and any(is_fd_family(m) for m in ms)
    )

def method_tag_class(m):
    m = str(m)
    if m.startswith("DK"): return "tag-dk"
    if m.startswith("MGM") or m in ("Last one left", "Stayed in the group") or "Stayed in group" in m: return "tag-mgm"
    if m.startswith("FD"): return "tag-fd"
    if m in ("Exact Match", "MGM Exact", "All books same", "Books tight") or m.startswith("Match "): return "tag-match"
    if "Multi-book" in m or m == "Same on 3+ books": return "tag-strong"
    return ""

def render_method_tags(methods, limit=8):
    seen = []
    for m in methods:
        nm = normalize_method_name(m)
        if nm not in seen: seen.append(nm)
    return "".join(f'<span class="tag {method_tag_class(m)}">{m}</span>' for m in seen[:limit])

def girl_magic_score(core_count, edge, methods):
    method_pts = min(core_count, 5) * 10
    edge_pts = min(40, max(0, int((edge / 180) * 40)))
    bonus = 0
    ms = {normalize_method_name(m) for m in methods}
    if "Stayed in the group" in ms: bonus += 3
    if "Multi-book method" in ms or "Multi-book Shorten" in ms: bonus += 4
    if "Same on 3+ books" in ms: bonus += 2
    if "FD 600" in ms: bonus += 2
    # trifecta: DK + MGM + FD all present -> score boost only (does NOT change TAKE IT)
    if has_dk_mgm_fd(methods):
        bonus += 12
    return min(100, method_pts + edge_pts + min(18, bonus))


def american_implied(p):
    try:
        p = int(p)
    except Exception:
        return None
    if p > 0:
        return 100.0 / (p + 100.0)
    return abs(p) / (abs(p) + 100.0)

def implied_to_american(prob):
    try:
        prob = float(prob)
    except Exception:
        return None
    if prob <= 0.02 or prob >= 0.98:
        return None
    if prob >= 0.5:
        return int(round(-prob / (1.0 - prob) * 100))
    return int(round((1.0 - prob) / prob * 100))

def no_vig_fair_american(prices):
    imps = [american_implied(p) for p in prices]
    imps = [x for x in imps if x]
    if len(imps) < 2:
        return (int(prices[0]) if prices else None), (imps[0] if imps else None)
    avg = sum(imps) / len(imps)
    return implied_to_american(avg), avg

def shop_price_action(best, fair):
    if best is None or fair is None:
        return "WATCH", "no fair", "shop-mkt"
    gap = int(best) - int(fair)
    if gap >= EDGE_MIN:
        return "TAKE", f"take at {format_odds(best)} · fair {format_odds(fair)} · +{gap}", "shop-take"
    if gap >= 40:
        return "LEAN", f"lean {format_odds(best)} · fair {format_odds(fair)} · +{gap}", "shop-lean"
    if gap <= -40:
        return "DON'T", f"don't take {format_odds(best)} · fair {format_odds(fair)} · {gap}", "shop-dont"
    return "MARKET", f"market {format_odds(best)} · fair {format_odds(fair)} · {gap:+d}", "shop-mkt"

SHOP_BOOKS = [
    ("draftkings", "DK"),
    ("fanduel", "FD"),
    ("betmgm", "MGM"),
    ("hardrockbet", "HR"),
    ("caesars", "CZ"),
]

def build_shop_board(df):
    if df is None or getattr(df, "empty", True):
        return []
    rows = []
    for (player, event), g in df.groupby(["player", "event"], dropna=False):
        if is_blocked_player(player):
            continue
        book_px = {}
        for _, r in g.iterrows():
            try:
                bk = normalize_book(r.get("book"))
                book_px[bk] = int(r["price"])
            except Exception:
                continue
        prices = list(book_px.values())
        if not prices:
            continue
        books = list(book_px.keys())
        best, best_book = smart_best(prices, books) if len(prices) >= 2 else (prices[0], books[0])
        try:
            med = int(statistics.median(prices)) if len(prices) >= 2 else int(best)
        except Exception:
            med = int(best) if best is not None else None
        fair_nv, fair_p = no_vig_fair_american(prices)
        fair = fair_nv if fair_nv is not None else med
        action, why, cls = shop_price_action(best, fair)
        edge = (int(best) - int(fair)) if best is not None and fair is not None else 0
        rows.append({
            "player": player, "event": event or "", "books": book_px,
            "best": best, "best_book": best_book, "median": med, "fair": fair,
            "fair_prob": fair_p, "edge": edge, "action": action, "why": why,
            "cls": cls, "n_books": len(book_px),
            "ending": last_two(best) if best is not None else None,
            "bucket": price_bucket(best),
        })
    rows.sort(key=lambda x: (-x.get("edge", 0), x.get("player") or ""))
    return rows

def ending_heat_from_results(rows, min_n=20):
    stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    for r in rows or []:
        if r.get("result") not in ("HIT", "MISS"):
            continue
        end = r.get("ending")
        if end is None and r.get("best_price") is not None:
            end = last_two(r.get("best_price"))
        if end is None:
            continue
        key = f"{int(end):02d}"
        if r["result"] == "HIT":
            stats[key]["hit"] += 1
        else:
            stats[key]["miss"] += 1
    out = []
    for name, stt in stats.items():
        t = stt["hit"] + stt["miss"]
        if t < min_n:
            continue
        out.append({"ending": name, "pct": 100.0 * stt["hit"] / t, "hit": stt["hit"], "miss": stt["miss"], "n": t})
    out.sort(key=lambda x: (-x["pct"], -x["n"]))
    return out

def render_shop_tab(df):
    st.markdown("### Odds Shop")
    st.caption("Fair = mean implied of posted Overs. TAKE ≥80 long vs fair. DON'T = 40+ short. Not a who-goes-yard call.")
    if df is None or getattr(df, "empty", True):
        st.info("Fetch 0.5 HR first — Shop fills from the live slate.")
        return
    shop = build_shop_board(df)
    take_s = sum(1 for r in shop if r["action"] == "TAKE")
    lean_s = sum(1 for r in shop if r["action"] == "LEAN")
    dont_s = sum(1 for r in shop if r["action"] == "DON'T")
    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box"><div class="petty-num">{take_s}</div><div class="petty-label">TAKE PRICE</div></div>
        <div class="petty-box"><div class="petty-num">{lean_s}</div><div class="petty-label">LEAN</div></div>
        <div class="petty-box"><div class="petty-num">{dont_s}</div><div class="petty-label">DON'T</div></div>
        <div class="petty-box"><div class="petty-num">{len(shop)}</div><div class="petty-label">PLAYERS</div></div>
    </div>
    """, unsafe_allow_html=True)
    view = st.radio("Call", ["All", "TAKE + LEAN", "TAKE", "LEAN", "DON'T", "MARKET"], horizontal=True, key="shop_filter")
    c1, c2, c3, c4 = st.columns(4)
    book_opts = ["Any"] + [lab for _, lab in SHOP_BOOKS]
    with c1:
        book_f = st.selectbox("Best book", book_opts, key="shop_best_book")
    with c2:
        has_f = st.selectbox("Has book", book_opts, key="shop_has_book")
    ends = sorted({f"{int(r['ending']):02d}" for r in shop if r.get("ending") is not None})
    with c3:
        end_f = st.multiselect("Best ends in", ends, key="shop_ends")
    with c4:
        min_gap = st.slider("Min gap vs fair", 0, 300, 0, 10, key="shop_min_gap")
    c5, c6, c7 = st.columns(3)
    with c5:
        min_books = st.selectbox("Min books posted", [1, 2, 3, 4, 5], index=0, key="shop_min_books")
    buckets = sorted({r.get("bucket") for r in shop if r.get("bucket")})
    with c6:
        buck_f = st.multiselect("Price bucket", buckets, key="shop_buckets")
    with c7:
        q = st.text_input("Player search", key="shop_q")

    shown = shop
    if view == "TAKE + LEAN":
        shown = [r for r in shown if r["action"] in ("TAKE", "LEAN")]
    elif view in ("TAKE", "LEAN", "DON'T", "MARKET"):
        shown = [r for r in shown if r["action"] == view]
    if book_f != "Any":
        want = {lab: key for key, lab in SHOP_BOOKS}.get(book_f)
        shown = [r for r in shown if r.get("best_book") == want]
    if has_f != "Any":
        want = {lab: key for key, lab in SHOP_BOOKS}.get(has_f)
        shown = [r for r in shown if want in (r.get("books") or {})]
    if end_f:
        shown = [r for r in shown if r.get("ending") is not None and f"{int(r['ending']):02d}" in end_f]
    if min_gap:
        shown = [r for r in shown if int(r.get("edge") or 0) >= min_gap]
    if min_books:
        shown = [r for r in shown if int(r.get("n_books") or 0) >= min_books]
    if buck_f:
        shown = [r for r in shown if r.get("bucket") in buck_f]
    if q.strip():
        qq = q.strip().lower()
        shown = [r for r in shown if qq in (r.get("player") or "").lower() or qq in (r.get("event") or "").lower()]
    st.caption(f"Showing {len(shown)} of {len(shop)} players")
    heat = ending_heat_from_results(load_results(), min_n=20)
    if heat:
        st.markdown("#### Endings that have been hitting (graded best price)")
        chips = []
        for h in heat[:12]:
            chips.append(
                f'<div class="rate-chip"><div class="rate-pct">{h["pct"]:.0f}%</div>'
                f'<div class="rate-name">ends {h["ending"]}</div>'
                f'<div class="rate-n">{h["hit"]}H · {h["miss"]}M · n={h["n"]}</div></div>'
            )
        st.markdown("".join(chips), unsafe_allow_html=True)
    heads = "".join(f"<th>{lab}</th>" for _, lab in SHOP_BOOKS)
    body = []
    for r in shown[:80]:
        cells = []
        for key, _lab in SHOP_BOOKS:
            px = r["books"].get(key)
            if px is None:
                cells.append("<td>—</td>")
                continue
            cls = "shop-best" if key == r.get("best_book") else ""
            if r.get("fair") is not None and key != r.get("best_book") and int(px) <= int(r["fair"]) - 40:
                cls = "shop-short"
            cells.append(f'<td class="{cls}">{format_odds(px)}</td>')
        fair_s = format_odds(r["fair"]) if r.get("fair") is not None else "—"
        body.append(
            "<tr>"
            f'<td><div class="shop-name">{r["player"]}</div><div class="shop-game">{r.get("event") or ""}</div></td>'
            + "".join(cells)
            + f"<td>{fair_s}</td>"
            f'<td class="shop-best">{format_odds(r["best"])} {book_label(r.get("best_book"))}</td>'
            f'<td>{int(r.get("edge") or 0):+d}</td>'
            f'<td class="{r["cls"]}">{r["action"]}</td></tr>'
        )
    st.markdown(
        '<div class="shop-wrap"><table class="shop-table"><thead><tr>'
        "<th>Player</th>" + heads + "<th>Fair</th><th>Best</th><th>Gap</th><th>Call</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.caption("Green = longest book. Red = short vs fair. TAKE ≥80 over fair. DON'T = 40+ short.")

def get_odds_api_key():
    key = st.secrets.get("ODDS_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("The Odds API Key", type="password", key="odds_key")
    return key

def get_sgo_key():
    return st.secrets.get("SGO_API_KEY", "d5422e23cc05702bf95197f6a98ec8ce")

def format_odds(p):
    try: return f"{int(p):+d}"
    except Exception: return str(p)

def price_bucket(p):
    try:
        p = abs(int(p))
    except Exception:
        return None
    if p < 400:
        return "under +400"
    if p < 500:
        return "+400s"
    if p < 600:
        return "+500s"
    if p < 700:
        return "+600s"
    if p < 800:
        return "+700s"
    if p < 1000:
        return "+800-999"
    return "+1000+"

def last_two(p):
    try: return abs(int(p)) % 100
    except Exception: return None

def book_label(b):
    b = str(b or "").lower()
    if "betmgm" in b or b == "mgm": return "MGM"
    if "draftkings" in b or b == "dk": return "DK"
    if "fanduel" in b or b == "fd": return "FD"
    if "hardrock" in b: return "HardRock"
    if "caesars" in b or "williamhill" in b: return "Caesars"
    if b in ("untagged", "unknown", "-", ""): return "Untagged"
    return b.title() if b else "Untagged"

def clean_name(name):
    name = str(name).strip()
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
    parts = name.split()
    if parts and parts[-1].lower().rstrip(".") in suffixes:
        parts = parts[:-1]
    return " ".join(parts)

def is_blocked_player(name):
    n = clean_name(name).lower().strip()
    if n in PLAYER_BLOCKLIST:
        return True
    for blocked in PLAYER_BLOCKLIST:
        bp = blocked.split()
        np = n.split()
        if len(bp) >= 2 and len(np) >= 2 and np[0] == bp[0] and np[-1] == bp[-1]:
            return True
    return False

def get_initials(name):
    name = clean_name(name)
    parts = name.split()
    if len(parts) < 2:
        return None, None, None, None
    first, last = parts[0], parts[-1]
    return first[0].upper(), last[0].upper(), first.lower(), last.lower()

def names_match(a, b):
    a, b = clean_name(a).lower(), clean_name(b).lower()
    if a == b:
        return True
    a2 = a.replace(".", "").replace("  ", " ").strip()
    b2 = b.replace(".", "").replace("  ", " ").strip()
    if a2 == b2:
        return True
    pa, pb = a2.split(), b2.split()
    if len(pa) >= 2 and len(pb) >= 2:
        if pa[-1] == pb[-1] and pa[0][0] == pb[0][0]:
            return True
        if pa[-1] == pb[-1] and (pa[0].startswith(pb[0]) or pb[0].startswith(pa[0])):
            return True
    return False

def clean_team(tid):
    if not tid: return ""
    return str(tid).replace("_MLB", "").replace("_", " ").strip()

def now_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%I:%M %p")

def today_az():
    return datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")

def today_mlb_date():
    return datetime.now(timezone(timedelta(hours=-4))).strftime("%Y-%m-%d")

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def smart_best(prices, books):
    """Longest price, preferring DK / FD / HardRock for where to bet.
    Median/edge still use all books."""
    if not prices:
        return None, None
    paired = list(zip(prices, books))
    def _is_value(b):
        k = str(b or "").lower()
        try:
            k = normalize_book(k)
        except Exception:
            pass
        return k in VALUE_BOOKS or "hardrock" in k
    value_paired = [(p, b) for p, b in paired if _is_value(b)]
    pool = value_paired if value_paired else paired
    pool = sorted(pool, key=lambda x: x[0], reverse=True)
    best_p, best_b = pool[0]
    if len(pool) >= 2 and best_p - pool[1][0] >= OUTLIER_GAP:
        return pool[1][0], pool[1][1]
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
    return html + "</div>"

def event_matches_chosen(ev, chosen):
    if not chosen: return True
    if ev in chosen: return True
    ev_l = str(ev).lower()
    for c in chosen:
        parts_c = [p.strip() for p in str(c).lower().split("@")]
        if len(parts_c) == 2 and parts_c[0] in ev_l and parts_c[1] in ev_l:
            return True
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

def american_to_decimal(american):
    try: a = int(american)
    except Exception: return None
    if a > 0: return 1 + a / 100.0
    return 1 + 100.0 / abs(a)

def simple_ev_lean(p_win, american):
    if p_win is None or p_win <= 0: return False, None
    dec = american_to_decimal(american)
    if not dec: return False, None
    ev = p_win * (dec - 1) - (1 - p_win)
    return ev > 0, ev

def load_pregame():
    """Local first; if empty, pull GitHub so Cloud restarts keep lock."""
    local = _load_local_json(PREGAME_FILE, {})
    if not isinstance(local, dict):
        local = {}
    if local:
        st.session_state["_pregame_source"] = "local"
        return local
    gh = _load_pregame_github()
    if isinstance(gh, dict) and gh:
        st.session_state["_pregame_source"] = "github"
        _save_local_json(PREGAME_FILE, gh)
        return gh
    st.session_state["_pregame_source"] = "empty"
    return {}


def save_pregame(data):
    _save_local_json(PREGAME_FILE, data)
    if _gh_configured():
        _save_pregame_github(data)

def _book_slot_normalize(info):
    """Migrate old {price, ending, seen_at} → first/latest/close shape."""
    if not isinstance(info, dict):
        return {}
    out = dict(info)
    p = out.get("latest_price")
    if p is None:
        p = out.get("price")
    if p is not None:
        try:
            p = int(p)
        except Exception:
            p = None
    first = out.get("first_price")
    if first is None:
        first = p
    if first is not None:
        try:
            first = int(first)
        except Exception:
            first = p
    latest = out.get("latest_price")
    if latest is None:
        latest = p if p is not None else first
    if latest is not None:
        try:
            latest = int(latest)
        except Exception:
            latest = first
    close = out.get("close_price")
    if close is not None:
        try:
            close = int(close)
        except Exception:
            close = None
    out["first_price"] = first
    out["latest_price"] = latest
    out["close_price"] = close
    # canonical "price" = best research number: close > latest > first
    use = close if close is not None else (latest if latest is not None else first)
    out["price"] = use
    out["ending"] = last_two(use) if use is not None else out.get("ending")
    out.setdefault("first_at", out.get("seen_at") or out.get("first_at"))
    out.setdefault("latest_at", out.get("seen_at") or out.get("latest_at"))
    return out


def update_pregame_lock(df):
    """Timing lock: first (open) never changes; latest updates each pregame fetch;
    close freezes when a book disappears from the feed (post-live / pulled).
    """
    if df is None or df.empty:
        return load_pregame()
    lock = load_pregame()
    today, ts = today_az(), now_utc_iso()
    seen_keys = set()  # (player, book) present this fetch

    for _, r in df.iterrows():
        player = clean_name(r["player"])
        if is_blocked_player(player):
            continue
        book = str(r["book"]).lower()
        try:
            book = normalize_book(book)
        except Exception:
            pass
        price = r["price"]
        event = r.get("event") or ""
        if price is None:
            continue
        try:
            ip = int(price)
        except Exception:
            continue
        if ip > MAX_HR_AMERICAN:
            continue

        if player not in lock or lock[player].get("date") != today:
            lock[player] = {
                "date": today, "event": event, "books": {},
                "locked_at": ts, "updated_at": ts,
            }
        entry = lock[player]
        if event:
            entry["event"] = event
        entry["date"] = today
        entry["updated_at"] = ts
        entry.setdefault("books", {})
        seen_keys.add((player, book))

        prev = _book_slot_normalize(entry["books"].get(book) or {})
        if prev.get("first_price") is None:
            # OPEN — first pull of the day
            entry["books"][book] = {
                "first_price": ip,
                "first_at": ts,
                "latest_price": ip,
                "latest_at": ts,
                "close_price": None,
                "close_at": None,
                "price": ip,
                "ending": last_two(ip),
                "seen_at": ts,
                "locked": True,
            }
        else:
            # Keep open; walk latest (even if close already set, still track live path pre-close)
            first = int(prev["first_price"])
            close = prev.get("close_price")
            entry["books"][book] = {
                "first_price": first,
                "first_at": prev.get("first_at") or ts,
                "latest_price": ip,
                "latest_at": ts,
                "close_price": close,
                "close_at": prev.get("close_at"),
                "price": int(close) if close is not None else ip,
                "ending": last_two(int(close) if close is not None else ip),
                "seen_at": ts,
                "locked": True,
            }
        if "betmgm" in book or book == "mgm":
            slot = entry["books"][book]
            if entry.get("mgm_first") is None:
                entry["mgm_first"] = slot["first_price"]
            entry["mgm_price"] = slot.get("close_price") or slot["latest_price"]
            entry["mgm_ending"] = last_two(entry["mgm_price"])

    # CLOSE: books we had today but not in this fetch → freeze latest as close
    for player, entry in list(lock.items()):
        if entry.get("date") != today:
            continue
        books = entry.get("books") or {}
        for book, raw in list(books.items()):
            slot = _book_slot_normalize(raw)
            if (player, book) in seen_keys:
                entry["books"][book] = slot
                continue
            if slot.get("close_price") is not None:
                entry["books"][book] = slot
                continue
            latest = slot.get("latest_price") or slot.get("first_price")
            if latest is None:
                continue
            slot["close_price"] = int(latest)
            slot["close_at"] = ts
            slot["price"] = int(latest)
            slot["ending"] = last_two(int(latest))
            entry["books"][book] = slot
            if "betmgm" in book or book == "mgm":
                entry["mgm_price"] = int(latest)
                entry["mgm_ending"] = last_two(int(latest))

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
        slot = _book_slot_normalize(info)
        use = slot.get("close_price")
        if use is None:
            use = slot.get("latest_price")
        if use is None:
            use = slot.get("first_price")
        if use is not None:
            parts.append(f"{book_label(b)} {format_odds(use)}")
    return " · ".join(parts)


def format_az_from_iso(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=-7))).strftime("%I:%M %p")
    except Exception:
        return ""


def lock_movement_rows(lock=None):
    """Open → latest / open → close moves from the timing lock (500+ filter)."""
    lock = lock if lock is not None else (st.session_state.get("pregame_lock") or load_pregame())
    up, down = defaultdict(list), defaultdict(list)
    today = today_az()
    for player, entry in lock.items():
        if entry.get("date") != today:
            continue
        for book, raw in (entry.get("books") or {}).items():
            slot = _book_slot_normalize(raw)
            first = slot.get("first_price")
            latest = slot.get("latest_price")
            close = slot.get("close_price")
            if first is None:
                continue
            # prefer close vs open if closed; else latest vs open
            end_p = close if close is not None else latest
            if end_p is None or end_p == first:
                continue
            if abs(first) < MOVE_PRICE_MIN and abs(end_p) < MOVE_PRICE_MIN:
                continue
            delta = int(end_p) - int(first)
            if abs(delta) < MOVE_MIN:
                continue
            phase = "close" if close is not None else "latest"
            t0 = format_az_from_iso(slot.get("first_at")) or "?"
            t1 = format_az_from_iso(slot.get("close_at") if close is not None else slot.get("latest_at")) or "?"
            line = (
                f"{book_label(book)} open {format_odds(first)} ({t0}) → "
                f"{phase} {format_odds(end_p)} ({t1}) ({delta:+d})"
            )
            (up if delta > 0 else down)[player].append(line)
    return up, down

def _apply_history_payload(data):
    """Load snaps into session. Skip if older than HISTORY_MAX_AGE_HOURS."""
    if not data or not isinstance(data, dict):
        return False
    saved_at = data.get("saved_at")
    if saved_at:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(saved_at)
            if age > timedelta(hours=HISTORY_MAX_AGE_HOURS):
                return False
        except Exception:
            pass
    try:
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
        ph = []
        for snap in data.get("price_history", []):
            if isinstance(snap, dict):
                ph.append({tuple(k.split("||", 1)): v for k, v in snap.items()})
        st.session_state["price_history"] = ph[-8:]
        mh = []
        for snap in data.get("mgm_history", []):
            mh.append([
                {
                    "event": g["event"],
                    "ending": g["ending"],
                    "team": g.get("team", ""),
                    "players": frozenset(g["players"]),
                }
                for g in snap
            ])
        st.session_state["mgm_history"] = mh[-8:]
        if "prev_ev" in data:
            st.session_state["prev_ev"] = data["prev_ev"]
        return True
    except Exception:
        return False


def _build_history_payload(prev_ev=None):
    ph = [{f"{a}||{b}": v for (a, b), v in snap.items()} for snap in st.session_state.get("price_history", [])]
    pr = [[[a, b, e] for (a, b, e) in snap] for snap in st.session_state.get("presence_history", [])]
    mh = [
        [{"event": g["event"], "ending": g["ending"], "team": g.get("team", ""), "players": list(g["players"])} for g in snap]
        for snap in st.session_state.get("mgm_history", [])
    ]
    payload = {
        "saved_at": now_utc_iso(),
        "price_history": ph,
        "presence_history": pr,
        "mgm_history": mh,
    }
    if prev_ev is not None:
        payload["prev_ev"] = prev_ev
    elif "prev_ev" in st.session_state:
        payload["prev_ev"] = st.session_state["prev_ev"]
    return payload


def load_history():
    """Prefer GitHub history (survives Streamlit sleep), else local file."""
    local = None
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                local = json.load(f)
        except Exception:
            local = None

    gh, status = None, "unconfigured"
    if _gh_configured():
        gh, status = _gh_load_json(HISTORY_FILE, "_history_sha")
    st.session_state["_history_gh_status"] = status

    chosen = None
    if isinstance(gh, dict) and isinstance(local, dict):
        if str(gh.get("saved_at") or "") >= str(local.get("saved_at") or ""):
            chosen = gh
            st.session_state["_history_source"] = "github"
        else:
            chosen = local
            st.session_state["_history_source"] = "local"
    elif isinstance(gh, dict):
        chosen = gh
        st.session_state["_history_source"] = "github"
    elif isinstance(local, dict):
        chosen = local
        st.session_state["_history_source"] = "local"
    else:
        st.session_state["_history_source"] = "empty"
        return

    if _apply_history_payload(chosen) and chosen is gh:
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(chosen, f)
        except Exception:
            pass


def save_history(prev_ev=None):
    """Write movement snaps locally AND to GitHub so sleep does not wipe Late/Fallen/Moves."""
    try:
        payload = _build_history_payload(prev_ev)
        with open(HISTORY_FILE, "w") as f:
            json.dump(payload, f)
        if _gh_configured():
            ok = _gh_save_json(HISTORY_FILE, payload, "_history_sha", "girl magic history")
            st.session_state["_history_gh_save"] = "ok" if ok else "fail"
        else:
            st.session_state["_history_gh_save"] = "no_secrets"
    except Exception:
        pass

def _gh_repo():
    return (st.secrets.get("GITHUB_REPO") or "").strip()

def _gh_token():
    return (st.secrets.get("GITHUB_TOKEN") or "").strip()

def _gh_headers():
    return {
        "Authorization": f"Bearer {_gh_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def _gh_branch():
    return (st.secrets.get("GITHUB_BRANCH") or "main").strip() or "main"

def _gh_configured():
    return bool(_gh_repo() and _gh_token())


def _gh_load_json(filename, sha_key):
    """Load a JSON file from GitHub. Returns (data, status).
    status: ok | missing | error | unconfigured
    missing → file 404 (not an error). error → auth/network/parse failure.
    """
    if not _gh_configured():
        return None, "unconfigured"
    url = f"https://api.github.com/repos/{_gh_repo()}/contents/{filename}"
    try:
        r = requests.get(url, headers=_gh_headers(), params={"ref": _gh_branch()}, timeout=20)
        if r.status_code == 404:
            return None, "missing"
        if r.status_code != 200:
            st.session_state["_gh_last_err"] = f"GET {filename} HTTP {r.status_code}"
            return None, "error"
        data = r.json()
        st.session_state[sha_key] = data.get("sha")
        content = base64.b64decode(data["content"]).decode("utf-8")
        parsed = json.loads(content)
        return parsed, "ok"
    except Exception as e:
        st.session_state["_gh_last_err"] = f"GET {filename}: {e}"
        return None, "error"


def _gh_save_json(filename, payload, sha_key, msg_prefix):
    """Save JSON to GitHub. Returns True on success."""
    if not _gh_configured():
        return False
    url = f"https://api.github.com/repos/{_gh_repo()}/contents/{filename}"
    body = {
        "message": f"{msg_prefix} {today_az()} {now_az()}",
        "content": base64.b64encode(json.dumps(payload, indent=2).encode("utf-8")).decode("utf-8"),
        "branch": _gh_branch(),
    }
    sha = st.session_state.get(sha_key)
    if sha:
        body["sha"] = sha
    try:
        r = requests.put(url, headers=_gh_headers(), json=body, timeout=25)
        if r.status_code in (200, 201):
            st.session_state[sha_key] = r.json().get("content", {}).get("sha")
            return True
        if r.status_code == 409:
            cur = requests.get(url, headers=_gh_headers(), params={"ref": _gh_branch()}, timeout=20)
            if cur.status_code == 200:
                body["sha"] = cur.json().get("sha")
                r2 = requests.put(url, headers=_gh_headers(), json=body, timeout=25)
                if r2.status_code in (200, 201):
                    st.session_state[sha_key] = r2.json().get("content", {}).get("sha")
                    return True
        st.session_state["_gh_last_err"] = f"PUT {filename} HTTP {r.status_code}"
        return False
    except Exception as e:
        st.session_state["_gh_last_err"] = f"PUT {filename}: {e}"
        return False


def _load_local_json(filename, default):
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception:
        return default


def _save_local_json(filename, payload):
    try:
        with open(filename, "w") as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False


def _merge_results_lists(a, b):
    """Union by id; prefer graded HIT/MISS over PENDING; keep newest logged_at."""
    by_id = {}
    for row in (a or []) + (b or []):
        if not isinstance(row, dict):
            continue
        rid = row.get("id")
        if not rid:
            # fallback key
            rid = f"{row.get('date')}_{row.get('player')}_{row.get('source')}_{row.get('best_price')}"
            row = dict(row)
            row["id"] = rid
        prev = by_id.get(rid)
        if prev is None:
            by_id[rid] = row
            continue
        # prefer non-PENDING
        pr, cr = prev.get("result"), row.get("result")
        if pr == "PENDING" and cr in ("HIT", "MISS"):
            by_id[rid] = row
        elif cr == "PENDING" and pr in ("HIT", "MISS"):
            pass
        else:
            # newer logged_at wins
            if str(row.get("logged_at") or "") >= str(prev.get("logged_at") or ""):
                by_id[rid] = row
    return list(by_id.values())


def _load_results_github():
    data, status = _gh_load_json(RESULTS_FILE, "_results_sha")
    st.session_state["_results_gh_status"] = status
    if status == "ok" and isinstance(data, list):
        return data
    if status == "missing":
        return []  # explicit empty remote — caller may still merge local
    return None  # error / unconfigured


def _save_results_github(rows):
    ok = _gh_save_json(RESULTS_FILE, rows, "_results_sha", "girl magic results")
    st.session_state["_results_gh_save"] = "ok" if ok else "fail"
    return ok


def load_results():
    """Prefer the richer of local + GitHub. Never throw away local for an empty remote."""
    local = _load_local_json(RESULTS_FILE, [])
    if not isinstance(local, list):
        local = []
    gh = _load_results_github()
    status = st.session_state.get("_results_gh_status", "unconfigured")

    if gh is None:
        # unconfigured or error → local only
        st.session_state["_results_source"] = "local" if local else "empty"
        return local

    if not gh and local:
        # remote missing/empty but we have local (pre-GitHub day or failed upload)
        st.session_state["_results_source"] = "local>github_empty"
        return local

    if gh and not local:
        st.session_state["_results_source"] = "github"
        # mirror to local so session is fast
        _save_local_json(RESULTS_FILE, gh)
        return gh

    if gh and local:
        merged = _merge_results_lists(local, gh)
        st.session_state["_results_source"] = "merged"
        return merged

    st.session_state["_results_source"] = "empty"
    return []


def save_results(rows):
    _save_local_json(RESULTS_FILE, rows)
    if _gh_configured():
        ok = _save_results_github(rows)
        if not ok and not st.session_state.get("_gh_save_warned"):
            st.session_state["_gh_save_warned"] = True
            try:
                err = st.session_state.get("_gh_last_err") or "unknown"
                st.warning(
                    "Results saved on this server only — GitHub save failed. "
                    f"Check GITHUB_TOKEN / GITHUB_REPO / GITHUB_BRANCH. ({err})"
                )
            except Exception:
                pass
    else:
        st.session_state["_results_gh_save"] = "no_secrets"


def _load_pregame_github():
    data, status = _gh_load_json(PREGAME_FILE, "_pregame_sha")
    st.session_state["_pregame_gh_status"] = status
    if status == "ok" and isinstance(data, dict):
        return data
    if status == "missing":
        return {}
    return None


def _save_pregame_github(data):
    ok = _gh_save_json(PREGAME_FILE, data, "_pregame_sha", "girl magic pregame lock")
    st.session_state["_pregame_gh_save"] = "ok" if ok else "fail"
    return ok

def set_result_status(row_id, status):
    rows = load_results()
    for row in rows:
        if row.get("id") == row_id:
            row["result"] = status
            if status == "HIT" and row.get("ending") is None and row.get("best_price") is not None:
                row["ending"] = last_two(row["best_price"])
            row["graded_by"] = row.get("graded_by") or "manual"
            save_results(rows)
            return True
    return False

def undo_result(row_id, source):
    if source == "manual_hr":
        rows = [x for x in load_results() if x.get("id") != row_id]
        save_results(rows)
        return True
    return set_result_status(row_id, "PENDING")

def log_bet_this(ev_board, watch_board=None):
    """Log TAKE IT (is_bet) and WATCH (1+ core, not bet) for auto-grade learning."""
    rows = load_results()
    today = today_az()
    added = 0
    watch_board = watch_board or []

    def already(player, source):
        return any(
            r.get("date") == today and r.get("player") == player
            and r.get("source") != "manual_hr"
            for r in rows
        )

    def append_row(item, source):
        nonlocal added
        player = item["player"]
        if already(player, source):
            return
        locked = get_locked(player)
        # Prefer FROZEN pregame lock prices — never learn from live numbers
        price = item.get("best_price")
        book = item.get("best_book") or ""
        lock_books = locked.get("books") or {}
        if lock_books:
            best_p, best_b = None, None
            for b, info in lock_books.items():
                p = info.get("price")
                if p is None:
                    continue
                p = int(p)
                if best_p is None or (american_to_decimal(p) or 0) > (american_to_decimal(best_p) or 0):
                    best_p, best_b = p, b
            if best_p is not None:
                price, book = best_p, best_b
        book_prices = {}
        for b, info in (lock_books or {}).items():
            try:
                if info.get("price") is not None:
                    book_prices[normalize_book(b)] = int(info.get("price"))
            except Exception:
                pass
        if not book_prices:
            book_prices = dict(item.get("book_prices") or {})
        rows.append({
            "id": f"{today}_{player}_{source}_{int(item.get('score') or 0)}",
            "date": today, "time": now_az(), "player": player,
            "score": item.get("score", 0), "edge": int(item.get("edge") or 0),
            "best_price": price, "best_book": book,
            "median": item.get("median"),
            "book_prices": book_prices,
            "price_bucket": price_bucket(price),
            "ending": last_two(price) if price is not None else None,
            "mgm_locked": locked.get("mgm_price"), "mgm_ending": locked.get("mgm_ending"),
            "methods": [normalize_method_name(m) for m in (item.get("methods") or [])],
            "core": item.get("method_count", 0),
            "result": "PENDING", "source": source, "logged_at": now_utc_iso(),
            "price_source": "pregame_lock" if lock_books else "live_fetch",
        })
        added += 1

    for item in ev_board:
        if item.get("is_bet"):
            append_row(item, "take_it")
    for item in watch_board:
        # don't double-log TAKE IT; don't log 2+ core as WATCH (those are PASS/TAKE)
        if item.get("is_bet"):
            continue
        if (item.get("method_count") or 0) >= METHODS_MIN:
            continue
        append_row(item, "watch")

    if added:
        save_results(rows)
    return added

def pending_sort_key(r):
    return (r.get("date") or "", r.get("time") or "", r.get("logged_at") or "", r.get("player") or "")

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_mlb_hr_hitters_cached(dates_key):
    """Heavy MLB calls - cached ~2 min. dates_key = comma-joined YYYY-MM-DD."""
    dates = [d for d in dates_key.split(",") if d]
    hr_names, final_players = set(), set()
    games_checked = 0
    errors = []
    headers = {"User-Agent": "GirlMagicOdds/1.0", "Accept": "application/json"}

    for dstr in dates:
        try:
            r = requests.get(
                f"{MLB_STATS}/schedule",
                params={"sportId": 1, "date": dstr},
                headers=headers,
                timeout=15,
            )
            if r.status_code != 200:
                errors.append(f"schedule {dstr} HTTP {r.status_code}")
                continue
            games = []
            for day in r.json().get("dates", []):
                games.extend(day.get("games", []))
        except Exception as e:
            errors.append(f"schedule {dstr}: {e}")
            continue

        for g in games:
            status = (g.get("status") or {}).get("abstractGameState", "")
            if status not in ("Live", "Final"):
                continue
            pk = g.get("gamePk")
            if not pk:
                continue
            games_checked += 1

            try:
                b = requests.get(f"{MLB_STATS}/game/{pk}/boxscore", headers=headers, timeout=12)
                if b.status_code == 200:
                    box = b.json()
                    for side in ("home", "away"):
                        players = ((box.get("teams") or {}).get(side) or {}).get("players") or {}
                        for _pid, pdata in players.items():
                            name = (pdata.get("person") or {}).get("fullName") or ""
                            if not name:
                                continue
                            cn = clean_name(name)
                            bat = (pdata.get("stats") or {}).get("batting") or {}
                            try:
                                hrs = int(bat.get("homeRuns") or 0)
                            except Exception:
                                hrs = 0
                            if status == "Final" and bat:
                                final_players.add(cn)
                            if hrs >= 1:
                                hr_names.add(cn)
            except Exception as e:
                errors.append(f"box {pk}: {e}")

            # live feed only if boxscore found few HRs mid-game
            try:
                live = requests.get(
                    f"https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live",
                    headers=headers,
                    timeout=12,
                )
                if live.status_code == 200:
                    plays = ((live.json().get("liveData") or {}).get("plays") or {}).get("allPlays") or []
                    for p in plays:
                        if (p.get("result") or {}).get("eventType") != "home_run":
                            continue
                        batter = ((p.get("matchup") or {}).get("batter") or {}).get("fullName")
                        if batter:
                            hr_names.add(clean_name(batter))
            except Exception as e:
                errors.append(f"live {pk}: {e}")

    msg = f"{games_checked} live/final · {len(hr_names)} HR"
    if hr_names:
        msg += " · e.g. " + ", ".join(sorted(hr_names)[:5])
    if errors and not hr_names:
        msg += " · " + "; ".join(errors[:2])
    # sets not cache-friendly in return for some streamlit - use frozenset
    return frozenset(hr_names), frozenset(final_players), msg


def fetch_mlb_hr_hitters(date_str=None):
    if date_str:
        dates_key = date_str
    else:
        dates_key = ",".join(sorted({today_mlb_date(), today_az()}))
    hr, fin, msg = _fetch_mlb_hr_hitters_cached(dates_key)
    return set(hr), set(fin), msg



def auto_grade_pending():
    hr_names, final_players, msg = fetch_mlb_hr_hitters()
    rows = load_results()
    hits = misses = skipped = 0
    pending_n = sum(1 for r in rows if r.get("result") == "PENDING")

    for row in rows:
        if row.get("result") != "PENDING":
            continue
        player = row.get("player") or ""
        if any(names_match(player, h) for h in hr_names):
            row["result"] = "HIT"
            row["graded_by"] = "mlb_auto"
            if row.get("ending") is None and row.get("best_price") is not None:
                row["ending"] = last_two(row["best_price"])
            hits += 1
            continue
        if final_players and any(names_match(player, f) for f in final_players):
            row["result"] = "MISS"
            row["graded_by"] = "mlb_auto"
            misses += 1
        else:
            skipped += 1

    save_results(rows)
    return hits, misses, skipped, f"{msg} · PENDING {pending_n} · matched {hits} HIT / {misses} MISS"


def build_whats_going_today(rows):
    """Today's MLB HRs + ending/book from grades or Lock (best among DK/FD/MGM/HardRock).
    Not the same as MGM pair methods — those stay pair/trio-only on the Board.
    """
    today = today_az()
    hr_names, _final, _msg = fetch_mlb_hr_hitters()

    todays = [r for r in rows if r.get("date") == today]
    hits_logged = [r for r in todays if r.get("result") == "HIT"]
    graded = [r for r in todays if r.get("result") in ("HIT", "MISS")]
    our_list = [r for r in todays if r.get("source") in ("take_it", "watch")]
    lock = st.session_state.get("pregame_lock") or load_pregame()

    # Players who appeared in an MGM pair/trio in history this session
    pair_players = set()
    for snap in st.session_state.get("mgm_history") or []:
        for g in snap:
            if len(g.get("players") or []) in (2, 3):
                pair_players.update(g["players"])

    FOCUS = {"DK", "FD", "MGM", "HardRock"}
    book_ending = Counter()
    pair_ending = Counter()  # MGM endings only when player was in a pair/trio
    on_our_list = 0

    def _pick_best_from_lock(entry):
        """Longest American odds among DK / FD / MGM / HardRock only."""
        books = entry.get("books") or {}
        best_bl, best_p, best_end = None, None, None
        for b, info in books.items():
            p = info.get("price")
            if p is None:
                continue
            bl = book_label(b)
            if bl not in FOCUS:
                continue
            p = int(p)
            end = info.get("ending")
            if end is None:
                end = last_two(p)
            dec = american_to_decimal(p)
            if dec is None:
                continue
            if best_p is None or dec > american_to_decimal(best_p):
                best_bl, best_p, best_end = bl, p, end
        return best_bl, best_p, best_end

    for r in hits_logged:
        ending = r.get("ending")
        if ending is None and r.get("best_price") is not None:
            ending = last_two(r["best_price"])
        if ending is None and r.get("mgm_ending") is not None:
            ending = r["mgm_ending"]
        book = r.get("best_book") or ""
        if ending is None:
            continue
        ending = int(ending)
        bl = book_label(book)
        if bl not in FOCUS:
            # still show under Other via label as-is
            pass
        book_ending[(bl, ending)] += 1
        pname = clean_name(r.get("player") or "")
        if bl == "MGM" and any(names_match(pname, p) for p in pair_players):
            pair_ending[ending] += 1

    for hr in hr_names:
        if any(names_match(hr, r.get("player") or "") for r in our_list):
            on_our_list += 1
        already = any(names_match(hr, r.get("player") or "") for r in hits_logged)
        if already:
            continue
        entry = None
        matched_name = None
        for pname, data in lock.items():
            if names_match(hr, pname):
                entry = data
                matched_name = pname
                break
        if not entry:
            continue
        bl, _p, end = _pick_best_from_lock(entry)
        if bl is None or end is None:
            continue
        end = int(end)
        book_ending[(bl, end)] += 1
        if bl == "MGM" and matched_name and any(names_match(matched_name, p) for p in pair_players):
            pair_ending[end] += 1

    by_book = defaultdict(list)
    for (bl, end), cnt in book_ending.items():
        by_book[bl].append((int(end), int(cnt)))
    for bl in by_book:
        by_book[bl].sort(key=lambda x: (-x[1], x[0]))
    pair_list = sorted(pair_ending.items(), key=lambda x: (-x[1], x[0]))
    return len(hr_names), len(graded), dict(by_book), on_our_list, pair_list


def render_whats_going_today():
    rows = load_results()
    mlb_hr, n_graded, by_book, on_list, pair_list = build_whats_going_today(rows)
    order = ["DK", "FD", "MGM", "HardRock"]
    cols_html = []
    for bl in order:
        items = by_book.get(bl) or []
        if not items:
            continue
        chips = []
        for end, cnt in items[:5]:
            hot_cls = "hot" if end in (0, 10, 25, 50, 75) else ""
            chips.append(
                '<span class="trend-chip %s" style="padding:3px 8px;font-size:0.72rem">'
                '%02d: <span class="chip-count">%s</span></span>' % (hot_cls, end, cnt)
            )
        chips_joined = "".join(chips)
        cols_html.append(
            '<div style="flex:1;min-width:100px">'
            '<div style="font-size:0.72rem;font-weight:800;color:#f9a8d4;margin-bottom:4px">%s</div>'
            '<div style="display:flex;flex-wrap:wrap;gap:4px">%s</div>'
            '</div>' % (bl, chips_joined)
        )
    extra = []
    for bl, items in sorted(by_book.items()):
        if bl in order:
            continue
        for end, cnt in items[:3]:
            extra.append("%s %02d:%s" % (bl, end, cnt))
    if extra:
        cols_html.append(
            '<div style="flex:1;min-width:90px">'
            '<div style="font-size:0.72rem;font-weight:800;color:#e9d5ff;margin-bottom:4px">Other</div>'
            '<div style="font-size:0.72rem;color:#fce7f3">%s</div>'
            '</div>' % (" · ".join(extra[:6]))
        )
    if cols_html:
        body = '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:6px">%s</div>' % ("".join(cols_html))
    else:
        body = '<div style="font-size:0.78rem;opacity:0.85;margin-top:4px">No endings matched yet</div>'

    pair_note = ""
    if pair_list:
        bits = ["%02d:%s" % (e, c) for e, c in pair_list[:5]]
        pair_note = (
            '<div style="margin-top:8px;font-size:0.72rem;color:#fcd34d">'
            'MGM pair/trio only (method): %s'
            '</div>' % (" · ".join(bits))
        )

    title = "What's Going Today"
    sub = (
        "%s HRs · %s on our list · best price among DK/FD/MGM/HardRock "
        "(not MGM pair rules)"
    ) % (mlb_hr, on_list)
    html = (
        '<div class="trends-today" style="padding:12px 14px">'
        '<div class="trends-today-header" style="margin-bottom:4px">'
        '<div class="trends-today-title">%s</div>'
        '<div class="trends-today-sub">%s</div>'
        '</div>%s%s</div>'
    ) % (title, sub, body, pair_note)
    st.markdown(html, unsafe_allow_html=True)



def build_tracker_stats(rows):
    """Signal methods (tags) vs best book taken vs ending on best price — kept separate."""
    done = [r for r in rows if r.get("result") in ("HIT", "MISS") and r.get("source") != "manual_hr"]
    method_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    book_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    ending_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    bucket_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    number_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    book_end_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    for r in done:
        is_hit = r["result"] == "HIT"
        methods_to_count = set()
        for m in r.get("methods") or []:
            nm = normalize_method_name(m)
            if nm in TRACKER_BLOCKLIST or nm in NOISE_METHODS: continue
            if is_core_method(nm) or nm in PERSONAL_STRONG:
                methods_to_count.add(nm)
                break
        for m in r.get("methods") or []:
            nm = normalize_method_name(m)
            if nm in TRACKER_ALWAYS: methods_to_count.add(nm)
        for nm in methods_to_count:
            if nm in TRACKER_BLOCKLIST: continue
            if is_hit: method_stats[nm]["hit"] += 1
            else: method_stats[nm]["miss"] += 1
        # Best book we took (price source) — not the signal method
        bb = book_label(r.get("best_book"))
        if bb != "Untagged":
            if is_hit: book_stats[bb]["hit"] += 1
            else: book_stats[bb]["miss"] += 1
        # Ending on best_price (same row as book above)
        end = r.get("ending")
        if end is None and r.get("best_price") is not None: end = last_two(r["best_price"])
        if end is not None:
            key = f"{int(end):02d}"
            if is_hit: ending_stats[key]["hit"] += 1
            else: ending_stats[key]["miss"] += 1
        buck = r.get("price_bucket") or price_bucket(r.get("best_price"))
        if buck:
            if is_hit: bucket_stats[buck]["hit"] += 1
            else: bucket_stats[buck]["miss"] += 1
        try:
            exact = str(int(r.get("best_price")))
            if is_hit: number_stats[exact]["hit"] += 1
            else: number_stats[exact]["miss"] += 1
        except Exception:
            pass
        for bk, px in (r.get("book_prices") or {}).items():
            try:
                lab = f"{book_label(bk)} {int(px)%100:02d}"
            except Exception:
                continue
            if is_hit: book_end_stats[lab]["hit"] += 1
            else: book_end_stats[lab]["miss"] += 1
    return method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats


def take_it_baseline_rate(rows):
    """Overall TAKE IT hit rate for Tracker highlight (green if method beats this)."""
    hits = misses = 0
    for r in rows:
        if r.get("result") not in ("HIT", "MISS"):
            continue
        if r.get("source") != "take_it":
            continue
        if r["result"] == "HIT":
            hits += 1
        else:
            misses += 1
    n = hits + misses
    if n == 0:
        return None, 0
    return 100.0 * hits / n, n

def method_hit_rate(method_stats, method_name):
    s = method_stats.get(method_name)
    if not s: return None, 0
    t = s["hit"] + s["miss"]
    if t == 0: return None, 0
    return s["hit"] / t, t

def best_method_rate_for_player(methods, method_stats):
    best_p, best_n, best_m = None, 0, None
    for m in methods:
        nm = normalize_method_name(m)
        if not is_core_method(nm): continue
        p, n = method_hit_rate(method_stats, nm)
        if p is None: continue
        if best_p is None or p > best_p or (p == best_p and n > best_n):
            best_p, best_n, best_m = p, n, nm
    return best_p, best_n, best_m

def aggregate_by_player(items):
    by = defaultdict(lambda: {"reasons": [], "methods": [], "event": "", "book_count": 0, "prices": {}})
    for r in items:
        key = r.get("label") or ""
        by[key]["reasons"].append(r.get("reason") or "")
        by[key]["methods"].extend(r.get("methods") or [])
        if r.get("event"): by[key]["event"] = r["event"]
        by[key]["book_count"] = max(by[key]["book_count"], int(r.get("book_count") or 0))
        if r.get("prices"):
            by[key].setdefault("prices", {}).update(r["prices"])
    out = []
    for label, data in by.items():
        meths = list({normalize_method_name(m) for m in data["methods"]})
        seen_r, reasons = set(), []
        for rr in data["reasons"]:
            if rr not in seen_r:
                seen_r.add(rr)
                reasons.append(rr)
        out.append({
            "label": label,
            "reason": "<br>".join(reasons),
            "methods": meths,
            "event": data["event"],
            "book_count": data["book_count"],
            "prices": data.get("prices") or {},
        })
    return out

def _price_line_for_card(prices):
    """DK · FD · HardRock · MGM order for signal cards."""
    if not prices:
        return ""
    order = [("draftkings", "DK"), ("fanduel", "FD"), ("hardrockbet", "HardRock"), ("betmgm", "MGM"), ("caesars", "Caesars")]
    parts = []
    for key, lab in order:
        p = prices.get(key)
        if p is not None:
            parts.append(f"{lab} {format_odds(p)}")
    return " · ".join(parts)

def show_player_cards(typ, banner, explain, results):
    st.markdown(f'<div class="queen-banner">{banner}</div>', unsafe_allow_html=True)
    st.caption(explain)
    items = aggregate_by_player([r for r in results if r["type"] == typ])
    if typ == "signal":
        items = sorted(items, key=lambda r: (-int(r.get("book_count") or 0), r.get("label") or ""))
        st.caption("Sorted: most books first (3 → 2). Order stays correct on mobile.")
    if not items:
        st.info("None.")
        return
    # Row pairs (not one big 2-col) so mobile stacks 1→2→3→4 instead of all-left then all-right
    show_n = items[:40]
    for i in range(0, len(show_n), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(show_n):
                break
            r = show_n[i + j]
            with col:
                tags = render_method_tags(r.get("methods", []))
                price_line = _price_line_for_card(r.get("prices") or {})
                price_html = f"<br><small>{price_line}</small>" if price_line else ""
                st.markdown(
                    f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}{price_html}<br>{tags}</div>',
                    unsafe_allow_html=True,
                )

def fetch_rotowire_lineups():
    if not HAS_BS4:
        return set(), "Install beautifulsoup4 in requirements.txt"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(ROTOWIRE_URL, headers=headers, timeout=30)
        if r.status_code != 200:
            return set(), f"RotoWire HTTP {r.status_code}"
        soup = BeautifulSoup(r.content, "html.parser")
        names = set()
        for sel in (
            "div.lineup__player a",
            "li.lineup__player a",
            "a.lineup__player-link",
            ".lineup__player a",
            "a[href*='/baseball/player/']",
            "a[href*='/player/']",
        ):
            for el in soup.select(sel):
                t = el.get_text(strip=True)
                if t and len(t.split()) >= 2:
                    names.add(clean_name(t))
        if not names:
            return set(), "RotoWire 0 names - site may block Streamlit or changed layout"
        return names, f"RotoWire · {len(names)} names"
    except Exception as e:
        return set(), f"RotoWire error: {e}"

@st.cache_data(ttl=180, show_spinner=False)
def _fetch_events_oddsapi_cached(api_key):
    r = requests.get(f"{ODDS_API_BASE}/sports/baseball_mlb/events", params={"apiKey": api_key}, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_events_oddsapi(api_key):
    try:
        return _fetch_events_oddsapi_cached(api_key)
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
        raw = (book.get("key") or "").lower()
        found.add(raw)
        bk = normalize_book(raw)
        if bk not in PREFERRED: continue
        for market in book.get("markets", []):
            # accept standard + alternate HR markets; still force 0.5 only
            mkey = (market.get("key") or "")
            if mkey and "home_run" not in mkey and "homer" not in mkey:
                continue
            for o in market.get("outcomes", []):
                if o.get("name", "").lower() != "over": continue
                pt = o.get("point")
                if pt is None or abs(float(pt) - 0.5) > 0.01: continue
                player = o.get("description")
                price = o.get("price")
                if not player or price is None: continue
                try:
                    price = int(price)
                except Exception:
                    continue
                # only Over 0.5; drop absurd longshots (wrong market / junk)
                if price > MAX_HR_AMERICAN:
                    continue
                if is_blocked_player(player):
                    continue
                rows.append({"event": event, "book": bk, "player": player, "price": price, "point": 0.5, "team": "", "source": "oddsapi"})
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        r = requests.get(f"{SGO_BASE}/events", params={"apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 25}, timeout=25)
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
                    b = normalize_book(bk)
                    if b not in PREFERRED: continue
                    price = bd.get("odds")
                    if price is None: continue
                    try: price = int(str(price).replace("+", ""))
                    except Exception: continue
                    if price > MAX_HR_AMERICAN:
                        continue
                    if is_blocked_player(pname):
                        continue
                    found.add(b)
                    rows.append({"event": event_name, "book": b, "player": pname, "price": price, "point": 0.5, "team": team, "source": "sgo"})
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
        if r.get("team"): team_map[r["player"]] = r["team"]
    df["team"] = df.apply(lambda r: r["team"] if r.get("team") else team_map.get(r["player"], ""), axis=1)
    df = df.drop_duplicates(subset=["player", "book"], keep="first")
    return df.drop(columns=["priority", "source"], errors="ignore")

def do_fetch(odds_key, sgo_key, chosen_labels, options):
    all_rows, all_found_raw = [], set()
    http_ok = 0
    http_fail = 0
    for label in chosen_labels:
        eid = options.get(label)
        if not eid: continue
        data = fetch_odds_oddsapi(odds_key, eid)
        if data is None:
            http_fail += 1
            continue
        http_ok += 1
        rows, found = flatten_oddsapi(data)
        all_rows.extend(rows)
        all_found_raw.update(found)
    sgo_rows, sgo_found = fetch_sgo_hr_props(sgo_key)
    all_rows.extend(sgo_rows)
    all_found_raw.update(sgo_found)
    kept = {normalize_book(b) for b in all_found_raw} & PREFERRED
    st.session_state["fetch_debug"] = {
        "http_ok": http_ok,
        "http_fail": http_fail,
        "raw_books": sorted(all_found_raw),
        "kept_books": sorted(kept),
        "row_count_pre_filter": len(all_rows),
        "sgo_rows": len(sgo_rows),
    }
    if not all_rows:
        return None, set()
    df = merge_odds(
        [r for r in all_rows if r.get("source") == "oddsapi"],
        [r for r in all_rows if r.get("source") == "sgo"],
    )
    if chosen_labels and not df.empty and "event" in df.columns:
        before = len(df)
        mask = df["event"].apply(lambda e: event_matches_chosen(e, chosen_labels))
        filtered = df[mask].copy()
        # if label mismatch would wipe a good feed, keep unfiltered (still preferred books only)
        if filtered.empty and before > 0:
            st.session_state["fetch_debug"]["event_filter_wiped"] = before
        else:
            df = filtered
            st.session_state["fetch_debug"]["event_filter_wiped"] = 0
    st.session_state["fetch_debug"]["row_count_final"] = 0 if df is None or df.empty else len(df)
    return df, kept

def build_team_map(df):
    tm = {}
    for _, r in df.iterrows():
        if r.get("team"): tm[r["player"]] = r["team"]
    return tm

def tighten_board(ev_board):
    """Cap only TAKE IT (is_bet). PASS stays full so multi-method short-edge never falls into WATCH."""
    if not ev_board:
        return []
    takes = [x for x in ev_board if x.get("is_bet")]
    passes = [x for x in ev_board if not x.get("is_bet")]
    ranked = sorted(takes, key=lambda x: (-x["method_count"], -x["score"], -x["edge"]))
    per_team, per_game, out_takes = defaultdict(int), defaultdict(int), []
    for item in ranked:
        team = item.get("team") or "UNK"
        game = item.get("event") or (item.get("events") or ["UNK"])[0]
        if per_team[team] >= BOARD_MAX_PER_TEAM or per_game[game] >= BOARD_MAX_PER_GAME:
            continue
        out_takes.append(item)
        per_team[team] += 1
        per_game[game] += 1
    # PASS: sort but do not hard-cap (show the real short-edge multi-method list)
    passes = sorted(passes, key=lambda x: (-x["method_count"], -x["score"], -x["edge"]))
    return out_takes + passes

def run_flags(df, previous_df=None, record_history=True, selected_events=None):
    if df.empty: return [], [], [], []
    if "team" not in df.columns: df["team"] = ""
    df = df.sort_values("point").groupby(["player", "book"], dropna=False).first().reset_index()
    results, methods_map = [], defaultdict(list)
    all_players_now = set(df["player"].unique())
    selected = set(selected_events) if selected_events else set(df["event"].unique())
    team_map = build_team_map(df)
    lineup_names = st.session_state.get("lineup_names", set())
    signal_bucket, signal_methods = defaultdict(list), defaultdict(set)
    for k in ("presence_history", "price_history", "mgm_history"):
        if k not in st.session_state: st.session_state[k] = []
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
        late_bucket = {}
        def add_late(player, book, event, kind):
            if player not in late_bucket:
                late_bucket[player] = {"kind": kind, "books": [], "event": event}
            pri = {"Gone Missing": 3, "Just Appeared": 2, "Added Late": 1}
            if pri.get(kind, 0) >= pri.get(late_bucket[player]["kind"], 0):
                late_bucket[player]["kind"] = kind
            late_bucket[player]["books"].append(book)
            if event: late_bucket[player]["event"] = event
        for player, book, event in latest - previous: add_late(player, book, event, "Just Appeared")
        for player, book, event in previous - latest: add_late(player, book, event, "Gone Missing")
        for player, info in sorted(late_bucket.items()):
            kind = info["kind"]
            lock_note = locked_price_str(player)
            books_s = ", ".join(sorted(set(info["books"])))
            reason = f"{kind} · {books_s}"
            if lock_note and kind == "Gone Missing":
                reason += f"<br>🔒 last lock: {lock_note}"
            results.append({"type": "late", "label": player, "reason": reason, "methods": [kind]})
            methods_map[player].append(kind)

    # Lock had them on DK/FD/MGM — current fetch does not (true "missing from books")
    lock = st.session_state.get("pregame_lock") or load_pregame()
    FOCUS_LATE = ("draftkings", "fanduel", "betmgm", "hardrockbet")
    now_by_player = defaultdict(set)
    for _, r in df.iterrows():
        bk = str(r.get("book") or "").lower()
        try:
            bk = normalize_book(bk)
        except Exception:
            pass
        now_by_player[clean_name(r["player"])].add(bk)
    for pname, entry in (lock or {}).items():
        if entry.get("date") and entry.get("date") != today_az():
            continue
        books = entry.get("books") or {}
        missing = []
        for b, info in books.items():
            if info.get("price") is None:
                continue
            bk = str(b).lower()
            try:
                bk = normalize_book(bk)
            except Exception:
                pass
            if not any(k in bk for k in FOCUS_LATE):
                continue
            if bk not in now_by_player.get(clean_name(pname), set()) and not any(
                k in x for x in now_by_player.get(clean_name(pname), set()) for k in (bk,)
            ):
                # also check substring match
                present = now_by_player.get(clean_name(pname), set())
                if not any(bk in p or p in bk for p in present):
                    missing.append(book_label(b))
        if not missing:
            continue
        # skip if already on feed under another name form
        if clean_name(pname) in {clean_name(p) for p in all_players_now}:
            # on feed somewhere — only flag if focus books specifically missing
            present = now_by_player.get(clean_name(pname), set())
            missing = []
            for b, info in books.items():
                if info.get("price") is None:
                    continue
                bk = str(b).lower()
                try:
                    bk = normalize_book(bk)
                except Exception:
                    pass
                if not any(k in bk for k in FOCUS_LATE):
                    continue
                if not any(bk in p or p in bk for p in present):
                    missing.append(f"{book_label(b)} {format_odds(info['price'])}")
            if not missing:
                continue
        else:
            missing = []
            for b, info in books.items():
                if info.get("price") is None:
                    continue
                bk = str(b).lower()
                try:
                    bk = normalize_book(bk)
                except Exception:
                    pass
                if any(k in bk for k in FOCUS_LATE):
                    missing.append(f"{book_label(b)} {format_odds(info['price'])}")
        if not missing:
            continue
        reason = "Missing from books now · had on Lock: " + ", ".join(missing[:6])
        results.append({
            "type": "late",
            "label": pname,
            "reason": reason,
            "methods": ["Gone Missing"],
        })

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
            if delta >= BIG_MOVE:
                results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 Shot up on {book}: {format_odds(prev_price)} → {format_odds(curr_price)}", "methods": ["FADE · Shot way up"], "gap": abs(int(delta))})
            elif delta <= -BIG_MOVE:
                results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 Drop >100 on {book}: {format_odds(prev_price)} → {format_odds(curr_price)}", "methods": ["FADE · Drop >100"], "gap": abs(int(delta))})
        for player, moves in sorted(player_up.items()):
            results.append({"type": "hist", "move_dir": "up", "label": player, "reason": "<br>".join(moves), "methods": ["Price moved"]})
        for player, moves in sorted(player_down.items()):
            results.append({"type": "hist", "move_dir": "down", "label": player, "reason": "<br>".join(moves), "methods": ["Price moved"]})
    # Lock timing moves: open → latest/close (survives MGM drop)
    try:
        lock_up, lock_down = lock_movement_rows()
        for player, moves in sorted(lock_up.items()):
            if player not in all_players_now and player not in lock_up:
                pass
            results.append({
                "type": "hist", "move_dir": "up", "label": player,
                "reason": "🔒 from open<br>" + "<br>".join(moves),
                "methods": ["Price moved"],
            })
        for player, moves in sorted(lock_down.items()):
            results.append({
                "type": "hist", "move_dir": "down", "label": player,
                "reason": "🔒 from open<br>" + "<br>".join(moves),
                "methods": ["Price moved"],
            })
    except Exception:
        pass
    for player, g in df.groupby("player"):
        by_book = {r["book"]: r["price"] for _, r in g.iterrows()}
        fd = by_book.get("fanduel")
        mgm_price = next((v for k, v in by_book.items() if "betmgm" in k), None)
        others = [v for b, v in by_book.items() if b != "fanduel"]
        if fd is not None and mgm_price is not None:
            gap = mgm_price - fd
            if 10 <= gap <= 100:
                results.append({"type": "trend", "trend_kind": "good", "label": player, "reason": f"💚 FD under MGM by {int(gap)} · FD {format_odds(fd)} · MGM {format_odds(mgm_price)}", "methods": ["FD under MGM"], "gap": int(gap)})
        if fd is not None and others and fd > max(others):
            results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 FD highest · {format_odds(fd)}", "methods": ["FADE · FD highest"], "gap": 0})
    for _, row in df.iterrows():
        if row["book"] != "draftkings": continue
        d = last_two(row["price"])
        if d == 10:
            results.append({"type": "dk", "label": row["player"], "reason": f"DK ends 10 → {format_odds(row['price'])}", "event": row["event"], "methods": ["DK 10"]})
            methods_map[row["player"]].append("DK 10")
        elif d in FD_ENDINGS:
            results.append({"type": "dk", "label": row["player"], "reason": f"DK FD-style ends {d:02d} → {format_odds(row['price'])}", "event": row["event"], "methods": ["DK FD-style"]})
            methods_map[row["player"]].append("DK FD-style")
    mgm = df[df["book"].str.contains("betmgm|mgm", case=False, na=False)].copy()
    current_mgm = []
    group_key = ["event", "team"] if (not mgm.empty and mgm["team"].astype(str).str.len().gt(0).any()) else ["event"]
    if not mgm.empty:
        for keys, g in mgm.groupby(group_key, dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            event, team = keys[0], (keys[1] if len(keys) > 1 else "")
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in MGM_ENDINGS: ends[d].append(r["player"])
            for d, ps in ends.items():
                names = sorted(set(ps))
                if len(names) not in (2, 3): continue
                current_mgm.append({"event": event, "ending": d, "team": team if isinstance(team, str) else "", "players": frozenset(names)})
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
            if len(g["players"]) == 3: early.update(g["players"])
        late = set()
        for g in h[-1]: late.update(g["players"])
        survivor = early & late
    for grp in current_mgm:
        names = sorted(grp["players"])
        if len(names) not in (2, 3): continue
        d = grp["ending"]
        team = grp.get("team") or ""
        meth = [f"MGM {d:02d}", "Match 00" if d == 0 else f"Match {d:02d}"]
        extra = []
        for n in names:
            if mgm_stayed.get(n, 0) >= 2:
                meth.append("Stayed in the group")
                extra.append("Stayed in the group")
            if n in survivor:
                meth.append("Last one left")
                extra.append("Last one left")
        kind = "pair" if len(names) == 2 else "group of 3"
        tnote = f" · {team}" if team else " · same team"
        reason = f"MGM {kind} ends {d:02d}{tnote}"
        if extra: reason += " • " + " + ".join(sorted(set(extra)))
        results.append({"type": "mgm", "label": " + ".join(names), "reason": reason, "event": grp["event"], "methods": list(set(meth))})
        for n in names: methods_map[n].extend(meth)
    if not mgm.empty:
        gk = ["event", "team"] if mgm["team"].astype(str).str.len().gt(0).any() else ["event"]
        for keys, g in mgm.groupby(gk, dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            event, team = keys[0], (keys[1] if len(keys) > 1 else "")
            for price, pg in g.groupby("price"):
                names = sorted(pg["player"].unique())
                if len(names) not in (2, 3): continue
                tnote = f" · {team}" if team else ""
                results.append({"type": "mgm", "label": " + ".join(names), "reason": f"MGM Exact {format_odds(price)} ({len(names)}){tnote}", "event": event, "methods": ["MGM Exact"]})
                for n in names: methods_map[n].append("MGM Exact")
    FOCUS_KEYS = ("draftkings", "fanduel", "betmgm", "hardrockbet")
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if len(g) < 2:
            continue
        # Prefer focus books only for cluster tags
        focus_rows = []
        for _, r in g.iterrows():
            bk = str(r.get("book") or "").lower()
            try:
                bk = normalize_book(bk)
            except Exception:
                pass
            if any(k in bk for k in FOCUS_KEYS) or bk in FOCUS_KEYS:
                if r.get("price") is not None:
                    focus_rows.append((bk, int(r["price"])))
        if len(focus_rows) < 2:
            prices = [int(p) for p in g["price"].dropna().tolist()]
            books = list(g["book"].astype(str))
            if len(prices) >= 2 and len(set(prices)) == 1:
                results.append({
                    "type": "match", "label": player,
                    "reason": f"Same price {format_odds(prices[0])} on {', '.join(books)}",
                    "event": g["event"].iloc[0], "methods": ["Exact Match"],
                })
                methods_map[player].append("Exact Match")
            continue
        # one price per book (if dupes, keep first)
        by_bk = {}
        for bk, p in focus_rows:
            if bk not in by_bk:
                by_bk[bk] = p
        prices = list(by_bk.values())
        labels = [book_label(b) for b in by_bk.keys()]
        if len(prices) < 2:
            continue
        lo, hi = min(prices), max(prices)
        spread = hi - lo
        ev0 = g["event"].iloc[0]
        if spread == 0:
            tag = "All books same" if len(prices) >= 3 else "Exact Match"
            results.append({
                "type": "match", "label": player,
                "reason": f"{tag}: {format_odds(lo)} on {', '.join(labels)}",
                "event": ev0, "methods": [tag],
            })
            methods_map[player].append(tag)
            if tag != "Exact Match":
                methods_map[player].append("Exact Match")
        elif spread <= BOOK_CLUSTER_GAP and len(prices) >= 2:
            results.append({
                "type": "match", "label": player,
                "reason": f"Books tight: {format_odds(lo)}–{format_odds(hi)} (gap {spread}) on {', '.join(labels)}",
                "event": ev0, "methods": ["Books tight"],
            })
            methods_map[player].append("Books tight")
    for _, row in df.iterrows():
        if row["book"] != "fanduel": continue
        player = row["player"]
        if not has_dk_or_mgm(methods_map.get(player, [])): continue
        price = abs(int(row["price"])) if row["price"] else 0
        last = last_two(row["price"])
        if price == 600:
            results.append({"type": "fd", "label": player, "reason": f"FD +600 (with DK/MGM) → {format_odds(row['price'])}", "event": row["event"], "methods": ["FD 600"]})
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in FD_ENDINGS:
            results.append({"type": "fd", "label": player, "reason": f"FD ends {last:02d} (with DK/MGM) → {format_odds(row['price'])}", "event": row["event"], "methods": ["FD Pattern"]})
            methods_map[player].append("FD Pattern")
    # FD+MGM classic combo (support tag — study timing before promoting)
    for player, ms in list(methods_map.items()):
        ms_set = set(ms)
        has_fd = ("FD Pattern" in ms_set) or ("FD 600" in ms_set)
        has_mgm_classic = bool(ms_set & {"MGM 25", "MGM 50", "MGM 75", "Match 25", "Match 50", "Match 75"})
        if has_fd and has_mgm_classic and "FD+MGM classic" not in ms_set:
            methods_map[player].append("FD+MGM classic")
            results.append({
                "type": "fd", "label": player,
                "reason": "FD Pattern/600 + MGM classic 25/50/75 (combo — tracking)",
                "event": "", "methods": ["FD+MGM classic"],
            })
    signal_book_n = {}  # player -> # of method-books (DK/MGM/FD) for sorting Signals
    for player, ms in list(methods_map.items()):
        core = [m for m in set(ms) if is_core_method(m)]
        books_hit = set()
        for m in core:
            if m.startswith("DK"): books_hit.add("dk")
            if m.startswith("MGM") or m.startswith("Match ") or m == "MGM Exact": books_hit.add("mgm")
            if m.startswith("FD"): books_hit.add("fd")
        if len(books_hit) >= 2:
            n = len(books_hit)
            signal_book_n[player] = max(signal_book_n.get(player, 0), n)
            methods_map[player].append("Multi-book method")
            signal_bucket[player].append(f"Methods on {n} books")
            signal_methods[player].add("Multi-book method")
    if len(phist) >= 2:
        prev_snap, curr_snap = phist[-2], phist[-1]
        down_by = defaultdict(list)
        for key, curr_price in curr_snap.items():
            player, book = key
            if player not in all_players_now or key not in prev_snap: continue
            if curr_price - prev_snap[key] <= -MOVE_MIN: down_by[player].append(book)
        for player, books in down_by.items():
            if len(books) >= 2:
                methods_map[player].append("Multi-book Shorten")
                signal_bucket[player].append(f"Shorten on {', '.join(books)}")
                signal_methods[player].add("Multi-book Shorten")
                signal_book_n[player] = max(signal_book_n.get(player, 0), len(books))
    # price lookup for signal cards (DK / FD / HardRock / MGM)
    price_by_player = defaultdict(dict)
    for _, r in df.iterrows():
        bk = str(r.get("book") or "").lower()
        try:
            bk = normalize_book(bk)
        except Exception:
            pass
        if bk in ("draftkings", "fanduel", "hardrockbet", "betmgm", "caesars"):
            try:
                price_by_player[r["player"]][bk] = int(r["price"])
            except Exception:
                pass
    # highest book-count first, then name
    for player in sorted(signal_bucket.keys(), key=lambda p: (-signal_book_n.get(p, 0), p)):
        results.append({
            "type": "signal",
            "label": player,
            "reason": "<br>".join(signal_bucket[player]),
            "methods": list(signal_methods[player]),
            "book_count": signal_book_n.get(player, 0),
            "prices": dict(price_by_player.get(player) or {}),
        })
    player_events = defaultdict(set)
    for _, r in df.iterrows(): player_events[r["player"]].add(r["event"])
    ev_board = []
    watch_board = []
    coverage_board = []
    for (player, _), g in df.groupby(["player", "point"], dropna=False):
        if is_blocked_player(player): continue
        if lineup_names and name_in_lineup(player, lineup_names) is False: continue
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 1: continue
        best, best_book = smart_best(prices, books) if len(prices) >= 2 else (prices[0], books[0])
        if best is None: continue
        try: med = statistics.median(prices) if len(prices) >= 2 else best
        except Exception: med = best
        edge = best - med if len(prices) >= 2 else 0
        meths = list({normalize_method_name(m) for m in methods_map.get(player, [])})
        core_count = count_core_methods(meths)
        # show premium + support tags on cards; core_count still premium-only
        display_meths = [m for m in meths if is_core_method(m) or m in SUPPORT_ONLY or m in TAKE_IT_STRONG]
        if not display_meths:
            display_meths = list(meths)
        score = girl_magic_score(core_count, edge, display_meths)
        conf, bars, level = get_confidence(score, core_count >= METHODS_MIN and edge >= EDGE_MIN)
        book_px = {}
        for bk, px in zip(books, prices):
            try:
                book_px[normalize_book(bk)] = int(px)
            except Exception:
                pass
        row = {
            "player": player, "best_price": best, "best_book": best_book, "median": med,
            "book_prices": book_px,
            "edge": edge, "is_bet": False,
            "why": f"Score {score}/100 · {core_count} core · edge {int(edge)}",
            "methods": display_meths, "score": score, "bars": bars, "level": level,
            "method_count": core_count, "team": team_map.get(player, ""),
            "events": list(player_events.get(player, [])),
            "event": next(iter(player_events.get(player, [])), ""),
        }
        # WATCH list starts as 1+ core; refined at display/log time
        if core_count >= 1:
            watch_board.append(dict(row))
        # COVERAGE = support-only tags (0 premium) — eyes only, never TAKE IT
        elif display_meths:
            support_tags = [
                m for m in display_meths
                if m in SUPPORT_ONLY
                or m.startswith("MGM end")
            ]
            if support_tags:
                cov = dict(row)
                cov["methods"] = support_tags
                cov["why"] = (
                    f"Coverage only · no premium core · tags: {', '.join(support_tags[:6])}"
                    " · not a bet — so we don't miss weak-tag names on Lab days"
                )
                cov["bars"], cov["level"] = 1, "low"
                coverage_board.append(cov)
        # PASS / TAKE IT pool: 2+ PREMIUM core (support tags do not count)
        if core_count < METHODS_MIN:
            continue
        is_bet = qualifies_take_it(core_count, display_meths, edge)
        row["is_bet"] = is_bet
        fams = strong_method_families(display_meths)
        strong_n = len(fams)
        has_pri = has_priority_method(display_meths)
        tri = " · 💎 DK+MGM+FD" if has_dk_mgm_fd(display_meths) else ""
        pri_note = " · priority ✓" if (is_bet and has_pri) else ""
        if is_bet:
            why = (
                f"Score {score}/100 · {core_count} premium · {strong_n} families · "
                f"edge {int(edge)}{tri}{pri_note}"
            )
        else:
            miss = []
            if not has_pri:
                miss.append("need priority (25-match / FD / Multi-book method / Exact / FD+MGM)")
            if edge < EDGE_MIN:
                miss.append(f"edge ≥{EDGE_MIN}")
            why = (
                f"Score {score}/100 · {core_count} premium · {strong_n} families · "
                f"edge {int(edge)}{tri} · PASS ({' · '.join(miss) if miss else 'filtered'})"
            )
        row["why"] = why
        conf, bars, level = get_confidence(score, is_bet)
        row["bars"], row["level"] = bars, level
        ev_board.append(row)
    ev_board = tighten_board(ev_board)
    current_ev = {item["player"]: {"methods": item["methods"], "edge": item["edge"], "is_bet": item["is_bet"], "method_count": item["method_count"], "score": item["score"], "events": item.get("events", [])} for item in ev_board}
    prev_ev = st.session_state.get("prev_ev", {})
    fallen = []
    for player, old in prev_ev.items():
        if player in current_ev: continue
        old_events = old.get("events") or []
        if selected and old_events and not any(event_matches_chosen(e, selected) for e in old_events): continue
        lock_note = locked_price_str(player)
        reasons = []
        if player not in all_players_now:
            reasons.append("Left feed (often MGM after pitch)")
            if lock_note: reasons.append(f"🔒 {lock_note}")
        else:
            reasons.append("Dropped filters")
        if old.get("is_bet"): reasons.insert(0, "Was TAKE IT")
        fallen.append({"type": "fallen", "label": player, "reason": " · ".join(reasons), "methods": ["Fallen Off"], "old_score": old.get("score", 0)})
        results.append(fallen[-1])
    # ── Name Magic (only with methods · prefer different teams) ──
    pev = defaultdict(set)
    for _, r in df.iterrows():
        pev[r["player"]].add(r["event"])

    def _diff_teams(a, b):
        ta, tb = team_map.get(a, ""), team_map.get(b, "")
        if ta and tb:
            return ta != tb
        return len(pev[a] & pev[b]) == 0

    def _has_strong(ms):
        return any(
            m in PERSONAL_STRONG or m.startswith("Match ") or m.startswith("MGM")
            or m.startswith("DK") or m.startswith("FD")
            for m in ms
        )

    pool = [
        p for p, ms in methods_map.items()
        if count_core_methods(ms) >= NAME_METHODS_MIN and _has_strong(ms)
    ]
    if lineup_names:
        pool = [p for p in pool if name_in_lineup(p, lineup_names) is not False]

    n_pairs = 0
    # Same initials (first+last)
    init_map = defaultdict(list)
    for p in pool:
        fi, li, _, _ = get_initials(p)
        if fi and li:
            init_map[fi + li].append(p)
    for k, names in init_map.items():
        names = sorted(set(names))
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if n_pairs >= NAME_MAX_PAIRS:
                    break
                if not _diff_teams(a, b):
                    continue
                results.append({
                    "type": "same_init", "label": f"{a} + {b}",
                    "reason": f"Same initials {k} · different teams",
                    "methods": ["Same Initials"], "event": "",
                })
                n_pairs += 1

    # Cross initials: A's last = B's first
    n_cross = 0
    for i, a in enumerate(pool):
        fi_a, li_a, _, _ = get_initials(a)
        if not fi_a or not li_a:
            continue
        for b in pool[i + 1:]:
            if n_cross >= NAME_MAX_PAIRS:
                break
            fi_b, li_b, _, _ = get_initials(b)
            if not fi_b or not li_b:
                continue
            if not _diff_teams(a, b):
                continue
            if li_a == fi_b or li_b == fi_a:
                if li_a == fi_b:
                    rsn = f"Cross initials ({li_a}↔{fi_b}) · different teams"
                else:
                    rsn = f"Cross initials ({li_b}↔{fi_a}) · different teams"
                results.append({
                    "type": "cross", "label": f"{a} + {b}",
                    "reason": rsn,
                    "methods": ["Cross Initials"], "event": "",
                })
                n_cross += 1

    # Fix cross reason properly in a cleaner loop - replace the broken cross block
    # Actually my reason string is broken. Let me fix in a second pass.

    # Same last name
    last_map = defaultdict(list)
    for p in pool:
        _, _, _, last = get_initials(p)
        if last:
            last_map[last].append(p)
    n_last = 0
    for last, names in last_map.items():
        names = sorted(set(names))
        if len(names) < 2:
            continue
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if n_last >= NAME_MAX_PAIRS:
                    break
                if not _diff_teams(a, b):
                    continue
                results.append({
                    "type": "last", "label": f"{a} + {b}",
                    "reason": f"Same last name · {last.title()} · different teams",
                    "methods": ["Same Last Name"], "event": "",
                })
                n_last += 1

    # Same first name
    first_map = defaultdict(list)
    for p in pool:
        _, _, first, _ = get_initials(p)
        if first:
            first_map[first].append(p)
    n_first = 0
    for first, names in first_map.items():
        names = sorted(set(names))
        if len(names) < 2:
            continue
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if n_first >= NAME_MAX_PAIRS:
                    break
                if not _diff_teams(a, b):
                    continue
                results.append({
                    "type": "first", "label": f"{a} + {b}",
                    "reason": f"Same first name · {first.title()} · different teams",
                    "methods": ["Same First Name"], "event": "",
                })
                n_first += 1

    if record_history:
        st.session_state["prev_ev"] = current_ev
        save_history(prev_ev=current_ev)
    return results, ev_board, fallen, watch_board, coverage_board


def build_backtest_stats(rows, days=14):
    """Daily + overall TAKE IT vs WATCH hit rates from graded results."""
    today = today_az()
    try:
        today_dt = datetime.strptime(today, "%Y-%m-%d")
    except Exception:
        today_dt = datetime.now()
    cutoff = (today_dt - timedelta(days=days)).strftime("%Y-%m-%d")

    graded = [
        r for r in rows
        if r.get("result") in ("HIT", "MISS")
        and r.get("source") in ("take_it", "watch")
        and (r.get("date") or "") >= cutoff
    ]

    def rate(subset):
        h = sum(1 for r in subset if r["result"] == "HIT")
        m = sum(1 for r in subset if r["result"] == "MISS")
        t = h + m
        pct = (100.0 * h / t) if t else None
        return h, m, t, pct

    overall = {}
    for src in ("take_it", "watch"):
        overall[src] = rate([r for r in graded if r.get("source") == src])

    by_date = {}
    for r in graded:
        d = r.get("date") or ""
        by_date.setdefault(d, {"take_it": [], "watch": []})
        src = r.get("source")
        if src in by_date[d]:
            by_date[d][src].append(r)

    daily = []
    for d in sorted(by_date.keys(), reverse=True):
        ti = rate(by_date[d]["take_it"])
        wa = rate(by_date[d]["watch"])
        daily.append({"date": d, "take_it": ti, "watch": wa})

    # method rates within WATCH vs TAKE IT
    method_by_src = {"take_it": defaultdict(lambda: {"hit": 0, "miss": 0}), "watch": defaultdict(lambda: {"hit": 0, "miss": 0})}
    for r in graded:
        src = r.get("source")
        if src not in method_by_src:
            continue
        is_hit = r["result"] == "HIT"
        counted = set()
        for m in r.get("methods") or []:
            nm = normalize_method_name(m)
            if nm in TRACKER_BLOCKLIST or nm in NOISE_METHODS:
                continue
            if not (is_core_method(nm) or nm in TRACKER_ALWAYS or nm in PERSONAL_STRONG):
                continue
            if nm in counted:
                continue
            counted.add(nm)
            if is_hit:
                method_by_src[src][nm]["hit"] += 1
            else:
                method_by_src[src][nm]["miss"] += 1

    return overall, daily, method_by_src, len(graded)




def event_is_today(e):
    """True if commence_time falls on today in AZ or ET (covers late West Coast)."""
    t = e.get("commence_time") or ""
    if not t:
        return True  # keep if unknown
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:
        return True
    az = today_az()
    et = today_mlb_date()
    for hours, day in [(-7, az), (-4, et)]:
        local = dt.astimezone(timezone(timedelta(hours=hours))).strftime("%Y-%m-%d")
        if local == day:
            return True
    return False


def filter_events_today(events):
    today_only = [e for e in events if event_is_today(e)]
    return today_only if today_only else events  # fallback if filter empty




def lock_player_summary(player, lock_entry, price_mode="close"):
    """Tags from lock. price_mode: close | latest | first.
    lines show open → now/close when they differ.
    """
    books = lock_entry.get("books") or {}
    tags, lines, ends_by_book = [], [], {}
    best_book, best_price, best_key = None, None, None
    price_map = {}  # bl -> research price
    primary_end = None  # one ending for Lab chips (DK/FD/MGM best)
    primary_prices = {}

    for b, info in books.items():
        slot = _book_slot_normalize(info)
        first = slot.get("first_price")
        latest = slot.get("latest_price")
        close = slot.get("close_price")
        if price_mode == "first":
            p = first
        elif price_mode == "latest":
            p = latest if latest is not None else first
        else:
            p = close if close is not None else (latest if latest is not None else first)
        if p is None:
            continue
        p = int(p)
        bl = book_label(b)
        price_map[bl] = p
        t0 = format_az_from_iso(slot.get("first_at"))
        t1 = format_az_from_iso(slot.get("close_at") or slot.get("latest_at"))
        if first is not None and first != p:
            lines.append(
                f"{bl} open {format_odds(first)}"
                + (f" ({t0})" if t0 else "")
                + f" → {format_odds(p)}"
                + (f" ({t1})" if t1 else "")
            )
        else:
            lines.append(f"{bl} {format_odds(p)}" + (f" · {t0 or t1}" if (t0 or t1) else ""))
        end = last_two(p)
        if end is not None:
            end = int(end)
            ends_by_book[bl] = end
            if bl == "MGM" and end in MGM_ENDINGS:
                tags.append(f"MGM end {end:02d}")
            if bl == "DK" and end == 10:
                tags.append("DK 10")
            if bl == "DK" and end in FD_ENDINGS:
                tags.append("DK FD-style")
            if bl == "FD" and abs(p) >= FD_MIN and end in FD_ENDINGS:
                tags.append("FD Pattern")
            if bl == "FD" and abs(p) == 600:
                tags.append("FD 600")
        if bl in ("DK", "FD", "MGM"):
            primary_prices[bl] = p
        if best_price is None or american_to_decimal(p) > american_to_decimal(best_price):
            best_price, best_book, best_key = p, bl, b
    # primary ending for 1-chip-per-HR: longest among DK/FD/MGM
    if primary_prices:
        pb = max(primary_prices.items(), key=lambda x: american_to_decimal(x[1]))
        primary_end = (pb[0], last_two(pb[1]), pb[1])
    end_vals = list(ends_by_book.values())
    if len(end_vals) >= 2 and len(set(end_vals)) == 1:
        tags.append(f"Same end {end_vals[0]:02d}")
    focus_prices = [int(p) for bl, p in price_map.items() if bl in ("DK", "FD", "MGM", "HardRock")]
    pool = focus_prices if len(focus_prices) >= 2 else list(price_map.values())
    if len(pool) >= 2:
        lo, hi = min(pool), max(pool)
        spread = hi - lo
        if spread == 0:
            tags.append("All books same" if len(pool) >= 3 else "Exact Match")
            if "Exact Match" not in tags:
                tags.append("Exact Match")
        elif spread <= BOOK_CLUSTER_GAP:
            tags.append("Books tight")
    # combo on lock tags
    has_fd = any(t in ("FD Pattern", "FD 600") for t in tags)
    has_mgm = any(t.startswith("MGM end") and t[-2:] in ("25", "50", "75") for t in tags)
    if has_fd and has_mgm:
        tags.append("FD+MGM classic")
    return list(dict.fromkeys(tags)), lines, ends_by_book, best_book, best_price, price_map, primary_end


def build_lock_lab():
    """Today's MLB HRs matched to pregame Lock for learning."""
    hr_names, _fin, mlb_msg = fetch_mlb_hr_hitters()
    lock = st.session_state.get("pregame_lock") or load_pregame()
    matched, unmatched = [], []
    ending_counter, tag_counter, book_end_counter = Counter(), Counter(), Counter()
    book_appear = Counter()
    best_book_wins = Counter()   # longest price among ALL books in lock
    focus_best_wins = Counter()  # longest among MGM / DK / FD / Bet365
    focus_best_prices = []
    cross_counter = Counter()
    multi_tag_n = 0

    for hr in sorted(hr_names):
        entry, lock_name = None, None
        for pname, data in lock.items():
            if names_match(hr, pname):
                entry, lock_name = data, pname
                break
        if not entry:
            unmatched.append(hr)
            continue
        tags, lines, ends_by_book, best_book, best_price, price_map, primary_end = lock_player_summary(
            hr, entry, price_mode="close"
        )
        # 1 chip per HR for primary books (DK/FD/MGM best price) — no multi-book inflation
        if primary_end:
            bl, end, _p = primary_end
            if end is not None:
                ending_counter[int(end)] += 1
                book_end_counter[(bl, int(end))] += 1
                book_appear[bl] += 1
        # still track full book×ending for noise warnings (HardRock/Caesars)
        for bl, end in ends_by_book.items():
            if bl in ("HardRock", "Caesars"):
                book_end_counter[(bl, end)] += 1
        for t in tags:
            tag_counter[t] += 1
        if best_book:
            best_book_wins[best_book] += 1
        # among focus books only (MGM / DK / FD)
        focus = {b: p for b, p in price_map.items() if b in ("MGM", "DK", "FD", "HardRock", "Bet365")}
        if focus:
            fb = max(focus.items(), key=lambda x: american_to_decimal(x[1]))
            focus_best_wins[fb[0]] += 1
            focus_best_prices.append((hr, fb[0], fb[1]))
        core_tags = [t for t in tags if t.startswith(("MGM", "DK", "FD", "Exact", "Same"))]
        if len(core_tags) >= 2:
            multi_tag_n += 1
            cross_counter[tuple(sorted(core_tags))] += 1
        matched.append({
            "hr_name": hr, "lock_name": lock_name, "tags": tags, "lines": lines,
            "event": entry.get("event") or "", "core_n": len(core_tags),
            "tag_n": len(tags),
            "best_book": best_book, "best_price": best_price,
        })

    # most tags first → then most core tags → name
    matched_ranked = sorted(
        matched,
        key=lambda m: (-m.get("tag_n", 0), -m.get("core_n", 0), m["hr_name"]),
    )

    # insights text
    insights = []
    n = len(matched) or 1
    if tag_counter:
        top_tags = tag_counter.most_common(5)
        insights.append(
            "🔥 <b>Methods showing up most on HRs:</b> "
            + ", ".join(f"{t} ({c})" for t, c in top_tags)
        )
    if focus_best_wins:
        tot = sum(focus_best_wins.values()) or 1
        ranked = focus_best_wins.most_common()
        insights.append(
            "💰 <b>Best price (longest) among DK / FD / HardRock / MGM"
            + (" / Bet365" if any(b == "Bet365" for b, _ in ranked) else "")
            + " on HRs:</b> "
            + ", ".join(f"{b} won {c}/{tot} ({100*c/tot:.0f}%)" for b, c in ranked)
        )
    if best_book_wins:
        tot = sum(best_book_wins.values()) or 1
        ranked = best_book_wins.most_common(5)
        insights.append(
            "📚 <b>Longest price among every book in Lock:</b> "
            + ", ".join(f"{b} {c}/{tot}" for b, c in ranked)
        )
    # best book×ending combos among our classic endings
    classic = []
    for (bl, end), c in book_end_counter.most_common():
        if bl in ("MGM", "DK", "FD") and (end in MGM_ENDINGS or end == 10 or end in FD_ENDINGS):
            classic.append(((bl, end), c))
        if len(classic) >= 6:
            break
    if classic:
        insights.append(
            "🎯 <b>Classic endings on HRs:</b> "
            + ", ".join(f"{bl} {end:02d}×{c}" for (bl, end), c in classic)
        )
    if cross_counter:
        top_cross = cross_counter.most_common(4)
        insights.append(
            "✨ <b>Cross-methods (2+ tags on same HR):</b> "
            + ", ".join(" + ".join(tags) + f" ({c})" for tags, c in top_cross)
        )
        insights.append(
            f"🧩 <b>{multi_tag_n}/{len(matched)}</b> Lock-matched HRs had 2+ of our tags - "
            "those are the cross-method hits to study."
        )
    # watch-outs
    watch = []
    for (bl, end), c in book_end_counter.most_common(8):
        if bl in ("HardRock", "Caesars") and c >= 5:
            watch.append(f"{bl} ending {end:02d} showed {c}× (noisy book - don't treat as a core trick yet)")
    other_ends = [(e, c) for e, c in ending_counter.most_common() if e not in MGM_ENDINGS and e != 10 and e not in FD_ENDINGS and c >= 3]
    for e, c in other_ends[:3]:
        watch.append(f"Ending {e:02d} showed {c}× on HRs - not in our official list; watch if it keeps repeating")
    if not matched:
        insights.append("No HRs matched Lock yet - need pregame fetches so Lock is full.")
    if len(matched) < len(hr_names) * 0.5 and hr_names:
        watch.append("Many HRs missing from Lock - fetch earlier / more games next slate.")

    return {
        "hr_count": len(hr_names), "matched": matched_ranked, "unmatched": unmatched,
        "ending_counter": ending_counter, "tag_counter": tag_counter,
        "book_end_counter": book_end_counter, "book_appear": book_appear,
        "cross_counter": cross_counter, "multi_tag_n": multi_tag_n,
        "insights": insights, "watch": watch,
        "mlb_msg": mlb_msg, "lock_n": len(lock),
    }



def main():
    if "history_loaded" not in st.session_state:
        load_history()
        st.session_state["pregame_lock"] = load_pregame()
        st.session_state["history_loaded"] = True
    if "pending_page" not in st.session_state:
        st.session_state["pending_page"] = 0

    # New AZ calendar day → clear yesterday's game picks + stale odds
    _today = today_az()
    if st.session_state.get("app_day") != _today:
        st.session_state["app_day"] = _today
        for k in ("selected_games", "last_selected", "events", "odds", "previous_odds", "found_books", "last_fetch_time", "auto_once", "new_fetch"):
            st.session_state.pop(k, None)
        st.session_state.pop("prev_ev", None)

    if HAS_AUTOREFRESH:
        refresh_count = st_autorefresh(interval=REFRESH_MINUTES * 60 * 1000, key="odds_refresh")
    else:
        refresh_count = 0
    st.markdown('<p class="kicker">♛ Boss · HBIC · We Rolling</p>', unsafe_allow_html=True)
    st.markdown("<h1>Girl Magic Odds</h1>", unsafe_allow_html=True)
    st.markdown('<p class="tagline">Where odds intuition meets Petty precision. 0.5 HR Over only.</p>', unsafe_allow_html=True)
    lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
    st.markdown(f"""
    <div class="how-to" style="padding:10px 14px;font-size:0.78rem;line-height:1.35">
        <b>How to use</b> · Lock <b>{lock_n}</b> ·
        ① Load → ② Fetch → ③ Lock saves → ④ Tags → ⑤ Board (TAKE/WATCH/PASS) → ⑥ Grade → ⑦ Tracker / Lab
    </div>
    """, unsafe_allow_html=True)
    if "auto_grade_ran" not in st.session_state:
        st.session_state["auto_grade_ran"] = False
    if not st.session_state["auto_grade_ran"]:
        try:
            pending_n = sum(1 for r in load_results() if r.get("result") == "PENDING")
            if pending_n:
                with st.spinner(f"Auto-grading {pending_n} pending…"):
                    h, m, s, msg = auto_grade_pending()
                st.session_state["auto_grade_ran"] = True
                if h or m:
                    st.caption(f"⚡ Auto-grade: {h} HIT · {m} MISS · {s} still open")
            else:
                st.session_state["auto_grade_ran"] = True
        except Exception:
            st.session_state["auto_grade_ran"] = True
    render_whats_going_today()
    try:
        _ms, _bs, _es, _bkt, _num, _be = build_tracker_stats(load_results())
        learn_bits = []
        for name, s in sorted(_bs.items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
            t = s["hit"] + s["miss"]
            if t < 8:
                continue
            pct = 100 * s["hit"] / t
            learn_bits.append(f"<b>{name}</b> best book → {pct:.0f}% hit · {t} plays")
        for name, s in sorted(_ms.items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
            t = s["hit"] + s["miss"]
            if t < 10:
                continue
            pct = 100 * s["hit"] / t
            if pct >= 40:
                learn_bits.append(f"<b>{name}</b> → {pct:.0f}% hit · {t} plays")
            if len(learn_bits) >= 6:
                break
        if learn_bits:
            chips = "".join(f'<span class="trend-chip">{b}</span>' for b in learn_bits[:5])
            st.markdown(
                '<div class="trends-today" style="padding:10px 14px">'
                '<div class="trends-today-title" style="margin-bottom:8px">After we grade</div>'
                f'<div class="trends-chips">{chips}</div></div>',
                unsafe_allow_html=True,
            )
    except Exception:
        pass
    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add The Odds API key.")
        st.stop()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("① Load Games", type="primary"):
            raw = fetch_events_oddsapi(odds_key)
            st.session_state["events"] = filter_events_today(raw)
            st.session_state["events_raw_count"] = len(raw or [])
    with c2:
        if st.button("📋 Lineups"):
            names, msg = fetch_rotowire_lineups()
            st.session_state["lineup_names"] = names
            (st.success if names else st.warning)(msg)
    with c3:
        if st.button("⚡ Auto-grade MLB"):
            with st.spinner("MLB box scores…"):
                h, m, s, msg = auto_grade_pending()
            st.success(f"{h} HIT · {m} MISS · {s} still open - {msg}")
            st.rerun()
    with c4:
        auto_lineups = st.checkbox("Lineups on fetch", value=True)
    events = st.session_state.get("events", [])
    if not events:
        st.info("Click **Load Games** once.")
        st.stop()
    def _game_label(e):
        away = e.get("away_team") or "?"
        home = e.get("home_team") or "?"
        t = e.get("commence_time") or ""
        hhmm = ""
        if t:
            try:
                # show AZ time so it matches your day
                dt = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=-7)))
                hhmm = dt.strftime("%-I:%M %p")
            except Exception:
                try:
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=-7)))
                    hhmm = dt.strftime("%I:%M %p").lstrip("0")
                except Exception:
                    hhmm = ""
        base = f"{away} @ {home}"
        return f"{base} · {hhmm}" if hhmm else base

    # safety: re-filter if stale events from yesterday still in session
    events = filter_events_today(events)
    st.session_state["events"] = events

    options = {}
    for e in events:
        lab = _game_label(e)
        if lab in options:
            lab = f"{lab} · {str(e.get('id', ''))[:6]}"
        options[lab] = e["id"]

    raw_n = st.session_state.get("events_raw_count")
    st.markdown(
        f'<p class="games-hint">② Today · {len(options)} games'
        + (f" · feed had {raw_n}" if raw_n else "")
        + " · live games often have no HR props</p>",
        unsafe_allow_html=True,
    )

    default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
    c_sel, c_btn = st.columns([4, 1])
    with c_sel:
        chosen = st.multiselect(
            "Games",
            list(options.keys()),
            default=default_sel,
            label_visibility="collapsed",
        )
    with c_btn:
        if st.button("Clear games"):
            st.session_state["selected_games"] = []
            st.rerun()
    st.session_state["selected_games"] = chosen
    manual_fetch = st.button("③ Fetch now", type="primary")
    if "last_refresh_count" not in st.session_state:
        st.session_state["last_refresh_count"] = refresh_count
    auto_fetch = HAS_AUTOREFRESH and refresh_count != st.session_state["last_refresh_count"] and bool(chosen)
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
                if names: st.session_state["lineup_names"] = names
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
            st.success(f"Loaded {len(df)} props · {now_az()} AZ")
        else:
            dbg = st.session_state.get("fetch_debug") or {}
            raw = ", ".join(dbg.get("raw_books") or []) or "none"
            kept = ", ".join(dbg.get("kept_books") or []) or "none"
            st.warning(
                "No preferred-book 0.5 HR props after fetch. "
                "This is not always 'games live' — check debug below."
            )
            st.caption(
                f"API games OK: {dbg.get('http_ok', 0)} · fail: {dbg.get('http_fail', 0)} · "
                f"rows before filter: {dbg.get('row_count_pre_filter', 0)} · SGO: {dbg.get('sgo_rows', 0)} · "
                f"raw books: {raw} · kept: {kept}"
            )
    if st.session_state.get("last_fetch_time"):
        st.caption(f"Last fetch: {st.session_state['last_fetch_time']} AZ")
    found = st.session_state.get("found_books", [])
    dbg = st.session_state.get("fetch_debug") or {}
    if found or dbg.get("raw_books"):
        missing = [CORE_BOOKS[b] for b in CORE_BOOKS if b not in found]
        with st.expander("Feed debug", expanded=False):
            st.markdown(
                f'<div class="info-box"><b>Books kept:</b> {", ".join(found) or "none"}'
                + (f"<br><b>API raw keys:</b> {', '.join(dbg.get('raw_books') or [])}" if dbg.get("raw_books") else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            if missing:
                st.caption("Core missing from this feed: " + ", ".join(missing))
            if dbg.get("event_filter_wiped"):
                st.caption(f"Event label filter would have dropped {dbg['event_filter_wiped']} rows — kept unfiltered.")
    odds = st.session_state.get("odds", [])
    prev = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    prev_df = pd.DataFrame(prev) if prev else None
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, fallen, watch_board, coverage_board = (
        run_flags(df, prev_df, record_history=new_fetch, selected_events=selected_events)
        if not df.empty else ([], [], [], [], [])
    )
    if ev_board or watch_board:
        log_bet_this(ev_board, watch_board)
    method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats = build_tracker_stats(load_results())
    for item in ev_board:
        p, n, mname = best_method_rate_for_player(item["methods"], method_stats)
        item["method_p"], item["method_n"], item["method_rate_name"] = p, n, mname
        if p is not None and n >= EV_MIN_N:
            lean, ev = simple_ev_lean(p, item["best_price"])
            item["ev_lean"] = lean
            item["ev_value"] = ev
        else:
            item["ev_lean"] = item["ev_value"] = None
    takes_all = [e for e in ev_board if e.get("is_bet")]
    passes_all = [e for e in ev_board if not e.get("is_bet")]
    take_n = len(takes_all)  # already post tighten_board
    pass_n = len(passes_all)
    multi_names = {e["player"] for e in ev_board}
    watch_only = [
        w for w in watch_board
        if w["player"] not in multi_names and (w.get("method_count") or 0) < METHODS_MIN
    ]
    watch_n = len(watch_only)
    cov_names = multi_names | {w["player"] for w in watch_only}
    coverage_only = [
        c for c in coverage_board
        if c["player"] not in cov_names
    ]
    coverage_only = sorted(
        coverage_only,
        key=lambda x: (-len(x.get("methods") or []), -x.get("score", 0), x.get("player") or ""),
    )
    coverage_n = len(coverage_only)
    dk_n = len(aggregate_by_player([r for r in results if r.get("type") == "dk"]))
    fd_n = len(aggregate_by_player([r for r in results if r.get("type") == "fd"]))
    mgm_n = len(aggregate_by_player([r for r in results if r.get("type") == "mgm"]))
    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box"><div class="petty-num">{take_n}</div><div class="petty-label">🟢 TAKE IT</div></div>
        <div class="petty-box"><div class="petty-num">{watch_n}</div><div class="petty-label">👀 WATCH</div></div>
        <div class="petty-box"><div class="petty-num">{pass_n}</div><div class="petty-label">⚪ PASS</div></div>
        <div class="petty-box"><div class="petty-num">{coverage_n}</div><div class="petty-label">👁️ COVERAGE</div></div>
        <div class="petty-box"><div class="petty-num">{dk_n}</div><div class="petty-label">🎯 DK</div></div>
        <div class="petty-box"><div class="petty-num">{fd_n}</div><div class="petty-label">💙 FD</div></div>
        <div class="petty-box"><div class="petty-num">{mgm_n}</div><div class="petty-label">🎰 MGM</div></div>
    </div>
    """, unsafe_allow_html=True)
    MAIN_TABS = ["Board", "Shop", "Methods", "Lines", "Grade", "Code"]
    main = st.radio(
        "Section",
        MAIN_TABS,
        horizontal=True,
        label_visibility="collapsed",
        key="main_nav",
    )
    sub = None
    if main == "Methods":
        sub = st.radio("Methods", ["DK", "MGM", "FD", "Exact", "Names", "Signals"], horizontal=True, label_visibility="collapsed", key="sub_methods")
    elif main == "Lines":
        sub = st.radio("Lines", ["Moves", "Trends", "Late", "Lock", "Search"], horizontal=True, label_visibility="collapsed", key="sub_lines")
    elif main == "Grade":
        sub = st.radio("Grade", ["Lock Lab", "Tracker", "Results", "Backtest"], horizontal=True, label_visibility="collapsed", key="sub_grade")
    page = f"{main}:{sub or ''}"
    if page == "Board:":
        st.markdown("### The Board")
        st.caption(
            "Green is TAKE IT. PASS has two premium cores but is missing priority or edge. "
            "WATCH is one premium method — we track it to learn."
        )

        def _render_board_card(item, label, cls):
            tags = render_method_tags(item.get("methods") or [])
            meter = make_meter(item.get("bars", 1), item.get("level", "low"))
            ev_s = ""
            if item.get("ev_lean") is True:
                ev_s = f" · +EV lean ({item.get('method_rate_name')})"
            team = item.get("team") or ""
            game = item.get("event") or ""
            meta = " · ".join([x for x in (team, game) if x])
            pack = item.get("median")
            pack_s = f" · pack {format_odds(pack)}" if pack is not None else ""
            st.markdown(
                f'<div class="card {cls}">'
                f'<div class="card-kicker">{label}</div>'
                f'<span class="score-pill">{item.get("score", 0)}</span>'
                f'<div class="card-name">{item["player"]}</div>'
                f'<div class="card-meta">{meta}</div>'
                f'{meter}'
                f'<div class="card-line"><b>Best {format_odds(item.get("best_price"))}</b> on {book_label(item.get("best_book"))}{pack_s}</div>'
                f'<div class="card-line">Edge <b>{int(item.get("edge") or 0)}</b> · {item.get("method_count", 0)} premium</div>'
                f'<div style="margin-top:6px">{tags}</div>'
                f'<div class="card-foot">{item.get("why", "")}{ev_s}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        takes = [e for e in ev_board if e.get("is_bet")]
        passes = [e for e in ev_board if not e.get("is_bet")]
        # WATCH = strictly under 2 core methods (never dump capped PASS into WATCH)
        multi_names = {e["player"] for e in ev_board}  # anyone with 2+ core already classified
        watches = [
            w for w in watch_board
            if w["player"] not in multi_names and (w.get("method_count") or 0) < METHODS_MIN
        ]
        watches = sorted(watches, key=lambda x: (-x.get("method_count", 0), -x.get("score", 0)))

        if not takes and not passes and not watches and not coverage_only:
            st.info("Fetch while pregame — board fills when methods fire.")
        else:
            if takes:
                st.markdown("#### Take it")
                # Away @ Home → commence_time from loaded events (order board by tip time)
                commence_by_event = {}
                for e in st.session_state.get("events", []):
                    key = f"{e.get('away_team')} @ {e.get('home_team')}"
                    t = e.get("commence_time") or ""
                    if t:
                        commence_by_event[key] = t

                by_game = defaultdict(list)
                for item in takes:
                    by_game[item.get("event") or "Game"].append(item)

                def _resolve_commence(game_name):
                    t = commence_by_event.get(game_name)
                    if t:
                        return t
                    for k, v in commence_by_event.items():
                        if k in game_name or game_name in k:
                            return v
                    return None

                def _game_sort_key(game_name):
                    t = _resolve_commence(game_name)
                    if not t:
                        return (1, 9e18, game_name)  # unknown → bottom
                    try:
                        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                        return (0, dt.timestamp(), game_name)
                    except Exception:
                        return (1, 9e18, game_name)

                def _fmt_game_header(game_name):
                    t = _resolve_commence(game_name)
                    if not t:
                        return game_name
                    try:
                        dt = datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(
                            timezone(timedelta(hours=-7))
                        )
                        try:
                            hhmm = dt.strftime("%-I:%M %p")
                        except Exception:
                            hhmm = dt.strftime("%I:%M %p").lstrip("0")
                        return f"{game_name} · {hhmm} AZ"
                    except Exception:
                        return game_name

                for game in sorted(by_game.keys(), key=_game_sort_key):
                    items = sorted(by_game[game], key=lambda x: -x.get("score", 0))
                    st.markdown(f"**{_fmt_game_header(game)}**")
                    cols = st.columns(2)
                    for idx, item in enumerate(items):
                        with cols[idx % 2]:
                            _render_board_card(item, "TAKE IT", "bet")
            else:
                st.markdown("#### Take it")
                st.caption("None right now — need a heavier method stack (see Code).")

            if passes:
                st.markdown("#### Pass")
                cols = st.columns(2)
                for idx, item in enumerate(passes):
                    with cols[idx % 2]:
                        _render_board_card(item, "PASS", "skip")

            st.markdown("#### Watch")
            if not watches:
                st.caption("None with exactly 1 premium method right now.")
            else:
                cols = st.columns(2)
                for idx, item in enumerate(watches[:40]):
                    with cols[idx % 2]:
                        _render_board_card(item, "WATCH", "watch-card")

            st.markdown("#### 👁️ COVERAGE · support tags only (not a bet)")
            st.caption(
                "75s · 00s · Stayed alone · Last one left · Exact / tight — "
                "support tags only. Never upgrades to TAKE IT without priority + edge."
            )
            if not coverage_only:
                st.caption("No support-only names right now.")
            else:
                cols = st.columns(2)
                for idx, item in enumerate(coverage_only[:40]):
                    with cols[idx % 2]:
                        _render_board_card(item, "COVERAGE", "watch-card")

    if page == "Shop:":
        render_shop_tab(df)
    if page == "Methods:DK":
        show_player_cards("dk", "🎯 DraftKings", "One card per player · DK 10 + FD-style", results)
    if page == "Methods:MGM":
        show_player_cards("mgm", "🎰 BetMGM", "Pairs / groups of 3 · classic endings · Exact 2-3 · all on one card", results)
    if page == "Methods:FD":
        show_player_cards("fd", "💙 FanDuel", f"≥+{FD_MIN} pattern or +600 · needs DK/MGM · one card per player", results)
    if page == "Methods:Exact":
        show_player_cards("match", "🤝 Exact (all books)", "Same price across books · one card per player", results)
    if page == "Methods:Names":
        st.markdown('<div class="queen-banner">💅 Name Magic</div>', unsafe_allow_html=True)
        st.caption(
            f"Same / cross initials · same first or last name · "
            f"both need {NAME_METHODS_MIN}+ core methods + a strong tag · different teams · max {NAME_MAX_PAIRS} pairs each"
        )
        show_player_cards("same_init", "💅 Same Initials", "Same first+last initial (e.g. MM) · different teams", results)
        show_player_cards("cross", "🔄 Cross Initials", "One last initial = other first initial · different teams", results)
        show_player_cards("last", "👩‍👧 Same Last Name", "Exact last name · different teams", results)
        show_player_cards("first", "👯 Same First Name", "Exact first name · different teams", results)
    if page == "Methods:Signals":
        show_player_cards("signal", "📈 Signals", "Multi-book method · one card per player", results)
    if page == "Lines:Moves":
        st.markdown('<div class="queen-banner">⏳ Moves (500+)</div>', unsafe_allow_html=True)
        st.caption("Fetch-to-fetch + 🔒 open → now/close from Lock.")
        for move_dir, title in (("up", "🔴 UP"), ("down", "🟢 DOWN")):
            st.markdown(f"#### {title}")
            items = aggregate_by_player([r for r in results if r["type"] == "hist" and r.get("move_dir") == move_dir])
            cols = st.columns(2)
            for idx, r in enumerate(items[:20]):
                with cols[idx % 2]:
                    st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
            if not items: st.info("None")
    if page == "Lines:Trends":
        st.markdown('<div class="queen-banner">📉 Trends</div>', unsafe_allow_html=True)
        good = sorted([r for r in results if r["type"] == "trend" and r.get("trend_kind") == "good"], key=lambda r: r.get("gap", 0), reverse=True)
        fade = [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "fade"]
        st.markdown("#### 💚 FD under MGM")
        for r in aggregate_by_player(good)[:15]:
            st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
        st.markdown("#### 🔴 Fade")
        for r in aggregate_by_player(fade)[:15]:
            st.markdown(f'<div class="card"><b>{r["label"]}</b><br>{r["reason"]}</div>', unsafe_allow_html=True)
    if page == "Lines:Late":
        show_player_cards(
            "late",
            "👻 Late / Missing books",
            "Gone from DK / FD / MGM (or HardRock) vs last fetch or Lock — not a RotoWire list",
            results,
        )
    if page == "Lines:Lock":
        st.markdown('<div class="queen-banner">🔒 Pregame Lock · open / now / close</div>', unsafe_allow_html=True)
        st.caption(
            "Open = first pull (never changes) · Now = latest pregame fetch · "
            "Close = frozen when the book drops off the feed (often at first pitch)."
        )
        lock = st.session_state.get("pregame_lock") or load_pregame()
        if not lock:
            st.info("Fetch pregame to build lock.")
        else:
            q = st.text_input("Filter", key="lock_q")
            show_moved = st.checkbox("Only show open → now/close movers", value=False, key="lock_movers")
            cols = st.columns(2)
            i = 0
            today = today_az()
            for player, entry in sorted(lock.items()):
                if entry.get("date") and entry.get("date") != today:
                    continue
                if q and q.lower() not in player.lower():
                    continue
                lines = []
                moved = False
                for b, info in sorted((entry.get("books") or {}).items()):
                    slot = _book_slot_normalize(info)
                    first = slot.get("first_price")
                    latest = slot.get("latest_price")
                    close = slot.get("close_price")
                    if first is None and latest is None:
                        continue
                    t0 = format_az_from_iso(slot.get("first_at"))
                    tL = format_az_from_iso(slot.get("latest_at"))
                    tC = format_az_from_iso(slot.get("close_at"))
                    bl = book_label(b)
                    bit = f"<b>{bl}</b> open {format_odds(first)}" + (f" <small>({t0})</small>" if t0 else "")
                    if latest is not None and latest != first:
                        moved = True
                        d = int(latest) - int(first)
                        bit += f"<br>→ now {format_odds(latest)}" + (f" <small>({tL})</small>" if tL else "") + f" ({d:+d})"
                    if close is not None:
                        if close != first:
                            moved = True
                        d2 = int(close) - int(first)
                        bit += f"<br>→ close {format_odds(close)}" + (f" <small>({tC})</small>" if tC else "") + f" ({d2:+d})"
                    lines.append(bit)
                if not lines:
                    continue
                if show_moved and not moved:
                    continue
                ev = entry.get("event") or ""
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="card"><b>{player}</b>'
                        + (f"<br><small>{ev}</small>" if ev else "")
                        + "<br>" + "<br>".join(lines)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                i += 1
            if i == 0:
                st.info("No lock rows matched.")

    if page == "Lines:Search":
        st.markdown('<div class="queen-banner">🔍 Search · by book / price / ending</div>', unsafe_allow_html=True)
        st.caption(
            f"Pregame Lock only · 0.5 HR Over · prices above +{MAX_HR_AMERICAN} are dropped as junk. "
            "Sort “best odds first” shows the longest numbers on top — not the most likely HRs."
        )
        lock = st.session_state.get("pregame_lock") or load_pregame()
        if not lock:
            st.info("Fetch pregame so Lock has prices, then search here.")
        else:
            BOOK_OPTS = [
                ("All", None),
                ("HardRock", "hardrock"),
                ("BetMGM", "betmgm"),
                ("DraftKings", "draftkings"),
                ("FanDuel", "fanduel"),
                ("Caesars", "caesars"),
            ]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                book_label_pick = st.selectbox(
                    "Book",
                    [x[0] for x in BOOK_OPTS],
                    index=1,
                    key="search_book",
                )
            with c2:
                sort_pick = st.selectbox(
                    "Sort",
                    ["Best odds first (highest)", "Lowest first", "Name A–Z"],
                    key="search_sort",
                )
            with c3:
                ending_pick = st.selectbox(
                    "Ending",
                    ["Any", "00", "10", "25", "50", "75", "20", "30", "60", "70", "90"],
                    key="search_end",
                )
            with c4:
                min_price = st.number_input("Min price (+)", min_value=0, value=0, step=50, key="search_min")
            name_q = st.text_input("Player name contains", key="search_name")

            book_key = dict(BOOK_OPTS).get(book_label_pick)

            rows = []
            for player, entry in lock.items():
                if is_blocked_player(player):
                    continue
                if name_q and name_q.lower() not in player.lower():
                    continue
                event = entry.get("event") or ""
                for b, info in (entry.get("books") or {}).items():
                    slot = _book_slot_normalize(info)
                    price = slot.get("close_price")
                    if price is None:
                        price = slot.get("latest_price")
                    if price is None:
                        price = slot.get("first_price")
                    if price is None:
                        continue
                    bl = str(b).lower()
                    if book_key:
                        if book_key == "hardrock" and "hardrock" not in bl:
                            continue
                        if book_key == "betmgm" and "betmgm" not in bl and bl != "mgm":
                            continue
                        if book_key == "draftkings" and "draftkings" not in bl:
                            continue
                        if book_key == "fanduel" and "fanduel" not in bl:
                            continue
                        if book_key == "caesars" and "caesars" not in bl and "williamhill" not in bl:
                            continue
                    end = info.get("ending")
                    if end is None:
                        end = last_two(price)
                    if ending_pick != "Any":
                        if end is None or int(end) != int(ending_pick):
                            continue
                    if min_price and abs(int(price)) < int(min_price):
                        continue
                    if int(price) > MAX_HR_AMERICAN:
                        continue
                    rows.append({
                        "player": player,
                        "book": b,
                        "price": int(price),
                        "ending": end,
                        "event": event,
                    })

            # Book = All → one card per player (all books under them)
            # Book = specific → one row per matching book line
            if book_key is None:
                by_player = {}
                for r in rows:
                    p = r["player"]
                    if p not in by_player:
                        by_player[p] = {"event": r.get("event") or "", "lines": [], "best": r["price"]}
                    by_player[p]["lines"].append(r)
                    if r["price"] > by_player[p]["best"]:
                        by_player[p]["best"] = r["price"]
                cards = []
                for p, info in by_player.items():
                    lines_sorted = sorted(info["lines"], key=lambda x: -x["price"])
                    line_bits = []
                    for r in lines_sorted:
                        end = r.get("ending")
                        end_s = f" ends {int(end):02d}" if end is not None else ""
                        line_bits.append(f"{book_label(r['book'])} <b>{format_odds(r['price'])}</b>{end_s}")
                    cards.append({
                        "player": p,
                        "event": info["event"],
                        "best": info["best"],
                        "html_lines": " · ".join(line_bits),
                    })
                if sort_pick.startswith("Best"):
                    cards.sort(key=lambda c: c["best"], reverse=True)
                elif sort_pick.startswith("Lowest"):
                    cards.sort(key=lambda c: c["best"])
                else:
                    cards.sort(key=lambda c: c["player"])
                st.markdown(f"**{len(cards)}** player(s) · {len(rows)} book lines")
                if not cards:
                    st.info("Nothing matched — loosen filters.")
                else:
                    cols = st.columns(2)
                    for idx, c in enumerate(cards[:120]):
                        ev = c.get("event") or ""
                        with cols[idx % 2]:
                            st.markdown(
                                f'<div class="card"><b>{c["player"]}</b>'
                                + (f"<br><small>{ev}</small>" if ev else "")
                                + f"<br>{c['html_lines']}</div>",
                                unsafe_allow_html=True,
                            )
                    if len(cards) > 120:
                        st.caption(f"Showing first 120 of {len(cards)} players")
            else:
                if sort_pick.startswith("Best"):
                    rows.sort(key=lambda r: r["price"], reverse=True)
                elif sort_pick.startswith("Lowest"):
                    rows.sort(key=lambda r: r["price"])
                else:
                    rows.sort(key=lambda r: r["player"])
                st.markdown(f"**{len(rows)}** result(s)")
                if not rows:
                    st.info("Nothing matched — loosen filters.")
                else:
                    cols = st.columns(2)
                    for idx, r in enumerate(rows[:150]):
                        end = r.get("ending")
                        end_s = f" · ends {int(end):02d}" if end is not None else ""
                        ev = r.get("event") or ""
                        with cols[idx % 2]:
                            st.markdown(
                                f'<div class="card"><b>{r["player"]}</b> · {book_label(r["book"])} '
                                f'<b>{format_odds(r["price"])}</b>{end_s}'
                                + (f"<br><small>{ev}</small>" if ev else "")
                                + "</div>",
                                unsafe_allow_html=True,
                            )
                    if len(rows) > 150:
                        st.caption(f"Showing first 150 of {len(rows)}")

    if page == "Grade:Lock Lab":
        st.markdown('<div class="queen-banner">🧠 Lock Lab · Who went & what Lock had</div>', unsafe_allow_html=True)
        st.caption("Today's homers matched to what we locked before first pitch.")
        lab = build_lock_lab()
        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{lab["hr_count"]}</div><div class="petty-label">MLB HR</div></div>
            <div class="petty-box"><div class="petty-num">{len(lab["matched"])}</div><div class="petty-label">In Lock</div></div>
            <div class="petty-box"><div class="petty-num">{len(lab["unmatched"])}</div><div class="petty-label">Not in Lock</div></div>
            <div class="petty-box"><div class="petty-num">{lab["lock_n"]}</div><div class="petty-label">Lock size</div></div>
        </div>
        """, unsafe_allow_html=True)
        if lab.get("mlb_msg"):
            st.caption(lab["mlb_msg"])

        st.markdown("#### What stood out today")
        if lab.get("insights"):
            for line in lab["insights"]:
                st.markdown(f'<div class="info-box">{line}</div>', unsafe_allow_html=True)
        if lab.get("watch"):
            st.markdown("#### Be careful with")
            for line in lab["watch"]:
                st.markdown(f'<div class="warning-box">{line}</div>', unsafe_allow_html=True)
        if not lab.get("insights") and not lab.get("watch"):
            st.info("Insights appear after HRs match Lock.")

        st.markdown("#### Endings on today's HRs")
        chips = []
        for (bl, end), cnt in sorted(lab["book_end_counter"].items(), key=lambda x: -x[1])[:14]:
            hot = end in (0, 25, 50, 75, 10) or cnt >= 2
            chips.append(
                f'<span class="trend-chip {"hot" if hot else ""}">{bl} {end:02d}: '
                f'<span class="chip-count">{cnt}</span></span>'
            )
        st.markdown("".join(chips) if chips else "_(No Lock↔HR matches yet)_", unsafe_allow_html=True)

        st.markdown("#### Our tags that showed up")
        tag_chips = []
        for tag, cnt in sorted(lab["tag_counter"].items(), key=lambda x: -x[1])[:16]:
            tag_chips.append(
                f'<div class="rate-chip"><div class="rate-pct">{cnt}</div>'
                f'<div class="rate-name">{tag}</div></div>'
            )
        st.markdown("".join(tag_chips) if tag_chips else "_(None)_", unsafe_allow_html=True)

        st.markdown("#### Who went · most tags first")
        if not lab["matched"]:
            st.info("No HR names matched Lock. Fetch pregame more so Lock fills.")
        else:
            # one column: st.columns(2) on mobile stacks left then right and wrecks sort order
            for m in lab["matched"][:40]:
                tags_html = render_method_tags(m["tags"]) if m["tags"] else "<i>no standard tags</i>"
                prices = " · ".join(m["lines"][:6])
                ev = m["event"]
                best = ""
                if m.get("best_book") and m.get("best_price") is not None:
                    best = f"<br><b>Best price:</b> {m['best_book']} {format_odds(m['best_price'])}"
                tn = m.get("tag_n", len(m.get("tags") or []))
                tag_line = f"{tn} tag" + ("s" if tn != 1 else "")
                st.markdown(
                    f'<div class="card"><b>{m["hr_name"]}</b> · <span class="score-pill">{tag_line}</span>'
                    + (f"<br><small>{ev}</small>" if ev else "")
                    + f"<br>{prices}{best}<br>{tags_html}</div>",
                    unsafe_allow_html=True,
                )
        if lab["unmatched"]:
            with st.expander(f"Not in Lock ({len(lab['unmatched'])})"):
                st.write(", ".join(lab["unmatched"][:50]))

    if page == "Grade:Tracker":
        st.markdown('<div class="queen-banner">📡 Tracker</div>', unsafe_allow_html=True)
        st.caption(
            "What has been hitting after we grade it. "
            f"Buckets with n &lt; {TRACKER_MIN_N} are hidden. "
            "Green border = beats overall TAKE IT %."
        )
        baseline, baseline_n = take_it_baseline_rate(load_results())
        if baseline is not None:
            st.markdown(
                f'<div class="info-box"><b>Baseline TAKE IT:</b> {baseline:.0f}% '
                f'(n={baseline_n}). Signal methods above this get a green border.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="info-box">No graded TAKE IT yet — baseline appears after HIT/MISS.</div>',
                unsafe_allow_html=True,
            )

        def chips_from_stats(stats, min_n=TRACKER_MIN_N, compare_baseline=False):
            out = []
            for name, s in sorted(
                stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                if t < min_n:
                    continue
                pct = 100 * s["hit"] / t
                beat = (
                    compare_baseline
                    and baseline is not None
                    and pct > baseline + 0.5
                )
                cls = "rate-chip beat" if beat else "rate-chip"
                beat_html = '<div class="rate-beat">▲ beats TAKE IT</div>' if beat else ""
                out.append(
                    f'<div class="{cls}">'
                    f'<div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{name}</div>'
                    f'<div class="rate-n">{s["hit"]} hit · {s["miss"]} miss · {t} plays</div>'
                    f"{beat_html}</div>"
                )
            return out

        # Signal method = Girl Magic tags (why we cared)
        st.markdown("#### By signal method")
        st.caption("Tags on the pick (MGM 25, FD Pattern, Multi-book method, Exact, …) — not which book you bet.")
        chips = chips_from_stats(method_stats, compare_baseline=True)
        st.markdown(
            "".join(chips) if chips else f"_(Need graded plays with n ≥ {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        # Best book = where the logged best_price lived
        st.markdown("#### By best book we took")
        st.caption("Which sportsbook held the best price on the graded row — separate from the signal tag.")
        chips = chips_from_stats(book_stats, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else f"_(Need n ≥ {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        st.markdown("#### By ending on best price")
        st.caption("Last two digits of the best_price we logged (not MGM-only unless that was best).")
        chips = chips_from_stats(ending_stats, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else f"_(Need n ≥ {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        st.markdown("#### By price bucket")
        st.caption("How long the number was when we logged it. Tells you if +500s cash more than +800s.")
        chips = chips_from_stats(bucket_stats, min_n=15, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else "_(Need more graded prices)_",
            unsafe_allow_html=True,
        )

        st.markdown("#### By exact number")
        st.caption("The raw American we logged as best. Hidden under 15 plays.")
        chips = chips_from_stats(number_stats, min_n=15, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else "_(Need repeats of the same number)_",
            unsafe_allow_html=True,
        )

        st.markdown("#### By book × ending")
        st.caption("Every posted book on the row when we logged it — DK 10, MGM 25, HR 00, etc.")
        chips = chips_from_stats(book_end_stats, min_n=15, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else "_(Fills as new logs store every book price)_",
            unsafe_allow_html=True,
        )
    if page == "Grade:Results":
        st.markdown('<div class="queen-banner">📊 Results</div>', unsafe_allow_html=True)
        if st.button("⚡ Run auto-grade now", type="primary"):
            with st.spinner("MLB…"):
                h, m, s, msg = auto_grade_pending()
            st.success(f"{h} HIT · {m} MISS · {s} open - {msg}")
            st.rerun()
        rows = load_results()
        n_all = len(rows)
        n_pending_all = sum(1 for r in rows if r.get("result") == "PENDING")
        n_today = sum(1 for r in rows if r.get("date") == today_az())
        src = st.session_state.get("_results_source", "?")
        gh_st = st.session_state.get("_results_gh_status", "unconfigured")
        gh_save = st.session_state.get("_results_gh_save", "—")
        lock_src = st.session_state.get("_pregame_source", "?")
        lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
        hist_src = st.session_state.get("_history_source", "?")
        hist_save = st.session_state.get("_history_gh_save", "—")
        secrets_ok = "yes" if _gh_configured() else "NO — add GITHUB_TOKEN + GITHUB_REPO"
        st.caption(
            f"{n_all} logged · {n_pending_all} waiting · {n_today} today · "
            f"source={src} · GH load={gh_st} · GH save={gh_save} · "
            f"lock={lock_n} ({lock_src}) · hist={hist_src}/{hist_save} · secrets={secrets_ok}"
        )
        if not _gh_configured():
            st.warning(
                "GitHub secrets missing — Results, Lock, and movement history wipe on reboot. "
                "Add GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH in Streamlit Secrets."
            )
        elif n_all == 0:
            st.info(
                "No rows yet. Fetch **pregame** so TAKE IT / WATCH log here, then auto-grade after games. "
                "If you had data before, check that girl_magic_results.json exists in your GitHub repo."
            )
        today_only = st.checkbox("Today only", value=False)
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
        page = min(st.session_state.get("pending_page", 0), max(0, (total_p - 1) // PENDING_PAGE) if total_p else 0)
        st.session_state["pending_page"] = page
        start, end = page * PENDING_PAGE, min((page + 1) * PENDING_PAGE, total_p)
        st.caption(f"Manual leftover {start+1 if total_p else 0}-{end} of {total_p}")
        n1, n2, _ = st.columns([1, 1, 4])
        with n1:
            if st.button("← Prev", disabled=page <= 0):
                st.session_state["pending_page"] = page - 1
                st.rerun()
        with n2:
            if st.button("Next →", disabled=end >= total_p):
                st.session_state["pending_page"] = page + 1
                st.rerun()
        for r in pending[start:end]:
            rid = r["id"]
            endg = r.get("ending")
            end_s = f" ends {int(endg):02d}" if endg is not None else ""
            st.markdown(f"**{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}{end_s}")
            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("🟢 HIT", key=f"hit_{rid}"):
                    set_result_status(rid, "HIT")
                    st.rerun()
            with c2:
                if st.button("🔴 MISS", key=f"miss_{rid}"):
                    set_result_status(rid, "MISS")
                    st.rerun()
        st.markdown("#### Graded - ↩️ Undo")
        for r in reversed(done[-40:]):
            rid = r["id"]
            icon = "🟢" if r["result"] == "HIT" else "🔴"
            auto = " · auto" if r.get("graded_by") == "mlb_auto" else ""
            endg = r.get("ending")
            end_s = f" ends {int(endg):02d}" if endg is not None else ""
            st.markdown(f"{icon} **{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}{end_s}{auto}")
            if st.button("↩️ Undo", key=f"undo_{rid}"):
                undo_result(rid, r.get("source"))
                st.rerun()
    if page == "Grade:Backtest":
        st.markdown('<div class="queen-banner">🧪 Backtest · TAKE IT vs WATCH</div>', unsafe_allow_html=True)
        st.caption("How our picks have been grading. Needs a few days of HIT/MISS before the % means much.")
        rows_bt = load_results()
        overall, daily, method_by_src, n_graded = build_backtest_stats(rows_bt, days=14)

        def fmt_rate(h, m, t, pct):
            if t == 0 or pct is None:
                return "-"
            return f"{pct:.0f}% · {h}H / {m}M · n={t}"

        ti = overall.get("take_it", (0, 0, 0, None))
        wa = overall.get("watch", (0, 0, 0, None))
        ti_pct = f"{ti[3]:.0f}" if ti[3] is not None else "-"
        wa_pct = f"{wa[3]:.0f}" if wa[3] is not None else "-"
        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{ti_pct}</div><div class="petty-label">🟢 TAKE IT %</div></div>
            <div class="petty-box"><div class="petty-num">{ti[2]}</div><div class="petty-label">TAKE n</div></div>
            <div class="petty-box"><div class="petty-num">{wa_pct}</div><div class="petty-label">👀 WATCH %</div></div>
            <div class="petty-box"><div class="petty-num">{wa[2]}</div><div class="petty-label">WATCH n</div></div>
            <div class="petty-box"><div class="petty-num">{n_graded}</div><div class="petty-label">Graded 14d</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Last 14 days")
        if not daily:
            st.info("No graded TAKE IT / WATCH rows yet. Fetch → let WATCH log → auto-grade after games.")
        else:
            for day in daily:
                ti_s = fmt_rate(*day["take_it"])
                wa_s = fmt_rate(*day["watch"])
                st.markdown(
                    f'<div class="card"><b>{day["date"]}</b><br>'
                    f'🟢 TAKE IT: {ti_s}<br>👀 WATCH: {wa_s}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("#### Methods on TAKE IT (graded)")
        chips_ti = []
        for name, s in sorted(method_by_src["take_it"].items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
            t = s["hit"] + s["miss"]
            if t < 5:
                continue
            pct = 100 * s["hit"] / t
            chips_ti.append(
                f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                f'<div class="rate-name">{name}</div>'
                f'<div class="rate-n">{s["hit"]}H · {s["miss"]}M · n={t}</div></div>'
            )
        st.markdown("".join(chips_ti) if chips_ti else "_(Need more graded TAKE IT)_", unsafe_allow_html=True)

        st.markdown("#### Methods on WATCH (graded)")
        chips_wa = []
        for name, s in sorted(method_by_src["watch"].items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
            t = s["hit"] + s["miss"]
            if t < 5:
                continue
            pct = 100 * s["hit"] / t
            chips_wa.append(
                f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                f'<div class="rate-name">{name}</div>'
                f'<div class="rate-n">{s["hit"]}H · {s["miss"]}M · n={t}</div></div>'
            )
        st.markdown("".join(chips_wa) if chips_wa else "_(Need more graded WATCH)_", unsafe_allow_html=True)

        st.caption("Coverage = share of MLB HRs that were on WATCH/TAKE that day (see banner). Aim: TAKE IT hit rate > WATCH > random.")

    if page == "Code:":
        st.markdown('<div class="queen-banner">📖 The Code</div>', unsafe_allow_html=True)
        st.caption("Girl Magic cheat sheet — short blocks, real examples.")
        st.markdown(
            '<div class="glossary-block">'
            "<h4>🟢 The Board (start here)</h4>"
            "We only care about <b>0.5 HR</b> — one home run, Over.<br><br>"
            "<b>🟢 TAKE IT</b> — green light (re-eval Tracker 8/25 · baseline ~11%).<br>"
            "• <b>Priority (need ≥1):</b> Match/MGM <b>25</b> · FD Pattern · FD 600 · Multi-book method · FD+MGM classic · MGM Exact<br>"
            "• <b>Premium core (need ≥2):</b> priority tags + DK 10 + Multi-book Shorten + Match/MGM 50<br>"
            "• <b>Edge ≥ 80</b> (or ≥40 with 3+ core + priority + 2 families)<br>"
            "• Short list on purpose (caps per team / game)<br><br>"
            "<b>⚪ PASS</b> — 2+ premium but missing priority and/or edge.<br><br>"
            "<b>👀 WATCH</b> — 1 premium method. We track these to learn.<br>"
            "<b>Support only (never unlock TAKE IT alone):</b> Match/MGM 75 · 00s · "
            "Stayed in the group · Last one left · Books tight · Exact Match<br>"
            "WATCH + TAKE IT feed Results → auto-grade → Tracker / Backtest."
            "</div>"

            '<div class="glossary-block">'
            "<h4>Score · Edge · +EV lean</h4>"
            "<b>Score (0–100)</b> — strength meter. More tricks + better price → higher. <b>💎 DK+MGM+FD</b> (all three) adds a score bonus — ranks higher, does <b>not</b> change TAKE IT rules.<br>"
            "<b>Edge</b> — best price minus the middle of the books. Bigger = longer number vs consensus. "
            "<b>TAKE IT needs edge ≥ 80</b> after the tracker showed 8% TAKE IT vs 9% WATCH at the old 60 floor.<br>"
            "<b>+EV lean</b> — “this tag has been hitting enough in our grades that the price is okay.” "
            "Not Kelly. Not bankroll advice."
            "</div>"

            '<div class="glossary-block">'
            "<h4>🎰 BetMGM (same team only)</h4>"
            "We track endings <b>00 · 25 · 50 · 75</b>. <b>25</b> is the unlock ending (8/25 tracker); 50 is core only.<br><br>"
            "<b>Pair</b> — exactly <b>2 teammates</b> with the same ending.<br>"
            "<b>Group of 3</b> — exactly <b>3 teammates</b> same ending. Not 4+.<br>"
            "<b>Match/MGM 25</b> — <b>PRIORITY</b> (~15% overall · ~18% on TAKE IT).<br>"
            "<b>MGM Exact</b> — <b>PRIORITY</b> (~14%). Same MGM price on 2–3 teammates.<br>"
            "<b>Match/MGM 50</b> — premium core, not priority alone (below baseline in 8/25 sample).<br>"
            "<b>Match/MGM 75 · 00 · Stayed · Last one left</b> — "
            "<b>support only</b>. Still shown on tabs.<br><br>"
            "A lone +525 with no teammate partner is <b>not</b> an MGM method tag."
            "</div>"

            '<div class="glossary-block">'
            "<h4>🎯 DraftKings</h4>"
            "<b>DK 10</b> — ends in 10. <b>Premium core</b>, not priority alone (weak ~6% when forced onto TAKE IT; still fine as a second tag).<br>"
            "<b>DK FD-style</b> — DK using FanDuel-type endings (support only)."
            "</div>"

            '<div class="glossary-block">'
            "<h4>💙 FanDuel</h4>"
            "<b>FD Pattern</b> — price <b>+400 or higher</b> and ends in 10 / 20 / 30 / 60 / 70 / 90. "
            "<b>PRIORITY</b> when paired with DK/MGM on the player.<br>"
            "<b>FD 600</b> — specifically +600. <b>PRIORITY</b>.<br>"
            "<b>FD+MGM classic</b> — FD Pattern/600 <b>and</b> MGM 25/50/75 on the same player. <b>PRIORITY</b> (~14%)."
            "</div>"

            '<div class="glossary-block">'
            "<h4>🤝 Same / tight prices (across books)</h4>"
            "Looks at <b>DK · FD · MGM · HardRock</b>.<br><br>"
            "<b>Exact Match</b> — same number on <b>2</b> of those books.<br>"
            "<b>All books same</b> — same number on <b>3+</b> (e.g. all +650).<br>"
            "<b>Books tight</b> — within ~<b>50 points</b> (e.g. +450 to +475). "
            "<b>Support only</b> — common on WATCH, weak when forced onto TAKE IT."
            "</div>"

            '<div class="glossary-block">'
            "<h4>🔒 Lock vs 🧠 Lock Lab</h4>"
            "<b>Lock</b> — <b>Open</b> = first pull (never changes) · <b>Now</b> = latest pregame · <b>Close</b> = last number before the book vanishes (often first pitch).<br>"
            "<b>Movement</b> — open → now/close (and fetch-to-fetch). Study morning vs lineup vs final hour.<br>"
            "<b>Lock Lab</b> — HRs matched to Lock. Ending chips = <b>1 per HR</b> (best of DK/FD/MGM at close)."
            "</div>"

            '<div class="glossary-block">'
            "<h4>📊 Results · Auto-grade · 📡 Tracker · 🧪 Backtest</h4>"
            "<b>Results</b> — every TAKE IT / WATCH we logged → PENDING → HIT or MISS.<br>"
            "<b>Auto-grade</b> — checks MLB box scores so you don’t grade everything by hand.<br>"
            "<b>Tracker</b> — hit rate by tag / book / ending after enough grades.<br>"
            "<b>Backtest</b> — TAKE IT % vs WATCH % (needs a real sample — ignore n=2 days)."
            "</div>"

            '<div class="glossary-block">'
            "<h4>📚 Books we care about</h4>"
            "<b>Methods focus:</b> DraftKings · FanDuel · BetMGM<br>"
            "<b>Often best number to bet:</b> DK · FD · Hard Rock<br>"
            "<b>Compare:</b> Caesars · Hard Rock vs others<br>"
            "<b>Bet365:</b> on hold until the feed is solid (850s / pairs later)"
            "</div>"

            '<div class="glossary-block">'
            "<h4>⚡ Quick flow</h4>"
            "① Load games → ② Fetch (0.5 HR) → ③ Lock saves pregame → "
            "④ Tags fire → ⑤ Board TAKE / WATCH / PASS → ⑥ Grade results → ⑦ Learn in Tracker / Lab"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="footer">👑 Girl Magic · Boss Bitch · HBIC · Me & My Girls We Rolling</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
