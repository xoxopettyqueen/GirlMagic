# -*- coding: utf-8 -*-
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
try:
    from benford import analyze_benford, analyze_many
    HAS_BENFORD = True
except ImportError:
    HAS_BENFORD = False
    def analyze_benford(*a, **k):
        return {}
    def analyze_many(*a, **k):
        return {}

# ── NFL math (inlined — one file for GitHub paste) ──────────
# Do not leave a bare """ string here. Streamlit prints leftover strings as the page.
HAS_NFL_MATH = True

from collections import Counter

# ── price lanes (Anytime TD Over Yes) ────────────────────────
NFL_FLOOR = 115          # shorter than this is not a Girl Magic TD ticket
NFL_SWEET_LO = 150
NFL_SWEET_HI = 450       # the lane we actually hunt
NFL_LONG_LO = 500
NFL_LONG_HI = 1200       # long TDs hit. No 799 cap.
NFL_FLYER = 1201         # flyer: needs extra proof

# Endings that have actually shown up on TDs we like
NFL_HOT_ENDS = {10, 20, 25, 50, 70, 75, 90, 0}
NFL_DEAD_ENDS = {15, 35, 40, 45, 55, 65, 80, 85}  # fade-these on long prices
NFL_MGM_CLASSIC = {0, 25, 50, 75}                 # MGM group/pair endings
NFL_DK_10 = {10}
NFL_FD_PATTERN = {10, 20, 30, 60, 70, 90}
NFL_FD_EXACT = {600}                              # keep 600 as a specific FD tell

# FD vs MGM — NFL version (NOT "by 100" on +900 flyers)
NFL_FD_MGM_MIN = 25      # ignore tiny gaps
NFL_FD_MGM_MAX = 80      # 100+ on a +800 TD is noise, not a tell
NFL_FD_MGM_LANE = (150, 550)  # only shout in this price band

TICKET_BOOKS = {"draftkings", "fanduel", "hardrockbet", "fanatics", "caesars", "bet365"}
SIGNAL_ONLY = {"betmgm"}


def last_two(p):
    try:
        return abs(int(p)) % 100
    except Exception:
        return None


def abs_price(p):
    try:
        return abs(int(p))
    except Exception:
        return None


def nfl_price_ok(best_price):
    """Anytime TD ticket floor. PLUS money only. -260 is chalk, not a ticket."""
    try:
        p = int(best_price)
    except Exception:
        return False
    return p >= NFL_FLOOR


def nfl_hot_end(price):
    end = last_two(price)
    return end in NFL_HOT_ENDS if end is not None else False


def nfl_dead_long(price):
    p = abs_price(price)
    end = last_two(price)
    if p is None or end is None:
        return False
    return p >= NFL_LONG_LO and end in NFL_DEAD_ENDS


def nfl_lane(price):
    p = abs_price(price)
    if p is None:
        return "none"
    if p < NFL_FLOOR:
        return "too_short"
    if NFL_SWEET_LO <= p <= NFL_SWEET_HI:
        return "sweet"
    if NFL_LONG_LO <= p <= NFL_LONG_HI:
        return "long"
    if p >= NFL_FLYER:
        return "flyer"
    return "mid"


def _norm_book(b):
    b = str(b or "").lower()
    if "betmgm" in b or b == "mgm":
        return "betmgm"
    if "draftking" in b or b == "dk":
        return "draftkings"
    if "fanduel" in b or b == "fd":
        return "fanduel"
    if "hardrock" in b:
        return "hardrockbet"
    if "fanatic" in b:
        return "fanatics"
    if "caesar" in b or "williamhill" in b:
        return "caesars"
    if "bet365" in b or b == "365":
        return "bet365"
    return b


def nfl_fd_under_mgm(book_prices):
    """
    NFL tell: FD is 25–80 pts SHORTER than MGM, and the ticket is in the sweet/mid lane.
    MLB 'by 100' on +850 vs +950 is junk. Do not use that here.
    Returns (ok, gap, fd, mgm) or (False, 0, None, None).
    """
    books = {_norm_book(k): v for k, v in (book_prices or {}).items()}
    fd = books.get("fanduel")
    mgm = books.get("betmgm")
    if fd is None or mgm is None:
        return False, 0, fd, mgm
    try:
        fd_i, mgm_i = int(fd), int(mgm)
    except Exception:
        return False, 0, fd, mgm
    # American plus prices: higher number = longer. FD under MGM = mgm - fd > 0
    gap = mgm_i - fd_i
    lane_p = min(abs(fd_i), abs(mgm_i))
    lo, hi = NFL_FD_MGM_LANE
    if not (lo <= lane_p <= hi):
        return False, gap, fd_i, mgm_i
    if NFL_FD_MGM_MIN <= gap <= NFL_FD_MGM_MAX:
        return True, gap, fd_i, mgm_i
    return False, gap, fd_i, mgm_i


def nfl_b365_over_hardrock(book_prices):
    """Bet365 plus-price longer than Hard Rock."""
    books = {_norm_book(k): v for k, v in (book_prices or {}).items()}
    b365 = books.get("bet365")
    hr = books.get("hardrockbet")
    if b365 is None or hr is None:
        return False, 0
    try:
        gap = int(b365) - int(hr)
    except Exception:
        return False, 0
    return gap > 0, gap



FANATICS_VS_MGM_GAP = 80  # Fanatics way higher than MGM = signal book


def fanatics_price_logic(book_prices):
    """
    Fanatics rules:
    - WAY HIGHER than MGM (80+) → Fanatics is the SIGNAL BOOK
    - BEST and odds >= +500 → ALLOW TAKE even if DK/FD/MGM are mid
    - ALONE (no DK/FD/MGM) → WATCH, not TAKE
    - MATCHES DK/FD/MGM → treat normally
    """
    books = {}
    for raw, v in (book_prices or {}).items():
        try:
            books[_norm_book(raw)] = int(v)
        except Exception:
            continue
    fn = books.get("fanatics")
    mgm = books.get("betmgm")
    support = [b for b in ("draftkings", "fanduel", "betmgm") if b in books]
    out = {
        "price": fn,
        "alone": False,
        "best": False,
        "way_over_mgm": False,
        "matches": False,
        "allow_take": False,
        "watch_only": False,
        "gap_mgm": 0,
        "tag": None,
    }
    if fn is None:
        return out
    others = [p for b, p in books.items() if b != "fanatics"]
    out["best"] = (not others) or fn >= max(others)
    if mgm is not None:
        out["gap_mgm"] = fn - mgm
        out["way_over_mgm"] = (fn - mgm) >= FANATICS_VS_MGM_GAP
    out["matches"] = any(abs(fn - books[b]) <= 25 for b in ("draftkings", "fanduel", "betmgm") if b in books)
    out["alone"] = not support
    out["watch_only"] = out["alone"]
    out["allow_take"] = bool(out["best"] and abs(fn) >= 500 and not out["alone"])
    if out["way_over_mgm"]:
        out["tag"] = "Fanatics Loud"
    elif out["allow_take"]:
        out["tag"] = "Fanatics Best"
    elif out["alone"] and abs(fn) >= 500:
        out["tag"] = "Fanatics Alone"
    return out


def b365_over_mgm(book_prices):
    """Bet365 plus-price longer than BetMGM."""
    books = {_norm_book(k): v for k, v in (book_prices or {}).items()}
    b365 = books.get("bet365")
    mgm = books.get("betmgm")
    if b365 is None or mgm is None:
        return False, 0
    try:
        gap = int(b365) - int(mgm)
    except Exception:
        return False, 0
    return gap > 0, gap


def letter_value(ch):
    if not ch or not ch.isalpha():
        return 0
    return (ord(ch.upper()) - 64)


def name_number(player):
    """Pythagorean name number 1–9, keep 11/22/33 as master footnotes."""
    total = sum(letter_value(c) for c in str(player or ""))
    raw = total
    while total > 9 and total not in (11, 22, 33):
        total = sum(int(d) for d in str(total))
    reduced = total
    while reduced > 9:
        reduced = sum(int(d) for d in str(reduced))
    return reduced, raw, total if total in (11, 22, 33) else None


def end_number(price):
    end = last_two(price)
    if end is None:
        return None, None
    n = end
    while n > 9:
        n = sum(int(d) for d in str(n))
    return end, n


def nfl_magic_row(player, price, book_prices=None, methods=None):
    """One Magic Math card for an NFL TD name. Does not green TAKE by itself."""
    p = abs_price(price)
    end, end_n = end_number(price)
    name_n, raw, master = name_number(player)
    lane = nfl_lane(price)
    hot = nfl_hot_end(price)
    dead = nfl_dead_long(price)
    fd_ok, fd_gap, fd, mgm = nfl_fd_under_mgm(book_prices)
    tags = []
    if hot:
        tags.append(f"Hot end {end:02d}" if end is not None else "Hot end")
    if dead:
        tags.append("Dead long ending")
    if lane == "sweet":
        tags.append("Sweet lane")
    if lane == "long":
        tags.append("Long TD")
    if lane == "flyer":
        tags.append("Flyer")
    if fd_ok:
        tags.append(f"FD under MGM {fd_gap}")
    if name_n and end_n and name_n == end_n:
        tags.append("name+price")
    if master:
        tags.append(f"Master {master}")
    for m in methods or []:
        ms = str(m)
        if ms in ("DK 10", "FD Pattern", "FD 600", "MGM Exact") or ms.startswith("MGM") or ms.startswith("B365"):
            tags.append(ms)
    why_bits = [
        f"lane {lane}",
        f"Name# {name_n}",
        f"End {end:02d} → #{end_n}" if end is not None else "no end",
    ]
    if fd_ok:
        why_bits.append(f"FD {fd:+d} under MGM {mgm:+d} by {fd_gap}")
    return {
        "player": player,
        "price": p,
        "end": end,
        "end_n": end_n,
        "name_n": name_n,
        "master": master,
        "lane": lane,
        "hot": hot,
        "dead": dead,
        "fd_under_mgm": fd_ok,
        "fd_gap": fd_gap,
        "tags": tags,
        "why": " · ".join(why_bits),
        "match_name_price": bool(name_n and end_n and name_n == end_n),
    }


def nfl_take_ok(
    core_count,
    methods=None,
    best_price=None,
    best_book=None,
    book_prices=None,
    score=0,
    need_core=2,
):
    """
    NFL TAKE gate. Not MLB.
    - Ticket book only (never MGM as the buy)
    - Price >= +115
    - 2 premium methods (week-1 can pass need_core=1 from app)
    - Hot ending OR priority tag OR score >= 70
    - Dead long endings do not green
    - Flyers need priority + 2 real books
    """
    try:
        raw = int(best_price)
    except Exception:
        return False
    if raw < NFL_FLOOR:
        return False
    p = raw
    if nfl_dead_long(best_price):
        return False
    bk = _norm_book(best_book)
    if not bk and book_prices:
        # pick longest ticket book
        best = None
        for k, v in (book_prices or {}).items():
            nb = _norm_book(k)
            if nb in SIGNAL_ONLY:
                continue
            try:
                iv = int(v)
            except Exception:
                continue
            if best is None or iv > best[0]:
                best = (iv, nb)
        bk = best[1] if best else None
    if not bk or bk in SIGNAL_ONLY or bk not in TICKET_BOOKS:
        return False
    if int(core_count or 0) < int(need_core or 2):
        return False
    books = {_norm_book(k) for k in (book_prices or {})}
    fn = fanatics_price_logic(book_prices)
    if fn.get("watch_only"):
        return False
    if "draftkings" not in books and "fanduel" not in books:
        # Fanatics can green only if BEST +500 and MGM/DK/FD exists (even mid).
        if not fn.get("allow_take"):
            return False
    ms = set(str(m) for m in (methods or []))
    priority = bool(
        ms
        & {
            "DK 10",
            "FD Pattern",
            "FD 600",
            "MGM Exact",
            "Exact Match",
            "Last one left",
            "Multi-book Shorten",
            "B365 850",
        }
        or any(str(m).startswith("MGM ") or str(m).startswith("Match ") or str(m).startswith("B365") for m in ms)
    )
    hot = nfl_hot_end(best_price)
    lane = nfl_lane(best_price)
    try:
        sc = int(score or 0)
    except Exception:
        sc = 0
    if lane == "flyer":
        real = books & {"draftkings", "fanduel", "betmgm"}
        if not priority or len(real) < 2:
            return False
    if bk in ("fanatics", "hardrockbet") and not priority:
        return False
    if lane in ("long", "flyer") and not (hot and priority):
        return False
    if hot or priority:
        return True
    if sc >= 70 and priority:
        return True
    return False


def nfl_petty_alerts(ev_board, flag_rows=None, limit=8):
    """Replace MLB FD-under-100 spam with NFL-lane alerts."""
    alerts = []
    for item in ev_board or []:
        books = item.get("book_prices") or {}
        ok, gap, fd, mgm = nfl_fd_under_mgm(books)
        if ok:
            alerts.append(f"FD under MGM by {gap} · {item.get('player')}")
        ms = set(item.get("methods") or [])
        if "MGM Exact" in ms:
            alerts.append(f"MGM Exact · {item.get('player')}")
        if "DK 10" in ms and ("FD Pattern" in ms or "FD 600" in ms):
            alerts.append(f"DK 10 + FD · {item.get('player')}")
    for r in flag_rows or []:
        meths = r.get("methods") or []
        if "MGM Exact" in meths:
            alerts.append(f"MGM Exact · {r.get('label')}")
    seen, out = set(), []
    for a in alerts:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out[:limit]


def nfl_ending_board(rows):
    """What's Going Today helper — count TD endings from graded HITs."""
    ends = Counter()
    books = Counter()
    for r in rows or []:
        if str(r.get("result") or "").upper() != "HIT":
            continue
        end = r.get("ending")
        if end is None:
            end = last_two(r.get("best_price"))
        if end is None:
            continue
        ends[int(end)] += 1
        books[str(r.get("best_book") or "untagged")] += 1
    return ends, books


# ── copy for Magic Math tab (NFL) ────────────────────────────
NFL_MATH_BLURB = """
**NFL is not baseball.** Different sport, different stamps.

- We buy Anytime TD. We do not buy the passer.
- Green still means two of *our* tags — the Board already knows which.
- MGM talks. It does not get the ticket.
- Long junk still junk. If it’s purple, it’s homework.

The exact lanes live in the code, not on this page.
"""

nfl_math_fd_under_mgm = nfl_fd_under_mgm
import statistics
import time
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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Inter:ital,wght@0,400;0,600;0,700;1,400&family=Space+Grotesk:wght@500;700&display=swap');
.stApp{background:#0c0a1a;color:#fce7f3;font-family:'Inter',sans-serif}
.stButton>button{font-family:'Space Grotesk',sans-serif!important;letter-spacing:.06em;text-transform:uppercase;transition:transform .15s,box-shadow .15s!important}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 0 16px rgba(255,62,191,.45)!important}
.petty-banner{animation:pettyGlow 2.8s ease-in-out infinite}
@keyframes pettyGlow{0%,100%{box-shadow:0 0 0 rgba(255,62,191,0)}50%{box-shadow:0 0 18px rgba(255,62,191,.55)}}
.al-chip{animation:chipPulse 2.6s ease-in-out infinite}
@keyframes chipPulse{0%,100%{filter:brightness(1)}50%{filter:brightness(1.25)}}
.gm-num{color:#00e6c3;font-weight:700}
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
.card-name{font-size:1.22rem;font-weight:800;color:#fff;margin:0}
.card-meta{font-size:.82rem;color:#d1d5db;margin:2px 0 6px}
.card-line{font-size:.92rem;color:#e5e7eb;margin:1px 0}
.card-foot{font-size:.78rem;color:#c4b5d6;margin-top:8px}
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
.footer{text-align:center;color:#f9a8d4;font-size:.82rem;margin-top:28px;padding-bottom:18px;line-height:1.55;overflow:hidden}
.footer b{color:#00e6c3}
.footer-ticker{display:inline-block;white-space:nowrap;animation:tick 18s linear infinite;font-family:'Space Grotesk',sans-serif;letter-spacing:.04em}
@keyframes tick{0%{transform:translateX(12%)}100%{transform:translateX(-12%)}}
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
div[data-baseweb="select"] span{font-size:0.78rem!important;color:#fce7f3!important}
.stMultiSelect{max-width:920px}
.stMultiSelect [data-baseweb="tag"]{max-width:200px;background:linear-gradient(90deg,#db2777,#9333ea)!important;border:none!important;color:#fff!important}
.stMultiSelect [data-baseweb="tag"] span{color:#fff!important}
div[data-baseweb="select"]>div{
  background:#1a0f28!important;
  border:1px solid #a855f7!important;
  border-radius:12px!important;
  color:#fce7f3!important;
  box-shadow:none!important;
}
div[data-baseweb="popover"] div[data-baseweb="menu"],
ul[role="listbox"]{
  background:#160a22!important;
  border:1px solid #a855f7!important;
  color:#fce7f3!important;
}
li[role="option"]{color:#fce7f3!important}
.stSlider [data-testid="stTickBarMin"], .stSlider [data-testid="stTickBarMax"]{color:#c4b5d6!important}
.stSlider [data-baseweb="slider"] div[role="slider"]{
  background:#f472b6!important;border-color:#f9a8d4!important;
}
.stSlider [data-baseweb="slider"] div[data-testid="stThumbValue"]{color:#f9a8d4!important}
.stSlider [data-baseweb="slider"]>div>div{background:#4c1d95!important}
.stTextInput input, .stNumberInput input, textarea{
  background:#1a0f28!important;
  border:1px solid #7c3aed!important;
  color:#fce7f3!important;
  border-radius:12px!important;
}
.stTextInput label, .stSlider label, .stSelectbox label, .stMultiSelect label{
  color:#f9a8d4!important;font-size:.78rem!important;font-weight:700!important;letter-spacing:.04em;
}
.filter-shell{
  background:linear-gradient(155deg,#1a0f28,#251438);
  border:1px solid #a855f7;
  border-radius:16px;
  padding:12px 14px 6px 14px;
  margin:0 0 16px 0;
}
.filter-shell h4{color:#f9a8d4;margin:0 0 8px 0;font-size:.95rem}
.sport-row{margin:4px 0 10px 0}
div[data-testid="stSegmentedControl"] button{border-radius:999px!important}
div[role="radiogroup"] label p, div[role="radiogroup"] label span{color:#fce7f3!important;opacity:1!important}
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
/* ── Website shell (display only) ── */
.quote-bar{background:#1a1024;border:1px solid #f9a8d4;border-radius:14px;padding:9px 16px;margin:0 0 10px;color:#fce7f3;font-size:.88rem;letter-spacing:.3px;box-shadow:0 0 16px rgba(244,114,182,.2)}
.site-hero{
  background:linear-gradient(110deg,#2a1040 0%,#6d28d9 38%,#db2777 72%,#4c1d95 100%);
  background-size:180% 180%;
  animation:heroShimmer 14s ease-in-out infinite;
  border:1px solid #f9a8d4;border-radius:22px;padding:16px 20px 14px;
  margin:0 0 10px;box-shadow:0 16px 36px rgba(76,29,149,.38);
}
@keyframes heroShimmer{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.site-hero-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.site-kicker{color:#fde68a;font-size:.72rem;font-weight:800;letter-spacing:2.6px;text-transform:uppercase;margin:0 0 8px}
.site-title{font-family:'Playfair Display',serif;font-size:clamp(1.6rem,5vw,2.4rem);line-height:1.05;margin:0 0 6px;background:linear-gradient(90deg,#ff3ebf,#9b5fff,#00e6c3,#ff3ebf);background-size:220% auto;-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent;animation:titleIn .6s ease-out,gmShine 8s linear infinite}
@keyframes gmShine{0%{background-position:0%}100%{background-position:220%}}
@keyframes alFill{from{width:0}to{width:var(--w,100%)}}
.site-sub{color:#fce7f3;font-size:.92rem;margin:0 0 4px;max-width:740px;line-height:1.45;animation:fadeUp .7s ease-out .12s both}
.site-quote{color:#fde68a;font-size:.88rem;font-style:italic;margin:0 0 8px}
.site-live{color:#f9a8d4;font-size:.78rem;margin:0 0 8px}
@keyframes titleIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.site-chips{display:flex;flex-wrap:wrap;gap:8px}
.site-chip{background:rgba(11,6,18,.35);border:1px solid #e879f9;color:#fbcfe8;border-radius:999px;padding:5px 12px;font-size:.72rem;font-weight:700;transition:box-shadow .2s,border-color .2s}
.site-chip:hover{border-color:#c084fc;box-shadow:0 0 12px rgba(192,132,252,.45)}
.site-chip.sport{border-color:#f9a8d4;color:#fff;box-shadow:0 0 10px rgba(244,114,182,.35)}
.site-section{background:#120818;border:1px solid #2a2038;border-radius:22px;padding:16px 16px 8px;margin:0 0 18px}
.site-section-head{margin:0 0 10px}
.site-section-kicker{color:#f9a8d4;font-size:.64rem;letter-spacing:1.8px;text-transform:uppercase;font-weight:800;margin:0}
.site-section-title{font-family:'Playfair Display',serif;color:#fff;font-size:1.45rem;margin:2px 0 4px}
.site-section-help{color:#c4b5d6;font-size:.82rem;margin:0 0 8px;line-height:1.45}
div[data-testid="stExpander"]{border:1px solid #a855f7;border-radius:16px;background:linear-gradient(90deg,rgba(219,39,119,.18),rgba(124,58,237,.18));margin-bottom:8px}
div[data-testid="stExpander"] details{border:none}
div[data-testid="stExpander"] summary{color:#fce7f3!important}
.pill{display:inline-block;border-radius:999px;padding:3px 10px;font-size:.68rem;font-weight:800;letter-spacing:.4px;text-transform:uppercase}
.pill-take{background:#14532d;color:#bbf7d0;border:1px solid #34d399}
.pill-lean{background:#422006;color:#fde68a;border:1px solid #f59e0b}
.pill-watch{background:#1e3a5f;color:#bfdbfe;border:1px solid #60a5fa}
.pill-pass{background:#1f2937;color:#d1d5db;border:1px solid #4b5563}
.pill-dont{background:#450a0a;color:#fecaca;border:1px solid #f87171}
.score-pill.big{float:none;display:inline-block;margin:0 0 8px;font-size:.8rem;padding:4px 11px}
.card.site-card{padding:16px 16px 14px;margin-bottom:12px}
.card.site-card .card-name{font-size:1.18rem;letter-spacing:.2px}
.card.site-card.compact{padding:10px 12px 8px;margin-bottom:8px}
.card.site-card .card-meta{font-size:.78rem;color:#c4b5d6;margin-bottom:8px}
.price-row{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin:6px 0 4px}
.price-big{font-size:1.22rem;font-weight:800;color:#6ee7b7}
.price-book{font-size:.78rem;color:#e9d5ff}
.method-group{margin-top:8px;padding-top:8px;border-top:1px solid #2a2038}
.queen-line{color:#f9a8d4;font-style:italic;font-size:.86rem;margin-top:8px}


.wg-wrap{background:linear-gradient(110deg,#160c22,#2a1040 50%,#db2777 140%);border:1px solid #f9a8d4;border-radius:16px;padding:8px 12px 6px;margin:18px 0 8px;box-shadow:0 0 18px rgba(236,72,153,.22)}
.wg-top{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:baseline;margin:0 0 4px}
.wg-title{font-size:.88rem;font-weight:800;color:#fce7f3;letter-spacing:.3px}
.wg-sub{font-size:.68rem;color:#e9d5ff;margin:0}
.wg-switch{display:flex;gap:4px}
.wg-pill{border-radius:999px;padding:2px 8px;font-size:.62rem;font-weight:800;border:1px solid #4c1d95;color:#c4b5d6}
.wg-pill.on{border-color:#f9a8d4;color:#fff;background:linear-gradient(90deg,#6d28d9,#db2777);box-shadow:0 0 8px rgba(244,114,182,.4)}
.wg-counts{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:2px 0 6px;font-size:.78rem;color:#e9d5ff}
.wg-counts b{color:#f9a8d4}
.wg-books{display:flex;gap:6px;flex-wrap:wrap;align-items:flex-start}
.pulse-pill{display:inline-block;background:#120818;border:1px solid #a855f7;border-radius:999px;padding:3px 10px;font-size:.7rem;font-weight:700;color:#fce7f3;cursor:pointer;background-image:linear-gradient(#120818,#120818),linear-gradient(90deg,#f472b6,#a855f7);background-origin:border-box;box-shadow:0 0 8px rgba(168,85,247,.2);transition:transform .15s,box-shadow .15s}
.pulse-pill:hover,.pulse-pill[open]{transform:translateY(-2px);box-shadow:0 0 16px rgba(244,114,182,.5);border-color:#f9a8d4}
.pulse-pill summary{list-style:none;cursor:pointer}
.pulse-pill summary::-webkit-details-marker{display:none}
.pulse-pop{margin-top:6px;background:#100818;border:1px solid #3b0764;border-radius:12px;padding:6px 8px;min-width:160px}
.wg-player{font-size:.72rem;margin:3px 0;color:#fce7f3}
.wg-take{color:#86efac}
.wg-lean{color:#f9a8d4}
.wg-watch{color:#d8b4fe}
.wg-dont{color:#fda4af}
.wg-queen{margin:4px 0 0;text-align:right;font-size:.72rem;font-style:italic;color:#f9a8d4;text-shadow:0 0 10px rgba(244,114,182,.55)}
.recap-line{font-size:.82rem;margin:3px 0;color:#fce7f3}
.recap-wrap{max-height:420px;overflow:auto;border:1px solid #3b0764;border-radius:14px;background:#100818;box-shadow:0 0 16px rgba(168,85,247,.18);margin:8px 0 12px}
.recap-table{width:100%;border-collapse:separate;border-spacing:0;font-size:.78rem;color:#fce7f3}
.recap-table th{position:sticky;top:0;z-index:2;background:#1a0f28;color:#f9a8d4;font-size:.62rem;letter-spacing:.8px;text-transform:uppercase;text-align:left;padding:8px 10px;border-bottom:1px solid #a855f7}
.recap-table td{padding:7px 10px;border-bottom:1px solid #2a2038;vertical-align:middle}
.recap-table tr.r-hit{background:linear-gradient(90deg,rgba(16,185,129,.12),transparent 55%)}
.recap-table tr.r-miss{background:linear-gradient(90deg,rgba(248,113,113,.12),transparent 55%)}
.recap-table tr.r-lean{background:linear-gradient(90deg,rgba(244,114,182,.12),transparent 55%)}
.recap-table tr.r-watch{background:linear-gradient(90deg,rgba(192,132,252,.12),transparent 55%)}
.recap-badge{display:inline-block;margin-left:6px;background:linear-gradient(90deg,#db2777,#9333ea);color:#fff;font-size:.58rem;font-weight:800;padding:2px 6px;border-radius:999px;box-shadow:0 0 8px rgba(244,114,182,.4)}
.recap-table th.sig{width:92px}
.recap-table td.sig{width:92px;white-space:nowrap;font-weight:800}
.recap-table tr.r-sig-take{box-shadow:inset 3px 0 0 #34d399}
.recap-table tr.r-sig-lean{box-shadow:inset 3px 0 0 #f472b6}
.recap-table tr.r-sig-watch{box-shadow:inset 3px 0 0 #c084fc}



.n1-pulse{animation:n1Shimmer 1.6s ease-out 1}
@keyframes n1Shimmer{
  0%{box-shadow:0 0 0 rgba(244,114,182,0);filter:brightness(1.4)}
  40%{box-shadow:0 0 28px rgba(244,114,182,.55)}
  100%{box-shadow:0 0 10px rgba(167,139,250,.2);filter:brightness(1)}
}
.n1-sum{
  background:linear-gradient(110deg,#2a1040,#7c3aed 45%,#db2777);
  border:1px solid #f9a8d4;border-radius:16px;padding:12px 16px;margin:0 0 12px;
  color:#fce7f3;font-size:.88rem;line-height:1.45;
}
.n1-card{position:relative;overflow:hidden}
.n1-card.take{border-color:#34d399;box-shadow:0 0 18px rgba(52,211,153,.28)}
.n1-card.lean{border-color:#f472b6;box-shadow:0 0 18px rgba(244,114,182,.28)}
.n1-card.watch{border-color:#c084fc;box-shadow:0 0 16px rgba(192,132,252,.25)}
.n1-card.dont{border-color:#fb7185;box-shadow:0 0 14px rgba(251,113,133,.22)}
.n1-hot{
  position:absolute;top:10px;right:10px;
  background:linear-gradient(90deg,#fb7185,#f472b6);
  color:#fff;font-size:.62rem;font-weight:800;letter-spacing:.6px;
  padding:3px 8px;border-radius:999px;box-shadow:0 0 12px rgba(244,114,182,.6);
}
.n1-meter{height:7px;background:#1f1630;border-radius:999px;overflow:hidden;margin:8px 0 4px}
.n1-meter>i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#fb7185,#c084fc,#34d399)}
.n1-meter.hot>i{animation:n1Shimmer 1.8s ease-in-out infinite}
.n1-meter-lab{font-size:.68rem;color:#e9d5ff;margin-bottom:6px}
.queen-take{color:#86efac;text-shadow:0 0 10px rgba(52,211,153,.45)}
.queen-lean{color:#f9a8d4;text-shadow:0 0 10px rgba(244,114,182,.45)}
.queen-watch{color:#d8b4fe;text-shadow:0 0 10px rgba(192,132,252,.4)}
.queen-dont{color:#fda4af;text-shadow:0 0 10px rgba(251,113,133,.4)}
.n1-gloss{
  display:grid;grid-template-columns:110px 1fr;gap:4px 10px;
  font-size:.78rem;color:#e9d5ff;margin-top:8px;
}
.n1-gloss b{color:#f9a8d4}
.petty-box.n1-live{animation:n1Shimmer 1.4s ease-out 1}

.tag-group-lab{color:#c4b5d6;font-size:.58rem;letter-spacing:1.2px;text-transform:uppercase;margin:8px 0 3px}
.motion-line{font-size:.72rem;font-weight:800;margin:6px 0;padding:4px 8px;border-radius:999px;display:inline-block;border:1px solid #64748b}
.card-hot{box-shadow:0 0 22px rgba(244,114,182,.4);animation:heatPulse 2.4s ease-in-out infinite}
.kelly-line{display:inline-block;margin:6px 0;padding:3px 10px;border-radius:999px;font-size:.72rem;font-weight:800}
.kelly-strong{color:#bbf7d0;border:1px solid #34d399;box-shadow:0 0 10px rgba(52,211,153,.35)}
.kelly-med{color:#fbcfe8;border:1px solid #f472b6;box-shadow:0 0 10px rgba(244,114,182,.35)}
.kelly-light{color:#e9d5ff;border:1px solid #c084fc}
.kelly-avoid{color:#fecaca;border:1px solid #fb7185}
.shop-wrap{border:1px solid #2a2038;border-radius:16px;padding:8px;background:#0d0814}
.shop-table th{padding:8px 8px}
.shop-table td{padding:10px 8px}
.shop-table tr.row-take td{background:#0d1c18;border-color:#1d4a3a}
.shop-table tr.row-lean td{background:#1a1408;border-color:#713f12}
.shop-table tr.row-dont td{background:#1a0b12;border-color:#4a1020}
.shop-table tr.row-mkt td{background:#16101f}
.shop-call{display:inline-block;border-radius:999px;padding:3px 8px;font-size:.68rem;font-weight:800}
.how-to.site-guide{border-radius:16px;margin-bottom:16px}
.card:hover,.card.site-card:hover{
  border-color:#e879f9;transform:translateY(-2px);
  box-shadow:0 10px 28px rgba(232,121,249,.22);
  transition:transform .14s ease,box-shadow .14s ease,border-color .14s ease;
}
.shop-table tr:hover td{filter:brightness(1.12)}
.tag[title]{cursor:help}
.petty-on .site-hero{box-shadow:0 0 36px rgba(244,114,182,.35)}
.petty-banner{
  background:linear-gradient(90deg,#831843,#6b21a8);
  border:1px solid #f9a8d4;border-radius:999px;
  padding:7px 14px;margin:0 0 12px;font-size:.78rem;color:#fce7f3;
  display:inline-block;
}
.petty-off-banner{
  background:#16101f;border:1px solid #4b5563;border-radius:999px;
  padding:7px 14px;margin:0 0 12px;font-size:.78rem;color:#c4b5d6;
  display:inline-block;
}
[data-testid="stSidebar"]{background:#0d0814}
[data-testid="stSidebar"] .stMarkdown{color:#e9d5ff}
.gate-row{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 4px}
.gate{font-size:.62rem;border-radius:999px;padding:2px 7px;font-weight:700}
.gate-yes{background:#052e16;color:#86efac;border:1px solid #166534}
.gate-no{background:#1f0a12;color:#fda4af;border:1px solid #7f1d1d}
.why-call{color:#e9d5ff;font-size:.74rem;margin:6px 0 2px;line-height:1.35}
.board-wrap,.board-wrap *{list-style:none!important}
.game-head{font-family:'Playfair Display',serif;color:#fce7f3;font-size:1.05rem;margin:14px 0 8px;font-weight:700}
.trend-line{margin-top:8px;padding-top:6px;border-top:1px dashed #3b2a4f}
.trend-chip{display:inline-block;background:#3b0764;border:1px solid #e879f9;color:#fbcfe8;border-radius:999px;padding:2px 8px;font-size:.68rem;font-weight:800;margin-right:6px}
.trend-meta{color:#c4b5d6;font-size:.68rem;margin-top:2px}
.trend-mean{color:#fce7f3;font-size:.74rem;margin:4px 0 2px}
.motion-heat{border-color:#34d399!important;box-shadow:0 0 14px rgba(52,211,153,.35);animation:heatPulse 1.8s ease-in-out infinite}
.motion-cool{border-color:#fb7185!important;box-shadow:0 0 12px rgba(251,113,133,.28)}
.motion-chaos{border-color:#c084fc!important;box-shadow:0 0 16px rgba(192,132,252,.4);animation:chaosPulse 1.1s ease-in-out infinite}
.motion-stable{border-color:#64748b!important}
@keyframes heatPulse{0%,100%{box-shadow:0 0 8px rgba(52,211,153,.25)}50%{box-shadow:0 0 18px rgba(52,211,153,.55)}}
@keyframes chaosPulse{0%,100%{box-shadow:0 0 8px rgba(192,132,252,.25)}50%{box-shadow:0 0 20px rgba(244,114,182,.5)}}
.pulse-bar{background:linear-gradient(90deg,#4c1d95,#831843);border:1px solid #f9a8d4;border-radius:16px;padding:12px 14px;margin:0 0 12px;color:#fce7f3;font-size:.88rem;line-height:1.45}
.spark-wrap{margin-top:8px}
.spark-row{margin:3px 0}
.spark-lab{display:inline-block;width:64px;color:#c4b5d6;font-size:.62rem}
.shop-wrap{margin-top:12px}
@media (max-width: 700px){
  .site-title{font-size:1.55rem}
  .card.site-card .card-name{font-size:1.05rem}
  .price-big{font-size:1.05rem}
  .site-section{padding:12px 10px 6px}
  .shop-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -6px}
  .shop-table{font-size:.68rem;min-width:720px}
  .shop-table th,.shop-table td{padding:6px 5px}
  .shop-table td:first-child,.shop-table th:first-child{
    position:sticky;left:0;z-index:2;background:#120818;min-width:112px;box-shadow:4px 0 8px rgba(0,0,0,.35)
  }
  .shop-name{font-size:.78rem}
  .shop-game{font-size:.58rem}
  .wg-books{flex-direction:column}
  .wg-book{min-width:0}
}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
MLB_STATS = "https://statsapi.mlb.com/api/v1"
REGIONS = "us,uk"
# Sport profiles — MLB math stays the same; NFL only swaps feed + labels
SPORT_CFG = {
    "MLB": {
        "key": "baseball_mlb",
        "market": "batter_home_runs",
        "label": "0.5 HR Over",
        "hit": "HR",
        "hits": "HRs",
        "sgo": True,
        "days": 1,
        "when": "First pitch",
        "lock_caption": "Today's homers matched to what we locked before first pitch.",
        "lock_count": "MLB HR",
        "shop_empty": "Fetch 0.5 HR first - Shop fills from the live slate.",
    },
    "NFL": {
        "key": "americanfootball_nfl",
        "market": "player_anytime_td",
        "label": "Anytime TD Yes / 0.5",
        "hit": "TD",
        "hits": "TDs",
        "sgo": True,
        "days": 8,
        "when": "Kickoff",
        "lock_caption": "TDs matched to the number we locked before kick. Same List energy. Different scoreboard.",
        "lock_count": "NFL TD",
        "shop_empty": "Fetch Anytime TD — Shop fills when the slate breathes.",
    },
}

def active_sport():
    s = st.session_state.get("sport", "MLB")
    return s if s in SPORT_CFG else "MLB"

def sport_cfg():
    return SPORT_CFG[active_sport()]


def row_sport(r):
    """Infer MLB vs NFL on a results row (old logs may lack sport)."""
    if not isinstance(r, dict):
        return "MLB"
    s = str(r.get("sport") or "").strip().upper()
    if s in ("NFL", "MLB"):
        return s
    blob = " ".join(
        str(r.get(k) or "") for k in ("market", "source", "methods")
    ).lower()
    if any(x in blob for x in ("anytime_td", "anytime td", "nfl", "touchdown")):
        return "NFL"
    if any(x in blob for x in ("batter_home_runs", "home_run", "homer", "mlb")):
        return "MLB"
    # Historic file is almost all MLB HRs
    return "MLB"


def results_for_sport(rows=None, sport=None):
    """Tracker / rates for ONE sport only. Never mix HR with TD."""
    if rows is None:
        rows = load_results()
    sport = (sport or active_sport()).upper()
    return [r for r in (rows or []) if row_sport(r) == sport]


def lock_entry_sport(entry):
    if not isinstance(entry, dict):
        return "MLB"
    s = str(entry.get("sport") or "").strip().upper()
    if s in ("NFL", "MLB"):
        return s
    ev = str(entry.get("event") or "").lower()
    nfl_bits = (
        "nfl", "chiefs", "bills", "eagles", "cowboys", "49ers", "niners",
        "ravens", "lions", "packers", "vikings", "bears", "jets", "giants",
        "dolphins", "patriots", "steelers", "browns", "bengals", "titans",
        "colts", "jaguars", "texans", "broncos", "raiders", "chargers",
        "rams", "seahawks", "cardinals", "saints", "falcons", "panthers",
        "buccaneers", "commanders", "washington",
    )
    # "Cardinals" exists in both — only count NFL if another NFL token or @ football style
    if "nfl" in ev:
        return "NFL"
    hits = sum(1 for b in nfl_bits if b in ev)
    if hits >= 1 and any(x in ev for x in ("chiefs", "bills", "eagles", "cowboys", "ravens", "lions", "packers")):
        return "NFL"
    if hits >= 2:
        return "NFL"
    return "MLB"


def lock_for_sport(lock=None, sport=None):
    lock = lock if lock is not None else (st.session_state.get("pregame_lock") or load_pregame() or {})
    sport = (sport or active_sport()).upper()
    today, et = today_az(), today_mlb_date()
    try:
        yest = (datetime.now(timezone(timedelta(hours=-7))) - timedelta(days=1)).strftime("%Y-%m-%d")
    except Exception:
        yest = today
    fresh, stale = {}, {}
    for player, entry in (lock or {}).items():
        if not isinstance(entry, dict):
            continue
        if lock_entry_sport(entry) != sport:
            continue
        d = str(entry.get("date") or "")
        if d in (today, et, yest) or not d:
            fresh[player] = entry
        else:
            stale[player] = entry
    # Never let August leftovers look like today's lock.
    return fresh if fresh else stale


def lock_entry_from_results(player):
    """If Lock file missed them, rebuild a mini-lock from today's logged row."""
    rows = results_for_sport()
    dates = {today_az(), today_mlb_date()}
    hit = None
    for r in rows:
        if r.get("date") not in dates:
            continue
        if not names_match(player, r.get("player") or ""):
            continue
        hit = r
        if r.get("source") in ("take_it", "shop_take"):
            break
    if not hit:
        return None, None
    books = {}
    for b, pr in (hit.get("book_prices") or {}).items():
        try:
            ip = int(pr)
        except Exception:
            continue
        books[str(b).lower()] = {
            "price": ip, "first_price": ip, "latest_price": ip,
            "close_price": ip, "ending": last_two(ip),
        }
    if not books and hit.get("best_price") is not None:
        b = str(hit.get("best_book") or "unknown").lower()
        ip = int(hit.get("best_price"))
        books[b] = {
            "price": ip, "first_price": ip, "latest_price": ip,
            "close_price": ip, "ending": last_two(ip),
        }
    entry = {
        "date": hit.get("date"),
        "event": hit.get("event") or "",
        "books": books,
        "sport": hit.get("sport") or active_sport(),
        "from_results": True,
    }
    return hit.get("player"), entry


def methods_min():
    return METHODS_MIN


def tracker_min_n():
    return 8 if active_sport() == "NFL" else TRACKER_MIN_N


def nfl_loose_mode():
    """Week-one NFL: learn, don't copy MLB tightness."""
    return active_sport() == "NFL"

HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
ALIGN_EVENTS_FILE = "girl_magic_align_events.json"  # NEW. Never writes odds history.
TAKE_LEDGER_FILE = "girl_magic_take_ledger.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"
PREFERRED = {"fanduel", "draftkings", "betmgm", "hardrockbet", "caesars", "fanatics", "bet365"}
CORE_BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM", "fanatics": "Fanatics", "bet365": "Bet365"}
# Ticket = book we buy. MGM is signal-only (11% as ticket vs 13% baseline).
TICKET_BOOKS = {"draftkings", "fanduel", "hardrockbet", "fanatics", "bet365"}
VALUE_BOOKS = {"draftkings", "fanduel", "hardrockbet", "fanatics", "bet365"}
VALUE_BOOK_LABELS = {"DK", "FD", "HardRock", "Fanatics", "Bet365"}
SIGNAL_ONLY_BOOKS = {"betmgm"}
# Odds API uses different keys for the same books - map only
BOOK_ALIASES = {
    "bet365_au": "bet365",
    "bet365_uk": "bet365",
    "bet365_us": "bet365",
    "williamhill_us": "caesars",
    "hardrockbet_oh": "hardrockbet",
    "hardrockbet_nj": "hardrockbet",
    "hardrockbet_az": "hardrockbet",
    "hardrockbet_fl": "hardrockbet",
    "fanatics": "fanatics",
    "fanaticssportsbook": "fanatics",
    "fanatics_sportsbook": "fanatics",
    "fanatics_az": "fanatics",
    "fanatics_nj": "fanatics",
    "fanatics_il": "fanatics",
    "fanatics_pa": "fanatics",
    "fanatics_mi": "fanatics",
    "fanatics_oh": "fanatics",
    "fanatics_ny": "fanatics",
}

def normalize_book(key):
    k = str(key or "").lower().strip()
    if "bet365" in k or k in ("365", "b365", "bet_365") or k.replace(" ", "") in ("bet365", "b365"):
        return "bet365"
    if "fanatic" in k:
        return "fanatics"
    if "hardrock" in k:
        return "hardrockbet"
    if "draftking" in k or k == "dk":
        return "draftkings"
    if "fanduel" in k or k == "fd":
        return "fanduel"
    if "betmgm" in k or k == "mgm":
        return "betmgm"
    return BOOK_ALIASES.get(k, k)
LATE_BOOKS = {"fanduel", "draftkings", "betmgm", "fanatics"}
# ── Board gates (re-eval Tracker 2026-08-25) ─────────────────
# Baseline TAKE IT ~11% (n=256). Promote 25s / Exact / multi-book / FD combos.
# Demote 50s from priority (10% / 9% on TAKE). DK 10 = core only (6% on TAKE alone).
EDGE_MIN = 50
EDGE_SOFT = 30  # heavy stacks that still include a PRIORITY method
# Price lanes from Tracker 9/04: +400s 21% · +500s 19% · +600s 15% · +700s 11% · +1000+ 5%
SWEET_PRICE_MAX = 699   # +500-650 is the long number that still hits
LONG_PRICE = 700        # needs extra filters
JUNK_PRICE = 1000       # flyer lane starts here
FLYER_MAX = 1500        # +1000-1500 TAKE IT only with a priority tag
LONG_OK_ENDS = {10, 25, 50, 70, 75, 90}
LONG_DEAD_ENDS = {0, 30, 40}
METHODS_MIN = 2
NAME_METHODS_MIN = 3
NAME_MAX_PAIRS = 50
OUTLIER_GAP = 150
BOOK_CLUSTER_GAP = 50  # max spread across focus books to count as 'tight'
REFRESH_MINUTES = 20
FD_MIN = 400
MOVE_PRICE_MIN = 500
# 0.5 HR Over sanity - reject absurd API longshots (not real pregame 1HR prices)
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
TEAM_PICK_MIN_SCORE = 30  # floor pick: 1 per team when nobody greened; not TAKE IT
SCORE_TAKE_OVERRIDE = 85  # fat stack can green even on a dead 30 / long number ≤999
SCORE_SOFT_TAKE = 85      # was 70 — that made TAKE ≈ WATCH. 85+ only.

# PRIORITY = must have >=1 to unlock TAKE IT
# Tracker 9/10: MGM-as-ticket 11% (−1). MGM 50 book×ending 7% (−5). MGM 00 8%.
# Keep MGM 25 / Exact / FD / DK as unlocks. 50s and 00s are tags only.
# 9/13 eval: TAKE needs 2+ of these. One tag = WATCH. HardRock/Caesars endings are noise.
TAKE_STAMP_METHODS = {
    "DK 10",
    "MGM 25", "MGM 50", "MGM 75",
    "Match 25", "Match 50", "Match 75",
    "MGM Exact", "Exact Match",
    "Last one left", "Stayed in the group",
    "FD Pattern", "FD 600", "FD+MGM classic",
    "Fanatics Rogue",
}
# Week 1 NFL: agreement + MGM 25/75. FD Pattern almost absent. Last one left 0/7.
NFL_STAMP_METHODS = {
    "DK FD-style",
    "Books tight", "Multi-book method", "Multi-book Shorten",
    "MGM 25", "Match 25", "MGM 75", "Match 75",
    "MGM Exact",
    "DK 10",
    "Fanatics Rogue",
    "Stayed in the group",
}

PRIORITY_METHODS = {
    "MGM 25", "Match 25", "MGM Exact",
    "DK 10",
    "FD Pattern", "FD 600", "FD+MGM classic",
    "Multi-book Shorten",
    "Books tight",
    "Caesars Classic", "HardRock Heater", "Fanatics Rogue",
    "FD 90",
    "EV Premium", "Kelly Premium",
}
TAKE_HOT_ENDS = {10, 25, 50, 75, 90}  # ticket ending (DK/FD/HR). MGM-50 *method* is still support-only
TAKE_STRONG_BUCKETS = {"+400s", "+500s", "+600s"}  # +600s need a real priority tag, not MGM juice
TAKE_STRONG_BOOKS = {"fanduel", "draftkings", "hardrockbet", "fanatics", "caesars"}
BOOK_PERSONALITY = {
    "Fanatics Rogue", "Caesars Classic", "HardRock Heater",
    "FD 90", "FD 40", "FD 50",
    "MGM 60", "MGM 10", "MGM 40",
}
HOT_BOOK_ENDS = {
    "caesars": {25, 75, 90},
    "hardrockbet": {25, 75, 90},
    "fanduel": {40, 50, 90},
    "betmgm": {10, 40, 60},
}
# PREMIUM = counts as core (still need >=1 PRIORITY + edge for TAKE IT)
TAKE_IT_STRONG = {
    "Match 25", "MGM 25",
    "DK 10",
    "FD 600", "FD Pattern",
    "Multi-book method",
    "FD+MGM classic",
    "MGM Exact",
    "Multi-book Shorten",
    "Caesars Classic", "HardRock Heater", "Fanatics Rogue",
    "FD 90", "FD 50",
    "EV Premium", "Kelly Premium",
}
# SUPPORT = tagged / WATCH / Tracker only - never core, never unlocks alone
SUPPORT_ONLY = {
    "Books tight", "Exact Match", "All books same",
    "DK FD-style", "Same on 3+ books",
    "Match 75", "MGM 75",
    "Match 50", "MGM 50",
    "Match 00", "MGM 00",
    "Stayed in the group",
    "Last one left",
    "Fanatics Drift",
    "FD 40", "MGM 60", "MGM 10", "MGM 40",
    "EV Support", "Kelly Support", "EV Caution", "Kelly Caution",
    "Trend Heating", "Trend Cooling", "Trend Chaotic",
    "B365 over HardRock", "B365 over MGM", "Fanatics over pack", "HardRock over pack",
    "Caesars 90", "HardRock 50", "HardRock 00",
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
    "Caesars Classic", "HardRock Heater", "Fanatics Rogue",
    "FD 90", "FD 50", "FD 40", "MGM 60", "MGM 10", "MGM 40",
    "B365 over HardRock", "B365 over MGM", "Fanatics over pack", "HardRock over pack",
    "Mispriced line", "Caesars 90", "HardRock 50", "HardRock 00",
}
FD_ENDINGS = (10, 20, 30, 60, 70, 90)
MGM_ENDINGS = (0, 25, 50, 75)

def is_core_method(m):
    """Premium only - support/noise do not inflate core_count.
    NFL week 1: support tags still count so the board can learn."""
    m = normalize_method_name(m)
    if m in NOISE_METHODS:
        return False
    if m in SUPPORT_ONLY:
        return nfl_loose_mode()
    if m.startswith("FADE") or m.startswith("FD under"):
        return False
    if m.startswith("Outlier") or m.startswith("Stuck") or m.startswith("Same ending"):
        return False
    if m.startswith("Shortening") or m.startswith("Lengthening"):
        return False
    if m in TAKE_IT_STRONG:
        return True
    return nfl_loose_mode() and bool(m)

def normalize_method_name(m):
    m = str(m)
    if m.startswith("Stayed in group") or m == "Stayed in the group":
        return "Stayed in the group"
    return m

def count_core_methods(meths):
    return len({normalize_method_name(m) for m in meths if is_core_method(m)})

def has_priority_method(methods):
    """Step 1+3: TAKE IT requires >=1 priority tag from tracker winners."""
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
        elif m in BOOK_PERSONALITY:
            families.add("book_personality")
        else:
            families.add(m)
    return families



def long_price_block(best_price, methods=None, book_prices=None):
    """Why a long number cannot be TAKE IT. None = price is fine."""
    try:
        p = abs(int(best_price))
    except Exception:
        return None
    end = last_two(p)
    books = {normalize_book(b) for b in (book_prices or {})}
    real = books & {"draftkings", "fanduel", "betmgm"}
    if p > FLYER_MAX:
        return f"+{p} is past +{FLYER_MAX} - leave it"
    if p >= JUNK_PRICE:
        if not has_priority_method(methods or []):
            return f"+{p} flyer needs a priority tag"
        if len(real) < 2:
            return f"+{p} flyer needs DK/FD/MGM on at least 2 books"
        return None
    if p >= LONG_PRICE:
        if end in LONG_DEAD_ENDS:
            return f"+{p} ends {end:02d} - dead ending on long price"
        if end not in LONG_OK_ENDS:
            return f"+{p} needs ending 10/25/50/70/75/90"
        if len(real) < 2:
            return f"+{p} needs DK/FD/MGM on at least 2 books - not HR-only"
        if not has_priority_method(methods or []):
            return f"+{p} needs a priority tag"
    return None

def nfl_price_ok(best_price):
    """NFL Anytime TD: +115 and up. Minus prices are chalk — never TAKE."""
    try:
        p = int(best_price)
    except Exception:
        return False
    return p >= 115

def stamp_set():
    return NFL_STAMP_METHODS if active_sport() == "NFL" else TAKE_STAMP_METHODS

def stamp_count(methods):
    ms = {normalize_method_name(m) for m in (methods or [])}
    return len(ms & stamp_set()), ms


def qualifies_take_it(core_count, methods, edge=0, best_price=None, book_prices=None, best_book=None, score=0):
    """9/13: 2+ stamp methods. Ticket = DK / HardRock / Fanatics-Rogue. FD longest = fade the buy."""
    stamps, ms = stamp_count(methods)
    try:
        if best_price is not None and int(best_price) < 115:
            return False
    except Exception:
        return False
    need = methods_min()
    if stamps < 2:
        return False
    if core_count < need and stamps < 2:
        return False
    bk = normalize_book(best_book) if best_book else None
    if not bk and book_prices:
        best_dec = -1
        for k, px in (book_prices or {}).items():
            dec = american_to_decimal(px) or -1
            if dec > best_dec:
                best_dec, bk = dec, normalize_book(k)
    if bk and (bk in SIGNAL_ONLY_BOOKS or "betmgm" in str(bk)):
        # MGM can sit on the card as a tag. It cannot be the ticket that greens TAKE IT.
        return False
    fn = fanatics_price_logic(book_prices)
    if fn.get("watch_only"):
        return False
    if bk == "caesars":
        return False
    if active_sport() == "NFL":
        if bk and bk not in {"draftkings", "fanduel", "hardrockbet", "fanatics"}:
            return False
    else:
        if bk == "fanduel":
            return False
        if bk and bk not in {"draftkings", "hardrockbet", "fanatics"}:
            return False
    # Fanatics BEST +500 with DK/FD/MGM on the card (even mid) can still TAKE
    if bk == "fanatics" and not fn.get("allow_take") and not fn.get("matches"):
        if not (fn.get("way_over_mgm") and not fn.get("alone")):
            return False
    try:
        sc = int(score or 0)
    except Exception:
        sc = 0
    pri = bool(ms & PRIORITY_METHODS)
    end = last_two(best_price)
    hot = end in TAKE_HOT_ENDS or end in (0, 20, 30, 60)
    if active_sport() == "NFL":
        if not nfl_price_ok(best_price):
            return False
        try:
            px = abs(int(best_price or 0))
        except Exception:
            px = 0
        if px >= 1000:
            return False
        if end in (75,) and stamps < 3:
            return False
        if bk == "fanatics":
            if end == 0:
                return False
            if not fn.get("allow_take") and not fn.get("way_over_mgm"):
                return False
        return True
    if not pri and sc < SCORE_SOFT_TAKE:
        return False
    try:
        px = abs(int(best_price or 0))
    except Exception:
        px = 0
    if px and (px < 400 or px > 850):
        if stamps < 3:
            return False
    bucket = price_bucket(best_price)
    if bucket in ("+400s", "+500s"):
        pass
    elif bucket == "+600s":
        # 14% lane — only if a real priority tag fired (not MGM-as-ticket)
        if not pri:
            return False
    elif 500 <= abs(int(best_price or 0)) <= 900 and hot and pri:
        # long-ball lane: personality or EV/Kelly + score 70
        value_ok = bool(ms & {"EV Premium", "Kelly Premium", "EV Support"})
        pers_ok = bool(ms & BOOK_PERSONALITY)
        if not (pers_ok or value_ok):
            if sc < SCORE_TAKE_OVERRIDE:
                return False
        elif sc < SCORE_SOFT_TAKE:
            return False
    elif sc < SCORE_TAKE_OVERRIDE:
        return False
    if end is None or end not in TAKE_HOT_ENDS:
        if sc >= SCORE_SOFT_TAKE and pri:
            return True
        return False
    return True


def elite_take_ok(item):
    """Benford + numerology required for TAKE. Never unlock TAKE by themselves."""
    if not item.get("is_bet"):
        return False
    bf = item.get("benford") or {}
    if bf.get("tag") != "Authentic" and bf.get("aligned") is not True:
        return False
    tag = str(item.get("num_tag") or "")
    if "name+price" not in tag:
        return False
    return True


def board_gate_checklist(item):
    """Display-only pass/fail of the live Board gates. Does not change is_bet."""
    methods = item.get("methods") or []
    core = int(item.get("method_count") or count_core_methods(methods))
    bk = normalize_book(item.get("best_book"))
    end = last_two(item.get("best_price"))
    sc = int(item.get("score") or 0)
    bucket = price_bucket(item.get("best_price"))
    bf = item.get("benford") or {}
    authentic = bf.get("tag") == "Authentic" or bf.get("aligned") is True
    num_ok = "name+price" in str(item.get("num_tag") or "")
    pri = has_priority_method(methods)
    book_ok = bool(bk) and bk in TAKE_STRONG_BOOKS and bk not in SIGNAL_ONLY_BOOKS
    hot = end in TAKE_HOT_ENDS
    lane_ok = bucket in ("+400s", "+500s") or (bucket == "+600s" and pri) or sc >= SCORE_TAKE_OVERRIDE
    rows = [
        (core >= methods_min(), f"{methods_min()}+ premium methods ({core})"),
        (book_ok, f"Strong book ({book_label(bk) if bk else 'none'})"),
        (hot, f"Hot ending ({end if end is not None else '—'})"),
        (pri or sc >= SCORE_SOFT_TAKE, "Priority tag or score ≥ 70"),
        (sc >= SCORE_SOFT_TAKE, f"Petty Score {sc}"),
        (authentic, "Benford Authentic"),
        (num_ok, "Numerology name+price"),
        (lane_ok, f"Price lane {bucket}"),
    ]
    bits = []
    for ok, label in rows:
        mark = "✅" if ok else "❌"
        cls = "gate-yes" if ok else "gate-no"
        bits.append(f'<span class="gate {cls}">{mark} {label}</span>')
    return '<div class="gate-row">' + "".join(bits) + "</div>"


def why_this_call(label, item):
    if label in ("TAKE IT", "Take it"):
        return "Why TAKE: 2+ premium + allowed ticket book + hot ending / score hold. Green list."
    if label == "LEAN" or "LEAN" in str(item.get("why") or ""):
        return "Why LEAN: methods fired but score/edge/book did not clear the full TAKE gate."
    if label == "WATCH":
        return "Why WATCH: fewer than 2 premium methods. Log it. Do not buy from this card."
    if label == "DON'T":
        return "Why DON'T: Shop price is short vs fair or the number is in the junk lane."
    return "Why PASS: enough tags to stay on the page, not enough to buy."

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
    """Trifecta: DK + MGM + FD tags. Score bonus only - does NOT gate TAKE IT."""
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
    tips = {
        "DK 10": "DraftKings price ends in 10",
        "B365 850": "Bet365 is exactly +850",
        "B365 25": "Bet365 same-team pair/trio ending 25",
        "B365 50": "Bet365 same-team pair/trio ending 50",
        "B365 75": "Bet365 same-team pair/trio ending 75",
        "B365 Exact": "Same exact Bet365 price, same team",
        "B365 over HardRock": "Bet365 number longer than Hard Rock",
        "FD Pattern": "FanDuel ≥ +400 ending 10/20/30/60/70/90",
        "FD 600": "FanDuel exact +600",
        "MGM 25": "BetMGM same-team group ending 25",
        "MGM Exact": "Same exact MGM price, same team",
        "Multi-book Shorten": "Price shortened on 2+ books",
        "Books tight": "Focus books clustered within 50 pts",
        "Exact Match": "Same American price on 2+ books",
        "Fanatics Rogue": "Fanatics longest by 40+ on a long-ball hot ending",
        "Caesars Classic": "Caesars best ticket + ending 25/75/90",
        "HardRock Heater": "HardRock best ticket + ending 25/75/90",
        "FD 90": "FanDuel ending 90",
        "Fanatics Drift": "Fanatics off the cluster — info only",
    }
    bits = []
    for m in seen[:limit]:
        tip = tips.get(m, m)
        show = TAG_DISPLAY.get(m, m)
        bits.append(f'<span class="tag {method_tag_class(m)}" title="{tip}">{show}</span>')
    return "".join(bits)

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


# ── Petty layer (display only — never gates TAKE IT) ─────────
PETTY_FAMILIES = {
    "Classic Girl Magic": {
        "MGM 25", "MGM 50", "MGM Exact", "Match 25", "Match 50",
        "FD Pattern", "FD 600", "DK 10", "FD+MGM classic",
    },
    "Petty Pressure": {
        "Multi-book Shorten", "Multi-book method", "Books tight",
        "Exact Match", "All books same", "Same on 3+ books",
    },
    "Drama Queens": {
        "Gone Missing", "Just Appeared", "Added Late",
        "FADE · FD highest", "FADE · Shot way up", "FADE · Drop >100",
    },
    "Cute But Not Serious": {
        "Match 75", "MGM 75", "Same First", "Same Last",
        "Cross Init", "Same Init", "Double Init",
    },
}
FAMILY_EMOJI = {
    "Classic Girl Magic": "👑",
    "Petty Pressure": "💅",
    "Drama Queens": "🎭",
    "Cute But Not Serious": "🧸",
}
PETTY_COPY = {
    "TAKE IT": "Run it, baddie",
    "TAKE": "Run it, baddie",
    "LEAN": "Cute but maybe",
    "DON'T": "Girl no",
    "WATCH": "Keep an eye, queen",
    "PASS": "Not today, babe",
    "Board": "Who’s on the Board 💅",
    "Shop": "Where the Money Talks 💸",
    "Score": "Petty Score",
    "Take it": "Run it, baddie",
}


def petty_on():
    return bool(st.session_state.get("petty_mode", True))


def petty_label(key):
    if not petty_on():
        return key
    return PETTY_COPY.get(key, key)


def decision_pill(label):
    raw = str(label or "")
    key = raw.upper().replace("IT", "IT")
    if raw in ("TAKE IT", "TAKE", "Take it") or "Run it" in raw:
        cls = "pill-take"
    elif raw in ("LEAN", "Cute but maybe"):
        cls = "pill-lean"
    elif raw in ("WATCH", "Keep an eye, queen"):
        cls = "pill-watch"
    elif raw in ("DON'T", "DON’T", "Girl no"):
        cls = "pill-dont"
    else:
        cls = "pill-pass"
    return f'<span class="pill {cls}">{raw}</span>'


HERO_QUOTES = [
    "If the odds look ugly, they probably lying.",
    "Don’t chase vibes — chase value.",
    "Green names are gospel. Everything else is homework.",
    "Chaos pays better than cute numbers.",
]


def daily_quote():
    try:
        i = datetime.strptime(today_az(), "%Y-%m-%d").timetuple().tm_yday
    except Exception:
        i = 0
    return HERO_QUOTES[i % len(HERO_QUOTES)]


def site_hero_html(sport, slate_label, games_n, lock_n, fetch_time):
    live = fetch_time if fetch_time and fetch_time != "no fetch yet" else "no fetch yet"
    breathe = "odds breathing, not sleeping" if live != "no fetch yet" else "odds sleeping until you Fetch"
    if sport == "NFL":
        lane = "🏈 Anytime TD — chaos still pays better."
        icon = "🏈"
    else:
        lane = "💣 We only play 0.5 HR Over — because chaos pays better."
        icon = "⚾"
    return (
        '<div class="site-hero"><div class="site-hero-top"><div>'
        '<div class="site-title">Girl Magic Odds</div>'
        '<p class="site-quote" id="gm-quote">'+daily_quote()+'</p>'
        '<script>setInterval(function(){var q=["If the odds look ugly, they probably lying.","Don’t chase vibes — chase value.","Green names are gospel. Everything else is homework.","Chaos pays better than cute numbers.","Data spoke. Odds agreed. Board decides."];var e=document.getElementById("gm-quote");if(e)e.textContent=q[Math.floor(Date.now()/10000)%q.length];},10000);</script>'
        f'<p class="site-sub">Where intuition meets petty precision. {lane} Green names are gospel.</p>'
        f'<p class="site-live">Last fetch {live} — {breathe}</p>'
        '<div class="site-chips">'
        f'<span class="site-chip sport">{icon} {sport}</span>'
        f'<span class="site-chip">💣 {slate_label}</span>'
        f'<span class="site-chip">📋 {games_n} games</span>'
        f'<span class="site-chip">🔒 Lock {lock_n}</span>'
        '</div></div></div></div>'
    )


def site_section_open(kicker, title, help_text):
    st.markdown(
        f'<div class="site-section"><div class="site-section-head">'
        f'<p class="site-section-kicker">{kicker}</p>'
        f'<div class="site-section-title">{title}</div>'
        f'<p class="site-section-help">{help_text}</p></div>',
        unsafe_allow_html=True,
    )


def site_section_close():
    st.markdown("</div>", unsafe_allow_html=True)


QUEEN_PHRASES = [
    ("💚", "cleared the list", "Passed the Board gates. Green name. Short list. We actually play this one."),
    ("💅", "run it, baddie", "Petty Mode words for TAKE IT. Same math, same green card."),
    ("💖", "score hold", "Petty Score 85+. Keeps a green when Benford or numerology miss. Never invents one."),
    ("💜", "watch it, don’t force the ticket", "Not enough premium methods. Log it. Don’t buy from this card."),
    ("⚪", "close, not cleared", "Tags fired, but book / ending / score / edge didn’t all land. Homework, not a ticket."),
    ("👑", "Queen cleared it", "Same as cleared the list — personality line, not a second scoring system."),
]
TAG_DISPLAY = {
    "Caesars Classic": "Caesars Stamp",
    "MGM Exact": "MGM Signal",
    "FD Pattern": "FD Rhythm",
}


def render_card_guide():
    st.markdown("### 🎨 How to Read a Girl Magic Card — the Color Code")
    st.caption("You didn’t hear this from me. If you’ve read the Glossary, this is how those tags show up visually. Once you know the colors, you know the vibe.")
    st.markdown(
        "| Color | Meaning | Translation |\n"
        "| --- | --- | --- |\n"
        "| 💚 Green | Cleared / strong signal | Run it, baddie. |\n"
        "| 💖 Pink | Petty Score / personality | The vibe is loud. |\n"
        "| 💜 Purple | Queen commentary | Same decision, louder words. |\n"
        "| ❤️ Red | Caution / override | Don’t force it. |\n"
        "| ⚪ Edge | Confidence gap from the pack | How far the ticket sits. |\n"
        "| 🔢 Methods | How many systems agree | The math behind the magic. |"
    )
    st.caption("Keep this quiet. You’re not supposed to know how the colors talk.")


GLOSSARY_V2 = {
    "🧭 How": [
        ("Fetch", "The only moment new odds and Lock snapshots save. Nothing else on the site is live until you Fetch."),
        ("Green / TAKE", "Cleared the list. Two premium stamps. Score hold is 85 now, not 70. This is the ticket."),
        ("Gray / PASS", "Tags fired. Floor missed. Homework, not a dare."),
        ("Eyes / WATCH", "Log it for grade. Do not force the ticket."),
        ("Run It", "The Board. Who cleared. Number next to the name = Board score."),
        ("Money Talks", "Shop. Which book and whether the number is mispriced. Board can be green and Shop can still say DON'T."),
        ("Alignment", "Scouting card. Data + odds + park. Not the bet slip."),
        ("Need One", "0.5 rush / catch / reception, plus money. Separate from HR and Anytime TD."),
        ("Receipts", "Spoke / Locks / Tracker / Time Machine. Grade HIT or MISS. Undo exists."),
        ("Tickets vs Research", "Tickets = TAKE + Shop TAKE. Research = WATCH + LEAN. TAKE must beat Research or we raise the floor."),
        ("Lock Open / Now / Close", "First look / latest pregame / last number before the book vanished at first pitch."),
        ("Ghosts / Late / Fallen", "Showed up late or disappeared vs the last snapshot. Not automatic Takes."),
        ("Petty Mode", "Louder words. Same math."),
    ],
    "💫 Scores": [
        ("Board score", "The ticket stack on Run It. This is the number next to names on the Board. Align does not use this next to the name."),
        ("Align score", "Data + odds + context on the Align tab. Labeled “align score.” Not the Board score."),
        ("Petty Upside / Edge", "How loud the data side is. Footer line on Align cards."),
        ("Active / Whispers / Homework", "MLB: Align 85+ / 70–84 / under 70. NFL: plus-money under +500 / +500+ longshots / rookies and thin volume."),
        ("Weekly adjust", "Receipts + Tracker by tag. Cold stamps get demoted. Hot support can get watched harder. Never blindly keep a dead tell."),
        ("Tickets vs Research", "Recap pills: Tickets = TAKE / Shop TAKE. Research = WATCH / LEAN. Grade both. TAKE must beat Research or the floor goes up."),
        ("Caesars 90 / HardRock 50 / 00", "Other-book endings we now stamp and track. Support until n ≥ 25 and they beat baseline."),
    ],
    "📊 Data": [
        ("⚡ Exit Velocity (EV)", "How hard the ball leaves the bat. 95+ mph = bomb potential."),
        ("💥 Hard-Hit Rate (HH%)", "Share of balls hit 95+ mph. Higher = consistent power."),
        ("🎯 Barrel Rate", "Ideal HR contact — launch angle + EV in the sweet spot."),
        ("💣 HR L7", "Homers in the last 7 games. Short-term heat."),
        ("📈 SLG L7", "Slugging last 7 games. Total-base heat."),
        ("🔥 Heating", "Recent uptick in EV + HH. Trend is cooking."),
        ("💎 Longshot", "Price +500 or longer. Chaos lane."),
        ("Savant pull", "Live Baseball Savant leaderboard. EV, hard-hit, barrel. No CSV drop."),
        ("Contact gate", "Align only keeps hitters who clear EV / HH / barrel plus recent heat. Not the whole slate."),
        ("SP HR/9", "How many homers that starter allows per nine. Higher = friendlier to bats."),
        ("ERA next to SP", "Starter ERA. Context only. Not a ticket by itself."),
    ],
    "🧠 Context": [
        ("⚾ Pitcher Matchup", "Who’s on the mound and whether they feed bombs or kill them. SP HR/9 lives here."),
        ("🏟️ Park Vibe", "Stadium power rating. Hot Porch 💥 bombs fly. Cold Porch 🧊 pitcher’s park."),
        ("💸 Odds Cluster", "Multiple books on the same stamp = market confidence."),
        ("🧠 Board Note", "Board still decides if we ticket it. Align is the whisper, Board is the ticket."),
        ("Wind out / in", "Green arrow = blowing out to CF. Red = blowing in. Yellow = crosswind."),
        ("Temperature", "Open-Meteo at the park. Heat helps the ball carry a little. Not a method."),
        ("Books clustered", "Two or more books on the player. Thin one-book prices get faded."),
    ],
    "⚙️ Splits": [
        ("🏠 Home / Away", "Some bats only cook at home. Some only on the road."),
        ("🌙 Day / Night", "Sun vs lights. Production changes."),
        ("🆚 vs LHP / RHP", "Handedness split. Lefties vs righties."),
    ],
    "💸 Odds": [
        ("FD Pattern", "FanDuel +400+ ending 10/20/30/60/70/90."),
        ("FD 600", "Specific FanDuel number we watch."),
        ("MGM 25 / 50 / 75 / 00", "Same-team BetMGM group endings."),
        ("MGM Exact", "Same MGM price, same team."),
        ("DK 10", "DraftKings ends in 10."),
        ("Multi-book Shorten", "Price dropped on 2+ books."),
        ("Books Tight", "Ticket books within 50 points."),
        ("Exact Match", "Books agree on the number."),
        ("EV Support", "Expected value backing the pick."),
        ("Fanatics vs MGM", "Fanatics 80+ longer than MGM = signal book."),
        ("MGM", "Signal and grouping. Not the ticket we buy."),
        ("Caesars / HardRock / Fanatics", "Ticket books we can buy. Fanatics alone without DK/FD/MGM = Watch, not Take."),
        ("Kelly", "Bankroll confidence. Does not pick the name. 10%+ loud, under 1% homework."),
        ("I Just Need One", "0.5 rush / rec / reception lines at +100 or higher. Board clearance is still manual."),
        ("B365 over HardRock", "SUPPORT only. Bet365 longer than Hard Rock. Does not green a ticket alone."),
        ("B365 over MGM", "SUPPORT only. Bet365 longer than MGM. Signal, not a Take."),
        ("Fanatics over pack", "SUPPORT only. Fanatics 100+ longer than the DK/FD/MGM/HR/365 pack. Drift tell, not main-bitch energy."),
        ("HardRock over pack", "SUPPORT only. Hard Rock 50+ longer than the rest of the pack. Look-at-it stamp, not a Take."),
        ("Mispriced line", "The number is off the pack. Longer than the other books = extra juice / value. Shorter = you’re paying a tax. Shop is where we judge that. Support stamps flag it. They do not Take by themselves."),
        ("Out of place / outlier", "One book is far from the cluster. Look. Don’t auto-buy."),
        ("Fair / pack", "Where the ticket books sit together. Shop compares your number to that pack."),
        ("Fair line", "Shop’s blended number after the cushion. Not a sportsbook’s posted price."),
        ("Gap", "Posted price minus fair. Fat gap on a long number can still be a flyer, not a Take."),
        ("Kelly", "How loud the bankroll math is. Light / Avoid is not a Board green."),
        ("DON'T / flyer lane", "Shop says do not buy. +1000 and dead 00 on a moon price stay DON'T even if EV looks cute."),
    ],
    "💎 Tags": [
        ("🔥 Heating", "EV + HH trending up."),
        ("🎶 Rhythm", "Digit / book stamp fired."),
        ("🧠 Board Take", "Green on the Board."),
        ("💅 Petty Upside", "High-risk high-style lane."),
        ("💎 Longshot", "+500 or longer."),
        ("Priority / Premium / Support", "Priority can unlock TAKE with 2 premium. Support never greens alone."),
        ("Last one left", "MGM group shrank and this name stayed. Sticky tell."),
        ("Stayed in the group", "Still paired or tripled on MGM all day."),
        ("DK FD-style", "DraftKings priced like a FanDuel pattern ending."),
        ("FD+MGM classic", "FanDuel pattern and an MGM classic ending on the same name."),
        ("Multi-book method", "Same stamp across more than one book."),
        ("FD 90 / 50 / 40", "Exact FanDuel endings we track. 90 has been the loud one."),
        ("Benford", "Whether the leading digits look natural or forced. Support, not a Take."),
        ("Same initials / Cross / Same name", "Name tricks. Only count if a book method also fired. Prefer different teams."),
        ("Score hold", "Petty Score 85+. Can keep a green when Benford/name miss. Cannot invent a green."),
        ("HOT tile", "Tracker. Hit rate 15%+ vs this sport’s TAKE baseline. Thin n stays unlabeled."),
        ("Baseline", "TAKE hit rate for this sport. Signals above it get the green border."),
    ],
    "🏟️ Park Vibes": [
        ("💥 Hot Porch", "HR factor 130+. Bombs fly."),
        ("🔥 Live Air", "110–129. Ball carries."),
        ("🌬️ Neutral", "90–109. Average park."),
        ("🧊 Cold Porch", "Under 90. Pitcher’s park."),
    ],
    "🏈 NFL": [
        ("🏈 Anytime TD", "The only NFL ticket on Align. Plus money only. Favorites like -175 are off this tab."),
        ("Plus money", "Price +100 or longer. Negative juice does not belong on Align."),
        ("📊 Player Pulse", "Heating / cooling / role / attack in sentences. How they use him right now."),
        ("🎯 Attack Angle", "Anytime TD, receptions + yards, or longshot TD. That’s the lane."),
        ("WR1 / RB1", "Top usage at that position. WR2 / RB2 = second look."),
        ("Targets", "How many times the QB throws his way."),
        ("🐣 Rookie", "Drafted this year. Pop risk, not a free lock."),
        ("🛡️ DVP", "Last 10 games, PER GAME, what that defense gave this position. Also split when that D is home, on the road, and in primetime."),
        ("His last two seasons", "That player’s home / road / primetime totals. Not per game. Different from DVP."),
        ("NFL Show filters", "Active = +100 to +499. Whispers = +500+. Homework = rookies / missing usage."),
    ],
    "⚾ MLB": [
        ("0.5 HR Over", "The only baseball ticket. One homer. Not 2+."),
        ("VS BULLPEN", "Only prints when this hitter has PA vs that team’s current relievers. No fake staff ERA."),
        ("Park Vibe", "Hot Porch / Live Air / Neutral / Cold Porch from HR factor."),
        ("Align vs Board", "Align whispers. Board tickets. Footer shows both numbers labeled."),
        ("Tickets vs Research", "Receipts. What we told people to bet vs what we were only studying."),
        ("Savant / Statcast", "Live EV, hard-hit, barrel. Pulled for you. No CSV."),
        ("Wind vs CF", "Out to center helps. Into center fades. Crosswind is yellow."),
        ("Shop long-ball", "Shop TAKE wants gap ≥ 35. LEAN ≥ 25. +1000 is flyer/DON'T."),
        ("Dead 00 on a moon", "Ending 00 on +1000+ is junk. Shop fades it."),
        ("under +400", "Hits more often because it’s short. Not our chaos lane. Do not promote it."),
    ],
}


def render_mini_glossary():
    st.markdown("### ✨ Girl Magic Glossary 2.0")
    st.caption("Learn the vibe, then roll the slate. On Align, hover a word — the same definitions live on the card.")
    q = st.text_input("Search the vibe…", key="gloss_q")
    cats = list(GLOSSARY_V2.keys())
    cat = st.radio("Category", cats, horizontal=True, key="gloss_cat")
    rows = list(GLOSSARY_V2.get(cat) or [])
    if q.strip():
        needle = q.lower()
        rows = []
        for _, items in GLOSSARY_V2.items():
            for t, d in items:
                if needle in t.lower() or needle in d.lower():
                    rows.append((t, d))
    cols = st.columns(2)
    if not rows:
        st.info("Nothing in the language matched that search.")
        return
    for i, (term, defn) in enumerate(rows):
        with cols[i % 2]:
            st.markdown(
                f'<div class="card" title="{defn}"><div class="card-kicker">GLOSSARY</div>'
                f'<div class="card-name" style="font-size:1.05rem">{term}</div>'
                f'<div class="card-line">{defn}</div></div>',
                unsafe_allow_html=True,
            )
    st.caption("Learn the vibe, then roll the slate.")
    return
    st.markdown("**🔖 Tags**")
    st.markdown(
        "- **FD Pattern** — FanDuel’s rhythm. +400 or higher ending 10/20/30/60/70/90.\n"
        "- **FD 90 / 50 / 40** — those exact FD endings. Don’t ask why, just know they hit.\n"
        "- **MGM 25** — BetMGM same-team group ending 25.\n"
        "- **MGM Exact** — same MGM price, same team.\n"
        "- **DK 10** — DraftKings ends in 10.\n"
        "- **Multi-book Shorten** — price dropped on 2+ books. Somebody knows something.\n"
        "- **Books Tight** — ticket books within 50 points. That’s pressure.\n"
        "- **Caesars Classic / HardRock Heater / Fanatics Rogue** — the long ticket on a hot ending. If you see it, you didn’t hear it from me.\n"
        "- **Fanatics vs MGM** — if Fanatics is WAY HIGHER than MGM (80+), Fanatics is the SIGNAL BOOK.\n"
        "- **Fanatics BEST +500** — ALLOW TAKE even if DK/FD/MGM are mid.\n"
        "- **Fanatics ALONE** (no DK/FD/MGM) — WATCH, not TAKE.\n"
        "- **Fanatics MATCHES DK/FD/MGM** — treat normally."
    )
    st.markdown("**⚙️ Methods (how hard a tag works)**")
    st.markdown(
        "- **Priority** — can unlock TAKE. You’ll need 2 premium.\n"
        "- **Premium / Core** — counts toward the 2-method floor.\n"
        "- **Support** — shown and graded, never greens alone."
    )
    st.markdown("**🔢 Endings**")
    st.markdown(
        "- **25 / 50 / 75 / 90 / 10** — hot ticket endings we play.\n"
        "- **00 / 30 / 40** — usually dead on long prices. Don’t waste your vibe."
    )
    st.markdown("**📚 Books**")
    st.markdown(
        "- **DK / FD / HardRock / Fanatics / Caesars** — tickets we can buy.\n"
        "- **MGM** — signal and grouping tell. Not the ticket."
    )
    st.markdown("**💖 Petty Score**")
    st.markdown("0–100 vibe meter on the stack. Can hold a green at 70. Can’t invent one. If you know, you know.")
    st.markdown("**👑 Queen Commentary**")
    st.markdown("Personality layer. Same decision, louder words. It’s not math — it’s mood.")
    st.markdown("**📈 I JUST NEED ONE — one-play prop scan**")
    st.markdown(
        "Finds rush, receiving, and reception lines sitting at **0.5** with money odds **+100 or higher**. "
        "These are the one-play props — low volume, high vibe. "
        "Only shows **RE-tagged** players (receiving / receptions market, or rushers who also have a receiving number posted). "
        "Board clearance is manual — you decide. If it’s green, it’s gold. If it’s red, it’s homework."
    )
    st.markdown("**💸 Kelly — bankroll confidence**")
    st.markdown(
        "Kelly tells you how loud the value is. It mixes fair probability and book price to show how much of your bankroll a ticket deserves.\n"
        "- 💚 10%+ = strong\n"
        "- 💖 5–10% = medium\n"
        "- 💜 1–5% = light\n"
        "- 🔴 <1% = homework only\n\n"
        "Kelly doesn’t pick the name — it picks the confidence."
    )
    st.caption("Code tab has the long glossary. This is the language you need to roll.")


def render_queen_glossary():
    st.markdown("**Queen Phrase Book**")
    st.caption("Shhh. This is how the Board talks when the math hits. Don’t quote it. Don’t explain it. Just know it.")
    for icon, phrase, meaning in QUEEN_PHRASES:
        st.markdown(f"{icon} **{phrase}**  \n{meaning}")


def explain_card_text(item, label):
    name = item.get("player") or "This player"
    n = int(item.get("method_count") or 0)
    price = format_odds(item.get("best_price"))
    book = book_label(item.get("best_book"))
    score = item.get("score", 0)
    motion = item.get("trend_motion") or "Stable"
    if label in ("TAKE IT", "Take it"):
        vibe = "Queen cleared it."
    elif label == "WATCH":
        vibe = "Queen says watch it — do not force the ticket."
    else:
        vibe = "Queen says close, not cleared."
    widen = "widening" if motion == "Cooling down" else ("shortening / heating up" if motion == "Heating up" else motion.lower())
    return (
        f"{name} shows {n} premium method(s). {book} is the ticket at {price}. "
        f"Odds look {widen}. Petty Score {score}. {vibe}"
    )


def petty_family_for_method(method):
    m = normalize_method_name(method)
    for fam, members in PETTY_FAMILIES.items():
        if m in members:
            return fam
    return None


def petty_family_summary(method_list):
    hits, seen = [], set()
    for m in method_list or []:
        fam = petty_family_for_method(m)
        if fam and fam not in seen:
            seen.add(fam)
            hits.append(fam)
    order = list(PETTY_FAMILIES.keys())
    hits.sort(key=lambda f: order.index(f) if f in order else 99)
    return hits


def petty_family_chips(method_list):
    return " ".join(
        f'<span class="tag tag-family">{FAMILY_EMOJI.get(f, "✨")} {f}</span>'
        for f in petty_family_summary(method_list)
    )


def petty_score(methods, edge, core_count, benford_flag=None):
    """0-100 stack score. Feeds TAKE IT (85+ can hold a green)."""
    base = girl_magic_score(core_count, edge, methods or [])
    ms = {normalize_method_name(m) for m in (methods or [])}
    extra = 0
    if {"FD Pattern", "MGM 25"} <= ms or {"FD Pattern", "Match 25"} <= ms:
        extra += 8
    if {"Multi-book Shorten", "FD 600"} <= ms:
        extra += 10
    if {"Stayed in the group", "Last one left"} <= ms:
        extra += 6
    if ms & {"Caesars Classic", "HardRock Heater", "Fanatics Rogue", "FD 90"}:
        extra += 8
    if ms & {"EV Premium", "Kelly Premium"}:
        extra += 5
    if "Trend Heating" in ms:
        extra += 5
    if "Trend Chaotic" in ms:
        extra += 3
    if "Trend Cooling" in ms and not (ms & {"EV Premium", "Kelly Premium", "Caesars Classic"}):
        extra -= 5
    if ms & {"FD 40", "MGM 00", "EV Caution", "Kelly Caution"}:
        extra -= 5
    tag = ""
    if isinstance(benford_flag, dict):
        tag = str(benford_flag.get("tag") or "")
    if tag.lower() == "authentic":
        extra += 4
    elif tag.lower() == "fake":
        extra -= 10
    return max(0, min(100, base + extra))


def petty_notes_for(item):
    notes = []
    methods = item.get("methods") or []
    ms = {normalize_method_name(m) for m in methods}
    if has_dk_mgm_fd(methods):
        notes.append("trifecta present 👑")
    end = last_two(item.get("best_price"))
    try:
        p = abs(int(item.get("best_price"))) if item.get("best_price") is not None else 0
    except Exception:
        p = 0
    if p >= 700 and end in (10, 25, 75, 90):
        notes.append("long number but hot ending")
    bf = item.get("benford") or {}
    if str(bf.get("tag", "")).lower() == "authentic":
        notes.append("Benford says shape is real")
    if "Stayed in the group" in ms:
        notes.append("MGM group streak")
    if "FD Pattern" in ms or "FD 600" in ms:
        notes.append("FD pattern consistency")
    bucket = price_bucket(item.get("best_price"))
    if str(bf.get("tag", "")).lower() == "authentic" and end in (10, 25, 75, 90) and bucket in ("+400s", "+500s", "+600s"):
        notes.append("Benford Boost: +EV shape today")
    return notes


def collect_petty_alerts(ev_board, results):
    if HAS_NFL_MATH and active_sport() == "NFL":
        extra = nfl_petty_alerts(ev_board, results, limit=8)
        # still keep MGM Exact / shorten from flags
        return extra
    alerts = []
    for r in results or []:
        meths = r.get("methods") or []
        if r.get("type") == "mgm_exact" or "MGM Exact" in meths:
            alerts.append(f"MGM Exact · {r.get('label')}")
        if "Multi-book Shorten" in meths:
            alerts.append(f"Multi-book Shorten · {r.get('label')}")
        reason = str(r.get("reason") or "")
        if "FD under MGM" in meths:
            import re as _re
            m = _re.search(r"by (\d+)", reason)
            if m:
                gap = int(m.group(1))
                # We like FD 10-100 under MGM. Exact 100 on a pile of names is template, not a shout.
                if 25 <= gap <= 90:
                    alerts.append(f"FD under MGM by {gap} · {r.get('label')}")
    for item in ev_board or []:
        ms = set(item.get("methods") or [])
        if "DK 10" in ms and ("FD Pattern" in ms or "FD 600" in ms):
            alerts.append(f"DK 10 + FD Pattern · {item.get('player')}")
        bf = item.get("benford") or {}
        if str(bf.get("tag", "")).lower() == "fake":
            alerts.append(f"Benford Fake · {item.get('player')}")
        books = item.get("book_prices") or {}
        fd, mgm = books.get("fanduel"), books.get("betmgm")
        if fd is not None and mgm is not None:
            try:
                gap = int(mgm) - int(fd)
            except Exception:
                gap = 0
            # Banner the sweet gap only. 100-flat is how books copy each other.
            extra = bool(ms & {"DK 10", "FD Pattern", "FD 600", "MGM Exact", "Exact Match"}) or any(
                str(x).startswith("MGM ") or str(x).startswith("Match ") for x in ms
            )
            if 25 <= gap <= 90 or (10 <= gap <= 99 and extra):
                alerts.append(f"FD under MGM by {gap} · {item.get('player')}")
    seen, out = set(), []
    for a in alerts:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out[:10]


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

FAIR_WEIGHTS = {
    "caesars": 0.30,
    "hardrockbet": 0.25,
    "fanduel": 0.20,
    "draftkings": 0.15,
}
FAIR_OTHER_WEIGHT = 0.10
SHOP_GAP_TAKE_LONG = 50
SHOP_GAP_LEAN_LONG = 25
SHOP_GAP_DONT_LONG = -35
SHOP_GAP_TAKE_MID = 50
SHOP_GAP_LEAN_MID = 40


def american_to_decimal_pos(px):
    try:
        p = int(px)
    except Exception:
        return None
    if p > 0:
        return 1.0 + p / 100.0
    return 1.0 + 100.0 / abs(p)


def compute_market_fair(book_px):
    """Long-ball market fair: avg ticket books + cushion, or weighted if 3+ books."""
    px = {}
    for b, v in (book_px or {}).items():
        try:
            px[normalize_book(b)] = int(v)
        except Exception:
            pass
    lane = [b for b in ("draftkings", "fanduel", "hardrockbet", "fanatics", "caesars") if b in px]
    vals = [px[b] for b in lane] or list(px.values())
    if not vals:
        return None, None, "none"
    fair_base = sum(vals) / len(vals)
    fair_simple = int(round(fair_base + 15))
    wsum = 0.0
    wtot = 0.0
    used_w = 0
    leftover = [b for b in px if b not in FAIR_WEIGHTS]
    for b, w in FAIR_WEIGHTS.items():
        if b in px:
            wsum += w * px[b]
            wtot += w
            used_w += 1
    if leftover:
        share = FAIR_OTHER_WEIGHT / len(leftover)
        for b in leftover:
            wsum += share * px[b]
            wtot += share
    if used_w >= 3 and wtot > 0:
        fair = int(round(wsum / wtot + 10))
        mode = "weighted"
    else:
        fair = fair_simple
        mode = "avg+15"
    dec = american_to_decimal_pos(fair)
    p = (1.0 / dec) if dec else None
    return fair, p, mode


def ev_from_fair(best, fair):
    dec_f = american_to_decimal_pos(fair)
    dec_b = american_to_decimal_pos(best)
    if not dec_f or not dec_b:
        return None, None
    p = 1.0 / dec_f
    ev = p * (dec_b - 1.0) - (1.0 - p)
    b = dec_b - 1.0
    kelly = ((b * p) - (1.0 - p)) / b if b else None
    return ev, kelly


def kelly_style(frac):
    """Display-only tags. frac is full Kelly, not quarter-Kelly units."""
    if frac is None:
        return 0.0, "Avoid", "kelly-avoid"
    try:
        f = float(frac)
    except Exception:
        return 0.0, "Avoid", "kelly-avoid"
    pct = max(0.0, min(100.0, f * 100.0))
    if f > 0.10:
        return pct, "Strong", "kelly-strong"
    if f > 0.05:
        return pct, "Medium", "kelly-med"
    if f > 0.01:
        return pct, "Light", "kelly-light"
    return pct, "Avoid", "kelly-avoid"


def kelly_bar_html(frac):
    pct, tag, css = kelly_style(frac)
    return (
        f'<div class="kelly-line {css}" title="Kelly shows bankroll confidence. Higher Kelly = stronger long-ball value.">'
        f'KELLY — {pct:.1f}% ({tag.lower()})</div>'
    )


def value_method_tags(ev, kelly):
    tags = []
    if ev is None:
        return tags
    if ev > 0.05:
        tags.append("EV Premium")
    elif ev > 0:
        tags.append("EV Support")
    else:
        tags.append("EV Caution")
    if kelly is None:
        return tags
    if kelly > 0.05:
        tags.append("Kelly Premium")
    elif kelly > 0:
        tags.append("Kelly Support")
    else:
        tags.append("Kelly Caution")
    return tags


def shop_price_action(best, fair, book_prices=None, ev=None, kelly=None):
    if best is None or fair is None:
        return "WATCH", "no fair", "shop-mkt"
    try:
        bp = abs(int(best))
    except Exception:
        bp = 0
    gap = int(best) - int(fair)
    long_ball = bp >= 500
    take_g = SHOP_GAP_TAKE_LONG if long_ball else SHOP_GAP_TAKE_MID
    lean_g = SHOP_GAP_LEAN_LONG if long_ball else SHOP_GAP_LEAN_MID
    dont_g = SHOP_GAP_DONT_LONG if long_ball else -40
    if ev is not None and kelly is not None and ev <= 0 and kelly <= 0:
        return "DON'T", f"EV {ev:+.2f} · Kelly {kelly:+.2f} both dead", "shop-dont"
    if bp >= JUNK_PRICE:
        return "DON'T", f"+{bp} junk lane · fair {format_odds(fair)}", "shop-dont"
    if bp >= LONG_PRICE:
        end = last_two(bp)
        books = {normalize_book(b) for b in (book_prices or {})}
        real = books & {"draftkings", "fanduel", "betmgm"}
        if end in LONG_DEAD_ENDS or (end not in LONG_OK_ENDS) or len(real) < 2:
            if gap >= lean_g and ev and ev > 0:
                return "LEAN", f"longshot lean {format_odds(best)} · fair {format_odds(fair)}", "shop-lean"
            return "DON'T", f"long + bad shape {format_odds(best)}", "shop-dont"
    if gap >= take_g:
        return "TAKE", f"take at {format_odds(best)} · fair {format_odds(fair)} · +{gap}", "shop-take"
    if gap >= lean_g:
        return "LEAN", f"lean {format_odds(best)} · fair {format_odds(fair)} · +{gap}", "shop-lean"
    if gap <= dont_g:
        return "DON'T", f"don't take {format_odds(best)} · fair {format_odds(fair)} · {gap}", "shop-dont"
    return "MARKET", f"market {format_odds(best)} · fair {format_odds(fair)} · {gap:+d}", "shop-mkt"

SHOP_BOOKS = [
    ("draftkings", "DK"),
    ("fanduel", "FD"),
    ("betmgm", "MGM"),
    ("bet365", "365"),
    ("fanatics", "FN"),
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
        best, best_book = smart_best(prices, books) if len(prices) >= 2 else pick_ticket(prices, books)
        if best is None:
            best, best_book = prices[0], books[0]
        try:
            med = int(statistics.median(prices)) if len(prices) >= 2 else int(best)
        except Exception:
            med = int(best) if best is not None else None
        fair, fair_p, fair_mode = compute_market_fair(book_px)
        if fair is None:
            fair, fair_p, fair_mode = med, american_implied(med), "median"
        ev, kelly_f = ev_from_fair(best, fair)
        action, why, cls = shop_price_action(best, fair, book_px, ev, kelly_f)
        edge = (int(best) - int(fair)) if best is not None and fair is not None else 0
        ku, klabel, kfull = kelly_units(fair_p, best)
        kpct, ktag, kcss = kelly_style(kelly_f)
        vtags = value_method_tags(ev, kelly_f)
        if ktag == "Avoid" and action == "TAKE":
            action, why, cls = "LEAN", why + " · Kelly avoid (thin value)", "shop-lean"
        rows.append({
            "player": player, "event": event or "", "books": book_px,
            "best": best, "best_book": best_book, "median": med, "fair": fair,
            "fair_mode": fair_mode,
            "fair_prob": fair_p, "edge": edge, "ev": ev, "kelly_frac": kelly_f,
            "value_tags": vtags,
            "action": action, "why": why,
            "cls": cls, "n_books": len(book_px),
            "ending": last_two(best) if best is not None else None,
            "bucket": price_bucket(best),
            "kelly_u": ku, "kelly_label": ktag, "kelly_full": kfull,
            "kelly_pct": kpct, "kelly_css": kcss,
        })
    rows.sort(key=lambda x: (-x.get("edge", 0), x.get("player") or ""))
    return rows


NFL_QB_BLOCK = {
    "baker mayfield", "bryce young", "caleb williams", "cooper rush",
    "patrick mahomes", "jordan love", "dak prescott", "jalen hurts",
    "lamar jackson", "joe burrow", "josh allen", "patrick mahomes",
    "justin herbert", "geno smith", "kyler murray", "bo nix",
    "cj stroud", "c.j. stroud", "trevor lawrence", "tua tagovailoa",
    "matthew stafford", "jared goff", "sam darnold", "daniel jones",
    "drake maye", "jayden daniels", "michael penix", "michael penix jr",
    "aaron rodgers", "russell wilson", "kirk cousins", "justin fields",
    "anthony richardson", "will levis", "aidan oconnell", "aidan o'connell",
    "spencer rattler", "mac jones", "tyrod taylor", "marcus mariota",
    "joe flacco", "aaron rodgers", "mason rudolph", "skylar thompson",
    "kenny pickett", "desmond ridder", "sam howell", "drew lock",
    "davis mills", "tommy devito", "mitchell trubisky", "jacoby brissett",
    "jameis winston", "gardner minshew", "andy dalton", "nick mullens",
    "brock purdy", "tua tagovailoa",
}

def is_nfl_qb(name):
    n = clean_name(name).lower()
    if n in NFL_QB_BLOCK:
        return True
    for q in NFL_QB_BLOCK:
        if names_match(name, q) or names_match(n, q):
            return True
    return False


NEED_ONE_PERIOD_BITS = (
    "1st", "2nd", "3rd", "4th", "first_half", "second_half", "firsthalf", "secondhalf",
    "_1h", "_2h", "_1q", "_2q", "_3q", "_4q", "q1", "q2", "q3", "q4",
    "quarter", "period", "1q-", "2q-", "3q-", "4q-", "-1h", "-2h",
    "halftime", "1sthalf", "2ndhalf",
)

def is_full_game_prop(blob):
    s = str(blob or "").lower().replace(" ", "")
    return not any(b.replace("_", "") in s or b in str(blob or "").lower() for b in NEED_ONE_PERIOD_BITS)


NEED_ONE_MAJOR = {
    "draftkings", "fanduel", "hardrockbet", "fanatics", "caesars", "betmgm", "bet365",
}
NEED_ONE_LABELS = {
    "Rush Yards": "0.5 Rush Yards",
    "Receiving Yards": "0.5 Receiving Yards",
    "Receptions": "0.5 Receptions",
}


def need_one_is_live(row):
    raw = str(row.get("commence_time") or "")
    if not raw:
        return False
    try:
        ts = raw.replace("Z", "+00:00")
        start = datetime.fromisoformat(ts)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= start
    except Exception:
        return False


def need_one_re_players(rows):

    names = set()
    for r in rows or []:
        if r.get("prop_type") in ("Receiving Yards", "Receptions"):
            names.add(clean_name(r.get("player") or ""))
    return names


def need_one_call(kelly_f):
    try:
        k = float(kelly_f or 0) * 100
    except Exception:
        k = 0
    if k > 10:
        return "TAKE", "💚", "bet"
    if k >= 5:
        return "LEAN", "💖", "watch-card"
    if k >= 1:
        return "WATCH", "💜", "watch-card"
    return "DON'T", "🔴", "skip"



def log_need_one(items):
    """Persist TAKE/LEAN one-play props so this tab can learn."""
    rows = load_results()
    today = today_az()
    added = 0
    for it in items or []:
        if it.get("action") not in ("TAKE", "LEAN"):
            continue
        player = it.get("player") or ""
        if not player:
            continue
        src = "need_one_take" if it["action"] == "TAKE" else "need_one_lean"
        already = any(
            r.get("date") == today
            and r.get("source") == src
            and names_match(r.get("player") or "", player)
            and str(r.get("market") or "") == str(it.get("prop_type") or "need_one")
            for r in rows
        )
        if already:
            continue
        rows.append({
            "id": f"{today}_{player}_{src}_{it.get('prop_type')}_{int(it.get('best') or 0)}",
            "date": today, "time": now_az(), "player": player,
            "score": 0, "edge": int(it.get("edge") or 0),
            "best_price": it.get("best"), "best_book": it.get("best_book"),
            "book_prices": dict(it.get("books") or {}),
            "ending": last_two(it.get("best")) if it.get("best") is not None else None,
            "methods": [f"Need One {it.get('action')}", it.get("label") or it.get("prop_type")],
            "core": 0,
            "result": "PENDING", "source": src, "logged_at": now_utc_iso(),
            "price_source": "need_one",
            "sport": "NFL",
            "market": it.get("prop_type") or "need_one",
            "event": it.get("event") or "",
        })
        added += 1
    if added:
        save_results(rows)
    return added


def render_need_one_tracker():
    """Bottom of I JUST NEED ONE — hit rates for this tab only."""
    rows = [r for r in load_results() if str(r.get("source") or "").startswith("need_one")]
    st.markdown("#### I JUST NEED ONE — tracking")
    if not rows:
        st.caption("No Need One rows logged yet. TAKE/LEAN on this scan get saved automatically.")
        return
    def _rate(src):
        sub = [r for r in rows if r.get("source") == src and r.get("result") in ("HIT", "MISS")]
        h = sum(1 for r in sub if r.get("result") == "HIT")
        n = len(sub)
        pct = f"{100*h/n:.0f}%" if n else "—"
        return h, n, pct
    th, tn, tp = _rate("need_one_take")
    lh, ln, lp = _rate("need_one_lean")
    pend = sum(1 for r in rows if r.get("result") == "PENDING" and r.get("date") == today_az())
    st.markdown(
        f'<div class="petty-row">'
        f'<div class="petty-box"><div class="petty-num">{tp}</div><div class="petty-label">NEED ONE TAKE %</div></div>'
        f'<div class="petty-box"><div class="petty-num">{tn}</div><div class="petty-label">TAKE GRADED</div></div>'
        f'<div class="petty-box"><div class="petty-num">{lp}</div><div class="petty-label">NEED ONE LEAN %</div></div>'
        f'<div class="petty-box"><div class="petty-num">{ln}</div><div class="petty-label">LEAN GRADED</div></div>'
        f'<div class="petty-box"><div class="petty-num">{pend}</div><div class="petty-label">PENDING TODAY</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    by_m = {}
    for r in rows:
        if r.get("result") not in ("HIT", "MISS"):
            continue
        m = r.get("market") or "prop"
        by_m.setdefault(m, {"hit": 0, "miss": 0})
        by_m[m]["hit" if r["result"] == "HIT" else "miss"] += 1
    if by_m:
        bits = []
        for m, s in sorted(by_m.items(), key=lambda x: -(x[1]["hit"]+x[1]["miss"])):
            n = s["hit"] + s["miss"]
            bits.append(f"{m}: {s['hit']}/{n}")
        st.caption("By prop · " + " · ".join(bits))
    else:
        st.caption("Percents fill after Auto-grade or HIT/MISS on Results (Need One rows).")


def build_need_one_board(rows, want_types):
    """0.5 rush / receiving / receptions. Plus money. RE tag. No Board gate."""
    if not rows or not want_types:
        return []
    major = NEED_ONE_MAJOR
    re_names = need_one_re_players(rows)
    by = defaultdict(list)
    for r in rows:
        ptype = r.get("prop_type")
        if ptype not in want_types:
            continue
        try:
            price = int(r.get("price"))
            pt = float(r.get("point") if r.get("point") is not None else 0.5)
        except Exception:
            continue
        if abs(pt - 0.5) > 0.01:
            continue
        if price < 100:
            continue
        bk = normalize_book(r.get("book"))
        if bk not in major:
            continue
        player = r.get("player") or ""
        if ptype == "Rush Yards" and clean_name(player) not in re_names:
            continue
        if ptype in ("Receiving Yards", "Receptions"):
            pass  # market itself is the RE tag
        key = (player, r.get("event") or "", ptype)
        by[key].append((bk, price))
    out = []
    for (player, event, ptype), pairs in by.items():
        book_px = {}
        for bk, price in pairs:
            book_px[bk] = price
        if not book_px:
            continue
        # 0.5 yard/catch lines live around +100 to +300. +1000 is a different market leaking in.
        book_px = {b: p for b, p in book_px.items() if 100 <= int(p) <= 400}
        if not book_px:
            continue
        if len(book_px) < 2:
            continue
        books = list(book_px.keys())
        prices = list(book_px.values())
        best, best_book = smart_best(prices, books) if len(prices) >= 2 else pick_ticket(prices, books)
        if best is None:
            best, best_book = prices[0], books[0]
        try:
            if int(best) < 100:
                continue
        except Exception:
            continue
        try:
            med = int(statistics.median(prices)) if len(prices) >= 2 else int(best)
        except Exception:
            med = int(best)
        fair, fair_p, fair_mode = compute_market_fair(book_px)
        if fair is None:
            fair, fair_p, fair_mode = med, american_implied(med), "median"
        ev, kelly_f = ev_from_fair(best, fair)
        action, emoji, cls = need_one_call(kelly_f)
        gap = (int(best) - int(fair)) if best is not None and fair is not None else 0
        out.append({
            "player": player,
            "event": event,
            "prop_type": ptype,
            "label": NEED_ONE_LABELS.get(ptype, ptype),
            "books": book_px,
            "best": best,
            "best_book": best_book,
            "fair": fair,
            "edge": gap,
            "ev": ev,
            "kelly_frac": kelly_f,
            "action": action,
            "emoji": emoji,
            "cls": cls,
            "n_books": len(book_px),
            "re_tag": True,
        })
    out.sort(key=lambda x: (-(x.get("kelly_frac") or 0), -(x.get("edge") or 0), x.get("player") or ""))
    return out


def _need_one_queen(action, hot=False):
    lines = {
        "TAKE": [
            "Queen says: I just need one — run it if it’s green and loud.",
            "Queen says: one play, one vibe, one bag.",
        ],
        "LEAN": [
            "Queen says: math says maybe — keep her close.",
            "Queen says: math says no, but the streets say maybe.",
        ],
        "WATCH": [
            "Queen says: if it’s purple, it’s homework.",
            "Queen says: eyes on it — not a bag yet.",
        ],
        "DON'T": [
            "Queen says: I just need one — but this ain’t it.",
            "Queen says: if it’s red, it’s homework.",
        ],
    }
    pool = list(lines.get(action) or lines["DON'T"])
    if hot:
        pool.insert(0, "Queen says: hot zone — green and loud.")
    # stable per action so the card doesn't flicker every rerun
    idx = (hash(action) + (1 if hot else 0)) % len(pool)
    return pool[idx]



def _need_one_book_row(books):
    if not books:
        return "No book prices on this fetch."
    order = ["draftkings", "fanduel", "betmgm", "fanatics", "hardrockbet", "caesars", "bet365"]
    bits = []
    seen = set()
    for k in order:
        if k in books:
            bits.append("%s %s" % (book_label(k), format_odds(books[k])))
            seen.add(k)
    for k, v in books.items():
        if k in seen:
            continue
        bits.append("%s %s" % (book_label(k), format_odds(v)))
    return " · ".join(bits)


def render_need_one_cards(items):
    if not items:
        st.info("Nothing cleared I JUST NEED ONE. Fetch NFL, then tick a 0.5 box.")
        return
    top = items[0]
    kf0 = float(top.get("kelly_frac") or 0)
    kpct0 = max(0, min(100, kf0 * 100))
    ev0 = top.get("ev")
    ev_s0 = f"{ev0:+.2f}" if ev0 is not None else "—"
    vibe = "run it." if top.get("action") == "TAKE" else ("maybe." if top.get("action") == "LEAN" else "homework only.")
    st.markdown(
        f'<div class="n1-sum n1-pulse">'
        f'<b>{len(items)} prop{"s" if len(items)!=1 else ""} found</b> — '
        f'{top.get("label")} ({format_odds(top.get("best"))}). '
        f'Kelly confidence: {kpct0:.0f}%. EV: {ev_s0}. '
        f'Queen says: {vibe}'
        f'</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, r in enumerate(items):
        evs = r.get("ev")
        kf = float(r.get("kelly_frac") or 0)
        kpct = max(0, min(100, kf * 100))
        ev_s = f"{evs:+.2f}" if evs is not None else "—"
        gap = r.get("edge") or 0
        act = r.get("action") or "DON'T"
        hot = kpct > 10 and (evs or 0) > 0.05
        qclass = {"TAKE": "queen-take", "LEAN": "queen-lean", "WATCH": "queen-watch"}.get(act, "queen-dont")
        aclass = {"TAKE": "take", "LEAN": "lean", "WATCH": "watch"}.get(act, "dont")
        queen = _need_one_queen(act, hot)
        hot_tag = '<div class="n1-hot">🔥 HOT ZONE</div>' if hot else ""
        html = (
            f'<div class="card n1-card {aclass} n1-pulse {r.get("cls") or ""}">'
            f'{hot_tag}'
            f'<div class="card-kicker">I JUST NEED ONE · {act}</div>'
            f'<div class="card-name">{r.get("emoji")} {r.get("player")} — {r.get("label")} '
            f'({format_odds(r.get("best"))})</div>'
            f'<div class="card-line" title="Fair = weighted book average. Gap = posted minus fair. EV = expected value. Kelly = bankroll confidence.">'
            f'Fair {format_odds(r.get("fair"))} | Gap {gap:+d} | EV {ev_s} | Kelly {kpct:.0f}%</div>'
            f'<div class="card-meta">Best {book_label(r.get("best_book"))} {format_odds(r.get("best"))} · {r.get("n_books")} book'
            f'{"s" if (r.get("n_books") or 0)!=1 else ""} · {r.get("event") or ""}</div>'
            f'<div class="card-line">{_need_one_book_row(r.get("books") or {})}</div>'
            f'<div class="n1-meter-lab">Kelly confidence: {kpct:.0f}%</div>'
            f'<div class="n1-meter {"hot" if kpct>10 else ""}"><i style="width:{kpct:.0f}%"></i></div>'
            f'<div class="card-foot">RE tag active | Money-only</div>'
            f'<div class="queen-line {qclass}">{queen}</div>'
            f'</div>'
        )
        with cols[i % 2]:
            st.markdown(html, unsafe_allow_html=True)


def shop_block_reasons(r):
    """Read-only: why Shop did not print TAKE. Does not change action."""
    blocked = []
    best = r.get("best")
    fair = r.get("fair")
    books = r.get("books") or {}
    gap = r.get("edge")
    try:
        bp = abs(int(best)) if best is not None else 0
    except Exception:
        bp = 0
    try:
        gap_i = int(gap) if gap is not None else None
    except Exception:
        gap_i = None
    if best is None or fair is None:
        blocked.append("no fair line (need 2+ prices)")
    try:
        bp_chk = abs(int(best)) if best is not None else 0
    except Exception:
        bp_chk = 0
    need = SHOP_GAP_TAKE_LONG if bp_chk >= 500 else SHOP_GAP_TAKE_MID
    if gap_i is not None and gap_i < need:
        blocked.append(f"gap {gap_i:+d} < take gap {need}")
    if bp >= JUNK_PRICE:
        blocked.append(f"flyer/junk lane +{bp} ≥ {JUNK_PRICE}")
    if bp >= LONG_PRICE:
        end = last_two(bp)
        real = {normalize_book(b) for b in books} & {"draftkings", "fanduel", "betmgm"}
        if end in LONG_DEAD_ENDS:
            blocked.append(f"dead ending {end:02d} on long price")
        elif end not in LONG_OK_ENDS:
            blocked.append(f"ending {end} not in long-ok {sorted(LONG_OK_ENDS)}")
        if len(real) < 2:
            blocked.append(f"long price needs 2 of DK/FD/MGM (has {sorted(real) or 'none'}) — Fanatics does not count here")
    bk = normalize_book(r.get("best_book"))
    if bk in SIGNAL_ONLY_BOOKS:
        blocked.append("best book is MGM (signal only)")
    ticket_n = sum(1 for b in books if _is_ticket_book(b))
    if ticket_n < 2 and "fanatics" in {normalize_book(b) for b in books}:
        blocked.append("Fanatics-only / thin ticket pack — fair collapses toward the one number")
    if r.get("kelly_label") == "SKIP" and r.get("action") != "TAKE":
        blocked.append("Kelly SKIP demoted TAKE→LEAN or LEAN→DON'T")
    # Shop does not use these — note so the audit is honest
    blocked.append("Shop ignores Benford / numerology / Board score / cluster / stale (those are Board-only)")
    if not any(x.startswith("gap") or x.startswith("flyer") or x.startswith("dead") or x.startswith("ending") or x.startswith("long") or x.startswith("best") or x.startswith("Kelly") or x.startswith("no fair") or x.startswith("Fanatics") for x in blocked):
        if r.get("action") != "TAKE":
            blocked.insert(0, f"call is {r.get('action')} · {r.get('why')}")
    return blocked


# ── Trend Lab (display + scores only — does not gate TAKE) ──
_TREND_TICKETS = ("draftkings", "fanduel", "hardrockbet", "fanatics")


def _trend_window_rows(rows, days):
    today = today_az()
    try:
        cut = datetime.strptime(today, "%Y-%m-%d").date()
    except Exception:
        return []
    out = []
    for r in rows or []:
        if r.get("result") not in ("HIT", "MISS"):
            continue
        try:
            d = datetime.strptime(r.get("date") or "", "%Y-%m-%d").date()
        except Exception:
            continue
        if (cut - d).days <= days:
            out.append(r)
    return out


def _hit_rate(rows):
    h = sum(1 for r in rows if r.get("result") == "HIT")
    n = len(rows)
    return (100.0 * h / n if n else None), h, n


def _bucket_label_from_price(p):
    try:
        a = abs(int(p))
    except Exception:
        return None
    if a >= 1000:
        return "+1000+"
    if a >= 700:
        return "+700-900"
    if a >= 600:
        return "+600s"
    if a >= 500:
        return "+500s"
    if a >= 400:
        return "+400s"
    return "under +400"


def build_trend_pack():
    rows = load_results()
    today = today_az()
    today_rows = [r for r in rows if r.get("date") == today and r.get("result") in ("HIT", "MISS")]
    yday = None
    try:
        yday = (datetime.strptime(today, "%Y-%m-%d").date() - timedelta(days=1)).isoformat()
    except Exception:
        yday = ""
    yday_rows = [r for r in rows if r.get("date") == yday and r.get("result") in ("HIT", "MISS")]
    week = _trend_window_rows(rows, 7)

    def method_table(pool):
        bag = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in pool:
            for m in r.get("methods") or []:
                nm = normalize_method_name(m)
                if nm in NOISE_METHODS or nm in TRACKER_BLOCKLIST:
                    continue
                bag[nm]["hit" if r["result"] == "HIT" else "miss"] += 1
        out = []
        for name, stt in bag.items():
            n = stt["hit"] + stt["miss"]
            if not n:
                continue
            out.append({"name": name, "pct": 100.0 * stt["hit"] / n, "hit": stt["hit"], "miss": stt["miss"], "n": n})
        out.sort(key=lambda x: (-x["pct"], -x["n"]))
        return out

    def ending_table(pool):
        bag = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in pool:
            end = r.get("ending")
            if end is None and r.get("best_price") is not None:
                end = last_two(r.get("best_price"))
            if end is None:
                continue
            key = f"{int(end):02d}"
            bag[key]["hit" if r["result"] == "HIT" else "miss"] += 1
        out = []
        for name, stt in bag.items():
            n = stt["hit"] + stt["miss"]
            out.append({"name": name, "pct": 100.0 * stt["hit"] / n, "hit": stt["hit"], "n": n})
        out.sort(key=lambda x: (-x["pct"], -x["n"]))
        return out

    def bucket_table(pool):
        bag = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in pool:
            lab = _bucket_label_from_price(r.get("best_price"))
            if not lab:
                continue
            bag[lab]["hit" if r["result"] == "HIT" else "miss"] += 1
        order = ["+500s", "+600s", "+700-900", "+1000+", "+400s", "under +400"]
        out = []
        for lab in order:
            stt = bag.get(lab)
            if not stt:
                continue
            n = stt["hit"] + stt["miss"]
            out.append({"name": lab, "pct": 100.0 * stt["hit"] / n, "hit": stt["hit"], "n": n})
        return out

    def team_table(pool):
        bag = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in pool:
            team = (r.get("team") or "").strip()
            if not team:
                ev = r.get("event") or ""
                team = ev.split("@")[-1].strip() if "@" in ev else ev
            if not team:
                continue
            bag[team]["hit" if r["result"] == "HIT" else "miss"] += 1
        out = []
        for name, stt in bag.items():
            n = stt["hit"] + stt["miss"]
            if n < 2:
                continue
            out.append({"name": name, "pct": 100.0 * stt["hit"] / n, "hit": stt["hit"], "n": n})
        out.sort(key=lambda x: (-x["pct"], -x["n"]))
        return out

    def book_table(pool):
        bag = defaultdict(lambda: {"hit": 0, "miss": 0})
        for r in pool:
            bk = normalize_book(r.get("best_book") or r.get("book"))
            if not bk:
                continue
            bag[bk]["hit" if r["result"] == "HIT" else "miss"] += 1
        out = []
        for name, stt in bag.items():
            n = stt["hit"] + stt["miss"]
            out.append({"name": book_label(name), "key": name, "pct": 100.0 * stt["hit"] / n, "hit": stt["hit"], "n": n})
        out.sort(key=lambda x: (-x["pct"], -x["n"]))
        return out

    return {
        "today_m": method_table(today_rows),
        "yday_m": method_table(yday_rows),
        "week_m": method_table(week),
        "today_e": ending_table(today_rows),
        "week_e": ending_table(week),
        "week_bkt": bucket_table(week),
        "week_team": team_table(week),
        "week_book": book_table(week),
        "today_n": len(today_rows),
        "week_n": len(week),
    }


def player_motion(player, book_prices=None):
    """Heating / Cooling / Chaotic / Stable from price snaps. Display only."""
    phist = st.session_state.get("price_history") or []
    if len(phist) < 2:
        return {
            "label": "Stable",
            "icon": "🧊",
            "css": "motion-stable",
            "meaning": "Need another fetch to see motion.",
            "detail": "Need another fetch to see motion",
            "score": 40,
            "deltas": {},
            "cluster": None,
            "cluster_was": None,
            "rogue": None,
        }
    def px_for(snap):
        out = {}
        for (p, b), v in (snap or {}).items():
            if p != player:
                continue
            bk = normalize_book(b)
            try:
                out[bk] = int(v)
            except Exception:
                pass
        return out

    now = px_for(phist[-1])
    prev = px_for(phist[-2])
    if book_prices:
        for b, v in book_prices.items():
            try:
                now[normalize_book(b)] = int(v)
            except Exception:
                pass
    deltas = {}
    for bk in _TREND_TICKETS:
        if bk in now and bk in prev:
            deltas[bk] = int(now[bk]) - int(prev[bk])
    shorts = sum(1 for d in deltas.values() if d <= -20)
    longs = sum(1 for d in deltas.values() if d >= 20)
    if now:
        cluster = max(now.values()) - min(now.values()) if len(now) >= 2 else 0
    else:
        cluster = None
    cluster_was = None
    if prev and len(prev) >= 2:
        cluster_was = max(prev.values()) - min(prev.values())
    if shorts >= 2 and longs == 0:
        label, score, icon, css = "Heating up", 78, "🔺", "motion-heat"
        meaning = "Odds shortening across ticket books — books expect action."
    elif longs >= 2 and shorts == 0:
        label, score, icon, css = "Cooling down", 28, "🔻", "motion-cool"
        meaning = "Odds lengthening — pack is drifting. Value lane, or fade if it shot up."
    elif shorts and longs:
        label, score, icon, css = "Chaotic", 45, "⚡", "motion-chaos"
        meaning = "Books disagree. Volatility can be a window if one ticket stays long."
    elif deltas and all(abs(d) < 20 for d in deltas.values()):
        label, score, icon, css = "Stable", 50, "🧊", "motion-stable"
        meaning = "Barely moved since last fetch."
    else:
        label, score, icon, css = "Stable", 48, "🧊", "motion-stable"
        meaning = "Not enough book-to-book motion yet. Fetch again."
    bits = [f"{book_label(b)} {d:+d}" for b, d in deltas.items()]
    if cluster is not None and cluster_was is not None:
        if cluster < cluster_was - 15:
            bits.append("cluster tightening")
        elif cluster > cluster_was + 15:
            bits.append("cluster widening")
    rogue = None
    if deltas:
        ranked = sorted(deltas.items(), key=lambda kv: -abs(kv[1]))
        if ranked and abs(ranked[0][1]) >= 80:
            rogue = ranked[0][0]
            bits.append(f"rogue {book_label(rogue)} {ranked[0][1]:+d}")
    if cluster is not None and cluster_was is not None and cluster > cluster_was + 15:
        meaning = "Cluster widening — a rogue number may be the value lane."
    if rogue:
        meaning = f"Rogue {book_label(rogue)} move. Check that ticket before you buy the pack."
    return {
        "label": label,
        "icon": icon,
        "css": css,
        "meaning": meaning,
        "detail": " · ".join(bits) or "flat since last fetch",
        "score": score,
        "deltas": deltas,
        "cluster": cluster,
        "cluster_was": cluster_was,
        "rogue": rogue,
    }


def _lookup_trend(table, name, default="—"):
    for row in table or []:
        if str(row.get("name")) == str(name) or str(row.get("key")) == str(name):
            n = row.get("n") or 0
            pct = row.get("pct")
            if pct is None:
                return default
            heat = "hot" if pct >= 18 and n >= 4 else ("cold" if pct <= 8 and n >= 4 else "even")
            return f"{pct:.0f}% ({row.get('hit', 0)}/{n}) {heat}"
    return default


def attach_player_trends(item, pack):
    motion = player_motion(item.get("player"), item.get("book_prices") or item.get("books"))
    end = last_two(item.get("best_price") if item.get("best_price") is not None else item.get("best"))
    end_s = f"{int(end):02d}" if end is not None else None
    bkt = _bucket_label_from_price(item.get("best_price") if item.get("best_price") is not None else item.get("best"))
    team = item.get("team") or ""
    book = normalize_book(item.get("best_book"))
    methods = item.get("methods") or []
    meth_bits = []
    for m in methods[:4]:
        nm = normalize_method_name(m)
        lab = _lookup_trend(pack.get("week_m"), nm, "")
        if lab and lab != "—":
            meth_bits.append(f"{nm} {lab}")
    item["trend_motion"] = motion["label"]
    item["trend_motion_icon"] = motion.get("icon") or "🧊"
    item["trend_motion_css"] = motion.get("css") or "motion-stable"
    item["trend_motion_meaning"] = motion.get("meaning") or ""
    item["trend_motion_detail"] = motion["detail"]
    item["trend_motion_score"] = motion["score"]
    tag = None
    if motion["label"] == "Heating up":
        tag = "Trend Heating"
    elif motion["label"] == "Cooling down":
        tag = "Trend Cooling"
    elif motion["label"] == "Chaotic":
        tag = "Trend Chaotic"
    if tag:
        item["trend_tag"] = tag
        ms = item.get("methods") or []
        if tag not in ms:
            ms.append(tag)
            item["methods"] = ms
    item["trend_method"] = " · ".join(meth_bits[:2]) or "no graded method sample yet"
    item["trend_ending"] = _lookup_trend(pack.get("week_e"), end_s)
    item["trend_bucket"] = _lookup_trend(pack.get("week_bkt"), bkt)
    item["trend_team"] = _lookup_trend(pack.get("week_team"), team)
    item["trend_book"] = _lookup_trend(pack.get("week_book"), book)
    # display scores 0-100 — not used by qualifies_take_it
    try:
        edge = int(item.get("edge") or 0)
    except Exception:
        edge = 0
    item["trend_value_score"] = max(0, min(100, int(50 + edge / 2)))
    item["trend_score"] = max(0, min(100, int(
        0.4 * motion["score"] + 0.3 * item["trend_value_score"] + 0.3 * min(100, int(item.get("score") or 0))
    )))
    return item


def trend_chip_html(item, full=False):
    css = item.get("trend_motion_css") or "motion-stable"
    icon = item.get("trend_motion_icon") or "🧊"
    html = (
        f'<div class="trend-line">'
        f'<span class="trend-chip {css}">{icon} {item.get("trend_motion") or "Stable"}</span>'
        f'<div class="trend-mean">{item.get("trend_motion_meaning") or ""}</div>'
    )
    if full:
        html += (
            f'<span class="trend-meta">{item.get("trend_motion_detail") or ""}</span>'
            f'<div class="trend-meta">Method · {item.get("trend_method")}</div>'
            f'<div class="trend-meta">Ending · {item.get("trend_ending")} · Bucket · {item.get("trend_bucket")}</div>'
            f'<div class="trend-meta">Team · {item.get("trend_team")} · Book · {item.get("trend_book")}</div>'
        )
    return html + "</div>"


def _motion_sparkline(player):
    phist = st.session_state.get("price_history") or []
    series = defaultdict(list)
    for snap in phist:
        by_bk = {}
        for (p, b), v in (snap or {}).items():
            if p != player:
                continue
            try:
                by_bk[normalize_book(b)] = int(v)
            except Exception:
                pass
        for bk in _TREND_TICKETS:
            if bk in by_bk:
                series[bk].append(by_bk[bk])
    if not series:
        return ""
    all_px = [v for vs in series.values() for v in vs]
    lo, hi = min(all_px), max(all_px)
    span = max(1, hi - lo)
    colors = {"draftkings": "#34d399", "fanduel": "#60a5fa", "hardrockbet": "#fbbf24", "fanatics": "#f472b6"}
    rows = []
    for bk, vs in series.items():
        dots = []
        for i, v in enumerate(vs):
            h = 8 + int(22 * (v - lo) / span)
            dots.append(
                f'<span title="{book_label(bk)} {format_odds(v)}" '
                f'style="display:inline-block;width:8px;height:{h}px;margin-right:2px;'
                f'background:{colors.get(bk, "#c084fc")};border-radius:2px;vertical-align:bottom"></span>'
            )
        rows.append(f'<div class="spark-row"><span class="spark-lab">{book_label(bk)}</span>{"".join(dots)}</div>')
    return '<div class="spark-wrap">' + "".join(rows) + "</div>"


def render_trend_lab(ev_board, shop_rows):
    pack = build_trend_pack()
    if "seen_trend_lab" not in st.session_state:
        st.session_state["seen_trend_lab"] = False
    if not st.session_state.get("seen_trend_lab"):
        with st.expander("Welcome to the Trend Lab 💅", expanded=True):
            st.markdown(
                "This is where we track the motion **before first pitch**.\n\n"
                "🔺 / 🔥 **Heating up** = books shortening.\n"
                "🔻 / 🧊 **Cooling down** = books lengthening or a method losing steam.\n"
                "⚡ **Chaotic** = books disagree.\n\n"
                "These trends **do not change TAKE math** — they show what’s moving and where value might pop."
            )
            if st.button("Got it — show the lab", type="primary"):
                st.session_state["seen_trend_lab"] = True
                st.rerun()

    hot_m = [r for r in pack.get("week_m") or [] if r["pct"] >= 18 and r["n"] >= 3][:4]
    hot_e = [r for r in pack.get("week_e") or [] if r["pct"] >= 18 and r["n"] >= 3][:3]
    hot_t = [r for r in pack.get("week_team") or [] if r["pct"] >= 20][:3]
    rogue_live = [x for x in (ev_board or []) if x.get("trend_motion") == "Chaotic"]
    pulse = (
        "Long-ball lane is the story. "
        + (("Methods cooking: " + ", ".join(x["name"] for x in hot_m) + ". ") if hot_m else "Grade hits so methods can cook. ")
        + (("Teams: " + ", ".join(x["name"] for x in hot_t) + ". ") if hot_t else "")
        + (("Chaotic tickets on the slate: " + str(len(rogue_live)) + ".") if rogue_live else "Fetch twice to see book motion.")
    )
    st.markdown(
        f'<div class="pulse-bar">{pulse}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="site-section"><div class="site-section-head">'
        '<p class="site-section-kicker">Trend Lab</p>'
        '<div class="site-section-title">What’s hitting right now 💣</div>'
        '<p class="site-section-help">+500 and up is the lane. Green glow = heating. Red = cooling. Purple = chaos.</p></div>',
        unsafe_allow_html=True,
    )

    heat = [x for x in (ev_board or []) if x.get("trend_motion") == "Heating up"]
    cool = [x for x in (ev_board or []) if x.get("trend_motion") == "Cooling down"]
    chaos = [x for x in (ev_board or []) if x.get("trend_motion") == "Chaotic"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔺 Heating", len(heat))
    c2.metric("🔻 Cooling", len(cool))
    c3.metric("⚡ Chaotic", len(chaos))
    c4.metric("Week graded", pack.get("week_n") or 0)

    f1, f2, f3, f4 = st.columns(4)
    only_heat = f1.checkbox("Only heating up", key="tl_heat")
    only_chaos = f2.checkbox("Only chaotic", key="tl_chaos")
    only_long = f3.checkbox("Only long-ball +500+", value=True, key="tl_long")
    fav = f4.multiselect("Favorite books", ["DK", "FD", "Fanatics", "HardRock"], key="tl_books")
    fav_keys = {"DK": "draftkings", "FD": "fanduel", "Fanatics": "fanatics", "HardRock": "hardrockbet"}

    live = list(ev_board or [])
    if only_heat:
        live = [x for x in live if x.get("trend_motion") == "Heating up"]
    if only_chaos:
        live = [x for x in live if x.get("trend_motion") == "Chaotic"]
    if only_long:
        live = [x for x in live if abs(int(x.get("best_price") or 0)) >= 500]
    if fav:
        want = {fav_keys[x] for x in fav}
        live = [x for x in live if normalize_book(x.get("best_book")) in want]
    live = sorted(live, key=lambda x: -(x.get("trend_motion_score") or 0))

    st.markdown("#### 🔥 Hot right now")
    if hot_m:
        for r in hot_m:
            y = next((z for z in pack.get("yday_m") or [] if z["name"] == r["name"]), None)
            arrow = "🔺" if y and r["pct"] > y["pct"] + 5 else ("🔻" if y and r["pct"] + 5 < y["pct"] else "⚡")
            st.markdown(f"- {arrow} **{r['name']}** → {r['pct']:.0f}% this week (n={r['n']}) — still cooking")
    else:
        st.caption("Grade a few hits and this fills.")
    if hot_e:
        st.caption("Hot endings: " + ", ".join(f"{x['name']} {x['pct']:.0f}%" for x in hot_e))

    st.markdown("#### Live motion (last fetches)")
    quick = st.toggle("Quick Read (headline + Queen only)", value=True, key="tl_quick")
    if not live:
        st.caption("Nothing matches those toggles. Fetch twice so snapshots exist.")
    else:
        for item in live[:30]:
            motion = item.get("trend_motion") or "Stable"
            meaning = item.get("trend_motion_meaning") or ""
            if motion == "Heating up":
                queen = "Queen whispered: this one’s heating, not cleared."
            elif motion == "Cooling down":
                queen = "Queen whispered: cooling. Don’t force the ticket."
            elif motion == "Chaotic":
                queen = "Queen whispered: chaos. Check the rogue ticket."
            else:
                queen = "Queen whispered: stable. Still homework unless the Board is green."
            extra = "" if quick else f'{trend_chip_html(item)}{_motion_sparkline(item.get("player"))}'
            st.markdown(
                f'<div class="card site-card {item.get("trend_motion_css") or ""}">'
                f'<div class="card-name">{item.get("player")}</div>'
                f'<div class="card-meta">{item.get("team") or ""} · {format_odds(item.get("best_price"))} {book_label(item.get("best_book"))}</div>'
                f'{motion_line_html(item)}'
                f'<div class="trend-mean">{meaning}</div>'
                f'{extra}'
                f'<div class="queen-line">{queen}</div></div>',
                unsafe_allow_html=True,
            )

    cold_m = [r for r in pack.get("week_m") or [] if r["pct"] <= 8 and r["n"] >= 4][:8]
    st.markdown("#### 🧊 Cooling off")
    if cold_m:
        st.caption(" · ".join(f"{x['name']} {x['pct']:.0f}%" for x in cold_m))
    else:
        st.caption("No cold methods with a real sample yet.")

    st.markdown("#### 💣 Long-ball lanes")
    bkt = pack.get("week_bkt") or []
    if not bkt:
        st.caption("Grade +500s and up to fill buckets.")
    else:
        html = "".join(
            f'<div class="rate-chip"><div class="rate-pct">{r["pct"]:.0f}%</div>'
            f'<div class="rate-name">{r["name"]}</div>'
            f'<div class="rate-n">{r.get("hit", 0)}H · n={r["n"]}</div></div>'
            for r in bkt
        )
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("#### 📈 Book behavior")
    books = pack.get("week_book") or []
    if not books:
        st.caption("Books fill from graded ticket book.")
    else:
        html = "".join(
            f'<div class="rate-chip"><div class="rate-pct">{r["pct"]:.0f}%</div>'
            f'<div class="rate-name">{r["name"]}</div>'
            f'<div class="rate-n">{r.get("hit", 0)}H · n={r["n"]}</div></div>'
            for r in books
        )
        st.markdown(html, unsafe_allow_html=True)
        st.caption("Rogue on the live slate = Chaotic cards above (one book jumped while others sat).")
    st.markdown("</div>", unsafe_allow_html=True)


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
    st.caption(
        "Odds Shop is where math meets petty precision. "
        "Read left to right: player → book → fair pack → ticket → gap → call. "
        "Green means best ticket. Red means short vs fair. "
        "Kelly shows bankroll confidence. Everything else is homework."
    )
    if df is None or getattr(df, "empty", True):
        st.info(sport_cfg()["shop_empty"])
        return
    shop = build_shop_board(df)
    book_meter = benford_book_meter(df)
    pack = st.session_state.get("_trend_pack") or build_trend_pack()
    for r in shop:
        r["benford"] = prop_benford_flag(r.get("books"), book_meter, None)
        r["best_price"] = r.get("best")
        attach_player_trends(r, pack)
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
    st.markdown('<div class="filter-shell">', unsafe_allow_html=True)
    st.caption("🎯 Call")
    view = st.radio(
        "Call",
        ["All", "TAKE + LEAN", "TAKE", "LEAN", "DON'T", "MARKET"],
        horizontal=True,
        key="shop_filter",
        help="TAKE — cleared play list. LEAN — math says maybe. DON’T — homework only. MARKET — neutral zone.",
        label_visibility="collapsed",
    )
    st.caption("📚 Books")
    c1, c2, c3 = st.columns(3)
    book_opts = ["Any"] + [lab for _, lab in SHOP_BOOKS]
    with c1:
        book_f = st.selectbox("Book that’s behaving", book_opts, key="shop_best_book", help="Ticket we would actually buy.")
    with c2:
        has_f = st.selectbox("Book that’s posting", book_opts, key="shop_has_book", help="Must have this book posted.")
    ends = sorted({f"{int(r['ending']):02d}" for r in shop if r.get("ending") is not None})
    with c3:
        end_f = st.multiselect("Odds ending pattern", ends, key="shop_ends", help="Last two of the ticket.")
    st.caption("💸 Math")
    c4, c5, c6 = st.columns(3)
    with c4:
        min_gap = st.slider("Minimum space between fair and posted", 0, 300, 0, 10, key="shop_min_gap", help="Gap vs fair — how far the posted odds drift from the fair number. Bigger gap = better value.")
    with c5:
        min_books = st.selectbox("Books showing odds", [1, 2, 3, 4, 5], index=0, key="shop_min_books")
    buckets = sorted({r.get("bucket") for r in shop if r.get("bucket")})
    with c6:
        buck_f = st.multiselect("Odds range", buckets, key="shop_buckets")
    st.caption("🧍‍♀️ Player")
    q = st.text_input("Find a name", key="shop_q")
    st.markdown("</div>", unsafe_allow_html=True)

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
    st.caption(f"Showing {len(shown)} of {len(shop)} players. If it disappeared, it wasn’t meant for you.")
    with st.expander("Long-Ball Math — How the Board Sees It", expanded=False):
        take_n = sum(1 for r in shop if r.get("action") == "TAKE")
        lean_n = sum(1 for r in shop if r.get("action") == "LEAN")
        long_n = sum(1 for r in shop if abs(int(r.get("best") or 0)) >= 500)
        st.caption(
            f"{take_n} TAKE · {lean_n} LEAN · {long_n} at +500+. "
            "Fair = weighted book vs cushion. Gap = space between fair and posted. "
            "EV = expected value. Kelly = bankroll confidence. Call = what the math says to do."
        )
        lines = []
        for r in shop[:80]:
            ev = r.get("ev")
            kf = r.get("kelly_frac")
            ev_s = f"{ev:+.3f}" if ev is not None else "—"
            k_s = f"{kf:+.3f}" if kf is not None else "—"
            tags = ", ".join(r.get("value_tags") or []) or "—"
            reasons = shop_block_reasons(r)
            act = r.get("action") or "MARKET"
            icon = "💚" if act in ("TAKE", "LEAN") else ("🔴" if act == "DON'T" else "💜")
            lines.append(
                f"{icon} **{r.get('player')}** — {format_odds(r.get('best'))} {book_label(r.get('best_book'))}  \n"
                f"Fair {format_odds(r.get('fair'))} | Gap {int(r.get('edge') or 0):+d} | EV {ev_s} | Kelly {k_s} ({r.get('kelly_label')})  \n"
                f"{tags} → **{act}** · {'; '.join(reasons[:3])}"
            )
        st.markdown("\n\n".join(lines) if lines else "_No shop rows._")
        st.caption("Queen whispered: if it’s green and the Kelly’s loud, run it. If it’s red, it’s homework.")
    heat = ending_heat_from_results(results_for_sport(), min_n=8 if nfl_loose_mode() else 20)
    if heat:
        st.markdown("#### Endings that have been hitting")
        st.caption("These are the odds endings that have been cashing most often. 💚 Hot 15%+ · 💜 Mid 10–14% · 🔴 Cold under 10%.")
        chips = []
        for h in heat[:12]:
            tone = "hot" if h["pct"] >= 15 else ("mid" if h["pct"] >= 10 else "cold")
            chips.append(
                f'<div class="rate-chip {tone}"><div class="rate-pct">{h["pct"]:.0f}%</div>'
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
                cells.append("<td>-</td>")
                continue
            cls = "shop-best" if key == r.get("best_book") else ""
            if r.get("fair") is not None and key != r.get("best_book") and int(px) <= int(r["fair"]) - 40:
                cls = "shop-short"
            cells.append(f'<td class="{cls}">{format_odds(px)}</td>')
        fair_s = format_odds(r["fair"]) if r.get("fair") is not None else "-"
        act = r.get("action") or "MARKET"
        row_cls = {
            "TAKE": "row-take",
            "LEAN": "row-lean",
            "DON'T": "row-dont",
            "MARKET": "row-mkt",
        }.get(act, "row-mkt")
        # Shop CALL is a PRICE call, not a Board green.
        call_txt = {
            "TAKE": "TAKE PRICE",
            "LEAN": "LEAN PRICE",
            "DON'T": "DON'T",
            "MARKET": "MARKET",
        }.get(act, act)
        body.append(
            f'<tr class="{row_cls}">'
            f'<td><div class="shop-name">{r["player"]}</div><div class="shop-game">{r.get("event") or ""}</div></td>'
            + "".join(cells)
            + f"<td>{fair_s}</td>"
            f'<td class="shop-best">{format_odds(r["best"])} {book_label(r.get("best_book"))}</td>'
            f'<td>{int(r.get("edge") or 0):+d}</td>'
            f'<td>{int(r.get("trend_value_score") or 0)}</td>'
            f'<td>{r.get("trend_motion") or "—"}</td>'
            f'<td>{int(r.get("trend_score") or 0)}</td>'
            f'<td class="{r.get("kelly_css") or ""}" title="Kelly shows how much of your bankroll this ticket deserves.">{(r.get("kelly_pct") or 0):.1f}% {r.get("kelly_label") or "—"}</td>'
            f'<td class="{r["cls"]}"><span class="shop-call">{call_txt}</span></td></tr>'
        )
    st.markdown(
        '<div class="shop-wrap"><table class="shop-table"><thead><tr>'
        "<th>Player</th>" + heads + "<th>Fair</th><th>Ticket</th><th>Gap</th><th>Value</th><th>Motion</th><th>Trend</th><th>Kelly</th><th>Call</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Ticket = DK / FD / HardRock / Fanatics — never MGM. "
        "Kelly = quarter-Kelly in units (20u roll). SKIP = no bet. "
        "TAKE / LEAN still need a real gap. This is size, not a second Board."
    )

# From Tracker: 4-6 cash, 1-2 die
_DIGIT_GOOD = {4, 5, 6}
_DIGIT_BAD = {1, 2}

def _benford_bars(res):
    actual = res.get("actual_distribution") or {}
    bits = []
    for d in range(1, 10):
        a = float(actual.get(str(d), 0)) * 100
        if d in _DIGIT_GOOD:
            col, mark = "#34d399", "good"
        elif d in _DIGIT_BAD:
            col, mark = "#fb7185", "fade"
        else:
            col, mark = "#c084fc", "mid"
        bits.append(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:.78rem">'
            f'<div style="width:72px;color:#e9d5ff">{_digit_lane(d)}</div>'
            f'<div style="flex:1;background:#1a1224;border-radius:6px;height:12px">'
            f'<div style="width:{min(100,a*3):.1f}%;height:12px;background:{col};border-radius:6px"></div>'
            f'</div>'
            f'<div style="width:70px;color:{col};font-weight:700">{a:.0f}% {mark}</div>'
            f'</div>'
        )
    return "".join(bits)

def _benford_card(res, title):
    n = res.get("n") or 0
    st.markdown(
        f'<div class="card">'
        f'<div class="card-name">{title}</div>'
        f'<div class="card-meta">{n} numbers in this pile. {POND_LEGEND}</div>'
        f'{_benford_bars(res)}'
        f'</div>',
        unsafe_allow_html=True,
    )

def _digit_lane(d):
    return {
        1: "+1000+",
        2: "+200-299 or +2000+",
        3: "+300s",
        4: "+400s",
        5: "+500s",
        6: "+600s",
        7: "+700s",
        8: "+800s",
        9: "+900s",
    }.get(int(d), f"{d}s")


def digits_playbook(hits_res, graded_res, live_res):
    """Plain do / don't from first-digit piles. Not a player pick."""
    def dist(res):
        return {int(k): float(v) for k, v in (res.get("actual_distribution") or {}).items()}

    h, g, live = dist(hits_res), dist(graded_res), dist(live_res)
    hn, gn = hits_res.get("n") or 0, graded_res.get("n") or 0
    do, dont, notes = [], [], []
    if hn < 25:
        notes.append("Not enough hits logged yet - treat this as a sketch.")
    hit_ranked = sorted(h.items(), key=lambda kv: -kv[1])
    hot = [d for d, p in hit_ranked if p >= 0.14][:3]
    if 1 not in hot and h.get(1, 1) <= 0.12:
        dont.append("Leave +1000 and longer alone. Those almost never cash in our log.")
    for d in hot:
        do.append(f"Look at {_digit_lane(d)} if the Board already greened the name.")
    if h.get(2, 0) <= 0.05:
        dont.append("Ignore the +2000 / +2xx junk.")
    if live.get(5, 0) >= 0.15 or live.get(6, 0) >= 0.15:
        notes.append("Today the books are printing a lot of +500 and +600. That's the pond.")
    notes.append("Same story at every book. Don't switch books because of this page.")
    notes.append("Green light is still The Board. This page only says which PRICE shape has been hitting.")
    if not do:
        do.append("No price band is standing out yet.")
    if not dont:
        dont.append("Nothing extra to fade.")
    return do, dont, notes


POND_LEGEND = "💚 Green = cash pond · 💜 Purple = mid pond · 🔴 Red = fade"


def lookat_box(title, body, why="", queen=""):
    extra = f'<div class="note" style="margin-top:4px"><b>Why it matters:</b> {why}</div>' if why else ""
    q = f'<div class="queen-line">{queen}</div>' if queen else ""
    st.markdown(
        f'<div class="how-box"><b>{title}</b>'
        f'<div class="note" style="margin-top:6px">{body}</div>'
        f'{extra}{q}'
        f'<div class="note" style="margin-top:6px">{POND_LEGEND}</div></div>',
        unsafe_allow_html=True,
    )


def render_digits_tab(df):
    st.markdown("""
    <style>
    .bf-hero{background:linear-gradient(135deg,#2e1065,#831843);border:1px solid #c084fc;border-radius:22px;padding:16px 18px;margin-bottom:12px;box-shadow:0 0 24px rgba(192,132,252,.25)}
    .bf-hero h3{font-family:'Playfair Display',serif;color:#fff;margin:0 0 6px;font-size:1.45rem}
    .bf-hero p{color:#f5d0fe;margin:0;font-size:.88rem}
    .bf-meter{height:10px;background:#1e1b4b;border-radius:999px;overflow:hidden;margin:8px 0}
    .bf-meter span{display:block;height:100%;border-radius:999px}
    .bf-heat{display:grid;grid-template-columns:repeat(9,1fr);gap:6px;margin:8px 0 12px}
    .bf-cell{text-align:center;border-radius:12px;padding:10px 4px;border:1px solid #3b0764;background:#16101f}
    .bf-cell b{display:block;font-size:1.1rem;color:#fbcfe8}
    .bf-cell:hover{box-shadow:0 0 12px #e879f9}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(
        '<div class="bf-hero"><h3>Benford Energy Check 🔢✨</h3>'
        "<p>Benford’s Law shows which numbers occur naturally — and which look forced.</p>"
        '<p style="margin-top:6px;color:#f9a8d4">Benford spots fake odds faster than any algorithm.</p></div>',
        unsafe_allow_html=True,
    )
    lookat_box(
        "🔢 Benford — are the odds natural or forced?",
        "Benford spots fake odds faster than any algorithm. Score closer to 1.0 = natural. Closer to 0.0 = forced.",
        why="This shows if the odds look real or forced. Green means natural energy — red means fake math.",
        queen="Queen whispered: confirm the pond before you buy.",
    )
    if not HAS_BENFORD:
        st.warning("Need benford.py next to app.py.")
        return
    live_all, live_best = [], []
    if df is not None and not getattr(df, "empty", True):
        try:
            live_all = [int(x) for x in df["price"].dropna().tolist()]
        except Exception:
            live_all = []
        live_best = [r["best"] for r in build_shop_board(df) if r.get("best") is not None]
    lock = st.session_state.get("pregame_lock") or load_pregame() or {}
    lock_px = []
    if isinstance(lock, dict):
        for rec in lock.values():
            if not isinstance(rec, dict):
                continue
            for info in (rec.get("books") or {}).values():
                try:
                    if isinstance(info, dict) and info.get("price") is not None:
                        lock_px.append(int(info["price"]))
                    elif isinstance(info, (int, float)):
                        lock_px.append(int(info))
                except Exception:
                    pass
    graded, hits = [], []
    for r in load_results():
        if r.get("result") not in ("HIT", "MISS") or r.get("best_price") is None:
            continue
        try:
            px = int(r["best_price"])
        except Exception:
            continue
        graded.append(px)
        if r["result"] == "HIT":
            hits.append(px)
    live_res = analyze_benford(live_all, "live_all")
    best_res = analyze_benford(live_best, "live_best")
    lock_res = analyze_benford(lock_px, "lock")
    graded_res = analyze_benford(graded, "graded")
    hits_res = analyze_benford(hits, "hits")
    do, dont, notes = digits_playbook(hits_res, graded_res, live_res)
    score = float(live_res.get("benford_score") or 0)
    hue = "#22c55e" if score >= 0.7 else ("#eab308" if score >= 0.45 else "#ef4444")
    mood = "Clean energy" if score >= 0.7 else ("Mixed energy" if score >= 0.45 else "Forced energy")
    st.markdown(
        f'<div class="card"><b>Benford Score</b> · {score:.2f} / 1 · {mood}'
        f'<div class="bf-meter"><span style="width:{int(score*100)}%;background:{hue}"></span></div>'
        f'<div class="note">{live_res.get("n") or 0} live prices in the pile · {POND_LEGEND}</div>'
        f'<div class="queen-line">{"Queen whispered: fake math alert." if score < 0.45 else "Queen whispered: energy is clean enough to look."}</div></div>',
        unsafe_allow_html=True,
    )
    do_h = "".join(f"<div>✅ {x}</div>" for x in do)
    no_h = "".join(f"<div>🚫 {x}</div>" for x in dont)
    st.markdown(
        f'<div class="card"><b>Do</b><div class="note">{do_h}</div>'
        f'<b>Do not</b><div class="note">{no_h}</div>'
        f'<div class="card-foot">Board still picks the name. This page picks the pond.</div></div>',
        unsafe_allow_html=True,
    )
    dist = {int(k): float(v) for k, v in (live_res.get("actual_distribution") or {}).items()}
    cells = []
    for d in range(1, 10):
        p = dist.get(d, 0)
        glow = min(1.0, p * 4)
        cells.append(
            f'<div class="bf-cell" title="Digit {d} · {_digit_lane(d)} · {p:.0%}">'
            f'<b>{d}</b><span class="note">{p:.0%}</span></div>'
        )
    st.markdown('<div class="card"><b>Benford Heatmap</b><div class="bf-heat">' + "".join(cells) + "</div></div>", unsafe_allow_html=True)
    lookat_box(
        "📚 Book Piles — which books are clean today?",
        "Book Piles show which books are clean today. Look for green in +400–+600.",
        why="Green = playable long-ball pond. Red in +1000+ = bait.",
        queen="Queen whispered: pick the clean book, then pick the name.",
    )
    st.markdown("#### Benford vs Board")
    c1, c2 = st.columns(2)
    with c1:
        _benford_card(live_res, "Live board prices")
    with c2:
        _benford_card(hits_res, "History hits")
    lookat_box(
        "🧠 More Piles — is today normal or weird?",
        "More Piles tell you if today’s vibe is normal or weird. Today = live. Lock = pregame. History = what hits.",
        why="If Today and History match, the pond’s clean. If Lock disagrees, the book’s faking.",
        queen="Queen whispered: don’t fight history unless Lock is screaming.",
    )
    with st.expander("🧠 More piles — today vs lock vs history", expanded=False):
        _benford_card(best_res, "Today - best number only")
        _benford_card(lock_res, "Lock - pregame book prices")
        _benford_card(graded_res, "History - graded bests")
        st.markdown("#### By book today")
        meter = benford_book_meter(df)
        if meter:
            cols = st.columns(min(3, max(1, len(meter))))
            for i, (bk, res) in enumerate(meter.items()):
                with cols[i % len(cols)]:
                    _benford_card(res, book_label(bk))
        else:
            st.caption("Fetch first.")
    lookat_box(
        "△ The Triangle — how to actually use all this",
        "The Board picks the name. The Book Piles pick the pond. Benford picks the energy. Kelly picks the value.",
        why="All four agree → TAKE. Three → LEAN. Two → WATCH. One or zero → DON’T.",
        queen="Queen whispered: when Board, Pond, Energy, and Value agree — run it.",
    )

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


def _prices_by_book(df):
    out = defaultdict(list)
    if df is None or getattr(df, "empty", True):
        return out
    for _, r in df.iterrows():
        try:
            out[normalize_book(r.get("book"))].append(int(r["price"]))
        except Exception:
            continue
    return out


def benford_book_meter(df):
    """Book Authenticity Meter - first digits of that book's whole 0.5 HR board."""
    if not HAS_BENFORD:
        return {}
    pack = {}
    for bk, vals in _prices_by_book(df).items():
        if not vals:
            continue
        res = analyze_benford(vals, label=book_label(bk))
        res["score100"] = int(round((res.get("benford_score") or 0) * 100))
        # digit this book over-uses vs Benford
        delta = res.get("delta") or {}
        heavy = max(delta.items(), key=lambda kv: kv[1]) if delta else ("?", 0)
        res["heavy_digit"] = str(heavy[0])
        res["heavy_delta"] = heavy[1]
        pack[bk] = res
    return pack


def prop_benford_flag(book_prices, book_meter=None, lock_prices=None):
    """Tiny tag for one player. n is small - this is cluster/template, not a proof."""
    book_prices = book_prices or {}
    digits = []
    for bk, px in book_prices.items():
        d = None
        try:
            from benford import first_significant_digit
            d = first_significant_digit(px)
        except Exception:
            try:
                d = int(str(abs(int(px)))[0])
            except Exception:
                d = None
        if d:
            digits.append((normalize_book(bk), d, int(px)))
    if not digits:
        return {
            "tag": "No read",
            "cls": "bf-none",
            "cluster": 0,
            "note": "no prices",
            "aligned": None,
        }
    ds = [d for _, d, _ in digits]
    from collections import Counter as _C
    top_d, top_n = _C(ds).most_common(1)[0]
    cluster = round(top_n / len(ds), 2)
    template = len(set(ds)) == 1 and len(ds) >= 3
    drift = False
    if lock_prices:
        for bk, d, px in digits:
            lp = None
            info = (lock_prices or {}).get(bk)
            if isinstance(info, dict):
                lp = info.get("price")
            elif isinstance(info, (int, float)):
                lp = info
            if lp is None:
                continue
            try:
                ld = int(str(abs(int(lp)))[0])
            except Exception:
                continue
            if ld != d:
                drift = True
                break
    heavy_hit = False
    book_art = False
    if book_meter:
        for bk, d, _px in digits:
            m = book_meter.get(bk) or {}
            if m.get("alignment_flag") is False and (m.get("n") or 0) >= 25:
                book_art = True
            if str(d) == str(m.get("heavy_digit")) and (m.get("heavy_delta") or 0) >= 0.08:
                heavy_hit = True
    if template or (cluster >= 0.75 and len(ds) >= 3) or (book_art and heavy_hit):
        tag, cls, aligned = "Fake", "bf-broken", False
        note = ""
    else:
        tag, cls, aligned = "Authentic", "bf-ok", True
        note = ""
    return {
        "tag": tag,
        "cls": cls,
        "cluster": cluster,
        "note": note,
        "aligned": aligned,
        "first_digits": ds,
        "top_digit": top_d,
    }

def book_label(b):
    b = str(b or "").lower()
    if "betmgm" in b or b == "mgm": return "MGM"
    if "draftkings" in b or b == "dk": return "DK"
    if "fanduel" in b or b == "fd": return "FD"
    if "hardrock" in b: return "HardRock"
    if "fanatic" in b: return "Fanatics"
    if "caesars" in b or "williamhill" in b: return "Caesars"
    if "bet365" in b or b in ("365", "b365"): return "Bet365"
    if b in ("untagged", "unknown", "-", ""): return "Untagged"
    return b.title() if b else "Untagged"

def fold_name(name):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def player_key(name):
    """Same human, one key: Andrés Giménez == Andres Gimenez."""
    return fold_name(clean_name(name))


def pretty_player_name(names):
    """Keep the accented spelling when two feeds disagree."""
    opts = [str(n).strip() for n in names if n]
    if not opts:
        return ""
    def _score(n):
        return (sum(1 for c in n if ord(c) > 127), len(n))
    return max(opts, key=_score)


def unify_player_names(df):
    """Collapse accent / punctuation splits onto one display name."""
    if df is None or getattr(df, "empty", True) or "player" not in df.columns:
        return df
    df = df.copy()
    df["player_key"] = df["player"].map(player_key)
    canon = {}
    for k, g in df.groupby("player_key"):
        if not k:
            continue
        canon[k] = pretty_player_name(g["player"].tolist())
    df["player"] = df.apply(
        lambda r: canon.get(r.get("player_key"), r.get("player")),
        axis=1,
    )
    return df


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

def _fold_name(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace(".", "").replace("  ", " ").strip().lower()

def names_match(a, b):
    a, b = clean_name(a), clean_name(b)
    a2, b2 = _fold_name(a), _fold_name(b)
    if not a2 or not b2:
        return False
    if a2 == b2:
        return True
    pa, pb = a2.split(), b2.split()
    if len(pa) >= 2 and len(pb) >= 2:
        if pa[-1] == pb[-1] and pa[0][0] == pb[0][0]:
            return True
        if pa[-1] == pb[-1] and (pa[0].startswith(pb[0]) or pb[0].startswith(pa[0])):
            return True
    # box score sometimes last name only
    if len(pa) == 1 and len(pb) >= 2 and pa[0] == pb[-1]:
        return True
    if len(pb) == 1 and len(pa) >= 2 and pb[0] == pa[-1]:
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

def _norm_bk(b):
    k = str(b or "").lower()
    try:
        return normalize_book(k)
    except Exception:
        return k

def _is_ticket_book(b):
    k = _norm_bk(b)
    return k in TICKET_BOOKS or "hardrock" in k

def pick_ticket(prices, books):
    """Book we actually buy. Never BetMGM — MGM is a grouping tell only."""
    if not prices:
        return None, None
    paired = list(zip(prices, books))
    tickets = [(p, _norm_bk(b)) for p, b in paired if _is_ticket_book(b)]
    if tickets:
        tickets.sort(key=lambda x: x[0], reverse=True)
        best_p, best_b = tickets[0]
        if len(tickets) >= 2 and best_p - tickets[1][0] >= OUTLIER_GAP:
            return tickets[1][0], tickets[1][1]
        return best_p, best_b
    others = [(p, _norm_bk(b)) for p, b in paired if _norm_bk(b) not in SIGNAL_ONLY_BOOKS]
    if others:
        others.sort(key=lambda x: x[0], reverse=True)
        return others[0]
    return None, None

def longest_any(prices, books):
    if not prices:
        return None, None
    paired = sorted(zip(prices, [_norm_bk(b) for b in books]), key=lambda x: x[0], reverse=True)
    return paired[0]

def smart_best(prices, books):
    """Ticket price (DK/FD/HardRock/Fanatics). Falls back only if no ticket book exists."""
    t_p, t_b = pick_ticket(prices, books)
    if t_p is not None:
        return t_p, t_b
    return longest_any(prices, books)

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


def motion_line_html(item):
    lab = item.get("trend_motion") or "Stable"
    css = {"Heating up": "motion-heat", "Cooling down": "motion-cool", "Chaotic": "motion-chaos"}.get(lab, "motion-stable")
    return f'<div class="motion-line {css}">Motion: {lab}</div>'


def grouped_tag_html(methods):
    core, pattern, personality, meta = [], [], [], []
    for m in methods or []:
        nm = normalize_method_name(m)
        if nm in TAKE_IT_STRONG or nm in PRIORITY_METHODS or nm.startswith("EV") or nm.startswith("Kelly"):
            core.append(nm)
        elif nm in ("Classic Girl Magic", "Petty Pressure") or "Girl" in nm:
            personality.append(nm)
        elif nm in ("Benford Authentic",) or "Benford" in nm or "Numerology" in nm or "Trend" in nm:
            meta.append(nm)
        else:
            pattern.append(nm)
    blocks = []
    for title, pile in (("Core", core), ("Patterns", pattern), ("Personality", personality), ("Meta", meta)):
        if not pile:
            continue
        blocks.append(f'<div class="tag-group-lab">{title}</div>{render_method_tags(pile, 8)}')
    return "".join(blocks) or render_method_tags(methods or [])

def event_has_started(commence_iso):
    """True once first pitch / kick is at or past commence time (UTC)."""
    if not commence_iso:
        return False
    try:
        dt = datetime.fromisoformat(str(commence_iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= dt
    except Exception:
        return False


def _strip_game_clock(s):
    """'Away @ Home · 10:36 AM' -> 'Away @ Home' so fetch filter doesn't drop games."""
    s = str(s or "").strip()
    if " · " in s:
        left, right = s.rsplit(" · ", 1)
        if any(ch.isdigit() for ch in right) and ("am" in right.lower() or "pm" in right.lower() or ":" in right):
            return left.strip()
    return s



def live_event_labels():
    """Event names that have already kicked off / first pitch."""
    out = set()
    now = datetime.now(timezone.utc)
    for e in st.session_state.get("events") or []:
        t = e.get("commence_time") or ""
        if not t:
            continue
        try:
            start = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if now >= start:
                away = e.get("away_team") or ""
                home = e.get("home_team") or ""
                out.add(f"{away} @ {home}".strip())
        except Exception:
            continue
    return out


def row_event_is_live(event, live_labels):
    if not event or not live_labels:
        return False
    ev = _strip_game_clock(event)
    ev_l = ev.lower()
    for lab in live_labels:
        if ev == lab or ev_l == lab.lower():
            return True
        parts = [p.strip() for p in lab.lower().split("@")]
        if len(parts) == 2 and parts[0] and parts[1] and parts[0] in ev_l and parts[1] in ev_l:
            return True
    return False


def drop_live_game_rows(df):
    """Boards only. Results / lock / ledger keep the live names."""
    if df is None or getattr(df, "empty", True) or "event" not in df.columns:
        return df
    live = live_event_labels()
    if not live:
        return df
    mask = ~df["event"].map(lambda e: row_event_is_live(e, live))
    return df[mask].copy()

def event_matches_chosen(ev, chosen):
    if not chosen:
        return True
    ev_base = _strip_game_clock(ev)
    ev_l = ev_base.lower()
    chosen_bases = [_strip_game_clock(c) for c in chosen]
    if ev in chosen or ev_base in chosen or ev_base in chosen_bases:
        return True
    if ev_l in {c.lower() for c in chosen_bases}:
        return True
    for c in chosen_bases:
        parts_c = [p.strip() for p in str(c).lower().split("@")]
        if len(parts_c) == 2 and parts_c[0] and parts_c[1] and parts_c[0] in ev_l and parts_c[1] in ev_l:
            return True
    return False

def name_in_lineup(player, lineup_names):
    if not lineup_names:
        return None
    cn = clean_name(player)
    folded = fold_name(cn)
    lined = {fold_name(x) for x in lineup_names}
    if folded in lined or fold_name(player) in lined:
        return True
    parts = folded.split()
    if len(parts) >= 2:
        last, first = parts[-1], parts[0]
        fi = first[0]
        f3 = first[:3]
        for ln in lined:
            lp = ln.split()
            if len(lp) < 2:
                continue
            if lp[-1] == last and (lp[0][0] == fi or lp[0][:3] == f3):
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

def kelly_full(p_win, american):
    """Full Kelly fraction of bankroll. Negative = no bet."""
    dec = american_to_decimal(american)
    if not dec or p_win is None or p_win <= 0 or p_win >= 1:
        return 0.0
    b = dec - 1.0
    if b <= 0:
        return 0.0
    f = (b * p_win - (1.0 - p_win)) / b
    return float(f)

def kelly_units(p_win, american, fraction=0.25, bank_units=20.0):
    """Quarter-Kelly in units. Skip if full Kelly <= 0 or quarter < 0.25u.
    bank_units=20 means 1u is 5% of roll — no $100 language."""
    full = kelly_full(p_win, american)
    if full <= 0:
        return 0.0, "SKIP", full
    q = full * fraction
    units = q * bank_units
    if units < 0.25:
        return 0.0, "SKIP", full
    units = min(2.0, round(units * 2) / 2.0)
    if units <= 0.5:
        return 0.5, "0.5u", full
    if units <= 1:
        return 1.0, "1u", full
    return units, f"{units:g}u", full

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
    """Migrate old {price, ending, seen_at} -> first/latest/close shape."""
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
        if active_sport() == "MLB" and ip > MAX_HR_AMERICAN:
            continue

        if player not in lock or lock[player].get("date") != today:
            lock[player] = {
                "date": today, "event": event, "books": {},
                "locked_at": ts, "updated_at": ts,
                "sport": active_sport(),
            }
        entry = lock[player]
        if event:
            entry["event"] = event
        entry["date"] = today
        entry["updated_at"] = ts
        entry["sport"] = active_sport()
        entry.setdefault("books", {})
        seen_keys.add((player, book))

        prev = _book_slot_normalize(entry["books"].get(book) or {})
        if prev.get("first_price") is None:
            # OPEN - first pull of the day
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

    # CLOSE: books we had today but not in this fetch -> freeze latest as close
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
    if not lock:
        return {}
    if player in lock:
        return lock[player]
    cn = clean_name(player)
    if cn in lock:
        return lock[cn]
    want = player_key(player)
    for k, v in lock.items():
        if player_key(k) == want:
            return v
    return {}


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
    """Open -> latest / open -> close moves from the timing lock (500+ filter)."""
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
                f"{book_label(book)} open {format_odds(first)} ({t0}) -> "
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
    missing -> file 404 (not an error). error -> auth/network/parse failure.
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
        return []  # explicit empty remote - caller may still merge local
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
        # unconfigured or error -> local only
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
    # NEVER write today-only over the archive. Union with GitHub first.
    gh = _load_results_github()
    if isinstance(gh, list) and gh:
        rows = _merge_results_lists(gh, rows)
    _save_local_json(RESULTS_FILE, rows)
    if _gh_configured():
        ok = _save_results_github(rows)
        if not ok and not st.session_state.get("_gh_save_warned"):
            st.session_state["_gh_save_warned"] = True
            try:
                err = st.session_state.get("_gh_last_err") or "unknown"
                st.warning(
                    "Results saved on this server only - GitHub save failed. "
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


def load_take_ledger():
    """Durable Run It names. Survives board drop + session reset (same Cloud box)."""
    if not os.path.exists(TAKE_LEDGER_FILE):
        return {}
    try:
        with open(TAKE_LEDGER_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_take_ledger(data):
    try:
        with open(TAKE_LEDGER_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def ledger_dates():
    """AZ + ET so late/early slates still attach."""
    return sorted({today_az(), today_mlb_date()})


def ledger_names_today():
    data = load_take_ledger()
    names = []
    for d in ledger_dates():
        for row in data.get(d) or []:
            n = row.get("player")
            if n:
                names.append(n)
    try:
        rows = load_results()
    except Exception:
        rows = []
    for r in rows or []:
        if r.get("source") not in ("take_it", "shop_take"):
            continue
        if r.get("date") not in ledger_dates():
            continue
        if r.get("player"):
            names.append(r["player"])
    out, seen = [], set()
    for n in names:
        k = _fold_name(clean_name(n))
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    return out


def freeze_take_to_ledger(item, source="take_it"):
    data = load_take_ledger()
    today = today_az()
    bucket = data.setdefault(today, [])
    player = item.get("player") or ""
    if not player:
        return False
    for row in bucket:
        if names_match(row.get("player") or "", player) and row.get("source") == source:
            return False
    bucket.append({
        "player": player,
        "source": source,
        "score": item.get("score") or 0,
        "methods": list(item.get("methods") or []),
        "best_price": item.get("best_price"),
        "best_book": item.get("best_book"),
        "time": now_az(),
        "sport": active_sport(),
    })
    try:
        y = (datetime.now(timezone(timedelta(hours=-7))) - timedelta(days=1)).strftime("%Y-%m-%d")
        keep = set(ledger_dates()) | {y}
    except Exception:
        keep = set(ledger_dates())
    data = {k: v for k, v in data.items() if k in keep}
    save_take_ledger(data)
    return True


def log_bet_this(ev_board, watch_board=None):
    """Log TAKE IT (is_bet) and WATCH (1+ core, not bet) for auto-grade learning."""
    rows = load_results()
    today = today_az()
    added = 0
    watch_board = watch_board or []

    def already(player, source):
        """Block only the SAME source. WATCH can upgrade to take_it."""
        for r in rows:
            if r.get("date") not in (today, today_mlb_date()):
                continue
            if r.get("source") == "manual_hr":
                continue
            if not names_match(r.get("player") or "", player):
                continue
            if r.get("source") == source:
                return True
            if source == "watch" and r.get("source") in ("take_it", "shop_take"):
                return True
        return False

    def upgrade_watch_to_take(player):
        changed = False
        for r in rows:
            if r.get("date") not in (today, today_mlb_date()):
                continue
            if r.get("source") != "watch":
                continue
            if names_match(r.get("player") or "", player):
                r["source"] = "take_it"
                r["upgraded_from"] = "watch"
                changed = True
        return changed

    def append_row(item, source):
        nonlocal added
        player = item["player"]
        if already(player, source):
            return
        locked = get_locked(player)
        # Prefer FROZEN pregame lock prices - never learn from live numbers
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
            "sport": active_sport(),
            "team": item.get("team") or "",
            "market": "anytime_td" if active_sport() == "NFL" else "batter_home_runs",
            "benford_tag": (item.get("benford") or {}).get("tag"),
            "benford_note": (item.get("benford") or {}).get("note"),
            "benford_cluster": (item.get("benford") or {}).get("cluster"),
        })
        added += 1

    for item in ev_board:
        if item.get("is_bet") and stamp_count(item.get("methods") or [])[0] >= 2:
            upgrade_watch_to_take(item.get("player") or "")
            if not already(item.get("player") or "", "take_it"):
                append_row(item, "take_it")
            freeze_take_to_ledger(item, "take_it")
    for item in list(watch_board or []) + [x for x in ev_board if not x.get("is_bet")]:
        if item.get("is_bet"):
            continue
        stamps, _ms = stamp_count(item.get("methods") or [])
        if stamps < 1:
            continue
        if stamps >= 2:
            continue
        append_row(item, "watch")

    if added:
        save_results(rows)
    return added


def log_shop_calls(df):
    """Shop TAKE / LEAN -> Results so auto-grade can score the price call."""
    if df is None or getattr(df, "empty", True):
        return 0
    shop = build_shop_board(df)
    rows = load_results()
    today = today_az()
    added = 0

    def already_shop(player, source):
        return any(
            r.get("date") == today
            and r.get("player") == player
            and r.get("source") == source
            for r in rows
        )

    for r in shop:
        if r.get("action") not in ("TAKE", "LEAN"):
            continue
        player = r.get("player")
        if not player:
            continue
        if active_sport() == "NFL" and is_nfl_qb(player):
            continue
        src = "shop_take" if r["action"] == "TAKE" else "shop_lean"
        if already_shop(player, src):
            continue
        price = r.get("best")
        rows.append({
            "id": f"{today}_{player}_{src}_{int(r.get('edge') or 0)}",
            "date": today, "time": now_az(), "player": player,
            "score": 0, "edge": int(r.get("edge") or 0),
            "best_price": price, "best_book": r.get("best_book"),
            "median": r.get("median"),
            "book_prices": dict(r.get("books") or {}),
            "price_bucket": price_bucket(price),
            "ending": last_two(price) if price is not None else None,
            "methods": [f"Shop {r['action']}"],
            "core": 0,
            "result": "PENDING", "source": src, "logged_at": now_utc_iso(),
            "price_source": "shop",
            "sport": active_sport(),
            "market": "anytime_td" if active_sport() == "NFL" else "batter_home_runs",
        })
        added += 1
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



@st.cache_data(ttl=180, show_spinner=False)
def _fetch_nfl_td_scorers_cached():
    """Anytime TD scorers from ESPN. LIVE games + finals. Miss pool = finals only."""
    scorers, finished = set(), set()
    days = []
    for dfn in (today_az, today_mlb_date):
        try:
            days.append(datetime.strptime(dfn(), "%Y-%m-%d").strftime("%Y%m%d"))
        except Exception:
            pass
    if not days:
        days = [datetime.now().strftime("%Y%m%d")]
    days = list(dict.fromkeys(days))
    LIVE = {
        "STATUS_IN_PROGRESS", "STATUS_HALFTIME", "STATUS_END_PERIOD",
        "STATUS_END_QUARTER", "STATUS_FIRST_HALF", "STATUS_SECOND_HALF",
        "STATUS_END_OF_PERIOD", "STATUS_TIMEOUT",
    }
    FINAL = {"STATUS_FINAL", "STATUS_FINAL_OVERTIME"}
    events, seen_eid = [], set()
    for day in days:
        try:
            sb = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
                params={"dates": day}, timeout=15,
            ).json()
        except Exception:
            continue
        for ev in sb.get("events") or []:
            eid = str(ev.get("id") or "")
            if eid and eid not in seen_eid:
                seen_eid.add(eid)
                events.append(ev)
    pull_ids = []
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0]
        status = ((comp.get("status") or {}).get("type") or {})
        eid = ev.get("id")
        if not eid:
            continue
        name = str(status.get("name") or "").upper()
        completed = bool(status.get("completed")) or name in FINAL
        live = name in LIVE or str(status.get("state") or "").lower() == "in"
        if completed or live:
            pull_ids.append((str(eid), completed))
    done_ids = [eid for eid, fin in pull_ids if fin]
    live_n = sum(1 for _e, fin in pull_ids if not fin)
    all_qb, all_rush = set(), set()
    for eid, is_final in pull_ids[:24]:
        try:
            sm = requests.get(
                "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary",
                params={"event": eid}, timeout=15,
            ).json()
        except Exception:
            continue
        for play in sm.get("scoringPlays") or []:
            text = str(play.get("text") or play.get("shortText") or "").lower()
            itype = str((play.get("type") or {}).get("text") or "").lower()
            if "touchdown" not in text and "touchdown" not in itype and " td" not in f" {text}":
                continue
            if "extra point" in text or "two-point" in text:
                continue
            athletes = list(play.get("athletesInvolved") or [])
            itype_l = itype
            is_pass = (
                "passing touchdown" in itype_l
                or "pass touchdown" in itype_l
                or ("pass" in itype_l and "rush" not in itype_l)
                or "pass to" in text
                or "pass intended" in text
            )
            is_int = "interception return" in text or "intercepted" in text
            is_rush = (
                "rushing touchdown" in itype_l
                or "rush" in itype_l
                or (("runs" in text or "rushed" in text or "scrambles" in text) and "pass" not in text)
            )
            is_return = "return" in itype_l or "punt return" in text or "kick return" in text or "kickoff return" in text
            names = []
            if is_pass and not is_rush:
                # Catcher only. Never the QB.
                if len(athletes) >= 2:
                    n = athletes[1].get("displayName") or athletes[1].get("fullName")
                    if n:
                        names.append(n)
                else:
                    import re as _re
                    m = _re.search(r"\b(?:to|for)\s+([A-Z][a-zA-Z\.\'\-]+(?:\s+[A-Z][a-zA-Z\.\'\-]+){0,3})", play.get("text") or "")
                    if not m:
                        m = _re.search(r"\b(?:to|for)\s+([a-z\.\'\- ]+?)(?:\s+for\s+|\s+\d+|$)", text)
                    if m:
                        names.append(m.group(1).strip().title())
            elif is_rush or is_return or is_int:
                for ath in athletes[:1]:
                    n = ath.get("displayName") or ath.get("fullName")
                    if n:
                        names.append(n)
            # else: ignore field goals / mystery scoring
            for n in names:
                if n:
                    scorers.add(clean_name(n))
        box = ((sm.get("boxscore") or {}).get("players") or [])
        qb_names = set()
        rush_td = set()
        rec_td = set()
        ret_td = set()
        for team_block in box:
            for stat_group in team_block.get("statistics") or []:
                name = str(stat_group.get("name") or stat_group.get("label") or "").lower()
                keys = [str(k).lower() for k in (stat_group.get("labels") or stat_group.get("names") or [])]
                td_idx = None
                for i, k in enumerate(keys):
                    if k in ("td", "tds", "touchdowns"):
                        td_idx = i
                        break
                for ath in stat_group.get("athletes") or []:
                    ad = ath.get("athlete") or {}
                    n = ad.get("displayName")
                    pos = str((ad.get("position") or {}).get("abbreviation") or ad.get("position") or "").upper()
                    if pos == "QB" and n:
                        qb_names.add(clean_name(n))
                    if n and is_final and ("rush" in name or "receiv" in name or "return" in name):
                        finished.add(clean_name(n))
                    stats = ath.get("stats") or []
                    scored = False
                    if td_idx is not None and td_idx < len(stats):
                        try:
                            scored = float(stats[td_idx]) >= 1
                        except Exception:
                            scored = False
                    if not scored or not n:
                        continue
                    cn = clean_name(n)
                    if "pass" in name or "qb" in name:
                        qb_names.add(cn)
                        continue
                    if "rush" in name:
                        rush_td.add(cn)
                    elif "receiv" in name:
                        rec_td.add(cn)
                    elif "return" in name:
                        ret_td.add(cn)
        # Anytime TD = rush / catch / return. Passing TDs never count.
        legit = rush_td | rec_td | ret_td
        drop_qb = {q for q in (qb_names | set()) if q not in rush_td}
        scorers |= legit
        scorers -= drop_qb
        all_qb |= qb_names
        all_rush |= rush_td
    drop_qb = {q for q in all_qb if q not in all_rush}
    scorers -= drop_qb
    return (
        frozenset(scorers),
        frozenset(finished),
        f"ESPN NFL {len(done_ids)} final · {live_n} live · {len(scorers)} anytime TD names",
        frozenset(all_rush),
        frozenset(all_qb),
    )


def fetch_nfl_td_scorers():
    packed = _fetch_nfl_td_scorers_cached()
    if len(packed) == 5:
        scorers, finished, msg, rush_td, qbs = packed
    else:
        scorers, finished, msg = packed[:3]
        rush_td, qbs = set(), set()
    scorers = set(scorers or [])
    finished = set(finished or [])
    rush_td = set(rush_td or [])
    st.session_state["nfl_rush_td"] = rush_td
    st.session_state["nfl_qb_names"] = set(qbs or [])
    # QB counts only with a rushing TD.
    kept = set()
    for s in scorers:
        if is_nfl_qb(s) and not any(names_match(s, r) for r in rush_td):
            continue
        kept.add(s)
    return kept, finished, msg



def auto_grade_pending():
    rows = load_results()
    hits = misses = skipped = 0
    pending_n = sum(1 for r in rows if r.get("result") == "PENDING")
    if active_sport() == "NFL":
        td_names, done_players, msg = fetch_nfl_td_scorers()
        hit_set, miss_pool, tag = td_names, done_players, "nfl_auto"
    else:
        hr_names, final_players, msg = fetch_mlb_hr_hitters()
        hit_set, miss_pool, tag = hr_names, final_players, "mlb_auto"

    for row in rows:
        if row.get("result") != "PENDING":
            continue
        if active_sport() == "NFL":
            src = str(row.get("source") or "")
            mkt = str(row.get("market") or "").lower()
            if src.startswith("need_one"):
                skipped += 1
                continue
            if any(x in mkt for x in ("rush", "receiv", "reception", "yard")):
                skipped += 1
                continue
            if mkt and "td" not in mkt and "touchdown" not in mkt and src not in ("take_it", "watch", "shop_take", "shop_lean"):
                skipped += 1
                continue
        elif str(row.get("market") or "") == "anytime_td":
            skipped += 1
            continue
        player = row.get("player") or ""
        rushed = st.session_state.get("nfl_rush_td") or set()
        if active_sport() == "NFL" and is_nfl_qb(player) and not any(names_match(player, x) for x in rushed):
            row["result"] = "MISS"
            row["graded_by"] = tag + "_qb_not_rush"
            misses += 1
            continue
        if any(names_match(player, h) for h in hit_set):
            row["result"] = "HIT"
            row["graded_by"] = tag
            if row.get("ending") is None and row.get("best_price") is not None:
                row["ending"] = last_two(row["best_price"])
            hits += 1
            continue
        if miss_pool and any(names_match(player, f) for f in miss_pool):
            row["result"] = "MISS"
            row["graded_by"] = tag
            misses += 1
        else:
            skipped += 1

    save_results(rows)
    return hits, misses, skipped, f"{msg} · PENDING {pending_n} · matched {hits} HIT / {misses} MISS"



def pulse_book_and_ending(player, best_book, best_price, ending, lock, book_prices=None):
    """Pills = best book. Ending MUST come from that book's own number."""
    claimed_bl = book_label(best_book or "") if best_book else ""
    own_px = None
    if book_prices:
        for b, v in (book_prices or {}).items():
            if book_label(b) == claimed_bl:
                try:
                    own_px = int(v)
                except Exception:
                    own_px = None
                if own_px is not None:
                    break
    if own_px is None and lock and player and claimed_bl:
        for pname, data in (lock or {}).items():
            if not names_match(player, pname):
                continue
            for b, info in ((data or {}).get("books") or {}).items():
                if book_label(b) != claimed_bl:
                    continue
                px = (info or {}).get("latest_price")
                if px is None:
                    px = (info or {}).get("price")
                if px is None:
                    px = (info or {}).get("close_price")
                if px is None:
                    continue
                own_px = int(px)
                break
            break
    if own_px is not None:
        own_end = last_two(own_px)
    elif claimed_bl == "Fanatics":
        # Do not inherit MGM 25/50/75 just because Fanatics was the buy.
        own_end = None
        try:
            cand = last_two(best_price) if best_price is not None else ending
            cand = int(cand) if cand is not None else None
        except Exception:
            cand = None
        if cand is not None and cand not in (25, 50, 75):
            own_end = cand
    else:
        own_end = last_two(best_price) if best_price is not None else ending
    try:
        own_end = int(own_end) if own_end is not None else None
    except Exception:
        own_end = None
    return claimed_bl or None, own_end


def build_whats_going_today(rows):
    """Today's MLB HRs + ending/book from grades or Lock (best among DK/FD/MGM/HardRock).
    Not the same as MGM pair methods - those stay pair/trio-only on the Board.
    """
    today = today_az()
    if active_sport() == "NFL":
        hr_names, _final, _msg = fetch_nfl_td_scorers()
    else:
        hr_names, _final, _msg = fetch_mlb_hr_hitters()

    todays = [r for r in rows if r.get("date") in ledger_dates()]
    if active_sport() == "NFL":
        def _is_nfl_row(r):
            m = str(r.get("market") or r.get("sport") or "").lower()
            return "td" in m or "nfl" in m or m == "anytime_td"
        hits_logged = [r for r in todays if r.get("result") == "HIT" and _is_nfl_row(r)]
        graded = [r for r in todays if r.get("result") in ("HIT", "MISS") and _is_nfl_row(r)]
        our_list = [
            r for r in todays
            if r.get("source") in ("take_it", "watch", "shop_take", "shop_lean") and _is_nfl_row(r)
        ]
    else:
        hits_logged = [r for r in todays if r.get("result") == "HIT"]
        graded = [r for r in todays if r.get("result") in ("HIT", "MISS")]
        our_list = [
            r for r in todays
            if r.get("source") in ("take_it", "watch", "shop_take", "shop_lean")
        ]
    lock = st.session_state.get("pregame_lock") or load_pregame()

    # Players who appeared in an MGM pair/trio in history this session
    pair_players = set()
    for snap in st.session_state.get("mgm_history") or []:
        for g in snap:
            if len(g.get("players") or []) in (2, 3):
                pair_players.update(g["players"])

    FOCUS = {"DK", "FD", "MGM", "HardRock", "Bet365"}
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
        bl, ending = pulse_book_and_ending(
            r.get("player"), r.get("best_book"), r.get("best_price"), ending, lock,
            r.get("book_prices") or r.get("books"),
        )
        if ending is None or not bl:
            continue
        ending = int(ending)
        if bl not in FOCUS:
            # still show under Other via label as-is
            pass
        book_ending[(bl, ending)] += 1
        pname = clean_name(r.get("player") or "")
        if bl == "MGM" and any(names_match(pname, p) for p in pair_players):
            pair_ending[ending] += 1

    board_names = list(st.session_state.get("last_take_names") or [])
    shop_names = list(st.session_state.get("last_shop_take_names") or [])
    extra_names = board_names + shop_names + ledger_names_today()
    for hr in hr_names:
        on_file = any(names_match(hr, r.get("player") or "") for r in our_list)
        on_session = any(names_match(hr, n) for n in extra_names)
        if on_file or on_session:
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
    hr_status = []
    for hr in sorted(hr_names):
        tagged = "TAKE" if any(names_match(hr, r.get("player") or "") for r in our_list if r.get("source") in ("take_it", "shop_take")) else (
            "SHOP LEAN" if any(names_match(hr, r.get("player") or "") for r in our_list if r.get("source") == "shop_lean") else (
            "WATCH" if any(names_match(hr, r.get("player") or "") for r in our_list if r.get("source") == "watch") else (
            "BOARD" if any(names_match(hr, n) for n in extra_names) else "NOT ON LIST"
        )))
        hr_status.append((hr, tagged))
    return len(hr_names), len(graded), dict(by_book), on_our_list, pair_list, hr_status



def render_run_it_recap():
    """Lock tab table. Pulse banner is untouched."""
    rows = results_for_sport()
    today = today_az()
    sport = active_sport()
    if sport == "NFL":
        try:
            fetch_nfl_td_scorers()
        except Exception:
            pass
    prop = "TD prop" if sport == "NFL" else "HR prop"
    extra_day = today
    try:
        extra_day = today_mlb_date()
    except Exception:
        pass
    keep = []
    for r in rows:
        if r.get("date") not in (today, extra_day):
            continue
        res = str(r.get("result") or "").upper()
        src = str(r.get("source") or "")
        if sport == "NFL":
            mkt = str(r.get("market") or "").lower()
            if src.startswith("need_one") or any(x in mkt for x in ("rush", "receiv", "reception", "yard")):
                continue
            if is_nfl_qb(r.get("player") or ""):
                rushed = st.session_state.get("nfl_rush_td") or set()
                if not any(names_match(r.get("player") or "", x) for x in rushed):
                    continue
        if res in ("HIT", "MISS"):
            keep.append(r)
        elif src in ("watch", "shop_lean") and res in ("PENDING", "HIT", "MISS", "LEAN", "WATCH", ""):
            keep.append(r)
    if not keep:
        st.caption("No completed names yet. Grade Results, then come back.")
        return
    fn_loud = any(
        "fanatics" in str(r.get("best_book") or "").lower()
        or book_label(r.get("best_book") or "") == "Fanatics"
        for r in keep
    )
    queen = "Queen says: these names actually went." + (" Fanatics was on a lot of them." if fn_loud else "")
    st.markdown(f'<div class="wg-queen" style="text-align:left">{queen}</div>', unsafe_allow_html=True)
    slice_r = st.radio(
        "recap_slice",
        ["Hits only", "Misses only", "Tickets only", "Research only", "All unique names"],
        horizontal=True,
        key="recap_slice",
        label_visibility="collapsed",
    )
    if slice_r.startswith("Tickets"):
        keep = [r for r in keep if str(r.get("source") or "") in ("take_it", "shop_take", "bet_this", "take")]
    elif slice_r.startswith("Research"):
        keep = [r for r in keep if str(r.get("source") or "") in ("watch", "shop_lean", "lean", "research")]
    elif slice_r.startswith("Hits"):
        keep = [r for r in keep if str(r.get("result") or "").upper() == "HIT"]
    elif slice_r.startswith("Misses"):
        keep = [r for r in keep if str(r.get("result") or "").upper() == "MISS"]
    raw_n = len(keep)

    lock = st.session_state.get("pregame_lock") or load_pregame()

    def _signal(r):
        src = str(r.get("source") or "")
        if src in ("take_it", "shop_take"):
            return "TAKE", "💚 TAKE", "r-sig-take", "Confirmed play — full send."
        if src == "shop_lean":
            return "LEAN", "💖 LEAN", "r-sig-lean", "Borderline value — monitor."
        return "WATCH", "💜 WATCH", "r-sig-watch", "Potential — not confirmed."

    def _result(r):
        res = str(r.get("result") or "").upper()
        src = str(r.get("source") or "")
        if res == "HIT":
            return "HIT", "💚 HIT", "r-hit", 0
        if res == "MISS":
            return "MISS", "🔴 MISS", "r-miss", 1
        if src == "shop_lean":
            return "LEAN", "💖 LEAN", "r-lean", 2
        return "WATCH", "💜 WATCH", "r-watch", 3

    def _fn_best(player, book):
        if book != "Fanatics":
            return False
        entry = None
        for pname, data in (lock or {}).items():
            if names_match(player, pname):
                entry = data
                break
        if not entry:
            return False
        prices = {}
        for b, info in (entry.get("books") or {}).items():
            p = (info or {}).get("price")
            if p is None:
                continue
            prices[book_label(b)] = int(p)
        fn = prices.get("Fanatics")
        if fn is None:
            return False
        if "MGM" in prices and fn > prices["MGM"]:
            return True
        if "DK" in prices and fn > prices["DK"]:
            return True
        return False

    buckets = {}
    for r in keep:
        res_key, res_show, res_cls, rank = _result(r)
        sig_key, sig_show, sig_cls, tip = _signal(r)
        name = r.get("player") or "?"
        book = book_label(r.get("best_book") or "") or "—"
        key = (clean_name(name).lower(), res_key)
        if key not in buckets:
            buckets[key] = {
                "res_show": res_show, "res_cls": res_cls,
                "sig_show": sig_show, "sig_cls": sig_cls, "tip": tip,
                "name": name, "books": [], "prop": prop, "n": 0, "rank": rank,
                "sig_ord": {"TAKE": 0, "LEAN": 1, "WATCH": 2}.get(sig_key, 9),
            }
        item = buckets[key]
        item["n"] += 1
        if book and book not in item["books"] and book != "—":
            item["books"].append(book)
        if {"TAKE": 0, "LEAN": 1, "WATCH": 2}.get(sig_key, 9) < item["sig_ord"]:
            item["sig_show"], item["sig_cls"], item["tip"] = sig_show, sig_cls, tip
            item["sig_ord"] = {"TAKE": 0, "LEAN": 1, "WATCH": 2}.get(sig_key, 9)
        if rank < item["rank"]:
            item["rank"], item["res_show"], item["res_cls"] = rank, res_show, res_cls

    for item in buckets.values():
        item["book"] = " · ".join(item["books"]) if item["books"] else "—"

    ordered = sorted(buckets.values(), key=lambda x: (x["rank"], x["sig_ord"], x["name"].lower()))
    PAGE = 25
    total = len(ordered)
    pages = max(1, (total + PAGE - 1) // PAGE)
    page = int(st.session_state.get("recap_page") or 0)
    if page >= pages:
        page = 0
        st.session_state["recap_page"] = 0
    slice_rows = ordered[page * PAGE: page * PAGE + PAGE]

    body = []
    for item in slice_rows:
        badge = '<span class="recap-badge">🔥 Best Price</span>' if any(_fn_best(item["name"], b) for b in (item.get("books") or [item.get("book")])) else ""
        logs = str(item["n"])
        body.append(
            "<tr class='%s %s' title='%s'><td class='sig'>%s</td><td>%s</td><td>%s</td><td>%s%s</td><td>%s</td></tr>"
            % (item["res_cls"], item["sig_cls"], item["tip"], item["sig_show"], item["res_show"], item["name"], item["book"], badge, logs)
        )
    html = (
        '<div class="recap-wrap"><table class="recap-table">'
        "<thead><tr><th class='sig'>We called it</th><th>Did it go?</th><th>Player</th><th>Book logged</th><th>Times logged</th></tr></thead>"
        "<tbody>%s</tbody></table></div>"
    ) % "".join(body)
    st.markdown(html, unsafe_allow_html=True)
    nav1, nav2, nav3 = st.columns([1, 1, 4])
    with nav1:
        if st.button("← Prev", key="recap_prev", disabled=page <= 0):
            st.session_state["recap_page"] = max(0, page - 1)
            st.rerun()
    with nav2:
        if st.button("Next →", key="recap_next", disabled=page >= pages - 1):
            st.session_state["recap_page"] = min(pages - 1, page + 1)
            st.rerun()
    with nav3:
        st.caption(
            "Names %s–%s of %s unique · %s raw log rows. "
            "Times logged = duplicate Fetch/TAKE rows, not extra homers. "
            "We called it = highest call on that name (TAKE beats WATCH)."
            % (page * PAGE + 1, min((page + 1) * PAGE, total), total, raw_n)
        )



def pulse_from_live_lock():
    """One scorer, one pill. Best lock book + that book's last two. No Need One rows."""
    sport = active_sport()
    if sport == "NFL":
        names, _fin, _m = fetch_nfl_td_scorers()
    else:
        names, _fin, _m = fetch_mlb_hr_hitters()
    lock = st.session_state.get("pregame_lock") or load_pregame()
    focus = ["DK", "FD", "HardRock", "MGM", "Fanatics", "Caesars", "Bet365"]
    hit_ends = Counter()
    used = 0
    for nm in names or []:
        entry = None
        for pname, data in (lock or {}).items():
            if names_match(nm, pname):
                entry = data
                break
        if not entry:
            continue
        best_bl, best_px = None, None
        for b, info in (entry.get("books") or {}).items():
            slot = _book_slot_normalize(info) if "_book_slot_normalize" in globals() else (info or {})
            px = slot.get("close_price")
            if px is None:
                px = slot.get("latest_price")
            if px is None:
                px = slot.get("price")
            if px is None:
                continue
            bl = book_label(b)
            if bl not in focus:
                continue
            try:
                px = int(px)
            except Exception:
                continue
            if best_px is None or px > best_px:
                best_bl, best_px = bl, px
        if best_bl is None:
            continue
        end = last_two(best_px)
        if end is None:
            continue
        hit_ends[(best_bl, int(end))] += 1
        used += 1
    by_book = defaultdict(list)
    for (bl, end), cnt in hit_ends.items():
        by_book[bl].append((int(end), int(cnt)))
    for bl in by_book:
        by_book[bl].sort(key=lambda x: (-x[1], x[0]))
    return dict(by_book), used, len(names or [])


def render_whats_going_today():
    rows = results_for_sport()
    mlb_hr, n_graded, by_book, on_list, pair_list, hr_status = build_whats_going_today(rows)
    sport = active_sport()
    cfg = sport_cfg()
    live_books, _used, live_n = pulse_from_live_lock()
    if live_books:
        by_book = live_books
    if sport == "NFL":
        live_tds, _fin, _m = fetch_nfl_td_scorers()
        mlb_hr = len(live_tds or [])
        take_pool = list(st.session_state.get("last_take_names") or [])
        try:
            take_pool += ledger_names_today()
        except Exception:
            pass
        take_pool += [r.get("player") for r in rows if r.get("source") in ("take_it", "shop_take", "watch", "shop_lean")]
        on_list = sum(1 for nm in (live_tds or []) if any(names_match(nm, t) for t in take_pool if t))

    listed = [(n, tag) for n, tag in (hr_status or []) if tag and tag != "NOT ON LIST"]
    take_n = sum(1 for _n, t in listed if t == "TAKE")
    lean_n = sum(1 for _n, t in listed if t in ("SHOP LEAN", "LEAN"))
    watch_n = sum(1 for _n, t in listed if t in ("WATCH", "BOARD"))
    hit_word = cfg.get("hits") or ("TDs" if sport == "NFL" else "HRs")
    prop_word = "TD prop" if sport == "NFL" else "HR prop"

    def _norm_tag(tag):
        if tag == "TAKE":
            return "TAKE", "wg-take", "💚"
        if tag in ("SHOP LEAN", "LEAN"):
            return "LEAN", "wg-lean", "💖"
        if tag in ("WATCH", "BOARD"):
            return "WATCH", "wg-watch", "💜"
        if tag in ("DON'T", "DONT", "PASS"):
            return "DON'T", "wg-dont", "🔴"
        return tag, "", "✨"

    FOCUS = ["DK", "FD", "HardRock", "MGM", "Fanatics", "Caesars"]
    lock = st.session_state.get("pregame_lock") or load_pregame()
    by_names = defaultdict(list)
    for n, tag in listed:
        call, cls, emo = _norm_tag(tag)
        bl = None
        for r in rows:
            if names_match(n, r.get("player") or ""):
                bl = book_label(r.get("best_book") or "")
                break
        if not bl:
            for pname, data in (lock or {}).items():
                if names_match(n, pname):
                    books = (data or {}).get("books") or {}
                    best_bl, best_p = None, None
                    for b, info in books.items():
                        p = (info or {}).get("price")
                        if p is None:
                            continue
                        lab = book_label(b)
                        if lab not in FOCUS:
                            continue
                        if best_p is None or int(p) > int(best_p):
                            best_p, best_bl = p, lab
                    bl = best_bl
                    break
        by_names[bl or "Fanatics"].append((n, call, cls, emo))

    pills = []
    for bl in FOCUS:
        items = by_book.get(bl) or []
        people = by_names.get(bl) or []
        if not items and not people:
            continue
        top = items[0] if items else None
        # top = (ending, count) of live hits on that book
        if top:
            label = "%s · %s ended +x%02d" % (bl, top[1], top[0])
        else:
            label = "%s · —" % bl
        pop = ['<div class="wg-player" style="opacity:.8">How to read: book · how many went · last two digits of the price.</div>']
        if top:
            extra = " · ".join("%s ended +x%02d" % (c, e) for e, c in items[:3])
            pop.append('<div class="wg-player" style="opacity:.8">%s</div>' % extra)
        for n, call, cls, emo in people[:4]:
            pop.append('<div class="wg-player %s">%s %s — %s (%s)</div>' % (cls, emo, call, n, prop_word))
        if len(people) == 0:
            pop.append('<div class="wg-player" style="opacity:.65">No list names yet.</div>')
        pills.append(
            '<details class="pulse-pill"><summary>%s</summary><div class="pulse-pop">%s</div></details>'
            % (label, "".join(pop))
        )

    if sport == "NFL":
        queen = "Queen says: the TDs on the list are the ones that matter." if take_n else "Queen says: NFL lane — ticket books only."
    else:
        queen = "Queen says: Run It names went." if take_n else "Queen says: waiting on first-pitch receipts."

    books_block = "".join(pills) if pills else '<span class="pulse-pill">No names have rolled yet — odds still sleeping.</span>'
    mlb_on = "on" if sport == "MLB" else ""
    nfl_on = "on" if sport == "NFL" else ""
    html = (
        '<div class="wg-wrap">'
        '<div class="wg-top"><div>'
        '<div class="wg-title">Today’s Run It Pulse · %s</div>'
        '<div class="wg-sub">Pills = live scorers only. Best Lock book + that book’s last two. Need One props are not in these pills.</div>'
        '</div><div class="wg-switch">'
        '<span class="wg-pill %s">MLB</span>'
        '<span class="wg-pill %s">NFL</span>'
        '</div></div>'
        '<div class="wg-counts">💚 TAKE <b>%s</b> · 💖 LEAN <b>%s</b> · 💜 WATCH <b>%s</b> · %s <b>%s</b></div>'
        '<div class="wg-books">%s</div>'
        '<div class="wg-queen">%s</div>'
        '</div>'
    ) % (
        sport,
        mlb_on, nfl_on,
        take_n, lean_n, watch_n, hit_word, mlb_hr,
        books_block, queen,
    )
    st.markdown(html, unsafe_allow_html=True)


def build_tracker_stats(rows):
    """Signal methods (tags) vs best book taken vs ending on best price - kept separate."""
    done = [r for r in rows if r.get("result") in ("HIT", "MISS") and r.get("source") != "manual_hr"]
    method_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    book_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    ending_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    bucket_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    number_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    book_end_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    score_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
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
        # Best book we took (price source) - not the signal method
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
        try:
            sc = int(r.get("score"))
        except Exception:
            sc = None
        if sc is not None:
            if sc >= 85:
                lane = "Petty 85–100"
            elif sc >= 70:
                lane = "Petty 70–84"
            elif sc >= 50:
                lane = "Petty 50–69"
            else:
                lane = "Petty 0–49"
            if is_hit:
                score_stats[lane]["hit"] += 1
            else:
                score_stats[lane]["miss"] += 1
    return method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats, score_stats


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

def lines_dashboard_strip(results):
    st.markdown("""
    <style>
    .mv-hero{background:linear-gradient(135deg,#4c0519,#3b0764);border:1px solid #fb7185;border-radius:22px;padding:16px 18px;margin-bottom:12px;box-shadow:0 0 22px rgba(251,113,133,.25)}
    .mv-hero h3{font-family:'Playfair Display',serif;color:#fff;margin:0 0 6px;font-size:1.4rem}
    .mv-hero p{color:#fecdd3;margin:0;font-size:.88rem}
    .mv-up{border-color:#fb7185!important;box-shadow:0 0 14px rgba(239,68,68,.2)}
    .mv-down{border-color:#4ade80!important;box-shadow:0 0 14px rgba(74,222,128,.2)}
    .bf-meter{height:10px;background:#1e1b4b;border-radius:999px;overflow:hidden;margin:8px 0}
    .bf-meter span{display:block;height:100%;border-radius:999px}
    </style>
    """, unsafe_allow_html=True)
    ups = sum(1 for r in results if r.get("type") == "hist" and r.get("move_dir") == "up")
    downs = sum(1 for r in results if r.get("type") == "hist" and r.get("move_dir") == "down")
    late = sum(1 for r in results if r.get("type") == "late")
    good = sum(1 for r in results if r.get("type") == "trend" and r.get("trend_kind") == "good")
    st.markdown(
        f'<div class="petty-row">'
        f'<div class="petty-box"><div class="petty-num">{ups + downs}</div><div class="petty-label">MOVES</div></div>'
        f'<div class="petty-box"><div class="petty-num">{late}</div><div class="petty-label">MISSING</div></div>'
        f'<div class="petty-box"><div class="petty-num">{good}</div><div class="petty-label">TRENDS</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def show_player_cards(typ, banner, explain, results):
    st.markdown("""
    <style>
    .meth-hero{background:linear-gradient(135deg,#3b0764,#831843);border:1px solid #e879f9;border-radius:22px;padding:14px 16px;margin-bottom:10px;box-shadow:0 0 20px rgba(232,121,249,.22)}
    .meth-hero h3{font-family:'Playfair Display',serif;color:#fff;margin:0 0 4px;font-size:1.28rem}
    .meth-hero p{color:#f5d0fe;margin:0;font-size:.84rem}
    .meth-card{transition:box-shadow .15s ease}
    .meth-card:hover{box-shadow:0 0 16px rgba(244,114,182,.35)}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="meth-hero"><h3>{banner}</h3><p>{explain}</p></div>', unsafe_allow_html=True)
    items = aggregate_by_player([r for r in results if r["type"] == typ])
    if typ == "signal":
        items = sorted(items, key=lambda r: (-int(r.get("book_count") or 0), r.get("label") or ""))
        st.caption("Sorted: most books first (3 → 2).")
    st.markdown(
        f'<div class="petty-row"><div class="petty-box"><div class="petty-num">{len(items)}</div>'
        f'<div class="petty-label">ON THIS PATTERN</div></div></div>',
        unsafe_allow_html=True,
    )
    if not items:
        st.info("Nobody wearing this tag yet.")
        return
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
                price_html = f'<div class="note">{price_line}</div>' if price_line else ""
                n_books = int(r.get("book_count") or 0)
                meter = make_meter(min(5, max(1, n_books or 2)), "high" if n_books >= 3 else "mid")
                st.markdown(
                    f'<div class="card meth-card" title="{explain}">'
                    f'<div class="card-name">{r["label"]}</div>'
                    f'<div class="note">{r["reason"]}</div>{price_html}{meter}'
                    f'<div style="margin-top:6px">{tags}</div></div>',
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
            "div.lineup.is-confirmed div.lineup__player a",
            "div.lineup.is-confirmed li.lineup__player a",
            "div.lineup__player a",
            "li.lineup__player a",
            "a.lineup__player-link",
        ):
            for el in soup.select(sel):
                t = el.get_text(" ", strip=True)
                t = " ".join(t.replace("\n", " ").split())
                if t and len(t.split()) >= 2 and not t.lower().startswith("http"):
                    names.add(clean_name(t))
        if not names:
            return set(), "RotoWire 0 names - site may block Streamlit or changed layout"
        return names, f"RotoWire {len(names)}"
    except Exception as e:
        return set(), f"RotoWire error: {e}"


def fetch_mlb_lineups():
    """Posted batting-order names from each game boxscore (works pre-game once posted)."""
    names = set()
    try:
        sch = requests.get(
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_mlb_date()}",
            timeout=20,
            headers={"User-Agent": "GirlMagic/1.0"},
        )
        if sch.status_code != 200:
            return set(), f"MLB schedule HTTP {sch.status_code}"
        pks = []
        for day in (sch.json().get("dates") or []):
            for g in day.get("games") or []:
                if g.get("gamePk"):
                    pks.append(g["gamePk"])
        for pk in pks:
            try:
                bx = requests.get(
                    f"https://statsapi.mlb.com/api/v1/game/{pk}/boxscore",
                    timeout=15,
                    headers={"User-Agent": "GirlMagic/1.0"},
                )
                if bx.status_code != 200:
                    continue
                teams = (bx.json().get("teams") or {})
                for side in ("away", "home"):
                    players = ((teams.get(side) or {}).get("players") or {})
                    for p in players.values():
                        if not p.get("battingOrder"):
                            continue
                        nm = (p.get("person") or {}).get("fullName")
                        if nm:
                            names.add(clean_name(nm))
            except Exception:
                continue
        return names, f"MLB {len(names)}"
    except Exception as e:
        return set(), f"MLB lineups error: {e}"



def short_lineup_msg(msg, n=0):
    raw = str(msg or "")
    if any(x in raw.lower() for x in ("nitter", "httpsconnection", "underdog", "max retries")):
        return f"{n} lineup names · MLB orders"
    # keep first two source bits only
    parts = [x.strip() for x in raw.replace("·", "|").split("|") if x.strip()]
    keep = [x for x in parts if "nitter" not in x.lower() and "http" not in x.lower()][:3]
    out = " · ".join(keep) if keep else raw
    return out[:80]


def fetch_all_lineups():
    rw, rw_msg = fetch_rotowire_lineups()
    mlb, mlb_msg = fetch_mlb_lineups()
    bits = [x for x in (rw_msg, mlb_msg) if x]
    if len(mlb) >= 40:
        names = set(mlb)
        note = "filter=MLB orders"
    else:
        names = set(mlb) | set(rw)
        note = "filter=merged"
    if not names:
        return set(), " · ".join(bits) or "No lineups yet"
    return names, f"{len(names)} used · " + " · ".join(bits) + " · " + note

def _slate_commence_window():
    """Full same-day card in AZ: early first pitch through late West extras."""
    az = timezone(timedelta(hours=-7))
    now_az = datetime.now(az)
    start = now_az.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)
    days = int(sport_cfg().get("days") or 1)
    end = now_az.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=max(1, days), hours=8)
    return (
        start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@st.cache_data(ttl=90, show_spinner=False)
def _fetch_events_oddsapi_cached(api_key, sport_key, t_from, t_to):
    params = {
        "apiKey": api_key,
        "commenceTimeFrom": t_from,
        "commenceTimeTo": t_to,
    }
    r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params=params, timeout=15)
    r.raise_for_status()
    data = r.json() or []
    # if the windowed call is empty, fall back so we never show zero on a live day
    if not data:
        r2 = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
        r2.raise_for_status()
        data = r2.json() or []
    return data


def fetch_events_oddsapi(api_key, sport_key=None):
    sport_key = sport_key or sport_cfg()["key"]
    t_from, t_to = _slate_commence_window()
    try:
        return _fetch_events_oddsapi_cached(api_key, sport_key, t_from, t_to)
    except Exception as e:
        st.error(f"Odds API events error: {e}")
        return []

def _merge_oddsapi_events(a, b):
    """Union bookmakers from US + UK payloads. Never drop either side."""
    if not a and not b:
        return None
    if not a:
        return b
    if not b:
        return a
    out = dict(a)
    books = list(a.get("bookmakers") or [])
    seen = {(bk.get("key") or "").lower() for bk in books}
    for bk in (b.get("bookmakers") or []):
        k = (bk.get("key") or "").lower()
        if k and k not in seen:
            books.append(bk)
            seen.add(k)
            continue
        # same book, merge extra markets
        if k:
            dest = next((x for x in books if (x.get("key") or "").lower() == k), None)
            if dest is not None:
                mk = list(dest.get("markets") or [])
                have = {(m.get("key") or "") for m in mk}
                for m in (bk.get("markets") or []):
                    if (m.get("key") or "") not in have:
                        mk.append(m)
                dest["markets"] = mk
    out["bookmakers"] = books
    return out


def fetch_odds_oddsapi(api_key, event_id, sport_key=None, market=None, restrict_books=True):
    """US books + UK Bet365. Pinning US keys on the UK call hides 365 — split them."""
    cfg = sport_cfg()
    sport_key = sport_key or cfg["key"]
    market = market or cfg["market"]
    markets = market
    if market == "batter_home_runs":
        markets = "batter_home_runs,batter_home_runs_alternate"
    if market == "player_anytime_td":
        markets = (
            "player_anytime_td,"
            "player_rush_yds,player_reception_yds,player_receptions"
        )
    url = f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds"
    us_books = ",".join([
        "fanduel", "draftkings", "betmgm", "fanatics",
        "hardrockbet", "hardrockbet_az", "hardrockbet_oh", "hardrockbet_fl",
        "caesars", "williamhill_us",
    ])
    dbg = st.session_state.setdefault("oddsapi_region_debug", {})

    def _one(region, bookmakers=None):
        params = {
            "apiKey": api_key,
            "regions": region,
            "markets": markets,
            "oddsFormat": "american",
        }
        if bookmakers:
            params["bookmakers"] = bookmakers
        try:
            r = requests.get(url, params=params, timeout=20)
            keys = []
            body = None
            if r.status_code == 200:
                body = r.json()
                keys = [(bk.get("key") or "") for bk in (body.get("bookmakers") or [])]
            dbg[str(region)] = {
                "status": r.status_code,
                "keys": keys,
                "err": (r.text or "")[:180] if r.status_code != 200 else "",
            }
            return body
        except Exception as e:
            dbg[str(region)] = {"status": "exc", "keys": [], "err": str(e)[:180]}
            return None

    us = _one("us", us_books if restrict_books else None)
    # AU: Bet365 AU only — The Odds API has no UK bet365 key. Do not send FanDuel keys on this call.
    uk = _one("au", "bet365_au")
    if not uk or not (uk.get("bookmakers") or []):
        uk = _one("uk", "bet365")
    if not uk or not (uk.get("bookmakers") or []):
        uk = _one("uk", None)
    if not uk or not (uk.get("bookmakers") or []):
        uk = _one("au", None)  # open AU feed, then we filter
    merged = _merge_oddsapi_events(us, uk)
    return merged


def flatten_oddsapi(data):
    if not data: return [], set()
    rows, found = [], set()
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    for book in data.get("bookmakers", []):
        raw = (book.get("key") or "").lower()
        title = book.get("title") or ""
        found.add(raw or title.lower())
        bk = normalize_book(raw) if raw else ""
        if bk not in PREFERRED:
            bk = normalize_book(title)
        if bk not in PREFERRED: continue
        for market in book.get("markets", []):
            # accept standard + alternate HR markets; still force 0.5 only
            mkey = (market.get("key") or "").lower()
            is_hr = ("home_run" in mkey) or ("homer" in mkey)
            is_td = ("anytime_td" in mkey) or ("touchdown" in mkey)
            need_map = {
                "player_rush_yds": "Rush Yards",
                "player_rush_yards": "Rush Yards",
                "player_reception_yds": "Receiving Yards",
                "player_receiving_yds": "Receiving Yards",
                "player_receptions": "Receptions",
            }
            prop_type = None
            for k, lab in need_map.items():
                if mkey == k or mkey == k + "_alternate":
                    prop_type = lab
                    break
            if prop_type and not is_full_game_prop(mkey):
                prop_type = None
                continue
            if mkey and not is_hr and not is_td and not prop_type:
                continue
            for o in market.get("outcomes", []):
                oname = str(o.get("name") or "").lower()
                pt = o.get("point")
                if is_td:
                    # Anytime TD Yes == Over 0.5 TD
                    if oname not in ("yes", "over"):
                        continue
                    if oname == "over" and pt is not None and abs(float(pt) - 0.5) > 0.01:
                        continue
                else:
                    if oname != "over":
                        continue
                    if pt is None or abs(float(pt) - 0.5) > 0.01:
                        continue
                player = o.get("description")
                price = o.get("price")
                if not player or price is None: continue
                try:
                    price = int(price)
                except Exception:
                    continue
                if prop_type:
                    if int(price) < 100:
                        continue
                elif price > MAX_HR_AMERICAN:
                    continue
                if is_td and abs(int(price)) < 115:
                    continue
                if is_blocked_player(player):
                    continue
                rows.append({
                    "event": event, "book": bk, "player": player, "price": price,
                    "point": 0.5, "team": "", "source": "oddsapi",
                    "sport": "NFL" if (is_td or prop_type) else "MLB",
                    "prop_type": prop_type,
                    "commence_time": data.get("commence_time") or "",
                })
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    """SGO is the Bet365 pipe. Odds API does not sell 365 NFL/MLB props."""
    rows, found = [], set()
    raw_keys = set()
    if not sgo_key:
        return rows, found
    league = "NFL" if active_sport() == "NFL" else "MLB"
    try:
        cursor = None
        pages = 0
        while pages < 8:
            pages += 1
            params = {
                "apiKey": sgo_key,
                "leagueID": league,
                "oddsAvailable": "true",
                "limit": 20,
            }
            if cursor:
                params["cursor"] = cursor
            r = requests.get(f"{SGO_BASE}/events", params=params, timeout=30)
            if r.status_code != 200:
                st.session_state.setdefault("fetch_debug", {})["sgo_http"] = r.status_code
                st.session_state["fetch_debug"]["sgo_err"] = (r.text or "")[:220]
                break
            payload = r.json() if r.content else {}
            batch = payload.get("data") or []
            if not batch:
                break
            for ev in batch:
                teams = ev.get("teams", {})
                home = teams.get("home", {}).get("names", {}).get("long", "Home")
                away = teams.get("away", {}).get("names", {}).get("long", "Away")
                event_name = f"{away} @ {home}"
                players_map = ev.get("players", {})
                for odd_id, odd_data in (ev.get("odds") or {}).items():
                    oid = str(odd_id).lower()
                    if "ou-over" not in oid and "-over" not in oid and "yes" not in oid:
                        continue
                    prop_type = None
                    is_hr = "batting_homeruns" in oid or "home_run" in oid
                    is_td = any(x in oid for x in (
                        "anytimetouchdown", "anytime_td", "anytime-touchdown",
                        "anytime_touchdown", "player_anytime_td", "atd",
                        "firsttouchdown", "lasttouchdown",
                    ))
                    # SGO often uses "touchdowns" / "scoringTouchdown" without "anytime"
                    if not is_td and "touchdown" in oid and "yard" not in oid and "pass" not in oid:
                        is_td = "rush" not in oid or "rushingtouchdown" in oid or "receivingtouchdown" in oid
                    if is_td or "touchdown" in oid or ("anytime" in oid and "yard" not in oid):
                        if is_td:
                            prop_type = None
                    elif "rushing_yards" in oid and "touchdown" not in oid:
                        prop_type = "Rush Yards"
                    elif "receiving_yards" in oid and "touchdown" not in oid:
                        prop_type = "Receiving Yards"
                    elif "receptions" in oid and "receiving" not in oid and "touchdown" not in oid:
                        prop_type = "Receptions"
                    if prop_type and not is_full_game_prop(oid):
                        prop_type = None
                    if league == "MLB" and not is_hr:
                        continue
                    if league == "NFL" and not (is_td or prop_type):
                        continue
                    ou = odd_data.get("bookOverUnder") or odd_data.get("fairOverUnder")
                    if is_td:
                        pass
                    else:
                        if ou is None:
                            continue
                        try:
                            if abs(float(ou) - 0.5) > 0.01:
                                continue
                        except Exception:
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
                        raw_keys.add(str(bk).lower())
                        b = normalize_book(bk)
                        if b not in PREFERRED:
                            continue
                        # Bet365 is often flagged available=false on SGO but still has a price
                        if not bd.get("available", True) and b != "bet365":
                            continue
                        price = bd.get("odds")
                        if price is None:
                            continue
                        try:
                            price = int(str(price).replace("+", ""))
                        except Exception:
                            continue
                        if prop_type and price < 100:
                            continue
                        if (is_hr or is_td) and price > MAX_HR_AMERICAN:
                            continue
                        if is_blocked_player(pname):
                            continue
                        found.add(bk)
                        found.add(b)
                        rows.append({
                            "event": event_name, "book": b, "player": pname, "price": price,
                            "point": 0.5, "team": team, "source": "sgo",
                            "sport": league,
                            "prop_type": prop_type,
                        })
            cursor = payload.get("nextCursor") or payload.get("next_cursor")
            if not cursor:
                break
        fd = st.session_state.setdefault("fetch_debug", {})
        fd["sgo_rows_built"] = len(rows)
        fd["sgo_books"] = sorted(found)
        fd["sgo_raw"] = sorted(raw_keys)
        fd["sgo_league"] = league
        fd["sgo_http"] = fd.get("sgo_http") or 200
    except Exception as e:
        st.warning(f"SGO note: {e}")
    return rows, found


def merge_odds(a, b):
    combined = a + b
    if not combined: return pd.DataFrame()
    df = pd.DataFrame(combined)
    if "prop_type" not in df.columns:
        df["prop_type"] = ""
    df["prop_type"] = df["prop_type"].fillna("")
    df["priority"] = df["source"].map({"oddsapi": 0, "sgo": 1})
    df = df.sort_values(["player", "book", "prop_type", "event", "priority"])
    team_map = {}
    for _, r in df.iterrows():
        if r.get("team"): team_map[r["player"]] = r["team"]
    df["team"] = df.apply(lambda r: r["team"] if r.get("team") else team_map.get(r["player"], ""), axis=1)
    # Andrés Giménez vs Andres Gimenez = one player before book dedupe
    df = unify_player_names(df)
    team_map2 = {}
    for _, r in df.iterrows():
        if r.get("team"):
            team_map2[r["player"]] = r["team"]
    df["team"] = df.apply(lambda r: r["team"] if r.get("team") else team_map2.get(r["player"], ""), axis=1)
    # Never collapse TD vs receiving vs rush onto one book price
    df = df.drop_duplicates(subset=["player", "book", "prop_type", "event"], keep="first")
    return df.drop(columns=["priority", "source", "player_key"], errors="ignore")

def resolve_event_id(label, options):
    """Match Away @ Home even when the clock on the multiselect label changed."""
    if not options:
        return None
    if label in options:
        return options[label]
    base = _strip_game_clock(label)
    for k, vid in options.items():
        if k == label or _strip_game_clock(k) == base:
            return vid
        if event_matches_chosen(k, [label]) or event_matches_chosen(label, [k]):
            return vid
    return None


def remap_selected_labels(old_sel, options):
    """Keep early + late picks after Load games rewrites ' · 7:10 PM'."""
    keys = list(options.keys())
    if not old_sel:
        return keys
    out = []
    seen = set()
    for s in old_sel:
        hit = None
        if s in options:
            hit = s
        else:
            base = _strip_game_clock(s)
            for k in keys:
                if _strip_game_clock(k) == base or event_matches_chosen(k, [s]):
                    hit = k
                    break
        if hit and hit not in seen:
            seen.add(hit)
            out.append(hit)
    # new late games that weren't in the old list — add them on a split slate
    for k in keys:
        if k not in seen:
            out.append(k)
    return out


def do_fetch(odds_key, sgo_key, chosen_labels, options):
    all_rows, all_found_raw = [], set()
    http_ok = 0
    http_fail = 0
    per_event = {}
    fetch_labels = list(chosen_labels or [])
    # if the box is empty or clocks desynced, pull the whole loaded slate
    if not fetch_labels:
        fetch_labels = list(options.keys())
    else:
        fetch_labels = remap_selected_labels(fetch_labels, options)
    for label in fetch_labels:
        eid = resolve_event_id(label, options)
        if not eid:
            continue
        data = fetch_odds_oddsapi(odds_key, eid, restrict_books=True)
        if data is None:
            http_fail += 1
            per_event[label] = {"rows": 0, "status": "http_fail"}
            continue
        http_ok += 1
        rows, found = flatten_oddsapi(data)
        # Some early slates return empty when we pin bookmakers. Retry open US feed.
        if not rows:
            data2 = fetch_odds_oddsapi(odds_key, eid, restrict_books=False)
            if data2:
                rows2, found2 = flatten_oddsapi(data2)
                if rows2:
                    rows, found = rows2, found2
        all_rows.extend(rows)
        all_found_raw.update(found)
        ev_name = ""
        if data:
            ev_name = f"{data.get('away_team')} @ {data.get('home_team')}"
        per_event[label] = {
            "rows": len(rows),
            "status": "ok" if rows else "no_props",
            "event": ev_name,
            "books": len(found),
        }
    sgo_rows, sgo_found = [], set()
    if sport_cfg().get("sgo"):
        sgo_rows, sgo_found = fetch_sgo_hr_props(sgo_key)
        all_rows.extend(sgo_rows)
        all_found_raw.update(sgo_found)
    kept = {normalize_book(b) for b in all_found_raw} & PREFERRED
    prev = st.session_state.get("fetch_debug") or {}
    st.session_state["fetch_debug"] = {
        "http_ok": http_ok,
        "http_fail": http_fail,
        "raw_books": sorted(all_found_raw),
        "kept_books": sorted(kept),
        "regions": st.session_state.get("oddsapi_region_debug") or {},
        "row_count_pre_filter": len(all_rows),
        "sgo_rows": len(sgo_rows),
        "sgo_league": prev.get("sgo_league"),
        "sgo_http": prev.get("sgo_http"),
        "sgo_books": prev.get("sgo_books"),
        "sgo_raw": prev.get("sgo_raw"),
        "sgo_err": prev.get("sgo_err"),
        "per_event": per_event,
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
    if df is not None and not df.empty and "prop_type" in df.columns:
        need_df = df[df["prop_type"].notna() & (df["prop_type"] != "")].copy()
        df = df[df["prop_type"].isna() | (df["prop_type"] == "")].copy()
        st.session_state["need_one_odds"] = need_df.to_dict("records")
    else:
        st.session_state["need_one_odds"] = st.session_state.get("need_one_odds") or []
    st.session_state["fetch_debug"]["row_count_final"] = 0 if df is None or df.empty else len(df)
    st.session_state["fetch_debug"]["need_one_rows"] = len(st.session_state.get("need_one_odds") or [])
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
    # NFL props often have no team — don't dump every green into UNK and cap at 3.
    max_team = 8 if nfl_loose_mode() else BOARD_MAX_PER_TEAM
    max_game = 8 if nfl_loose_mode() else BOARD_MAX_PER_GAME
    for item in ranked:
        team = (item.get("team") or "").strip()
        game = item.get("event") or (item.get("events") or ["UNK"])[0]
        if team and per_team[team] >= max_team:
            continue
        if per_game[game] >= max_game:
            continue
        out_takes.append(item)
        if team:
            per_team[team] += 1
        per_game[game] += 1
    passes = sorted(passes, key=lambda x: (-x["method_count"], -x["score"], -x["edge"]))
    return out_takes + passes


def _item_game(item):
    return item.get("event") or (item.get("events") or [""])[0]


def apply_team_picks(ev_board, watch_board, coverage_board):
    """1 name per team when that team has zero TAKE ITs. Never sets is_bet."""
    takes = [x for x in (ev_board or []) if x.get("is_bet")]
    taken = {(_item_game(x), x.get("team") or "") for x in takes}
    take_names = {x.get("player") for x in takes}

    leftovers = []
    for src, pool in (("PASS", ev_board), ("WATCH", watch_board), ("COVERAGE", coverage_board)):
        for x in pool or []:
            if x.get("is_bet") or x.get("player") in take_names:
                continue
            if src == "PASS" and x.get("is_bet"):
                continue
            if src == "PASS" and x.get("is_bet") is True:
                continue
            row = dict(x)
            row["_pick_src"] = src
            leftovers.append(row)

    leftovers.sort(key=lambda x: (
        0 if x.get("_pick_src") == "PASS" else 1 if x.get("_pick_src") == "WATCH" else 2,
        -count_core_methods(x.get("methods") or []),
        -(x.get("score") or 0),
        -(x.get("edge") or 0),
    ))

    used = set(taken)
    seen = set(take_names)
    picks = []
    for x in leftovers:
        team = x.get("team") or ""
        game = _item_game(x)
        if not game:
            continue
        # Odds API NFL props have no team — fall back to 2 names per game
        if not team:
            game_count = sum(1 for k in used if k[0] == game)
            if game_count >= 2:
                continue
            key = (game, x.get("player"))
        else:
            key = (game, team)
        if key in used or x.get("player") in seen:
            continue
        if (x.get("score") or 0) < TEAM_PICK_MIN_SCORE and not (x.get("methods") or []):
            continue
        if not team:
            team = "this game"
        x = dict(x)
        x["team_pick"] = True
        x["is_bet"] = False
        x["why"] = (
            f"TEAM PICK · best on {team} this game · not full TAKE IT · "
            f"from {x.get('_pick_src')} · score {x.get('score', 0)}"
        )
        picks.append(x)
        used.add(key)
        seen.add(x.get("player"))
    return picks

def run_flags(df, previous_df=None, record_history=True, selected_events=None):
    if df.empty: return [], [], [], []
    if "team" not in df.columns: df["team"] = ""
    df = unify_player_names(df)
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

    # Lock had them on DK/FD/MGM - current fetch does not (true "missing from books")
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
            # on feed somewhere - only flag if focus books specifically missing
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
            line = f"{book}: {format_odds(prev_price)} -> {format_odds(curr_price)} ({int(abs(delta))} pts)"
            (player_up if delta > 0 else player_down)[player].append(line)
            if delta >= BIG_MOVE:
                results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 Shot up on {book}: {format_odds(prev_price)} -> {format_odds(curr_price)}", "methods": ["FADE · Shot way up"], "gap": abs(int(delta))})
            elif delta <= -BIG_MOVE:
                results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 Drop >100 on {book}: {format_odds(prev_price)} -> {format_odds(curr_price)}", "methods": ["FADE · Drop >100"], "gap": abs(int(delta))})
        for player, moves in sorted(player_up.items()):
            results.append({"type": "hist", "move_dir": "up", "label": player, "reason": "<br>".join(moves), "methods": ["Price moved"]})
        for player, moves in sorted(player_down.items()):
            results.append({"type": "hist", "move_dir": "down", "label": player, "reason": "<br>".join(moves), "methods": ["Price moved"]})
    # Lock timing moves: open -> latest/close (survives MGM drop)
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
            if HAS_NFL_MATH and active_sport() == "NFL":
                ok, gap, _fd, _mgm = nfl_math_fd_under_mgm({"fanduel": fd, "betmgm": mgm_price})
                if ok:
                    results.append({"type": "trend", "trend_kind": "good", "label": player, "reason": f"💚 FD under MGM by {int(gap)} · FD {format_odds(fd)} · MGM {format_odds(mgm_price)}", "methods": ["FD under MGM"], "gap": int(gap)})
            else:
                gap = mgm_price - fd
                if 10 <= gap <= 100:
                    results.append({"type": "trend", "trend_kind": "good", "label": player, "reason": f"💚 FD under MGM by {int(gap)} · FD {format_odds(fd)} · MGM {format_odds(mgm_price)}", "methods": ["FD under MGM"], "gap": int(gap)})
        if fd is not None and others and fd > max(others):
            results.append({"type": "trend", "trend_kind": "fade", "label": player, "reason": f"🔴 FD highest · {format_odds(fd)}", "methods": ["FADE · FD highest"], "gap": 0})
    for _, row in df.iterrows():
        if row["book"] != "draftkings": continue
        d = last_two(row["price"])
        if d == 10:
            results.append({"type": "dk", "label": row["player"], "reason": f"DK ends 10 -> {format_odds(row['price'])}", "event": row["event"], "methods": ["DK 10"]})
            methods_map[row["player"]].append("DK 10")
        elif d in FD_ENDINGS:
            results.append({"type": "dk", "label": row["player"], "reason": f"DK FD-style ends {d:02d} -> {format_odds(row['price'])}", "event": row["event"], "methods": ["DK FD-style"]})
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

    # Bet365 methods: 850, same-team 25/50/75 pairs, exact, higher than HardRock
    b365 = df[df["book"].map(lambda x: normalize_book(x) == "bet365")].copy() if not df.empty else df
    if b365 is not None and not b365.empty:
        for _, row in b365.iterrows():
            try:
                px = int(row["price"])
            except Exception:
                continue
            if int(px) == 850:
                results.append({
                    "type": "b365", "label": row["player"],
                    "reason": f"Bet365 +850 -> {format_odds(px)}",
                    "event": row.get("event"), "methods": ["B365 850"],
                })
                methods_map[row["player"]].append("B365 850")
        gk = ["event", "team"] if b365["team"].astype(str).str.len().gt(0).any() else ["event"]
        for keys, g in b365.groupby(gk, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            event, team = keys[0], (keys[1] if len(keys) > 1 else "")
            ends = defaultdict(list)
            for _, r in g.iterrows():
                d = last_two(r["price"])
                if d in (25, 50, 75):
                    ends[d].append(r["player"])
            for d, names in ends.items():
                names = sorted(set(names))
                if len(names) not in (2, 3):
                    continue
                kind = "pair" if len(names) == 2 else "group of 3"
                tnote = f" · {team}" if team else " · same team"
                meth = [f"B365 {d:02d}"]
                results.append({
                    "type": "b365", "label": " + ".join(names),
                    "reason": f"Bet365 {kind} ends {d:02d}{tnote}",
                    "event": event, "methods": meth,
                })
                for n in names:
                    methods_map[n].extend(meth)
            for price, pg in g.groupby("price"):
                names = sorted(pg["player"].unique())
                if len(names) not in (2, 3):
                    continue
                results.append({
                    "type": "b365", "label": " + ".join(names),
                    "reason": f"Bet365 Exact {format_odds(price)} ({len(names)})",
                    "event": event, "methods": ["B365 Exact"],
                })
                for n in names:
                    methods_map[n].append("B365 Exact")
    for player, g in df.groupby("player"):
        by_book = {normalize_book(r["book"]): r["price"] for _, r in g.iterrows()}
        ok, gap = False, 0
        try:
            ok, gap = nfl_b365_over_hardrock(by_book)
        except Exception:
            b3, hr = by_book.get("bet365"), by_book.get("hardrockbet")
            if b3 is not None and hr is not None and int(b3) > int(hr):
                ok, gap = True, int(b3) - int(hr)
        if ok:
            results.append({
                "type": "trend", "trend_kind": "good", "label": player,
                "reason": f"💚 Bet365 over HardRock by {int(gap)} · 365 {format_odds(by_book.get('bet365'))} · HR {format_odds(by_book.get('hardrockbet'))}",
                "methods": ["B365 over HardRock"], "gap": int(gap),
            })
            methods_map[player].append("B365 over HardRock")
        ok2, gap2 = False, 0
        try:
            ok2, gap2 = b365_over_mgm(by_book)
        except Exception:
            b3, mg = by_book.get("bet365"), by_book.get("betmgm")
            if b3 is not None and mg is not None and int(b3) > int(mg):
                ok2, gap2 = True, int(b3) - int(mg)
        if ok2:
            results.append({
                "type": "trend", "trend_kind": "good", "label": player,
                "reason": f"💚 Bet365 over MGM by {int(gap2)} · 365 {format_odds(by_book.get('bet365'))} · MGM {format_odds(by_book.get('betmgm'))}",
                "methods": ["B365 over MGM"], "gap": int(gap2),
            })
            methods_map[player].append("B365 over MGM")
        fa = by_book.get("fanatics")
        pack = [int(by_book[k]) for k in ("draftkings", "fanduel", "betmgm", "hardrockbet", "bet365") if by_book.get(k) is not None]
        if fa is not None and pack:
            try:
                med = sorted(pack)[len(pack) // 2]
                gapf = int(fa) - int(med)
                if gapf >= 100:
                    results.append({
                        "type": "trend", "trend_kind": "good", "label": player,
                        "reason": f"💜 Fanatics over the pack by {gapf} · FA {format_odds(fa)} · pack ~{format_odds(med)}",
                        "methods": ["Fanatics over pack"], "gap": gapf,
                    })
                    methods_map[player].append("Fanatics over pack")
            except Exception:
                pass
        hr = by_book.get("hardrockbet")
        pack2 = [int(by_book[k]) for k in ("draftkings", "fanduel", "betmgm", "fanatics", "bet365") if by_book.get(k) is not None]
        if hr is not None and pack2:
            try:
                med2 = sorted(pack2)[len(pack2) // 2]
                gaph = int(hr) - int(med2)
                if gaph >= 50:
                    results.append({
                        "type": "trend", "trend_kind": "good", "label": player,
                        "reason": f"💜 HardRock over the pack by {gaph} · HR {format_odds(hr)} · pack ~{format_odds(med2)}",
                        "methods": ["HardRock over pack"], "gap": gaph,
                    })
                    methods_map[player].append("HardRock over pack")
            except Exception:
                pass

    FOCUS_KEYS = ("draftkings", "fanduel", "betmgm", "hardrockbet", "bet365")
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
                "reason": f"Books tight: {format_odds(lo)}-{format_odds(hi)} (gap {spread}) on {', '.join(labels)}",
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
            results.append({"type": "fd", "label": player, "reason": f"FD +600 (with DK/MGM) -> {format_odds(row['price'])}", "event": row["event"], "methods": ["FD 600"]})
            methods_map[player].append("FD 600")
        if price >= FD_MIN and last in FD_ENDINGS:
            results.append({"type": "fd", "label": player, "reason": f"FD ends {last:02d} (with DK/MGM) -> {format_odds(row['price'])}", "event": row["event"], "methods": ["FD Pattern"]})
            methods_map[player].append("FD Pattern")
    # FD+MGM classic combo (support tag - study timing before promoting)
    for player, ms in list(methods_map.items()):
        ms_set = set(ms)
        has_fd = ("FD Pattern" in ms_set) or ("FD 600" in ms_set)
        has_mgm_classic = bool(ms_set & {"MGM 25", "MGM 50", "MGM 75", "Match 25", "Match 50", "Match 75"})
        if has_fd and has_mgm_classic and "FD+MGM classic" not in ms_set:
            methods_map[player].append("FD+MGM classic")
            results.append({
                "type": "fd", "label": player,
                "reason": "FD Pattern/600 + MGM classic 25/50/75 (combo - tracking)",
                "event": "", "methods": ["FD+MGM classic"],
            })
    # Book personalities from Tracker week (display + TAKE helpers)
    px_map = defaultdict(dict)
    ev_map = {}
    for _, r in df.iterrows():
        try:
            px_map[r["player"]][normalize_book(r.get("book"))] = int(r["price"])
            ev_map[r["player"]] = r.get("event") or ""
        except Exception:
            pass
    for player, books in px_map.items():
        tickets = {b: p for b, p in books.items() if b in TICKET_BOOKS or b == "caesars"}
        if not tickets:
            continue
        best_b = max(tickets, key=lambda b: tickets[b])
        best_p = tickets[best_b]
        pack = [p for b, p in tickets.items() if b != best_b]
        pack_hi = max(pack) if pack else best_p
        end = last_two(best_p)
        ev0 = ev_map.get(player, "")

        def _add(tag, reason, typ="book"):
            if tag in methods_map[player]:
                return
            methods_map[player].append(tag)
            results.append({"type": typ, "label": player, "reason": reason, "event": ev0, "methods": [tag]})

        fn = fanatics_price_logic(books)
        if fn.get("way_over_mgm"):
            _add("Fanatics Loud", f"Fanatics {format_odds(fn['price'])} way over MGM by {fn['gap_mgm']}")
        if best_b == "fanatics" and pack and best_p - pack_hi >= 40 and abs(best_p) >= 500:
            if end in TAKE_HOT_ENDS or end in (10, 60):
                _add("Fanatics Rogue", f"Fanatics longest by {best_p - pack_hi} at {format_odds(best_p)}")
            else:
                _add("Fanatics Drift", f"Fanatics off cluster by {best_p - pack_hi}")
        elif best_b == "fanatics" and pack and pack_hi - best_p >= 40:
            _add("Fanatics Drift", "Fanatics short vs ticket pack")
        if fn.get("alone") and fn.get("price") and abs(fn["price"]) >= 500:
            _add("Fanatics Alone", "Fanatics only — WATCH, not TAKE")
        if best_b == "caesars" and end in HOT_BOOK_ENDS["caesars"] and abs(best_p) >= 500:
            _add("Caesars Classic", f"Caesars {format_odds(best_p)} ends {end:02d}")
        if best_b == "hardrockbet" and end in HOT_BOOK_ENDS["hardrockbet"] and abs(best_p) >= 500:
            _add("HardRock Heater", f"HardRock {format_odds(best_p)} ends {end:02d}")
        fd = books.get("fanduel")
        if fd is not None:
            fe = last_two(fd)
            if fe == 90:
                _add("FD 90", f"FD ends 90 at {format_odds(fd)}")
            elif fe == 50:
                _add("FD 50", f"FD ends 50 at {format_odds(fd)}")
            elif fe == 40:
                _add("FD 40", f"FD ends 40 at {format_odds(fd)}")
        cz = books.get("caesars")
        if cz is not None and last_two(cz) == 90 and abs(int(cz)) >= 400:
            _add("Caesars 90", f"Caesars ends 90 at {format_odds(cz)}")
        hrp = books.get("hardrockbet")
        if hrp is not None:
            he = last_two(hrp)
            if he == 50 and abs(int(hrp)) >= 400:
                _add("HardRock 50", f"HardRock ends 50 at {format_odds(hrp)}")
            elif he == 0 and abs(int(hrp)) >= 400:
                _add("HardRock 00", f"HardRock ends 00 at {format_odds(hrp)}")
        mgm = books.get("betmgm")
        if mgm is not None:
            me = last_two(mgm)
            if me == 60:
                _add("MGM 60", f"MGM ends 60 at {format_odds(mgm)}")
            elif me == 10:
                _add("MGM 10", f"MGM ends 10 at {format_odds(mgm)}")
            elif me == 40:
                _add("MGM 40", f"MGM ends 40 at {format_odds(mgm)}")
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
        if bk in ("draftkings", "fanduel", "hardrockbet", "betmgm", "caesars", "fanatics"):
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
        # MLB lineups only. Cached RotoWire HR names must never wipe the NFL Board.
        if active_sport() != "NFL" and lineup_names and len(lineup_names) >= 40 and name_in_lineup(player, lineup_names) is False: continue
        if active_sport() == "NFL" and is_nfl_qb(player):
            continue
        prices = g["price"].dropna().tolist()
        books = g["book"].tolist()
        if len(prices) < 1: continue
        signal_price, signal_book = longest_any(prices, books) if prices else (None, None)
        if len(prices) >= 2:
            best, best_book = smart_best(prices, books)
        else:
            best, best_book = pick_ticket(prices, books)
            if best is None:
                best, best_book = prices[0], _norm_bk(books[0])
        if best is None: continue
        try: med = statistics.median(prices) if len(prices) >= 2 else best
        except Exception: med = best
        # Edge vs pack uses the TICKET number, not the juiced MGM longshot.
        edge = best - med if len(prices) >= 2 else 0
        meths = list({normalize_method_name(m) for m in methods_map.get(player, [])})
        core_count = count_core_methods(meths)
        # show premium + support tags on cards; core_count still premium-only
        display_meths = [m for m in meths if is_core_method(m) or m in SUPPORT_ONLY or m in TAKE_IT_STRONG]
        if not display_meths:
            display_meths = list(meths)
        score = girl_magic_score(core_count, edge, display_meths)
        # Petty score is display/ranking only — is_bet still uses qualifies_take_it
        score = petty_score(display_meths, edge, core_count, None)
        conf, bars, level = get_confidence(score, core_count >= METHODS_MIN and edge >= EDGE_MIN)
        book_px = {}
        for bk, px in zip(books, prices):
            try:
                book_px[normalize_book(bk)] = int(px)
            except Exception:
                pass
        fair, fair_p, fair_mode = compute_market_fair(book_px)
        if fair is None:
            fair, fair_p, fair_mode = med, american_implied(med), "median"
        ev, kelly_f = ev_from_fair(best, fair)
        premium_core = count_core_methods(meths)
        for t in value_method_tags(ev, kelly_f):
            if t not in display_meths:
                display_meths.append(t)
            if t not in meths:
                meths.append(t)
        gap = (int(best) - int(fair)) if best is not None and fair is not None else edge
        core_count = count_core_methods(meths)
        score = petty_score(display_meths, gap, core_count, None)
        row = {
            "player": player, "best_price": best, "best_book": best_book, "median": med,
            "ticket_price": best, "ticket_book": best_book,
            "signal_price": signal_price, "signal_book": signal_book,
            "book_prices": book_px,
            "edge": gap, "fair": fair, "fair_mode": fair_mode,
            "ev": ev, "kelly_frac": kelly_f, "is_bet": False,
            "why": f"Score {score}/100 · {core_count} core · edge {int(edge)}",
            "methods": display_meths, "score": score, "bars": bars, "level": level,
            "method_count": core_count, "premium_core": premium_core,
            "team": team_map.get(player, ""),
            "events": list(player_events.get(player, [])),
            "event": next(iter(player_events.get(player, [])), ""),
        }
        # WATCH list starts as 1+ core; refined at display/log time
        if core_count >= 1:
            watch_board.append(dict(row))
        # COVERAGE = support-only tags (0 premium) - eyes only, never TAKE IT
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
                    " · not a bet - so we don't miss weak-tag names on Lab days"
                )
                cov["bars"], cov["level"] = 1, "low"
                coverage_board.append(cov)
        # PASS / TAKE IT pool: MLB needs 2 premium. NFL week 1 needs 1.
        if core_count < methods_min():
            continue
        is_bet = qualifies_take_it(core_count, display_meths, edge, best, book_px, best_book, score)
        has_pri = has_priority_method(display_meths)
        score_override = bool(is_bet and int(score or 0) >= SCORE_SOFT_TAKE)
        row["is_bet"] = is_bet
        row["num_tag"] = numerology_board_tag(player, best)
        fams = strong_method_families(display_meths)
        strong_n = len(fams)
        tri = " · 💎 DK+MGM+FD" if has_dk_mgm_fd(display_meths) else ""
        pri_note = " · priority ✓" if (is_bet and has_pri) else ""
        if is_bet:
            ov = " · score override (stack too fat to leave gray)" if score_override else ""
            why = (
                f"Score {score}/100 · {core_count} premium · {strong_n} families · "
                f"edge {int(edge)}{tri}{pri_note}{ov}"
            )
        else:
            miss = []
            if not has_pri:
                miss.append("pattern stack isn't complete")
            if edge < EDGE_MIN:
                miss.append("price isn't long enough vs the pack")
            if not nfl_loose_mode():
                lp = long_price_block(best, display_meths, book_px)
                if lp:
                    miss.append("number is too long / thin for a green light")
            why = (
                f"Score {score}/100 · PASS - "
                + (" · ".join(miss) if miss else "filtered")
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
        if count_core_methods(ms) >= (2 if nfl_loose_mode() else NAME_METHODS_MIN) and _has_strong(ms)
    ]
    if lineup_names:
        if len(lineup_names) >= 40:
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
                    rsn = f"Cross initials ({li_a}<->{fi_b}) · different teams"
                else:
                    rsn = f"Cross initials ({li_b}<->{fi_a}) · different teams"
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
        # One player, one vote. Dupes from extra fetches were inflating TAKE n.
        by_p = {}
        for r in subset:
            key = clean_name(r.get("player") or "").lower()
            if not key:
                continue
            prev = by_p.get(key)
            if prev is None or (prev.get("result") != "HIT" and r.get("result") == "HIT"):
                by_p[key] = r
        h = sum(1 for r in by_p.values() if r["result"] == "HIT")
        m = sum(1 for r in by_p.values() if r["result"] == "MISS")
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


def build_shop_grade_stats(rows, days=14):
    """Separate Shop report card: shop_take vs shop_lean (not Board methods)."""
    today = today_az()
    try:
        today_dt = datetime.strptime(today, "%Y-%m-%d")
    except Exception:
        today_dt = datetime.now()
    cutoff = (today_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    shop_src = ("shop_take", "shop_lean")
    graded = [
        r for r in rows
        if r.get("result") in ("HIT", "MISS")
        and r.get("source") in shop_src
        and (r.get("date") or "") >= cutoff
    ]

    def rate(subset):
        h = sum(1 for r in subset if r["result"] == "HIT")
        m = sum(1 for r in subset if r["result"] == "MISS")
        t = h + m
        pct = (100.0 * h / t) if t else None
        return h, m, t, pct

    overall = {src: rate([r for r in graded if r.get("source") == src]) for src in shop_src}

    by_date = {}
    for r in graded:
        d = r.get("date") or ""
        by_date.setdefault(d, {"shop_take": [], "shop_lean": []})
        src = r.get("source")
        if src in by_date[d]:
            by_date[d][src].append(r)
    daily = []
    for d in sorted(by_date.keys(), reverse=True):
        daily.append({
            "date": d,
            "shop_take": rate(by_date[d]["shop_take"]),
            "shop_lean": rate(by_date[d]["shop_lean"]),
        })

    book_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    ending_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    bucket_stats = defaultdict(lambda: {"hit": 0, "miss": 0})
    for r in graded:
        is_hit = r["result"] == "HIT"
        bl = book_label(r.get("best_book"))
        end = r.get("ending")
        if end is None and r.get("best_price") is not None:
            end = last_two(r.get("best_price"))
        buck = r.get("price_bucket") or price_bucket(r.get("best_price"))
        targets = [(book_stats, bl)]
        if end is not None:
            targets.append((ending_stats, f"{int(end):02d}"))
        if buck:
            targets.append((bucket_stats, buck))
        for store, key in targets:
            if not key:
                continue
            store[key]["hit" if is_hit else "miss"] += 1

    return overall, daily, book_stats, ending_stats, bucket_stats, len(graded)



def event_is_today(e):
    """Keep the FULL same-day slate: early cards already live + late first pitch still hours out."""
    t = e.get("commence_time") or ""
    if not t:
        return True
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:
        return True
    az = today_az()
    et = today_mlb_date()
    now = datetime.now(timezone.utc)
    # split slates: morning already underway through late West / extra innings
    if now - timedelta(hours=14) <= dt <= now + timedelta(hours=20):
        return True
    for hours, day in [(-7, az), (-4, et)]:
        local = dt.astimezone(timezone(timedelta(hours=hours))).strftime("%Y-%m-%d")
        if local == day:
            return True
    return False


def filter_events_today(events):
    days = sport_cfg().get("days", 1)
    if days <= 1:
        today_only = [e for e in events if event_is_today(e)]
        return today_only if today_only else events
    now = datetime.now(timezone.utc)
    kept = []
    for e in events:
        t = e.get("commence_time") or ""
        if not t:
            kept.append(e)
            continue
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except Exception:
            kept.append(e)
            continue
        if now - timedelta(hours=8) <= dt <= now + timedelta(days=days):
            kept.append(e)
    return kept if kept else events




def lock_player_summary(player, lock_entry, price_mode="close"):
    """Tags from lock. price_mode: close | latest | first.
    lines show open -> now/close when they differ.
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
                + f" -> {format_odds(p)}"
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


def _todays_nfl_td_names():
    """Who scored a TD today from graded Results (HIT)."""
    names = []
    seen = set()
    today = today_az()
    for r in load_results():
        if r.get("date") != today:
            continue
        if r.get("result") != "HIT":
            continue
        blob = str(r.get("market") or r.get("sport") or "").lower()
        is_nfl = "td" in blob or "nfl" in blob or blob == "anytime_td"
        if not is_nfl and r.get("source") != "manual_hr":
            # if sport toggle is NFL, still take HIT rows tagged NFL
            if str(r.get("sport") or "").upper() != "NFL":
                continue
        player = clean_name(r.get("player") or "")
        if not player or player.lower() in seen:
            continue
        seen.add(player.lower())
        names.append(player)
    return names


def build_lock_lab():
    """Today's hits matched to pregame Lock for learning. MLB = HRs. NFL = graded TDs."""
    if active_sport() == "NFL":
        live, _fin, espn_msg = fetch_nfl_td_scorers()
        graded = _todays_nfl_td_names()
        # Lock Lab needs WHO SCORED, not only who we already tapped HIT.
        names, seen = [], set()
        for n in list(live or []) + list(graded or []):
            k = _fold_name(clean_name(n))
            if not k or k in seen:
                continue
            seen.add(k)
            names.append(clean_name(n))
        hr_names = names
        mlb_msg = (
            f"{espn_msg}. {len(hr_names)} TD names (live ESPN + graded HIT). "
            "Lock match uses pre-kick prices when the name is in today's lock."
            if hr_names else
            f"{espn_msg}. No TD names yet — live games should appear as they score."
        )
    else:
        hr_names, _fin, mlb_msg = fetch_mlb_hr_hitters()
    lock = lock_for_sport()
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
            rn, rebuilt = lock_entry_from_results(hr)
            if rebuilt:
                entry, lock_name = rebuilt, rn
        if not entry:
            unmatched.append(hr)
            continue
        tags, lines, ends_by_book, best_book, best_price, price_map, primary_end = lock_player_summary(
            hr, entry, price_mode="close"
        )
        # 1 chip per HR for primary books (DK/FD/MGM best price) - no multi-book inflation
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

    # most tags first -> then most core tags -> name
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


# ── Numerology helpers (page only — does not change TAKE IT / Shop / Grade) ──
_NUM_SOFT = {
    1: "Leadership, ego, first-pitch energy.",
    2: "Partnership, balance, DK/FD harmony.",
    3: "Creativity, chaos, multi-book magic.",
    4: "Structure, lock discipline.",
    5: "Change, volatility, odds movement.",
    6: "Responsibility, lineup loyalty.",
    7: "Intuition, pattern-spotting.",
    8: "Power, payout, dominance.",
    9: "Completion, full-circle hits.",
    11: "Master intuition — double vision.",
    22: "Master builder — the long play.",
    33: "Master teacher — the lesson hits.",
}
_NUM_PETTY = {
    1: "Main character energy. First at-bat, first pitch, first in line.",
    2: "Pair energy. You and your girl. DK and FD holding hands.",
    3: "Chaos magic. Three books talking at once and somehow it slaps.",
    4: "Lock it. No wandering. Structure is sexy today.",
    5: "The line is gonna wiggle. Don’t panic — that’s the point.",
    6: "Lineup loyalty. If they’re penciled in, they’re penciled in.",
    7: "Intuition over impulse — trust your petty gut.",
    8: "Power and payout. 8s been loud when they wanna be loud.",
    9: "Full circle. If it started here, it ends here.",
    11: "Master 11. You’re seeing the pattern before the book does.",
    22: "Master 22. Build the parlay like architecture, not a vibe.",
    33: "Master 33. Teach the slate who’s running it.",
}
_DAY_SOFT = {
    1: "Today’s number 1 is first-pitch energy — lead, don’t chase.",
    2: "Today’s number 2 wants pairs and balance.",
    3: "Today’s number 3 is multi-book chaos. Stay cute, stay sharp.",
    4: "Today’s number 4 is lock discipline. No extra clicks.",
    5: "Today’s number 5 is movement day — watch the line, don’t marry it.",
    6: "Today’s number 6 is lineup loyalty. Starters only.",
    7: "Today’s number 7 means intuition over impulse — trust your petty gut.",
    8: "Today’s number 8 is power and payout energy.",
    9: "Today’s number 9 is completion — full-circle hits.",
}
_DAY_PETTY = {
    1: "1 today. You are the first pitch. Everybody else can wait.",
    2: "2 today. Find your pair. Solo heroics are mid.",
    3: "3 today. The books are messy and that’s the fun.",
    4: "4 today. If it ain’t locked, it ain’t loved.",
    5: "5 today. The number moves. So do you.",
    6: "6 today. If RotoWire didn’t write them down, we don’t either.",
    7: "7 today. Intuition over impulse — trust your petty gut.",
    8: "8 today. Power. Payout. Don’t whisper it.",
    9: "9 today. Close the circle. Grade the slate. Then we party.",
}
_TREND_NOTE = {
    1: "1s want the leadoff swing.",
    2: "2s keep pairing up like they rehearsed it.",
    3: "3s been chaotic in a cute way.",
    4: "4s are the lock girls — slow, then sudden.",
    5: "5s ride the move. Don’t fade the wiggle just to fade it.",
    6: "6s stay loyal to the lineup card.",
    7: "7s are the pattern-spotters. Quiet until they’re not.",
    8: "8s been wild all week — power and payout energy.",
    9: "9s close slates. Full-circle hits.",
}


def _num_reduce(n, keep_master=True):
    try:
        n = abs(int(n))
    except Exception:
        return None
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(d) for d in str(n))
    return n


def _num_date_number(d):
    """Returns (reduced 1-9, raw digit sum, formula string, optional master 11/22/33)."""
    raw = f"{d.year}{d.month:02d}{d.day:02d}"
    total = sum(int(ch) for ch in raw)
    master = total if total in (11, 22, 33) else None
    reduced = _num_reduce(total, keep_master=False)
    bits = " + ".join(list(raw)) + f" = {total}"
    if master:
        bits += f" → master {master} → {reduced}"
    elif total != reduced:
        bits += f" → {reduced}"
    return reduced, total, bits, master


def _num_letter(ch):
    return ((ord(ch.upper()) - 65) % 9) + 1 if ch.isalpha() else 0


def _num_name_number(name):
    return _num_reduce(sum(_num_letter(c) for c in clean_name(name)))


def _num_initials(text):
    letters = [c for c in str(text or "") if c.isalpha()]
    if not letters:
        return None
    return _num_reduce(sum(_num_letter(c) for c in letters))


def _num_meaning(n, petty):
    return (_NUM_PETTY if petty else _NUM_SOFT).get(n, "")


def _num_align(player_n, day_n):
    if player_n is None or day_n is None:
        return "neutral", "💜 Neutral"
    pn = _num_reduce(player_n, keep_master=False)
    dn = _num_reduce(day_n, keep_master=False)
    if pn == dn:
        return "strong", "💖 Strong match"
    if pn and dn and abs(pn - dn) in (1, 8):
        return "neutral", "💜 Neutral"
    return "off", "🖤 Off-vibe"


def numerology_board_tag(player, price):
    """Display-only. Never counts as a method / never flips TAKE IT."""
    try:
        d = datetime.strptime(today_az(), "%Y-%m-%d").date()
    except Exception:
        return None
    day = _num_reduce(_num_date_number(d)[0], keep_master=False)
    nn = _num_name_number(player)
    end = last_two(price)
    en = _num_reduce(end, False) if end is not None else None
    if nn == day and en == day:
        return f"Num {day} name+price"
    if en == day:
        return f"Num {day} price"
    if nn == day:
        return f"Num {day} name"
    return None


def _num_hits_window(rows, start_date, end_date):
    ends, names = Counter(), Counter()
    for r in rows:
        if r.get("result") != "HIT":
            continue
        try:
            d = datetime.strptime(r.get("date") or "", "%Y-%m-%d").date()
        except Exception:
            continue
        if not (start_date <= d <= end_date):
            continue
        end = r.get("ending")
        if end is None and r.get("best_price") is not None:
            end = last_two(r.get("best_price"))
        if end is not None:
            red = _num_reduce(int(end), keep_master=False)
            if red:
                ends[red] += 1
        nn = _num_name_number(r.get("player") or "")
        if nn:
            names[nn] += 1
    return ends, names


# ── ADDITIVE: data + alignment layer. Does not change TAKE / lock / digits. ──
def _align_book_prices(item):
    raw = item.get("book_prices") or item.get("books") or {}
    out = {}
    for k, v in raw.items():
        try:
            out[str(k)] = int(v)
        except Exception:
            continue
    return out


def _align_agree_band(prices):
    if len(prices) < 2:
        return 40
    vals = list(prices.values())
    spr = max(vals) - min(vals)
    if spr <= 15:
        return 100
    if spr <= 35:
        return 82
    if spr <= 60:
        return 68
    if spr <= 100:
        return 48
    return 22


_ALIGN_DIGIT = {
    "DK 10", "FD Pattern", "FD 600", "MGM 25", "MGM 50", "MGM 75", "MGM 00",
    "MGM Exact", "Match 25", "Match 50", "Match 75", "Exact Match", "B365 850",
}
_ALIGN_AGREE = {"Exact Match", "Books tight", "All books same", "Same on 3+ books", "Multi-book method"}
_ALIGN_MOVE = {"Multi-book Shorten", "FD under MGM", "B365 over HardRock"}
_ALIGN_MIS = {"Underpriced", "Overpriced", "Out-of-place"}


def odds_alignment_score(item, data_boost=0):
    methods = set(str(m) for m in (item.get("methods") or []))
    prices = _align_book_prices(item)
    score = _align_agree_band(prices)
    if methods & _ALIGN_DIGIT:
        score += 18
    if methods & _ALIGN_AGREE:
        score += 14
    if methods & _ALIGN_MOVE:
        score += 10
    if methods & _ALIGN_MIS:
        score += 12
    if "MGM Exact" in methods or "Exact Match" in methods:
        score += 8
    try:
        score += min(16, int(item.get("edge") or 0) // 12)
    except Exception:
        pass
    return int(score) + int(data_boost or 0)


_NFL_TEAMS = {
    "ARI": ["arizona", "cardinals"], "ATL": ["atlanta", "falcons"],
    "BAL": ["baltimore", "ravens"], "BUF": ["buffalo", "bills"],
    "CAR": ["carolina", "panthers"], "CHI": ["chicago", "bears"],
    "CIN": ["cincinnati", "bengals"], "CLE": ["cleveland", "browns"],
    "DAL": ["dallas", "cowboys"], "DEN": ["denver", "broncos"],
    "DET": ["detroit", "lions"], "GB": ["green bay", "packers"],
    "HOU": ["houston", "texans"], "IND": ["indianapolis", "colts"],
    "JAX": ["jacksonville", "jaguars"], "KC": ["kansas city", "chiefs"],
    "LA": ["la rams", "rams"], "LAC": ["chargers", "los angeles chargers"],
    "LAR": ["rams", "los angeles rams"], "LV": ["las vegas", "raiders"],
    "MIA": ["miami", "dolphins"], "MIN": ["minnesota", "vikings"],
    "NE": ["new england", "patriots"], "NO": ["new orleans", "saints"],
    "NYG": ["giants", "new york giants"], "NYJ": ["jets", "new york jets"],
    "PHI": ["philadelphia", "eagles"], "PIT": ["pittsburgh", "steelers"],
    "SEA": ["seattle", "seahawks"], "SF": ["san francisco", "49ers"],
    "TB": ["tampa", "buccaneers"], "TEN": ["tennessee", "titans"],
    "WAS": ["washington", "commanders"],
}


def _nfl_codes_in_text(text):
    t = str(text or "").lower()
    hits = []
    for code, aliases in _NFL_TEAMS.items():
        if code.lower() in t.split() or any(a in t for a in aliases):
            hits.append(code)
    return hits


def _fold_player(name):
    n = str(name or "").replace(",", " ")
    try:
        n = clean_name(n)
    except Exception:
        n = " ".join(n.split())
    return n.lower().strip()


def _savant_name_fold(raw):
    raw = str(raw or "").strip().strip('"')
    if "," in raw:
        last, first = raw.split(",", 1)
        return _fold_player(f"{first.strip()} {last.strip()}")
    return _fold_player(raw)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_savant_exit_velo(year=None):
    """Live Statcast EV / HH% / Barrel for every batter with 1+ BBE (longshots stay)."""
    year = year or datetime.now().year
    url = (
        "https://baseballsavant.mlb.com/leaderboard/statcast"
        f"?type=batter&year={year}&position=&team=&min=1&csv=true"
    )
    try:
        r = requests.get(url, timeout=25, headers={"User-Agent": "GirlMagic/1.0"})
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
    except Exception:
        return {}
    out = {}
    name_col = df.columns[0]
    for _, row in df.iterrows():
        key = _savant_name_fold(row.get(name_col))
        if not key:
            continue
        def num(*names):
            for n in names:
                if n in row and pd.notna(row[n]):
                    try:
                        return float(row[n])
                    except Exception:
                        continue
            return None
        out[key] = {
            "ev": num("avg_hit_speed"),
            "max_ev": num("max_hit_speed"),
            "hh": num("ev95percent"),
            "barrel": num("brl_percent"),
            "brl_pa": num("brl_pa"),
            "la": num("avg_hit_angle"),
            "sweet": num("anglesweetspotpercent"),
            "attempts": num("attempts"),
        }
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_mlb_hot_window(days=14):
    """Last N days HR / SLG via MLB Stats API. Low PA included."""
    end = datetime.now(timezone(timedelta(hours=-7))).date()
    start = end - timedelta(days=days)
    params = {
        "stats": "byDateRange",
        "group": "hitting",
        "sportId": 1,
        "season": end.year,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "playerPool": "all",
        "limit": 2000,
    }
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/stats", params=params, timeout=25)
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
    except Exception:
        return {}
    out = {}
    for s in splits:
        person = s.get("player") or {}
        name = person.get("fullName") or ""
        stt = s.get("stat") or {}
        key = _fold_player(name)
        if not key:
            continue
        def ni(*ks):
            for k in ks:
                if stt.get(k) not in (None, ""):
                    try:
                        return float(str(stt.get(k)).replace("%", ""))
                    except Exception:
                        continue
            return None
        out[key] = {
            "name": name,
            "pa": ni("plateAppearances"),
            "hr": ni("homeRuns"),
            "avg": ni("avg"),
            "slg": ni("slg"),
            "ops": ni("ops"),
        }
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_mlb_rookies(year=None):
    year = year or datetime.now().year
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1/sports/1/players?season={year}",
            timeout=25,
        )
        r.raise_for_status()
        people = (r.json() or {}).get("people") or []
    except Exception:
        return set()
    out = set()
    for p in people:
        debut = str(p.get("mlbDebutDate") or "")
        if debut.startswith(str(year)):
            out.add(_fold_player(p.get("fullName")))
    return out


# Park lat/lon for Open-Meteo. Enough to tag wind/temp, not a physics model.
_MLB_PARK_LL = {
    "yankees": (40.8296, -73.9262), "red sox": (42.3467, -71.0972),
    "blue jays": (43.6414, -79.3894), "orioles": (39.2839, -76.6217),
    "rays": (27.7683, -82.6534), "white sox": (41.8300, -87.6338),
    "guardians": (41.4962, -81.6852), "tigers": (42.3390, -83.0485),
    "royals": (39.0517, -94.4803), "twins": (44.9817, -93.2776),
    "astros": (29.7573, -95.3555), "athletics": (37.7516, -122.2005),
    "angels": (33.8003, -117.8827), "mariners": (47.5914, -122.3325),
    "rangers": (32.7473, -97.0812), "braves": (33.8908, -84.4677),
    "marlins": (25.7781, -80.2197), "mets": (40.7571, -73.8458),
    "phillies": (39.9061, -75.1665), "nationals": (38.8730, -77.0074),
    "cubs": (41.9484, -87.6553), "reds": (39.0979, -84.5082),
    "brewers": (43.0280, -87.9712), "pirates": (40.4469, -80.0057),
    "cardinals": (38.6226, -90.1928), "diamondbacks": (33.4453, -112.0667),
    "rockies": (39.7559, -104.9942), "dodgers": (34.0739, -118.2400),
    "padres": (32.7076, -117.1570), "giants": (37.7786, -122.3893),
}


def _team_key(name):
    n = str(name or "").lower()
    for k in _MLB_PARK_LL:
        if k in n:
            return k
    return ""


@st.cache_data(ttl=900, show_spinner=False)
def fetch_mlb_slate_context(day=None):
    """Today's games: park, probable SP + hand. Free Stats API."""
    day = day or datetime.now(timezone(timedelta(hours=-7))).strftime("%Y-%m-%d")
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "date": day,
        "hydrate": "probablePitcher,venue,weather,team",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        dates = (r.json() or {}).get("dates") or []
    except Exception:
        return {"games": [], "by_team": {}}
    games, by_team = [], {}
    for d in dates:
        for g in d.get("games") or []:
            home = ((g.get("teams") or {}).get("home") or {}).get("team") or {}
            away = ((g.get("teams") or {}).get("away") or {}).get("team") or {}
            venue = (g.get("venue") or {}).get("name") or ""
            wx = g.get("weather") or {}
            hp = ((g.get("teams") or {}).get("home") or {}).get("probablePitcher") or {}
            ap = ((g.get("teams") or {}).get("away") or {}).get("probablePitcher") or {}
            rec = {
                "home": home.get("name") or "",
                "away": away.get("name") or "",
                "venue": venue,
                "weather": " ".join(
                    str(wx.get(k) or "") for k in ("temp", "condition", "wind") if wx.get(k)
                ).strip(),
                "home_sp": hp.get("fullName") or "",
                "away_sp": ap.get("fullName") or "",
            }
            games.append(rec)
            by_team[_team_key(home.get("name"))] = {**rec, "ha": "home", "opp_sp": rec["away_sp"]}
            by_team[_team_key(away.get("name"))] = {**rec, "ha": "away", "opp_sp": rec["home_sp"]}
    return {"games": games, "by_team": by_team}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_open_meteo(lat, lon):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
            },
            timeout=12,
        )
        r.raise_for_status()
        cur = (r.json() or {}).get("current") or {}
        return {
            "temp": cur.get("temperature_2m"),
            "wind": cur.get("wind_speed_10m"),
            "wdir": cur.get("wind_direction_10m"),
        }
    except Exception:
        return {}


_PARK_HR = {
    "coors field": 128, "great american": 118, "yankee stadium": 116,
    "citizens bank": 114, "globe life": 112, "camden yards": 110,
    "fenway": 108, "guaranteed rate": 108, "minute maid": 107,
    "dodger stadium": 106, "american family": 105, "truist": 104,
    "loandepot": 103, "chase field": 102, "wrigley": 101,
    "busch stadium": 100, "citi field": 99, "target field": 98,
    "angel stadium": 97, "progressive": 97, "t-mobile": 96,
    "comerica": 95, "kauffman": 94, "pnc": 93, "oracle": 92,
    "tropicana": 91, "petco": 90, "nationals park": 102,
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_mlb_player_id(name):
    q = str(name or "").strip()
    if not q:
        return None
    try:
        r = requests.get(
            "https://statsapi.mlb.com/api/v1/people/search",
            params={"names": q},
            timeout=12,
        )
        r.raise_for_status()
        people = (r.json() or {}).get("people") or []
    except Exception:
        return None
    want = _fold_player(q)
    for p in people:
        if _fold_player(p.get("fullName")) == want:
            return p.get("id")
    return people[0].get("id") if people else None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_vs_pitcher(batter_id, pitcher_id):
    if not batter_id or not pitcher_id:
        return {}
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1/people/{batter_id}/stats",
            params={"stats": "vsPlayer", "opposingPlayerId": pitcher_id, "group": "hitting"},
            timeout=12,
        )
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
        stt = (splits[0].get("stat") if splits else {}) or {}
    except Exception:
        return {}
    def ni(*ks):
        for k in ks:
            if stt.get(k) not in (None, ""):
                try:
                    return float(str(stt.get(k)).replace("%", ""))
                except Exception:
                    continue
        return None
    return {"pa": ni("plateAppearances"), "hr": ni("homeRuns"), "avg": ni("avg"), "slg": ni("slg")}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_hitter_splits(batter_id, year=None):
    """Home/away + day/night. Pitch-type ISO is not on this free endpoint."""
    if not batter_id:
        return {}
    year = year or datetime.now().year
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1/people/{batter_id}/stats",
            params={"stats": "statSplits", "group": "hitting", "sitCodes": "h,a,d,n,vl,vr", "season": year},
            timeout=12,
        )
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
    except Exception:
        return {}
    out = {}
    for s in splits:
        code = str((s.get("split") or {}).get("code") or (s.get("split") or {}).get("description") or "").lower()
        stt = s.get("stat") or {}
        def ni(k):
            try:
                return float(stt.get(k))
            except Exception:
                return None
        row = {"hr": ni("homeRuns"), "slg": ni("slg"), "avg": ni("avg")}
        if "home" in code or code == "h":
            out["home"] = row
        elif "away" in code or code == "a":
            out["away"] = row
        elif code in ("d", "day") or "day" in code and "night" not in code:
            out["day"] = row
        elif "night" in code or code == "n":
            out["night"] = row
        elif "left" in code or code in ("vl", "l", "vs lhp", "vs left"):
            out["vl"] = row
        elif "right" in code or code in ("vr", "r", "vs rhp", "vs right"):
            out["vr"] = row
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_pitcher_profile(pitcher_id, year=None):
    if not pitcher_id:
        return {}
    year = year or datetime.now().year
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats",
            params={"stats": "season", "group": "pitching", "season": year},
            timeout=12,
        )
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
        stt = (splits[0].get("stat") if splits else {}) or {}
    except Exception:
        return {}
    try:
        hr = float(stt.get("homeRuns") or 0)
        ip = float(stt.get("inningsPitched") or 0)
        era = float(stt.get("era") or 0)
        hr9 = (hr / ip * 9.0) if ip else None
    except Exception:
        hr9, era = None, None
    return {"hr9": hr9, "era": era}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_hr9():
    year = datetime.now().year
    try:
        r = requests.get(
            "https://statsapi.mlb.com/api/v1/stats",
            params={"stats": "season", "group": "pitching", "sportId": 1, "season": year, "limit": 40},
            timeout=15,
        )
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
    except Exception:
        return {}
    out = {}
    for s in splits:
        team = ((s.get("team") or {}).get("name") or "")
        stt = s.get("stat") or {}
        key = _team_key(team)
        if not key:
            continue
        try:
            hr = float(stt.get("homeRuns") or 0)
            ip = float(stt.get("inningsPitched") or 0)
            era = float(stt.get("era") or 0)
            hr9 = (hr / ip * 9.0) if ip else None
        except Exception:
            hr9, era = None, None
        out[key] = {"hr9": hr9, "era": era}
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_id_map():
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/teams", params={"sportId": 1}, timeout=12)
        r.raise_for_status()
        return {_team_key(t.get("name")): t.get("id") for t in (r.json() or {}).get("teams") or []}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_reliever_ids(team_key):
    """Pitchers on that club with almost no starts = bullpen."""
    tid = (fetch_team_id_map() or {}).get(team_key)
    if not tid:
        return []
    year = datetime.now().year
    try:
        r = requests.get(
            f"https://statsapi.mlb.com/api/v1/teams/{tid}/stats",
            params={"stats": "season", "group": "pitching", "season": year},
            timeout=12,
        )
        r.raise_for_status()
        splits = (((r.json() or {}).get("stats") or [{}])[0].get("splits") or [])
    except Exception:
        return []
    rps = []
    for s in splits:
        stt = s.get("stat") or {}
        try:
            gs = int(float(stt.get("gamesStarted") or 0))
            g = int(float(stt.get("gamesPlayed") or stt.get("games") or 0))
        except Exception:
            gs, g = 0, 0
        if gs > 2 or g < 5:
            continue
        pid = ((s.get("player") or {}).get("id"))
        name = ((s.get("player") or {}).get("fullName"))
        if pid:
            rps.append({"id": int(pid), "name": name, "g": g, "gs": gs})
    rps.sort(key=lambda x: -x["g"])
    return rps[:6]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_batter_vs_relievers(batter_id, rp_ids):
    """This hitter vs that team's current relievers, summed."""
    if not batter_id or not rp_ids:
        return {}
    pa = hr = h = ab = 0
    names = []
    for pid in rp_ids[:5]:
        vs = fetch_vs_pitcher(batter_id, pid) or {}
        if not vs.get("pa"):
            continue
        pa += int(vs.get("pa") or 0)
        hr += int(vs.get("hr") or 0)
        h += int(vs.get("h") or 0)
        ab += int(vs.get("ab") or vs.get("pa") or 0)
        names.append(str(pid))
    if not pa:
        return {}
    slg = None
    # vs endpoint may only give slg per pair; skip fake slg if we only have HR/PA
    return {"pa": pa, "hr": hr, "arms": len(names)}


_PARK_CF = {
    "coors field": 0, "yankee stadium": 75, "fenway": 45,
    "wrigley": 30, "dodger stadium": 20, "oracle": 95,
    "petco": 0, "chase field": 0, "minute maid": 350,
    "citizens bank": 10, "citi field": 15, "busch stadium": 50,
    "great american": 15, "truist": 10, "american family": 0,
    "globe life": 30, "t-mobile": 45, "camden yards": 90,
    "guaranteed rate": 130, "comerica": 150, "kauffman": 30,
    "target field": 5, "progressive": 0, "pnc": 45,
    "tropicana": 45, "angel stadium": 45, "nationals park": 30,
}


def _wind_vs_park(venue, wind_mph, wind_from_deg):
    try:
        spd = float(wind_mph)
        deg = float(wind_from_deg)
    except Exception:
        if wind_mph not in (None, ""):
            return f"wind {wind_mph} mph", "cross"
        return "wind —", "cross"
    face = 0
    v = str(venue or "").lower()
    for k, h in _PARK_CF.items():
        if k in v:
            face = h
            break
    to_cf = abs(((deg - ((face + 180) % 360) + 180) % 360) - 180)
    from_cf = abs(((deg - face + 180) % 360) - 180)
    if to_cf <= 40:
        return f"wind {spd:.0f} mph → out to CF", "out"
    if from_cf <= 40:
        return f"wind {spd:.0f} mph ← in from CF", "in"
    return f"wind {spd:.0f} mph ↔ crosswind", "cross"


def _park_hr_factor(venue):
    v = str(venue or "").lower()
    for k, val in _PARK_HR.items():
        if k in v:
            return val
    return 100


def load_live_mlb_data():
    slate = fetch_mlb_slate_context()
    weather = {}
    for team, rec in (slate.get("by_team") or {}).items():
        ll = _MLB_PARK_LL.get(team)
        if ll:
            weather[team] = fetch_open_meteo(*ll)
    return {
        "ev": fetch_savant_exit_velo(),
        "hot14": fetch_mlb_hot_window(14),
        "hot7": fetch_mlb_hot_window(7),
        "rookies": fetch_mlb_rookies(),
        "slate": slate,
        "weather": weather,
        "hr9": fetch_team_hr9(),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nflverse_week_stats(year=None):
    year = year or datetime.now().year
    urls = [
        f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year}.csv",
        f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{year-1}.csv",
    ]
    chunks = []
    for url in urls:
        try:
            part = pd.read_csv(url)
            if part is not None and not part.empty:
                chunks.append(part)
        except Exception:
            pass
    df = pd.concat(chunks, ignore_index=True) if chunks else None
    if df is None or df.empty or "player_display_name" not in df.columns:
        return {}
    # Keep this season + last season (no 5-week cut).
    try:
        gdf = pd.read_csv(
            "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv",
            usecols=lambda c: c in ("game_id", "weekday", "gametime", "home_team", "away_team"),
        )
        if "game_id" in df.columns and not gdf.empty:
            df = df.merge(gdf, on="game_id", how="left")
    except Exception:
        gdf = pd.DataFrame()
    if "team" in df.columns and "home_team" in df.columns:
        df["is_home"] = df["team"].astype(str) == df["home_team"].astype(str)
    if "weekday" in df.columns:
        wd = df["weekday"].astype(str).str.lower()
        df["primetime"] = wd.isin(("thursday", "monday"))
    draft = {}
    try:
        pdf = pd.read_csv(
            "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv",
            usecols=lambda c: c in ("display_name", "draft_round", "draft_pick", "draft_year", "rookie_season"),
        )
        for _, r in pdf.iterrows():
            draft[_fold_player(r.get("display_name"))] = dict(r)
    except Exception:
        pdf = pd.DataFrame()
    out = {}
    for name, g in df.groupby("player_display_name"):
        key = _fold_player(name)
        def sm(*cols):
            for c in cols:
                if c in g.columns:
                    return float(pd.to_numeric(g[c], errors="coerce").fillna(0).sum())
            return 0.0
        def av(*cols):
            for c in cols:
                if c in g.columns:
                    s = pd.to_numeric(g[c], errors="coerce").dropna()
                    if len(s):
                        return float(s.mean())
            return None
        home_m = g["is_home"] if "is_home" in g.columns else None
        pt_m = g["primetime"] if "primetime" in g.columns else None
        vs = {}
        if "opponent_team" in g.columns:
            for opp, og in g.groupby("opponent_team"):
                vs[str(opp)] = {
                    "yds": float(pd.to_numeric(og.get("receiving_yards"), errors="coerce").fillna(0).sum()),
                    "td": float(pd.to_numeric(og.get("receiving_tds"), errors="coerce").fillna(0).sum()),
                    "g": int(len(og)),
                }
        dr = draft.get(key) or {}
        out[key] = {
            "weeks": int(g["week"].nunique()) if "week" in g.columns else len(g),
            "targets": sm("targets"),
            "tgt_share": av("target_share"),
            "rec": sm("receptions"),
            "rec_yds": sm("receiving_yards"),
            "rec_td": sm("receiving_tds"),
            "carries": sm("carries"),
            "rush_yds": sm("rushing_yards"),
            "rush_td": sm("rushing_tds"),
            "home_yds": (
                float(pd.to_numeric(g.loc[home_m, "receiving_yards"], errors="coerce").fillna(0).sum())
                + float(pd.to_numeric(g.loc[home_m, "rushing_yards"], errors="coerce").fillna(0).sum())
            ) if home_m is not None else 0,
            "away_yds": (
                float(pd.to_numeric(g.loc[~home_m, "receiving_yards"], errors="coerce").fillna(0).sum())
                + float(pd.to_numeric(g.loc[~home_m, "rushing_yards"], errors="coerce").fillna(0).sum())
            ) if home_m is not None else 0,
            "pt_yds": (
                float(pd.to_numeric(g.loc[pt_m, "receiving_yards"], errors="coerce").fillna(0).sum())
                + float(pd.to_numeric(g.loc[pt_m, "rushing_yards"], errors="coerce").fillna(0).sum())
            ) if pt_m is not None else 0,
            "pt_td": float(pd.to_numeric(g.loc[pt_m, "receiving_tds"], errors="coerce").fillna(0).sum()) if pt_m is not None else 0,
            "vs": vs,
            "pos": str(g["position"].iloc[0]) if "position" in g.columns else "",
            "team": str(g["recent_team"].iloc[-1]) if "recent_team" in g.columns else (str(g["team"].iloc[-1]) if "team" in g.columns else ""),
            "draft_round": dr.get("draft_round"),
            "draft_pick": dr.get("draft_pick"),
            "draft_year": dr.get("draft_year"),
            "rookie_season": dr.get("rookie_season"),
        }
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_nfl_dvp():
    """Last 10 games only. Per-game rates + D home/road + primetime."""
    year = datetime.now().year
    frames = []
    for y in (year, year - 1):
        try:
            frames.append(pd.read_csv(
                f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{y}.csv"
            ))
        except Exception:
            pass
    if not frames:
        return {}
    df = pd.concat(frames, ignore_index=True)
    need = {"opponent_team", "position", "week"}
    if df.empty or not need.issubset(set(df.columns)):
        return {}
    if "season" not in df.columns:
        df["season"] = year
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    weeks = (
        df[["season", "week"]].drop_duplicates().dropna()
        .sort_values(["season", "week"], ascending=False)
        .head(10)
    )
    df = df.merge(weeks, on=["season", "week"], how="inner")
    try:
        gdf = pd.read_csv(
            "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
        )
        keep = [c for c in ("season", "week", "weekday", "home_team", "away_team") if c in gdf.columns]
        gdf = gdf[keep]
        df = df.merge(gdf, how="left", on=["season", "week"])
        df = df[(df["opponent_team"] == df["home_team"]) | (df["opponent_team"] == df["away_team"])]
    except Exception:
        gdf = None
    if "home_team" in df.columns:
        df["def_home"] = df["opponent_team"] == df["home_team"]
    else:
        df["def_home"] = False
    if "weekday" in df.columns:
        df["primetime"] = df["weekday"].astype(str).str.lower().isin(["thursday", "monday"])
    else:
        df["primetime"] = False
    out = {}
    for (defn, pos), g in df.groupby(["opponent_team", "position"]):
        games = int(g[["season", "week"]].drop_duplicates().shape[0]) or 1
        rec = float(pd.to_numeric(g.get("receiving_yards"), errors="coerce").fillna(0).sum())
        rtd = float(pd.to_numeric(g.get("receiving_tds"), errors="coerce").fillna(0).sum())
        home = g[g["def_home"] == True]
        road = g[g["def_home"] == False]
        pt = g[g["primetime"] == True]
        hg = max(1, int(home[["season", "week"]].drop_duplicates().shape[0])) if len(home) else 0
        rg = max(1, int(road[["season", "week"]].drop_duplicates().shape[0])) if len(road) else 0
        pg = max(1, int(pt[["season", "week"]].drop_duplicates().shape[0])) if len(pt) else 0
        rush = float(pd.to_numeric(g.get("rushing_yards"), errors="coerce").fillna(0).sum())
        rusht = float(pd.to_numeric(g.get("rushing_tds"), errors="coerce").fillna(0).sum())
        out[f"{defn}|{pos}"] = {
            "g": games,
            "rec_yds_g": rec / games,
            "rec_td_g": rtd / games,
            "rush_yds_g": rush / games,
            "rush_td_g": rusht / games,
            "home_yds_g": float(pd.to_numeric(home.get("receiving_yards"), errors="coerce").fillna(0).sum()) / hg if hg else 0,
            "road_yds_g": float(pd.to_numeric(road.get("receiving_yards"), errors="coerce").fillna(0).sum()) / rg if rg else 0,
            "home_td_g": float(pd.to_numeric(home.get("receiving_tds"), errors="coerce").fillna(0).sum()) / hg if hg else 0,
            "road_td_g": float(pd.to_numeric(road.get("receiving_tds"), errors="coerce").fillna(0).sum()) / rg if rg else 0,
            "pt_yds_g": float(pd.to_numeric(pt.get("receiving_yards"), errors="coerce").fillna(0).sum()) / pg if pg else 0,
            "pt_td_g": float(pd.to_numeric(pt.get("receiving_tds"), errors="coerce").fillna(0).sum()) / pg if pg else 0,
            "pt_g": int(pt[["season", "week"]].drop_duplicates().shape[0]) if len(pt) else 0,
        }
    return out


def load_live_nfl_data():
    return {"form": fetch_nflverse_week_stats(), "dvp": fetch_nfl_dvp()}


def _petty_upside_from_item(item, sport="MLB", live=None):
    """Petty Upside from LIVE Savant + Stats API. Longshots never dropped."""
    try:
        p = abs(int(item.get("best_price") or 0))
    except Exception:
        p = 0
    name = str(item.get("player") or "")
    key = _fold_player(name)
    stars = ("judge", "ohtani", "soto", "trout", "harper", "betts", "acuna")
    is_star = any(s in name.lower() for s in stars)
    longshot = (p >= 550 and not is_star) or p >= 750
    live = live or {}
    if sport == "NFL":
        form = (live.get("form") or {}).get(key) or {}
        bits = []
        score = 22
        try:
            ts = form.get("tgt_share")
            if ts is not None and str(ts) not in ("nan", "None", ""):
                bits.append(f"tgt {float(ts)*100:.0f}%")
                if float(ts) >= 0.18:
                    score += 14
        except Exception:
            pass
        try:
            if form.get("targets"):
                bits.append(f"{int(float(form['targets']))} tgt (2 szn)")
            if form.get("rec_yds"):
                bits.append(f"{int(float(form['rec_yds']))} rec yds")
        except Exception:
            pass
        if form.get("away_yds") or form.get("home_yds"):
            bits.append(f"home {int(form.get('home_yds') or 0)} / road {int(form.get('away_yds') or 0)} yds")
        if form.get("pt_yds"):
            bits.append(f"primetime {int(form['pt_yds'])} yds / {int(form.get('pt_td') or 0)} TD")
        try:
            dr = form.get("draft_round")
            dp = form.get("draft_pick")
            dy = form.get("draft_year")
            if dr is not None and str(dr) not in ("", "nan", "None"):
                bits.append(f"draft R{int(float(dr))} P{int(float(dp or 0))} '{str(dy or '')[-2:]}")
        except Exception:
            pass
        if form.get("carries"):
            bits.append(f"{int(form['carries'])} car")
        tds = (form.get("rec_td") or 0) + (form.get("rush_td") or 0)
        if tds:
            bits.append(f"{int(tds)} TD")
            score += min(12, int(tds) * 3)
        if p >= 500:
            longshot = True
            bits.append("longshot")
            score += 8
        if not form:
            bits.append("nflverse miss — still listed")
        pos = str(form.get("pos") or item.get("position") or "")
        evn = " ".join(str(x) for x in (item.get("events") or [item.get("event") or ""]))
        dvp_line = ""
        dvp = live.get("dvp") or {}
        best = None
        own = str(form.get("team") or "")
        codes = _nfl_codes_in_text(evn)
        opp_codes = [c for c in codes if c != own] or codes
        for k, rec in dvp.items():
            defn, pcode = (k.split("|", 1) + [""])[:2]
            if pos and pcode.upper() != pos.upper():
                continue
            hit = defn in opp_codes or (defn and defn.lower() in evn.lower())
            if hit:
                best = rec
                if str(pos).upper() == "RB":
                    ypg = (rec.get("rush_yds_g") or 0) + (rec.get("rec_yds_g") or 0)
                    tpg = (rec.get("rush_td_g") or 0) + (rec.get("rec_td_g") or 0)
                    kind = "rush+rec"
                else:
                    ypg = rec.get("rec_yds_g") or 0
                    tpg = rec.get("rec_td_g") or 0
                    kind = "rec"
                dvp_line = (
                    f"last {int(rec.get('g') or 0)} games vs {pos or 'skill'} {defn} — PER GAME {kind}: "
                    f"{ypg:.0f} yds · {tpg:.2f} TD · "
                    f"when that D is home {rec.get('home_yds_g') or 0:.0f} rec yds / {rec.get('home_td_g') or 0:.2f} rec TD · "
                    f"when that D is on the road {rec.get('road_yds_g') or 0:.0f} rec yds / {rec.get('road_td_g') or 0:.2f} rec TD"
                )
                if rec.get("pt_g"):
                    dvp_line += (
                        f" · primetime PER GAME {rec.get('pt_yds_g') or 0:.0f} yds / "
                        f"{rec.get('pt_td_g') or 0:.2f} TD ({int(rec.get('pt_g') or 0)} PT games)"
                    )
                break
        if best and (best.get("rec_td_g") or 0) >= 0.6:
            score += 8
        return {
            "score": min(120, score),
            "longshot": longshot,
            "rookie": False,
            "summary": " · ".join(bits) if bits else "Anytime TD · usage",
            "boost": 6 if form else 2,
            "sport": "NFL",
            "ev": None,
            "hh": None,
            "barrel": None,
            "matchup": dvp_line,
            "weather": "",
            "wind_lane": "cross",
            "dvp_line": dvp_line,
            "nfl_ha": f"His last two seasons — {int(form.get('home_yds') or 0)} yards at home, {int(form.get('away_yds') or 0)} on the road.",
            "nfl_pt": f"His primetime — {int(form.get('pt_yds') or 0)} yards, {int(form.get('pt_td') or 0)} TDs.",
            "nfl_pos": pos,
            "trend": "🔥 Heating" if (form.get("tgt_share") or 0) >= 0.18 or (form.get("rec_td") or 0) >= 6 else ("🧊 Cooling" if (form.get("tgt_share") or 0) and float(form.get("tgt_share") or 0) < 0.08 else "😐 Neutral"),
            "role": (
                f"{pos}1" if pos and (form.get("tgt_share") or 0) >= 0.20
                else (f"{pos}2" if pos and (form.get("tgt_share") or 0) >= 0.12 else (pos or "skill"))
            ),
            "attack": "💎 Longshot TD" if p >= 500 else ("🎯 Receptions + yards" if (form.get("tgt_share") or 0) >= 0.18 else "💣 Anytime TD"),
            "rookie": bool(str(form.get("draft_year") or "")[-4:] == str(datetime.now().year) or str(form.get("rookie_season") or "")[-4:] == str(datetime.now().year)),
        }
    sav = (live.get("ev") or {}).get(key) or {}
    h7 = (live.get("hot7") or {}).get(key) or {}
    h14 = (live.get("hot14") or {}).get(key) or {}
    rookie = key in (live.get("rookies") or set())
    score = 20
    bits = []
    ev = sav.get("ev")
    hh = sav.get("hh")
    brl = sav.get("barrel")
    if ev:
        bits.append(f"EV {ev:.1f}")
        if ev >= 91:
            score += 14
        elif ev >= 88:
            score += 8
    if hh is not None:
        bits.append(f"HH {hh:.0f}%")
        if hh >= 45:
            score += 12
        elif hh >= 38:
            score += 6
    if brl is not None:
        bits.append(f"Barrel {brl:.1f}%")
        if brl >= 10:
            score += 14
        elif brl >= 6:
            score += 7
    hr7 = h7.get("hr")
    hr14 = h14.get("hr")
    slg7 = h7.get("slg")
    if hr7 is not None:
        bits.append(f"HR L7 {int(hr7)}")
        score += min(12, int(hr7) * 4)
    if hr14 is not None and hr7 is not None and hr7 > (hr14 - hr7):
        bits.append("heating L7")
        score += 8
    if slg7 and slg7 >= 0.500:
        bits.append(f"SLG7 {slg7:.3f}")
        score += 6
    if longshot:
        bits.append("longshot")
        score += 10
    if rookie:
        bits.append("rookie")
        score += 8
    if not sav and not h14:
        bits.append("live feed miss — name still listed")
    team_raw = item.get("team") or ""
    evname = " ".join(item.get("events") or [item.get("event") or ""])
    tk = _team_key(team_raw) or next((k for k in _MLB_PARK_LL if k in evname.lower()), "")
    ctx = ((live.get("slate") or {}).get("by_team") or {}).get(tk) or {}
    wx = (live.get("weather") or {}).get(tk) or {}
    matchup = ""
    if ctx.get("opp_sp"):
        matchup = f"vs {ctx['opp_sp']} ({ctx.get('ha') or ''}) @ {ctx.get('venue') or ''}".strip()
        bits.append(matchup)
    weather_line = ctx.get("weather") or ""
    wind_lane = "cross"
    if wx.get("temp") is not None:
        wtxt, wind_lane = _wind_vs_park(ctx.get("venue") or "", wx.get("wind"), wx.get("wdir"))
        weather_line = f"{wx.get('temp')}°F · {wtxt}"
        bits.append(weather_line)
        if wind_lane == "out":
            score += 3
        elif wind_lane == "in":
            score -= 2
        try:
            if float(wx.get("wind") or 0) >= 12:
                score += 4
        except Exception:
            pass
    boost = 3
    if ev and ev >= 91:
        boost += 6
    if brl and brl >= 8:
        boost += 5
    if longshot:
        boost += 4
    return {
        "score": min(130, score),
        "longshot": longshot,
        "rookie": rookie,
        "summary": " · ".join(bits) if bits else "No row yet — still on the list",
        "boost": boost,
        "sport": sport,
        "ev": ev,
        "hh": hh,
        "barrel": brl,
        "matchup": matchup,
        "weather": weather_line,
        "wind_lane": wind_lane,
    }


def load_align_events():
    try:
        if os.path.exists(ALIGN_EVENTS_FILE):
            with open(ALIGN_EVENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def save_align_events(rows):
    """Append-only alignment log. Never touches odds history / results / lock."""
    try:
        with open(ALIGN_EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(rows[-500:], f)
    except Exception:
        pass


def _align_kv(label, value, tip=""):
    if value in (None, "", "—"):
        return ""
    tip_attr = f' title="{tip}"' if tip else ""
    return (
        f'<div class="al-kv"{tip_attr}><span>{label}</span>'
        f'<span class="gm-num">{value}</span></div>'
    )


def _petty_meter(align):
    a = max(0, min(120, int(align or 0)))
    w = int(a / 120 * 100)
    return (
        f'<div style="background:#2a2038;border-radius:999px;height:8px;margin:6px 0 8px;overflow:hidden">'
        f'<div class="al-fill" style="width:{w}%;height:8px;border-radius:999px;'
        f'background:linear-gradient(90deg,#9b5fff,#ff3ebf,#00e6c3);animation:alFill .7s ease-out"></div></div>'
        f'<div style="font-size:.68rem;color:#c4b5d6">data 🔮 · odds 🎰 · <span class="gm-num">align score {a}</span></div>'
    )


def render_alignment_tab(ev_board, watch_board=None):
    """New Align tab. Odds engine untouched. Longshots stay on the list."""
    raw_rows = list(ev_board or []) + list(watch_board or [])
    seen_p = {}
    for it in raw_rows:
        k = _fold_player(it.get("player"))
        if not k:
            continue
        prev = seen_p.get(k)
        if prev is None:
            seen_p[k] = it
            continue
        try:
            better = int(it.get("score") or 0) > int(prev.get("score") or 0)
        except Exception:
            better = False
        if better or (it.get("is_bet") and not prev.get("is_bet")):
            seen_p[k] = it
    rows = list(seen_p.values())
    st.markdown(
        '<div class="queen-banner">✨ Align · when the data speaks and the odds agree, that’s Girl Magic</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .al-lock{border-color:#f472b6!important;box-shadow:0 0 14px rgba(244,114,182,.35);background:linear-gradient(165deg,#2a1020,#16101f)!important;position:relative;overflow:hidden}
        .al-lock::after{content:"";position:absolute;top:0;left:-40%;width:40%;height:6px;background:linear-gradient(90deg,transparent,#f9a8d4,transparent);animation:alShimmer 2.4s linear infinite}
        .al-speak{border-color:#a855f7!important;box-shadow:0 0 12px rgba(168,85,247,.3)}
        .al-shot{border-color:#2dd4bf!important;box-shadow:0 0 12px rgba(45,212,191,.28)}
        .al-home{opacity:.88;border-color:#3f3a48!important}
        .card.al-lock:hover,.card.al-speak:hover,.card.al-shot:hover{transform:translateY(-3px);transition:transform .15s ease}
        .wind-out{color:#34d399;font-weight:700}
        .wind-in{color:#f87171;font-weight:700}
        .wind-cross{color:#fbbf24}
        .al-chip{display:inline-block;border-radius:999px;padding:2px 8px;margin:2px 4px 0 0;font-size:.68rem;border:1px solid #2a2038;background:#1a1224}
        .card.al-lock,.card.al-speak,.card.al-shot,.card.al-home{text-align:left;max-width:520px;min-height:280px;margin:0 auto 28px;padding:24px;border-radius:18px;animation:alIn .35s ease-out}
        .card.al-lock .card-name,.card.al-speak .card-name{font-size:1.35rem}
        .al-pack{font-size:.95rem;line-height:1.4}
        .card.al-lock .card-name,.card.al-speak .card-name,.card.al-shot .card-name,.card.al-home .card-name{font-size:1.45rem}
        .card-foot{font-size:.72rem;font-style:italic;text-align:center}
        @keyframes alIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
        .al-kv{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid #24182f;padding:2px 0;font-size:.74rem}
        .al-sec{font-size:.62rem;letter-spacing:1.4px;text-transform:uppercase;color:#00e6c3;margin:6px 0 3px;font-weight:800}
        .al-tags{text-align:center;margin-top:6px}
        .al-pack{font-size:.95rem;line-height:1.4;color:#fce7f3;margin:0 0 6px}
        details.al-fold{margin:4px 0}
        details.al-fold>summary{cursor:pointer;color:#00e6c3;font-size:.62rem;letter-spacing:1.3px;text-transform:uppercase;font-weight:800}
        @keyframes alShimmer{0%{left:-40%}100%{left:120%}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    pass
    if not rows:
        st.info("Hit Fetch on the Board first. Align only reads names already on today’s slate.")
        return
    sport = active_sport()
    live = {}
    if sport != "NFL":
        with st.spinner("Pulling Savant EV / HH / Barrel + last 7–14 day HRs…"):
            live = load_live_mlb_data()
    else:
        with st.spinner("Pulling nflverse last-5-week usage…"):
            live = load_live_nfl_data()
        pass
    cards = []
    hidden = 0
    for item in rows:
        data = _petty_upside_from_item(item, sport, live)
        align = odds_alignment_score(item, data.get("boost"))
        ev, hh, brl = data.get("ev"), data.get("hh"), data.get("barrel")
        methods = item.get("methods") or []
        summ = data.get("summary") or ""
        hot = "heating L7" in summ
        try:
            hr7 = 0
            if "HR L7" in summ:
                bit = summ.split("HR L7")[1].strip().split()[0]
                hr7 = int(float(bit))
        except Exception:
            hr7 = 0
        contact = sum([
            1 if ev and ev >= 89 else 0,
            1 if hh is not None and hh >= 42 else 0,
            1 if brl is not None and brl >= 8 else 0,
        ])
        data_hit = bool(contact >= 2 and (hot or hr7 >= 1))
        rookie_spike = bool(data.get("rookie") and ((ev and ev >= 90) or (hh is not None and hh >= 42)))
        books_n = 0
        try:
            books_n = len(_align_book_prices(item))
        except Exception:
            books_n = len(item.get("book_prices") or item.get("books") or {})
        try:
            signed_px = int(item.get("best_price") or 0)
        except Exception:
            signed_px = 0
        px = abs(signed_px)
        rhythm = bool(set(str(m) for m in methods) & _ALIGN_DIGIT) or any(
            str(m).startswith("MGM") or str(m).startswith("DK") or str(m).startswith("FD") or "Exact" in str(m)
            for m in methods
        )
        long_lane = 500 <= px <= 999 or (px >= 500 and data.get("longshot"))
        if sport == "NFL":
            data_hit = bool(summ) and "nflverse miss" not in summ
            # Plus-money TD only. Favorites (-175) do not belong on this board.
            long_lane = signed_px >= 100
            rhythm = rhythm or bool(methods)
        board_take = bool(item.get("is_bet"))
        board_score = int(item.get("score") or 0)
        # HARD GATE: data + clustered books + a stamp + 70+ align.
        # Longshot is a tag, not a free pass.
        keep = (
            data_hit
            and books_n >= 2
            and rhythm
            and long_lane
            and align >= 70
        )
        if rookie_spike and books_n >= 2 and align >= 70 and rhythm:
            keep = True
        if board_take and data_hit and align >= 70:
            keep = True
        if sport == "NFL" and signed_px < 100:
            keep = False
        if not keep:
            hidden += 1
            continue
        # Matchup layer — MLB only. NFL uses nflverse form already on the card.
        if sport == "NFL":
            data["park_line"] = ""
            data["vs_line"] = ""
            data["pen_line"] = ""
            data["split_ha"] = data.get("nfl_ha") or ""
            data["split_dn"] = data.get("nfl_pt") or ""
            data["match_boost"] = 0
            odds_hit = bool(methods) or books_n >= 2
            notes = []
            if data.get("longshot"):
                notes.append("Longshot price")
            if methods:
                notes.append("Digit / book-stamp method fired")
            if not notes:
                notes.append("Usage + odds. Board still tickets.")
            if align >= 100:
                vibe = "🔒 Locked"
            elif align >= 85:
                vibe = "💬 Spoke"
            elif align >= 60:
                vibe = "🫧 Whisper"
            else:
                vibe = "📚 Homework"
            cards.append((align, item, data, notes, vibe))
            continue
        park_f = _park_hr_factor(data.get("matchup") or "")
        if not park_f or park_f == 100:
            park_f = _park_hr_factor((data.get("summary") or ""))
        opp = ""
        if "vs " in (data.get("matchup") or ""):
            opp = (data.get("matchup") or "").split("vs ", 1)[-1].split("(")[0].strip()
        vs = {}
        bid = fetch_mlb_player_id(item.get("player"))
        if opp:
            pid = fetch_mlb_player_id(opp)
            vs = fetch_vs_pitcher(bid, pid) or {}
        splits = fetch_hitter_splits(bid) or {}
        tk = _team_key(item.get("team") or "")
        # opposing team pitching: use event home/away
        evn = " ".join(item.get("events") or [item.get("event") or ""])
        opp_team = ""
        for k in _MLB_PARK_LL:
            if k in evn.lower() and k != tk:
                opp_team = k
                break
        bp = ((live.get("hr9") or {}).get(opp_team) or {})
        vs_pen = {}
        if bid and opp_team:
            rps = fetch_reliever_ids(opp_team)
            vs_pen = fetch_batter_vs_relievers(bid, [x["id"] for x in rps]) or {}
        match_boost = 0
        if park_f >= 105:
            match_boost += 5
        elif park_f <= 95:
            match_boost -= 3
        slg = vs.get("slg")
        vhr = vs.get("hr")
        vpa = vs.get("pa")
        if slg is not None and slg >= 0.500 and (vpa or 0) >= 8:
            match_boost += 8
        elif slg is not None and slg < 0.250 and (vpa or 0) >= 10:
            match_boost -= 5
        if vhr and vhr >= 1:
            match_boost += 5
        if bp.get("hr9") and bp["hr9"] >= 1.3:
            match_boost += 5
        if bp.get("era") and bp["era"] < 3.5:
            match_boost -= 3
        align = int(align) + int(match_boost)
        pp = {}
        try:
            if opp:
                pp = fetch_pitcher_profile(fetch_mlb_player_id(opp)) or {}
        except Exception:
            pp = {}
        vs_line = "no sample vs this SP"
        if vpa:
            vs_line = f"vs {opp} · {int(vhr or 0)} HR in {int(vpa)} PA · SLG {slg or 0:.3f}"
        if pp.get("hr9"):
            vs_line += f" · SP HR/9 {pp['hr9']:.2f} ERA {pp.get('era') or '—'}"
        if pp.get("hr9") and pp["hr9"] >= 1.3:
            match_boost += 4
            align = int(align) + 4
        park_line = f"HR factor {park_f}"
        if vs_pen.get("pa"):
            pen_line = (
                f"this hitter vs that bullpen · {int(vs_pen.get('hr') or 0)} HR "
                f"in {int(vs_pen['pa'])} PA vs {vs_pen.get('arms')} relievers"
            )
        else:
            pen_line = ""
        data["park_line"] = park_line
        data["vs_line"] = vs_line
        data["pen_line"] = pen_line
        data["match_boost"] = match_boost
        hm, aw = splits.get("home") or {}, splits.get("away") or {}
        dy, nt = splits.get("day") or {}, splits.get("night") or {}
        def _sl(row):
            if not row or row.get("slg") is None:
                return "—"
            return f"SLG {row['slg']:.3f} / {int(row.get('hr') or 0)} HR"
        data["split_ha"] = f"home {_sl(hm)} · away {_sl(aw)}"
        data["split_dn"] = f"day {_sl(dy)} · night {_sl(nt)}"
        vl, vr = splits.get("vl") or {}, splits.get("vr") or {}
        data["split_lr"] = f"vs LHP {_sl(vl)} · vs RHP {_sl(vr)}" if (vl or vr) else ""
        if aw.get("slg") and hm.get("slg") and aw["slg"] >= hm["slg"] + 0.040 and data.get("matchup") and "(away)" in data.get("matchup"):
            match_boost += 3
            align = int(align) + 3
        if nt.get("slg") and dy.get("slg") and nt["slg"] >= dy["slg"] + 0.040:
            match_boost += 2
            align = int(align) + 2
        data["match_boost"] = match_boost
        odds_hit = bool(methods) or books_n >= 2
        notes = []
        ms = [str(m) for m in methods]
        if data["longshot"] and align >= 70:
            notes.append("Books lining up on a longshot")
        if set(ms) & _ALIGN_DIGIT:
            notes.append("Digit / book-stamp method fired")
        if set(ms) & _ALIGN_AGREE:
            notes.append("Books clustered")
        if set(ms) & _ALIGN_MIS:
            notes.append("Pack vs one book looks off")
        if item.get("num_tag"):
            notes.append("Numerology tag present")
        if data_hit and odds_hit:
            notes.append("Data + odds both fired")
        if not notes:
            notes.append("Cleared the data bar. Still check the Board before you ticket.")
        if align >= 100:
            vibe = "🔒 Locked"
        elif align >= 85:
            vibe = "💬 Spoke"
        elif align >= 60:
            vibe = "🫧 Whisper"
        else:
            vibe = "📚 Homework"
        cards.append((align, item, data, notes, vibe))
    cards.sort(key=lambda x: (-x[0], x[1].get("player") or ""))
    view = st.radio(
        "align_view_pills",
        ["🎯 Active", "🫧 Whispers", "📚 Homework"],
        horizontal=True,
        key="align_view",
        label_visibility="collapsed",
    )
    perfect = [c for c in cards if c[0] >= 85][:24]
    if view.startswith("🎯"):
        st.markdown("#### ✨ Alignment Picks")
        st.caption("Data spoke. Odds agreed. Board’s got the final say.")
    ev_log = load_align_events()
    for align, item, data, notes, vibe in cards:
        if align < 70:
            continue
        ev_log.append({
            "date": today_az(),
            "sport": sport,
            "player": item.get("player"),
            "align": align,
            "vibe": vibe,
            "longshot": data.get("longshot"),
            "rookie": data.get("rookie"),
            "price": item.get("best_price"),
            "book": item.get("best_book"),
            "methods": list(item.get("methods") or [])[:6],
            "summary": data.get("summary"),
        })
    save_align_events(ev_log)
    if sport == "NFL":
        def _px(it):
            try:
                return int(it.get("best_price") or 0)
            except Exception:
                return 0
        if view.startswith("🎯"):
            cards = [c for c in cards if 100 <= _px(c[1]) < 500][:24]
        elif view.startswith("🫧"):
            cards = [c for c in cards if c[2].get("longshot") or _px(c[1]) >= 500]
        elif view.startswith("📚"):
            cards = [c for c in cards if c[2].get("rookie") or "nflverse miss" in (c[2].get("summary") or "")]
    elif view.startswith("🎯"):
        cards = [c for c in cards if c[0] >= 85][:24]
    elif view.startswith("🫧"):
        cards = [c for c in cards if 70 <= c[0] < 85]
    elif view.startswith("📚"):
        cards = [c for c in cards if c[0] < 70]
    cols = st.columns(2)
    already = set()
    shown_i = 0
    for align, item, data, notes, vibe in cards[:40]:
        pk = _fold_player(item.get("player"))
        if pk in already:
            continue
        already.add(pk)
        i = shown_i
        shown_i += 1
        if shown_i > 24:
            break
        pills = []
        if data.get("longshot"):
            pills.append('<span class="al-chip">💎 Longshot</span>')
        if "heating" in (data.get("summary") or ""):
            pills.append('<span class="al-chip">🔥 Heating</span>')
        if set(str(m) for m in (item.get("methods") or [])) & _ALIGN_DIGIT:
            pills.append('<span class="al-chip">💜 Rhythm</span>')
        if item.get("is_bet"):
            pills.append('<span class="al-chip">💚 Board take</span>')
        if align >= 85:
            pills.append('<span class="al-chip">✨ Petty Upside</span>')
        pf = 100
        try:
            pl = str(data.get("park_line") or "")
            if "factor" in pl.lower():
                pf = int("".join(ch for ch in pl.split("factor")[-1] if ch.isdigit()) or "100")
        except Exception:
            pf = 100
        if pf >= 130:
            porch = "💥 Hot Porch"
        elif pf >= 110:
            porch = "🔥 Live Air"
        elif pf >= 90:
            porch = "🌬️ Neutral"
        else:
            porch = "🧊 Cold Porch"
        price = format_odds(item.get("best_price"))
        stamps = " · ".join(str(m) for m in (item.get("methods") or [])[:4]) or "no stamp"
        klass = "card al-home"
        if data.get("longshot") and align >= 70:
            klass = "card al-shot"
        if align >= 85:
            klass = "card al-speak"
        if align >= 100 or item.get("is_bet"):
            klass = "card al-lock"
        wlane = data.get("wind_lane") or "cross"
        vs_l = data.get("vs_line") or ""
        if vs_l.lower().startswith("vs ") and (data.get("matchup") or "").split("(")[0].strip().lower() in vs_l.lower():
            vs_bit = vs_l
        else:
            vs_bit = data.get("matchup") or vs_l or "—"
        pen_html = ""
        if data.get("pen_line"):
            pen_html = f'<div class="card-line"><b>VS BULLPEN</b> {data.get("pen_line")}</div>'
        with cols[i % max(1, len(cols))]:
            if sport == "NFL":
                sm_raw = data.get("summary") or ""
                keep = []
                for p in sm_raw.replace("·", "•").split("•"):
                    pl = p.strip().lower()
                    if not p.strip():
                        continue
                    if pl.startswith(("home", "road", "primetime", "draft", "longshot")):
                        continue
                    keep.append(p.strip())
                vol = " • ".join(keep[:4]) if keep else ""
                rook = " Rookie year." if data.get("rookie") else ""
                tr = str(data.get("trend") or "")
                if "Heating" in tr:
                    heat_txt = "🔥 Heating — more targets right now."
                elif "Cooling" in tr:
                    heat_txt = "🧊 Cooling — volume is down."
                else:
                    heat_txt = "😐 Steady — no spike, no fade."
                role = data.get("role") or "skill"
                atk = str(data.get("attack") or "Anytime TD")
                if "Reception" in atk:
                    atk_txt = "Attack — receptions and yards."
                elif "Longshot" in atk:
                    atk_txt = "Attack — longshot touchdown."
                else:
                    atk_txt = "Attack — anytime touchdown."
                dvp = (data.get("dvp_line") or "No DVP tag yet.").replace(" · ", "<br>")
                pulse_html = (
                    f'<details class="al-fold" open><summary title="How they are being used right now">🧠 Player Pulse</summary>'
                    f'<div class="al-pack">{heat_txt}<br>'
                    f'👑 <span title="WR1 = top pass catcher">{role}</span> — how they use him.{rook}<br>'
                    f'🎯 {atk_txt}<br>'
                    f'📈 <span title="Targets = throws his way">{vol}</span></div></details>'
                    f'<details class="al-fold" open><summary title="DVP last 10 games per game + his home/road/primetime totals">⚔️ Matchup Vibe</summary>'
                    f'<div class="al-pack">🛡️ <span title="Last 10 games, per game">{dvp}</span><br>'
                    f'🏠 {data.get("nfl_ha") or ""}<br>🌙 {data.get("nfl_pt") or ""}</div></details>'
                    f'<div class="al-pack" style="font-style:italic" title="Books tight = they agree">💸 {price} {book_label(item.get("best_book"))} · {stamps}</div>'
                )
                st.markdown(
                    f'<div class="{klass}">'
                    f'<div class="card-name">{item.get("player")} <span class="card-kicker">🏈 Anytime TD</span></div>'
                    f'{_petty_meter(align)}'
                    f'{pulse_html}'
                    f'<div class="al-tags">{"".join(pills)}</div>'
                    f'<div class="card-foot" title="Board score is the ticket stack. Align score is data + odds + context.">Board score {item.get("score") or "—"} · Align {align} · Attack {data.get("attack")}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                continue
            ev = data.get("ev")
            hh = data.get("hh")
            brl = data.get("barrel")
            summ = data.get("summary") or ""
            hr7 = ""
            slg7 = ""
            try:
                if "HR L7" in summ:
                    hr7 = summ.split("HR L7")[1].strip().split()[0]
                if "SLG7" in summ:
                    slg7 = summ.split("SLG7")[1].strip().split()[0]
            except Exception:
                pass
            heat = "Yes" if "heating" in summ else "No"
            data_line = (
                f'<span title="How hard the ball leaves">EV {ev:.1f} mph</span> · '
                f'<span title="% of balls 95mph+">HH {hh:.0f}%</span> · '
                f'<span title="HR-quality contact">Barrel {brl:.1f}%</span>'
                if ev is not None and hh is not None and brl is not None
                else (data.get("summary") or "—")
            )
            if ev is not None and hh is not None and brl is not None:
                data_line += f' · 💣 HR L7 {hr7 or "—"} · 📈 SLG L7 {slg7 or "—"} · {"🔥 Heating" if heat=="Yes" else "🧊 Cold"} · {"💎 Longshot" if data.get("longshot") else ""}'
            st.markdown(
                f'<div class="{klass}">'
                f'<div class="card-name">{item.get("player")} <span class="card-kicker">⚾ 0.5 HR</span></div>'
                f'{_petty_meter(align)}'
                f'<details class="al-fold" open><summary title="Exit velo, hard-hit, barrel, last-7 bombs and slugging">📊 Data</summary>'
                f'<div class="al-pack">{data_line}</div></details>'
                f'<details class="al-fold" open><summary title="Pitcher, park vibe, weather, odds stamps">🧠 Context</summary>'
                f'<div class="al-pack">⚾ {vs_bit}<br>🏟️ {porch} ({pf}) · 🌡️ {data.get("weather") or ""}'
                + (f"<br>🧩 {data.get('pen_line')}" if data.get("pen_line") else "")
                + f"<br>💸 {price} {book_label(item.get('best_book'))} · {stamps}</div></details>"
                f'<details class="al-fold" open><summary title="Home/away, day/night, vs left and right">⚙️ Splits</summary>'
                f'<div class="al-pack">🏠 {data.get("split_ha") or "—"}<br>🌙 {data.get("split_dn") or "—"}<br>🆚 {data.get("split_lr") or "—"}</div></details>'
                f'<div class="al-tags">{"".join(pills)}</div>'
                f'<div class="card-foot">Board score {item.get("score") or "—"} · Align {align} · Board still decides if we ticket it.</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    pass


def main():
    if "history_loaded" not in st.session_state:
        load_history()
        st.session_state["pregame_lock"] = load_pregame()
        st.session_state["history_loaded"] = True
    if "pending_page" not in st.session_state:
        st.session_state["pending_page"] = 0

    # New AZ calendar day -> clear yesterday's game picks + stale odds
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
    if "sport" not in st.session_state:
        qp = "MLB"
        try:
            qp = st.query_params.get("sport", "MLB")
        except Exception:
            qp = "MLB"
        st.session_state["sport"] = qp if qp in SPORT_CFG else "MLB"
    sport = st.session_state.get("sport") if st.session_state.get("sport") in SPORT_CFG else "MLB"
    cfg = sport_cfg()
    _games_n = len(st.session_state.get("events") or [])
    _lock_n = len(lock_for_sport())
    _fetch = st.session_state.get("last_fetch_time") or "no fetch yet"
    st.markdown(
        site_hero_html(sport, cfg["label"], _games_n, _lock_n, _fetch),
        unsafe_allow_html=True,
    )
    try:
        sport_pick = st.segmented_control(
            "Pick your lane",
            options=["MLB", "NFL"],
            default=sport,
            key="sport_pick",
            help="MLB = 0.5 HR. NFL = Anytime TD.",
        )
    except Exception:
        sport_pick = st.radio(
            "Pick your lane",
            ["MLB", "NFL"],
            index=0 if sport != "NFL" else 1,
            horizontal=True,
            key="sport_pick",
        )
    if sport_pick in SPORT_CFG and sport_pick != st.session_state.get("sport"):
        st.session_state["sport"] = sport_pick
        try:
            st.query_params["sport"] = sport_pick
        except Exception:
            pass
        st.rerun()
    try:
        st.query_params["sport"] = sport
    except Exception:
        pass
    if st.session_state.get("_sport_seen") != sport:
        for k in ("selected_games", "last_selected", "events", "odds", "previous_odds", "found_books", "last_fetch_time", "auto_once", "new_fetch", "lineup_names"):
            st.session_state.pop(k, None)
        st.session_state["_sport_seen"] = sport
        st.session_state["_autoload_events"] = True
    if "onboard_step" not in st.session_state:
        st.session_state["onboard_step"] = "welcome"
    step = st.session_state.get("onboard_step") or "welcome"
    if step == "welcome":
        st.caption("💫 Girl Magic Odds speaks fluent chaos. Learn the code, then roll.")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💅 Glossary", type="primary", use_container_width=True):
                st.session_state["onboard_step"] = "glossary"
                st.rerun()
        with b2:
            if st.button("🔮 I Know the Vibe", use_container_width=True):
                st.session_state["onboard_step"] = "done"
                st.session_state["seen_card_guide"] = True
                st.rerun()
    elif step == "glossary":
        with st.expander("💅 Girl Magic Glossary", expanded=True):
            render_mini_glossary()
            if st.button("Next — color code", type="primary"):
                st.session_state["onboard_step"] = "colors"
                st.rerun()
    elif step == "colors":
        with st.expander("🎨 How to Read a Girl Magic Card — the Color Code", expanded=True):
            render_card_guide()
            if st.button("Unlock the Board 💅", type="primary"):
                st.session_state["onboard_step"] = "done"
                st.session_state["seen_card_guide"] = True
                st.rerun()
    else:
        r1, r2 = st.columns(2)
        with r1:
            if st.button("Glossary", use_container_width=True):
                st.session_state["onboard_step"] = "glossary"
                st.rerun()
        with r2:
            if st.button("Color code", use_container_width=True):
                st.session_state["onboard_step"] = "colors"
                st.rerun()
    st.toggle("Petty Mode 💅", value=True, key="petty_mode", help="Changes labels only. TAKE IT rules stay the same.")
    if petty_on():
        st.markdown('<div class="petty-banner">💅 Petty Mode ON — louder words, same math.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="petty-off-banner">Plain labels on. Same Board rules.</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .tag-family{background:#2a1040;color:#f9a8d4;border-color:#e879f9}
    .alert-strip{background:#3b0764;border:1px solid #f472b6;border-radius:12px;padding:8px 12px;margin:8px 0 12px;font-size:.82rem}
    .petty-note{color:#e9d5ff;font-size:.72rem;margin-top:3px}
    </style>
    """, unsafe_allow_html=True)
    lock_n = len(lock_for_sport())
    _ag = f"auto_grade_ran_{active_sport()}"
    last_ag = float(st.session_state.get(_ag) or 0)
    pending_n = sum(1 for r in results_for_sport() if r.get("result") == "PENDING")
    due = last_ag == 0 or (time.time() - last_ag) > 600
    if pending_n and due:
        try:
            with st.spinner(f"Auto-grading {pending_n} pending..."):
                h, m, s, msg = auto_grade_pending()
            st.session_state[_ag] = time.time()
            if h or m:
                st.caption(f"⚡ Auto-grade: {h} HIT · {m} MISS · {s} still open")
        except Exception:
            st.session_state[_ag] = time.time()
    render_whats_going_today()
    odds_key = get_odds_api_key()
    sgo_key = get_sgo_key()
    if not odds_key:
        st.warning("Add The Odds API key.")
        st.stop()
    last_ft = st.session_state.get("last_fetch_time") or "no fetch yet"
    ev_n = len(st.session_state.get("events") or [])
    with st.sidebar:
        st.markdown("**Slate**")
        st.caption(f"{ev_n} games · lock {lock_n} · {last_ft}")
        if st.button("Load games", type="primary", use_container_width=True) or st.session_state.pop("_autoload_events", False):
            raw = fetch_events_oddsapi(odds_key, sport_cfg()["key"])
            st.session_state["events"] = filter_events_today(raw)
            st.session_state["events_raw_count"] = len(raw or [])
        if active_sport() == "MLB":
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Lineups", use_container_width=True):
                    names, msg = fetch_all_lineups()
                    msg = short_lineup_msg(msg, len(names))
                    st.session_state["lineup_names"] = names
                    st.session_state["lineup_msg"] = msg
                    (st.success if names else st.warning)(msg)
            with b2:
                if st.button("Grade HRs", use_container_width=True):
                    with st.spinner("MLB box scores..."):
                        h, m, s, msg = auto_grade_pending()
                    st.success(f"{h} HIT · {m} MISS · {s} still open - {msg}")
                    st.rerun()
            auto_lineups = st.checkbox("Grab lineups on fetch", value=True)
            ln = st.session_state.get("lineup_names") or set()
            lm = short_lineup_msg(st.session_state.get("lineup_msg") or "", len(ln))
            st.session_state["lineup_msg"] = lm
            if lm:
                st.caption(lm)
            lock_now = st.session_state.get("pregame_lock") or {}
            if ln and lock_now:
                lock_fold = {fold_name(clean_name(k)) for k in lock_now}
                missing_lock = sum(1 for n in ln if fold_name(n) not in lock_fold)
                st.caption(f"{missing_lock} lineup names have no lock price yet")
        else:
            auto_lineups = False
            if st.button("Auto-grade TDs", type="primary", use_container_width=True):
                with st.spinner("ESPN NFL box scores..."):
                    h, m, s, msg = auto_grade_pending()
                st.success(f"{h} HIT · {m} MISS · {s} still open - {msg}")
                st.rerun()
            st.caption("NFL grades itself from finished games. No RotoWire. No MLB lineups.")
        events = st.session_state.get("events", [])
        if not events:
            st.info(f"Click **Load games** for {active_sport()}. Then select games and Fetch.")
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

        prev_sel = st.session_state.get("selected_games") or []
        default_sel = remap_selected_labels(prev_sel, options) if options else []
        if options and (not default_sel or len(default_sel) < len(options)):
            # split slate: keep every same-day card unless they hit Clear
            if not st.session_state.get("slate_cleared"):
                default_sel = list(options.keys())
        st.session_state["selected_games"] = default_sel
        raw_n = st.session_state.get("events_raw_count") or len(events)
        live_n = len(live_event_labels())
        st.caption(f"Showing {len(events)} today · API listed {raw_n} · {live_n} already live")
        chosen = st.multiselect(
            "Games",
            list(options.keys()),
            default=default_sel,
        )
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Select all", use_container_width=True):
                st.session_state["slate_cleared"] = False
                st.session_state["selected_games"] = list(options.keys())
                st.rerun()
        with s2:
            if st.button("Clear", use_container_width=True):
                st.session_state["slate_cleared"] = True
                st.session_state["selected_games"] = []
                st.rerun()
        st.session_state["selected_games"] = chosen
        manual_fetch = st.button("Fetch", type="primary", use_container_width=True)
        if "last_refresh_count" not in st.session_state:
            st.session_state["last_refresh_count"] = refresh_count
        auto_fetch = HAS_AUTOREFRESH and refresh_count != st.session_state["last_refresh_count"] and bool(chosen)
        first_load = bool(chosen) and not st.session_state.get("odds") and st.session_state.get("auto_once") is not False
        try:
            af = str(st.query_params.get("autofetch", "") or "").lower()
        except Exception:
            af = ""
        ping_fetch = af in ("1", "true", "yes")
        if auto_fetch:
            st.session_state["last_refresh_count"] = refresh_count
        if first_load:
            st.session_state["auto_once"] = False
            auto_fetch = True
        if ping_fetch and chosen:
            auto_fetch = True
        if (manual_fetch or auto_fetch) and chosen:
            with st.spinner("Fetching..."):
                if sport_cfg().get("sgo") and (auto_lineups or not st.session_state.get("lineup_names")):
                    names, msg = fetch_all_lineups()
                    if names:
                        st.session_state["lineup_names"] = names
                        st.session_state["lineup_msg"] = short_lineup_msg(msg, len(names))
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
                    f"No preferred-book {sport_cfg()['label']} props after fetch. "
                    "This is not always 'games live' - check debug below."
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
                    + f"<br><b>US/AU split:</b> {dbg.get('regions') or {}}"
                    + f"<br><b>SGO:</b> league={dbg.get('sgo_league')} http={dbg.get('sgo_http')} rows={dbg.get('sgo_rows') or dbg.get('sgo_rows_built')} kept={dbg.get('sgo_books')} raw={dbg.get('sgo_raw')} err={dbg.get('sgo_err') or ''}"
                    + "</div>",
                    unsafe_allow_html=True,
                )
                if missing:
                    st.caption("Core missing from this feed: " + ", ".join(missing))
                if dbg.get("event_filter_wiped"):
                    st.caption(f"Event label filter would have dropped {dbg['event_filter_wiped']} rows - kept unfiltered.")
    odds = st.session_state.get("odds", [])
    prev = st.session_state.get("previous_odds", [])
    df = pd.DataFrame(odds) if odds else pd.DataFrame()
    if not df.empty and "prop_type" in df.columns:
        df = df[df["prop_type"].isna() | (df["prop_type"] == "")].copy()
    # Keep live + late on the same slate. TAKE still ignores first-pitch
    # games inside run_flags; lock / Results / Fetch keep every card.
    prev_df = pd.DataFrame(prev) if prev else None
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, fallen, watch_board, coverage_board = (
        run_flags(df, prev_df, record_history=new_fetch, selected_events=selected_events)
        if not df.empty else ([], [], [], [], [])
    )
    st.session_state["ev_board"] = ev_board
    st.session_state["watch_board"] = watch_board
    st.session_state["coverage_board"] = coverage_board
    st.session_state["flag_results"] = results
    book_meter = benford_book_meter(df) if not df.empty else {}
    lock_all = st.session_state.get("pregame_lock") or {}
    for lst in (ev_board, watch_board, coverage_board):
        for item in lst:
            rec = lock_all.get(item.get("player")) or {}
            item["benford"] = prop_benford_flag(
                item.get("book_prices") or {},
                book_meter,
                rec.get("books") if isinstance(rec, dict) else None,
            )
            if not item.get("num_tag"):
                item["num_tag"] = numerology_board_tag(item.get("player"), item.get("best_price"))
            bf = item.get("benford") or {}
            authentic = bf.get("aligned") is True or bf.get("tag") == "Authentic"
            num_strong = "name+price" in str(item.get("num_tag") or "")
            if authentic:
                item["score"] = min(100, int(item.get("score") or 0) + 6)
            if num_strong:
                item["score"] = min(100, int(item.get("score") or 0) + 6)
            sc = int(item.get("score") or 0)
            # MLB: Benford/Num can lean off a thin green.
            if not nfl_loose_mode():
                if item.get("is_bet") and not elite_take_ok(item) and sc < 50:
                    item["is_bet"] = False
                    item["why"] = (item.get("why") or "") + " · LEAN — score too thin without Benford/Num"
                elif item.get("is_bet") and sc >= SCORE_SOFT_TAKE and not elite_take_ok(item):
                    item["why"] = (item.get("why") or "") + " · petty score hold"
            elif item.get("is_bet") and HAS_NFL_MATH:
                # Num-only Fanatics longshots are not TAKE.
                if not nfl_take_ok(
                    item.get("method_count") or 0,
                    item.get("methods") or [],
                    item.get("best_price"),
                    item.get("best_book"),
                    item.get("book_prices") or {},
                    sc,
                    need_core=max(1, methods_min()),
                ):
                    item["is_bet"] = False
                    item["why"] = (item.get("why") or "") + " · not a DK/FD ticket"
    if ev_board or watch_board:
        log_bet_this(ev_board, watch_board)
    if not df.empty:
        log_shop_calls(df)
    live_takes = [e.get("player") for e in ev_board if e.get("is_bet")]
    frozen = ledger_names_today()
    merged, seen = [], set()
    for n in live_takes + frozen:
        k = _fold_name(clean_name(n or ""))
        if not k or k in seen:
            continue
        seen.add(k)
        merged.append(n)
    st.session_state["last_take_names"] = merged
    try:
        shop_now = build_shop_board(df) if not df.empty else []
        st.session_state["last_shop_take_names"] = [
            r.get("player") for r in shop_now if r.get("action") in ("TAKE", "LEAN")
        ]
    except Exception:
        st.session_state["last_shop_take_names"] = st.session_state.get("last_shop_take_names") or []
    method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats, score_stats = build_tracker_stats(
        results_for_sport()
    )
    for item in ev_board:
        p, n, mname = best_method_rate_for_player(item["methods"], method_stats)
        item["method_p"], item["method_n"], item["method_rate_name"] = p, n, mname
        if p is not None and n >= EV_MIN_N:
            lean, ev = simple_ev_lean(p, item["best_price"])
            item["ev_lean"] = lean
            item["ev_value"] = ev
        else:
            item["ev_lean"] = item["ev_value"] = None
    _trend_pack = build_trend_pack()
    for lst in (ev_board, watch_board, coverage_board):
        for item in lst or []:
            attach_player_trends(item, _trend_pack)
    st.session_state["_trend_pack"] = _trend_pack
    takes_all = [e for e in ev_board if e.get("is_bet")]
    passes_all = [e for e in ev_board if not e.get("is_bet")]
    take_n = len(takes_all)
    pass_n = len(passes_all)
    multi_names = {e["player"] for e in ev_board}
    # Same buckets as MLB. Week-1 "hide PASS" made 0 Not Today / 0 Watch look broken.
    VALUE_FAKE = {"EV Premium", "Kelly Premium", "EV Support", "Kelly Support"}
    def _premium(item):
        if item.get("premium_core") is not None:
            return int(item.get("premium_core") or 0)
        return count_core_methods([m for m in (item.get("methods") or []) if m not in VALUE_FAKE])
    take_names = {e["player"] for e in ev_board if e.get("is_bet")}
    watch_only, seen_w = [], set(take_names)
    for src in list(watch_board or []) + [e for e in ev_board if not e.get("is_bet")]:
        pl = src.get("player")
        if not pl or pl in seen_w:
            continue
        pc = _premium(src)
        if 1 <= pc < methods_min():
            watch_only.append(src)
            seen_w.add(pl)
    watch_n = len(watch_only)
    watch_names = {w["player"] for w in watch_only}
    pass_n = len([e for e in ev_board if not e.get("is_bet") and e.get("player") not in watch_names])
    cov_names = multi_names | watch_names
    coverage_only = [
        c for c in coverage_board
        if c["player"] not in cov_names
    ]
    coverage_only = sorted(
        coverage_only,
        key=lambda x: (-len(x.get("methods") or []), -x.get("score", 0), x.get("player") or ""),
    )
    coverage_n = len(coverage_only)
    team_picks = apply_team_picks(ev_board, watch_only, coverage_only)
    # NFL: Shop can be full while Board is empty if methods didn't stamp.
    # Mirror Shop TAKE/LEAN onto WATCH so the five boxes aren't lying.
    if active_sport() == "NFL":
        try:
            shop_sync = build_shop_board(df) if df is not None and not getattr(df, "empty", True) else []
        except Exception:
            shop_sync = []
        have = {e.get("player") for e in ev_board} | {w.get("player") for w in watch_only} | {c.get("player") for c in coverage_only}
        for r in shop_sync:
            if r.get("action") not in ("TAKE", "LEAN"):
                continue
            name = r.get("player")
            if not name or name in have or is_nfl_qb(name):
                continue
            row = {
                "player": name,
                "best_price": r.get("best"),
                "best_book": r.get("best_book"),
                "book_prices": r.get("books") or {},
                "edge": r.get("edge") or 0,
                "is_bet": False,
                "methods": ["Shop " + r.get("action")],
                "method_count": 0,
                "score": 40 if r.get("action") == "TAKE" else 30,
                "why": f"Shop {r.get('action')} · ticket {format_odds(r.get('best'))} {book_label(r.get('best_book'))} · not a Board green",
                "event": r.get("event") or "",
                "events": [r.get("event") or ""],
                "team": "",
                "bars": 2,
                "level": "medium",
            }
            watch_only.append(row)
            have.add(name)
        watch_n = len(watch_only)
    pick_n = len(team_picks)
    dk_n = len(aggregate_by_player([r for r in results if r.get("type") == "dk"]))
    fd_n = len(aggregate_by_player([r for r in results if r.get("type") == "fd"]))
    mgm_n = len(aggregate_by_player([r for r in results if r.get("type") == "mgm"]))
    alerts = collect_petty_alerts(ev_board, results)
    if alerts:
        st.markdown(
            '<div class="alert-strip">' + "<br>".join(f"🚨 Petty Alert: {a}" for a in alerts[:8]) + "</div>",
            unsafe_allow_html=True,
        )
    st.markdown(f"""
    <div class="petty-row">
        <div class="petty-box"><div class="petty-num">{take_n}</div><div class="petty-label">{petty_label("TAKE IT")}</div></div>
        <div class="petty-box"><div class="petty-num">{pick_n}</div><div class="petty-label">TEAM PICK</div></div>
        <div class="petty-box"><div class="petty-num">{pass_n}</div><div class="petty-label">{petty_label("PASS")}</div></div>
        <div class="petty-box"><div class="petty-num">{watch_n}</div><div class="petty-label">{petty_label("WATCH")}</div></div>
        <div class="petty-box"><div class="petty-num">{take_n + pass_n + watch_n + coverage_n}</div><div class="petty-label">ON SLATE</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div{gap:6px!important;flex-wrap:wrap}
    div[data-testid="stRadio"] label{
      background:#16101f;border:1px solid #2a2038;border-radius:999px;padding:4px 12px!important;
      color:#e9d5ff!important;transition:transform .12s ease,box-shadow .12s ease,border-color .12s ease;
    }
    div[data-testid="stRadio"] label:hover{
      transform:translateY(-2px);
      border-color:#e879f9;
      box-shadow:0 0 14px rgba(232,121,249,.45);
      background:linear-gradient(90deg,#4c1d95,#9d174d)!important;
    }
    div[data-testid="stRadio"] label:active{transform:translateY(1px) scale(.98)}
    div[data-testid="stRadio"] label[data-checked="true"],
    div[data-testid="stRadio"] [aria-checked="true"] + div,
    div[data-testid="stRadio"] label:has(input:checked){
      border-color:#f472b6!important;
      box-shadow:0 0 16px rgba(244,114,182,.55);
      animation:gmPulse 1.6s ease-in-out infinite;
      background:linear-gradient(90deg,#7c3aed,#db2777)!important;
      color:#fff!important;
    }
    @keyframes gmPulse{0%,100%{box-shadow:0 0 10px rgba(244,114,182,.35)}50%{box-shadow:0 0 20px rgba(192,132,252,.7)}}
    </style>
    """, unsafe_allow_html=True)
    MAIN_TABS = ["Align", "Board", "Shop", "Labs", "Vault", "How"]
    if active_sport() == "NFL":
        MAIN_TABS = ["Align", "Board", "Shop", "Need One", "Labs", "Vault", "How"]
    if st.session_state.get("main_nav") not in MAIN_TABS:
        st.session_state["main_nav"] = "Align"
    NAV_LABELS = {
        "Board": "💚 Run It",
        "Align": "✨ Alignment",
        "Shop": "💸 Money Talks",
        "Need One": "🎯 Need One",
        "Labs": "🧪 Petty Lab",
        "Vault": "📈 Receipts",
        "Admin": "📈 Receipts",
        "Trend": "Trend", "Pattern": "Pattern", "Benford": "Benford", "Motion": "Motion", "Magic": "Magic Math",
        "DK": "DK 🎯", "MGM": "MGM 🎰", "FD": "FD 💙", "Exact": "Exact 🎯",
        "Names": "Names 💅", "Signals": "Signals 📡",
        "Moves": "Moves 💸", "Trends": "Trends 💅", "Late": "Ghosts 👻",
        "Lock": "Lock 🔒", "Search": "Search",
        "Lock Lab": "🔒 Locks", "Tracker": "📈 Tracker",
        "Results": "💎 Spoke",
        "Backtest": "🧠 Time Machine", "Heat": "🔥 Heat",
        "How": "⚙️ How We Roll", "GradeShop": "💸 Shop Card",
        "Lock": "🔐 Pregame", "Search": "🔎 Search",
        "Narratives": "📰 Narratives",
        "GradeShop": "Shop card",
    }
    main = st.radio(
        "Section",
        MAIN_TABS,
        horizontal=True,
        label_visibility="collapsed",
        key="main_nav",
        format_func=lambda x: NAV_LABELS.get(x, x),
    )
    sub = None
    if main == "Labs":
        sub = st.radio(
            "Labs",
            ["Trend", "Pattern", "Benford", "Motion", "Magic"],
            horizontal=True,
            label_visibility="collapsed",
            key="sub_labs",
            format_func=lambda x: NAV_LABELS.get(x, x),
        )
        if sub == "Pattern":
            sub2 = st.radio("Pattern", ["DK", "MGM", "FD", "Exact", "Names", "Signals"], horizontal=True, label_visibility="collapsed", key="sub_methods", format_func=lambda x: NAV_LABELS.get(x, x))
            page = f"Methods:{sub2}"
        elif sub == "Trend":
            page = "Trend Lab:"
        elif sub == "Benford":
            page = "Digits:"
        elif sub == "Motion":
            m2 = st.radio("Motion", ["Moves", "Trends", "Late"], horizontal=True, label_visibility="collapsed", key="sub_lines", format_func=lambda x: NAV_LABELS.get(x, x))
            page = f"Lines:{m2}"
        else:
            page = "Numerology:"
    elif main in ("Admin", "Vault"):
        sub = st.radio(
            "Admin",
            ["Results", "Lock Lab", "Tracker", "Backtest", "GradeShop", "Heat", "Lock", "Search"],
            horizontal=True,
            label_visibility="collapsed",
            key="sub_admin",
            format_func=lambda x: NAV_LABELS.get(x, x),
        )
        admin_map = {
            "Results": "Grade:Results",
            "Lock Lab": "Grade:Lock Lab",
            "Tracker": "Grade:Tracker",
            "Backtest": "Grade:Backtest",
            "GradeShop": "Grade:Shop",
            "Heat": "Analytics:",
            "Lock": "Lines:Lock",
            "Search": "Lines:Search",
        }
        page = admin_map.get(sub, "Grade:Results")
    elif main == "How":
        page = "Code:"
    else:
        page = f"{main}:{sub or ''}"
    if page == "Align:":
        render_alignment_tab(ev_board, watch_board)
    if page == "Board:":
        site_section_open(
            "👑 WHO",
            petty_label("Board"),
            "Green = play it. Gray = close but not cleared. Eyes = keep on the list, don’t force it. "
            "The score ranks names. It does not change the math.",
        )
        with st.expander("💅 What am I looking at on the Board?", expanded=False):
            st.markdown(
                "- 💚 **Green / TAKE / run it, baddie** — cleared the list. We play this.\n"
                "- ⚪ **Gray / PASS** — methods fired. Not enough to buy. Homework.\n"
                "- 👀 **WATCH** — logged for grading later. Don’t force the ticket.\n"
                "- 🎟 **Ticket** — DK / FD / HardRock / Fanatics / Caesars. **MGM is a tell, not the buy.**\n"
                "- 📈 **I JUST NEED ONE** — Shop only. 0.5 rush / receiving / receptions, plus money, RE tag. Not a Board green.\n"
                "- 💅 Hover a pink or green tag if you need the language. Otherwise trust the math."
            )
        elite = [e for e in ev_board if elite_take_ok(e)]
        if not elite:
            elite = [
                e for e in ev_board
                if e.get("is_bet")
                and normalize_book(e.get("best_book")) in ("draftkings", "fanduel")
                and "name+price" in str(e.get("num_tag") or "")
            ]
        if elite:
            st.markdown("#### Petty Picks")
            st.caption("Elite only. Fanatics longshot + “Num 5 price” is not a Petty Pick.")
            pc = st.columns(min(3, max(1, len(elite[:3]))))
            for i, item in enumerate(elite[:6]):
                with pc[i % len(pc)]:
                    st.markdown(
                        f'<div class="card bet"><div class="card-kicker">PETTY PICK</div>'
                        f'<div class="card-name">{item["player"]}</div>'
                        f'<div class="card-line"><b>{format_odds(item.get("best_price"))}</b> {book_label(item.get("best_book"))}</div>'
                        f'<div class="note">{item.get("num_tag") or ""}</div></div>',
                        unsafe_allow_html=True,
                    )
        st.markdown("""
        <style>
        .filter-shell{background:#1a1024;border:1px solid #6b21a8;border-radius:16px;padding:10px 12px 6px;margin:8px 0 12px}
        .filter-sentence{color:#fbcfe8;font-size:.88rem;margin:4px 0 8px}
        .qf-row{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
        .qf-chip{border-radius:999px;padding:4px 10px;font-size:.72rem;font-weight:800;border:1px solid #a855f7;color:#fce7f3;background:#2a1040}
        </style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="filter-shell">', unsafe_allow_html=True)
        st.markdown("#### What’s worth your time")
        q1, q2, q3, q4, q5 = st.columns(5)
        if q1.button("🔥 Hot today", use_container_width=True):
            st.session_state["qf_hot"] = not st.session_state.get("qf_hot")
        if q2.button("💸 Long-ball", use_container_width=True):
            st.session_state["qf_long"] = not st.session_state.get("qf_long")
        if q3.button("💅 Petty 85+", use_container_width=True):
            st.session_state["qf_petty85"] = not st.session_state.get("qf_petty85")
        if q4.button("🧊 Cooling", use_container_width=True):
            st.session_state["qf_cool"] = not st.session_state.get("qf_cool")
        if q5.button("⚡ Chaotic", use_container_width=True):
            st.session_state["qf_chaos"] = not st.session_state.get("qf_chaos")
        on = []
        if st.session_state.get("qf_hot"): on.append("🔥")
        if st.session_state.get("qf_long"): on.append("💸")
        if st.session_state.get("qf_petty85"): on.append("💅85")
        if st.session_state.get("qf_cool"): on.append("🧊")
        if st.session_state.get("qf_chaos"): on.append("⚡")
        st.caption("Quick filters on: " + (" · ".join(on) if on else "none"))
        cfa, cfb, cfc, cfd = st.columns(4)
        with cfa:
            show_kinds = st.multiselect(
                "What’s worth your time",
                ["TAKE IT", "TEAM PICK", "PASS", "WATCH", "COVERAGE"],
                default=["TAKE IT", "TEAM PICK", "PASS", "WATCH", "COVERAGE"],
                key="board_kinds_all",
                help="TAKE IT = cleared. PASS / WATCH / COVERAGE stay on the Board so we can grade them.",
            )
        with cfb:
            min_score = st.slider("Petty Score — how loud the vibe is", 0, 100, 0, 5, key="board_min_score_main")
        with cfc:
            sort_by = st.selectbox("Sort the chaos 🎯", [sport_cfg()["when"], "Highest score", "Biggest edge"], key="board_sort_main")
        with cfd:
            time_win = st.selectbox("When the drama starts 🕐", ["All times", "Next 3 hours", "Later than 3 hours"], key="board_when_main")
        name_q = st.text_input("Find a name", "", key="board_name_main").strip().lower()
        kinds_s = ", ".join(show_kinds) or "nothing"
        st.markdown(
            f'<div class="filter-sentence">Show me <b>{kinds_s}</b> with a Petty Score above <b>{min_score}</b>, sorted by <b>{sort_by}</b>.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Reset the vibe 💅"):
            st.session_state["board_kinds_all"] = ["TAKE IT", "TEAM PICK", "PASS", "WATCH", "COVERAGE"]
            st.session_state["board_min_score_main"] = 0
            st.session_state["board_sort_main"] = sport_cfg()["when"]
            st.session_state["board_when_main"] = "All times"
            st.session_state["board_name_main"] = ""
            for k in ("qf_hot", "qf_long", "qf_petty85", "qf_cool", "qf_chaos"):
                st.session_state[k] = False
            st.rerun()
        st.caption("If it disappeared, it wasn’t meant for you.")
        st.markdown("</div>", unsafe_allow_html=True)

        def _render_board_card(item, label, cls, zone="board"):
            tags = render_method_tags(item.get("methods") or [])
            if item.get("num_tag"):
                tags += f'<span class="tag tag-family">{item["num_tag"]}</span>'
            fams = petty_family_chips(item.get("methods") or [])
            notes = "".join(f'<div class="petty-note">• {n}</div>' for n in petty_notes_for(item))
            meter = motion_line_html(item)
            ev_s = ""
            if item.get("ev_lean") is True:
                ev_s = f" · +EV lean ({item.get('method_rate_name')})"
            team = item.get("team") or ""
            game = item.get("event") or ""
            meta = " · ".join([x for x in (team, game) if x])
            pack = item.get("median")
            pack_s = f" · pack {format_odds(pack)}" if pack is not None else ""
            sig_b = item.get("signal_book")
            sig_p = item.get("signal_price")
            sig_s = ""
            if sig_b and _norm_bk(sig_b) in SIGNAL_ONLY_BOOKS and sig_p is not None:
                if _norm_bk(item.get("best_book")) not in SIGNAL_ONLY_BOOKS:
                    sig_s = f" · MGM signal {format_odds(sig_p)} (not the ticket)"
            show_label = petty_label(label) if label in PETTY_COPY or label in ("TAKE IT", "PASS", "WATCH", "Take it") else label
            queen = ""
            if petty_on():
                if label in ("TAKE IT", "Take it"):
                    queen = "Queen whispered: this one’s green. Don’t argue."
                elif label == "WATCH":
                    queen = "Queen whispered: watch it. Don’t force the ticket."
                elif label == "PASS":
                    queen = "Queen whispered: close, not cleared."
            glow = " card-hot" if int(item.get("score") or 0) >= 90 else ""
            st.markdown(
                f'<div class="card site-card {cls}{glow}">'
                f'<div class="card-kicker">{decision_pill(show_label)} '
                f'<span class="score-pill big">{petty_label("Score")} {item.get("score", 0)}</span></div>'
                f'<div class="card-name">{item["player"]}</div>'
                f'<div class="card-meta">{meta or "Slate player"}</div>'
                f'<div class="why-call">{why_this_call(label, item)}</div>'
                f'<div class="price-row"><span class="price-big">{format_odds(item.get("best_price"))}</span>'
                f'<span class="price-book">{book_label(item.get("best_book"))} ticket{pack_s}{sig_s}</span></div>'
                f'<div class="card-line">Edge <b>{int(item.get("edge") or 0)}</b> · {item.get("method_count", 0)} premium methods</div>'
                f'{kelly_bar_html(item.get("kelly_frac"))}'
                f'{meter}'
                f'{trend_chip_html(item)}'
                f'{board_gate_checklist(item)}'
                f'<div class="method-group"><div class="tag-group-lab">Personality</div>{fams}'
                f'{grouped_tag_html(item.get("methods") or [])}</div>'
                f'{notes}'
                f'<div class="card-foot">{item.get("why", "")}{ev_s}</div>'
                f'{f"<div class=queen-line>{queen}</div>" if queen else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )
            ck = f"ex_{zone}_{cls}_{label}_{item.get('player')}_{str(item.get('event') or '')[:24]}"
            with st.expander("Explain this card", expanded=False, key=ck):
                st.write(explain_card_text(item, label))
            if queen:
                try:
                    with st.popover("👑 What Queen means", key=f"q_{ck}"):
                        render_queen_glossary()
                        st.caption(queen)
                except TypeError:
                    with st.expander("👑 What Queen means", expanded=False, key=f"q_{ck}"):
                        render_queen_glossary()
                        st.caption(queen)

        elite = [e for e in ev_board if e.get("is_bet")]
        st.markdown("#### Petty Picks")
        if elite:
            st.caption("Elite TAKE — ending + lane + method + book + Benford + name+price.")
            pc = st.columns(min(3, max(1, len(elite[:3]))))
            for i, item in enumerate(elite[:6]):
                with pc[i % len(pc)]:
                    _render_board_card(item, "TAKE IT", "bet", zone="picks")
        else:
            st.caption("Nobody made The List yet. Fetch the slate." if active_sport() != "NFL" else "NFL lane is open. Fetch Anytime TD and let the greens talk.")

        takes = [e for e in ev_board if e.get("is_bet")]
        passes = [e for e in ev_board if not e.get("is_bet")]
        multi_names = {e["player"] for e in ev_board}
        watches = [
            w for w in watch_board
            if w["player"] not in multi_names and (w.get("method_count") or 0) < methods_min()
        ]
        watches = sorted(watches, key=lambda x: (-x.get("method_count", 0), -x.get("score", 0)))

        if not takes and not passes and not watches and not coverage_only:
            st.info("Fetch while pregame - board fills when methods fire.")
        else:
            st.markdown(
                '<div class="board-wrap"><h3 class="game-head">💚 The List</h3>'
                '<p class="site-section-help">Gospel greens. If it ain’t here, it’s homework.</p></div>',
                unsafe_allow_html=True,
            )
            commence_by_event = {}
            slate_games = []
            chosen_labs = st.session_state.get("last_selected") or st.session_state.get("selected_games") or []
            for e in st.session_state.get("events", []):
                key = f"{e.get('away_team')} @ {e.get('home_team')}"
                t = e.get("commence_time") or ""
                if t:
                    commence_by_event[key] = t
                lab = f"{key} · {t}" if t else key
                if not chosen_labs or event_matches_chosen(key, chosen_labs) or event_matches_chosen(lab, chosen_labs):
                    slate_games.append(key)
            if not slate_games:
                slate_games = list(commence_by_event.keys())

            by_game = defaultdict(list)
            for item in takes:
                by_game[_strip_game_clock(item.get("event") or "Game")].append(item)
            picks_by_game = defaultdict(list)
            for item in team_picks:
                picks_by_game[_strip_game_clock(_item_game(item) or "Game")].append(item)
            extra = [g for g in (set(by_game) | set(picks_by_game)) if g not in slate_games]
            all_games = slate_games + extra

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
                    return (1, 9e18, game_name)
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

            def _in_time_win(game_name):
                t = _resolve_commence(game_name)
                if event_has_started(t):
                    return False
                if time_win == "All times":
                    return True
                if not t:
                    return True
                try:
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                    now = datetime.now(timezone.utc)
                    hours = (dt - now).total_seconds() / 3600.0
                    if time_win == "Next 3 hours":
                        return hours <= 3
                    return hours > 3
                except Exception:
                    return True

            def _keep_card(item):
                if (item.get("score") or 0) < min_score:
                    return False
                if name_q and name_q not in (item.get("player") or "").lower():
                    return False
                if st.session_state.get("qf_hot") and (item.get("score") or 0) < 70:
                    return False
                if st.session_state.get("qf_long") and abs(int(item.get("best_price") or 0)) < 500:
                    return False
                if st.session_state.get("qf_petty85") and (item.get("score") or 0) < 85:
                    return False
                if st.session_state.get("qf_cool") and item.get("trend_motion") != "Cooling down":
                    return False
                if st.session_state.get("qf_chaos") and item.get("trend_motion") != "Chaotic":
                    return False
                return True

            def _game_rank(game_name):
                pool = by_game.get(game_name, []) + picks_by_game.get(game_name, [])
                if sort_by == "Highest score":
                    return (0, -(max((x.get("score") or 0) for x in pool) if pool else -1), game_name)
                if sort_by == "Biggest edge":
                    return (0, -(max((x.get("edge") or 0) for x in pool) if pool else -1), game_name)
                return _game_sort_key(game_name)

            visible_games = [g for g in all_games if _in_time_win(g)]
            st.caption(
                f"{len(visible_games)} games after filters · min score {min_score} · "
                f"{', '.join(show_kinds) or 'nothing selected'}"
            )
            for game in sorted(visible_games, key=_game_rank):
                items = [x for x in by_game.get(game, []) if _keep_card(x)] if "TAKE IT" in show_kinds else []
                picks = [x for x in picks_by_game.get(game, []) if _keep_card(x)] if "TEAM PICK" in show_kinds else []
                items = sorted(items, key=lambda x: -x.get("score", 0))
                picks = sorted(picks, key=lambda x: -x.get("score", 0))
                if not items and not picks and (name_q or min_score or time_win != "All times"):
                    continue
                st.markdown(
                    f'<div class="board-wrap"><div class="game-head">{_fmt_game_header(game)}</div></div>',
                    unsafe_allow_html=True,
                )
                if items or picks:
                    cols = st.columns(2)
                    idx = 0
                    for item in items:
                        with cols[idx % 2]:
                            _render_board_card(item, "TAKE IT", "bet")
                        idx += 1
                    for item in picks:
                        with cols[idx % 2]:
                            _render_board_card(item, "TEAM PICK", "watch-card")
                        idx += 1
                else:
                    wire_n = 0
                    dbg = (st.session_state.get("fetch_debug") or {}).get("per_event") or {}
                    for lab, info in dbg.items():
                        if event_matches_chosen(game, [lab, info.get("event") or ""]):
                            wire_n = max(wire_n, int(info.get("rows") or 0))
                    if df is not None and not getattr(df, "empty", True) and "event" in df.columns:
                        try:
                            wire_n = max(
                                wire_n,
                                int(df["event"].apply(lambda e: event_matches_chosen(e, [game])).sum()),
                            )
                        except Exception:
                            pass
                    if wire_n:
                        st.caption(f"On the wire · {wire_n} 0.5 HR lines · nobody cleared TAKE IT / team pick yet.")
                    else:
                        st.caption("Books have not posted 0.5 HR on this game yet. Fetch again closer to first pitch.")

            if passes and "PASS" in show_kinds:
                shown_p = [x for x in passes if _keep_card(x)]
                with st.expander(f"⚪ Pass · {len(shown_p)}", expanded=False):
                    if not shown_p:
                        st.caption("No PASS names match the filters.")
                    else:
                        cols = st.columns(2)
                        for idx, item in enumerate(shown_p):
                            with cols[idx % 2]:
                                _render_board_card(item, "PASS", "skip")

            if "WATCH" in show_kinds:
                shown_w = [x for x in watches if _keep_card(x)]
                with st.expander(f"👀 Watch · {len(shown_w)}", expanded=False):
                    if not shown_w:
                        st.caption("No WATCH names match the filters.")
                    else:
                        cols = st.columns(2)
                        for idx, item in enumerate(shown_w[:40]):
                            with cols[idx % 2]:
                                _render_board_card(item, "WATCH", "watch-card")

            if "COVERAGE" in show_kinds:
                cov_n = len(coverage_only or [])
                with st.expander(f"📋 Coverage · {cov_n}", expanded=False):
                    st.caption("Support-only names. Still logged for grade. Never upgrades to TAKE IT alone.")
                    if not coverage_only:
                        st.caption("No support-only names right now.")
                    else:
                        cols = st.columns(2)
                        for idx, item in enumerate(coverage_only[:40]):
                            with cols[idx % 2]:
                                _render_board_card(item, "COVERAGE", "watch-card")
        site_section_close()

    if page == "Trend Lab:":
        shop_rows = build_shop_board(df) if df is not None and not getattr(df, "empty", True) else []
        render_trend_lab(ev_board, shop_rows)
    if page == "Shop:":
        site_section_open(
            "💸 PRICE",
            petty_label("Shop"),
            "Odds Shop is where math meets petty precision. Board already picked the name.",
        )
        with st.expander("💸 How to read Shop", expanded=False):
            st.markdown(
                "- 💚 Green price — best ticket book.\n"
                "- ❤️ Red price — short vs fair. Homework.\n"
                "- **TAKE** — cleared play list (price call, not a Board green).\n"
                "- **LEAN** — math says maybe.\n"
                "- **DON’T** — homework only.\n"
                "- **MARKET** — neutral zone.\n"
                "- FN is Fanatics when the feed actually sends it."
            )
        render_shop_tab(df)
        site_section_close()
    if page == "Need One:":
        site_section_open(
            "📈 ONE",
            "I JUST NEED ONE",
            "One-play props only. 0.5 rush / receiving / receptions. Money odds. RE tag. Board stays out of it.",
        )
        with st.expander("📈 What am I looking at?", expanded=True):
            st.markdown(
                "I JUST NEED ONE finds the one-play props — 0.5 rush, receiving, or receptions.\n\n"
                "We only take them when the line is clean, the odds are money-only, and the RE tag is active.\n"
                "Kelly shows the confidence. Benford shows the energy.\n"
                "Board clearance is manual.\n"
                "If it’s green and loud — run it."
            )
            st.markdown(
                '<div class="n1-gloss">'
                "<b>Fair</b><span>Weighted book average</span>"
                "<b>Gap</b><span>Space between fair and posted</span>"
                "<b>EV</b><span>Expected value of the number</span>"
                "<b>Kelly</b><span>Bankroll confidence (0–100%)</span>"
                "<b>RE tag</b><span>Receiving / receptions filter on rush</span>"
                "<b>Money-only</b><span>+100 or higher odds</span>"
                "</div>",
                unsafe_allow_html=True,
            )
        if active_sport() != "NFL":
            st.info("Switch the lane to NFL, Fetch, then come back. This tab is Anytime-TD weekend work.")
        else:
            n1, n2, n3, n4 = st.columns(4)
            with n1:
                t_rush = st.checkbox("0.5 Rush Yards", key="need_one_rush", value=True)
            with n2:
                t_recy = st.checkbox("0.5 Receiving Yards", key="need_one_recy", value=True)
            with n3:
                t_recs = st.checkbox("0.5 Receptions", key="need_one_recs", value=True)
            with n4:
                show_live = st.checkbox("Include live games", key="need_one_live", value=False)
            want = []
            if t_rush:
                want.append("Rush Yards")
            if t_recy:
                want.append("Receiving Yards")
            if t_recs:
                want.append("Receptions")
            need_rows = list(st.session_state.get("need_one_odds") or [])
            live_labs = live_event_labels()
            if not show_live:
                need_rows = [
                    r for r in need_rows
                    if not need_one_is_live(r) and not row_event_is_live(r.get("event") or "", live_labs)
                ]
            items = build_need_one_board(need_rows, want) if want else []
            st.caption(
                "Full game 0.5 only — no 1st quarter / 1st half. Not the 40.5 yard line. "
                "Needs 2+ books. Fair is math. Fetch again to refresh."
            )
            st.markdown(
                f'<div class="petty-row">'
                f'<div class="petty-box n1-live"><div class="petty-num">{sum(1 for x in items if x["action"]=="TAKE")}</div><div class="petty-label">💚 Cleared plays</div></div>'
                f'<div class="petty-box n1-live"><div class="petty-num">{sum(1 for x in items if x["action"]=="LEAN")}</div><div class="petty-label">💖 Math says maybe</div></div>'
                f'<div class="petty-box n1-live"><div class="petty-num">{sum(1 for x in items if x["action"]=="WATCH")}</div><div class="petty-label">💜 Homework zone</div></div>'
                f'<div class="petty-box n1-live"><div class="petty-num">{len(items)}</div><div class="petty-label">🔮 Live props found</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            render_need_one_cards(items)
            try:
                logged = log_need_one(items)
                if logged:
                    st.caption(f"Logged {logged} I JUST NEED ONE TAKE/LEAN row(s) for tracking.")
            except Exception:
                pass
            render_need_one_tracker()
        site_section_close()
    if page == "Digits:":
        render_digits_tab(df)
    if page == "Methods:DK":
        show_player_cards("dk", "🎯 DK Rhythm Lab", "DK 10 and FD-style endings. One card per player. Hover a tag if you forget why it fired.", results)
    if page == "Methods:MGM":
        show_player_cards("mgm", "🎰 MGM Clique Check", "Didn’t leave the clique 💎 — pairs / trios / exact on the same team.", results)
    if page == "Methods:FD":
        show_player_cards("fd", "💙 FanDuel Rhythm Board", f"+{FD_MIN}+ pattern or +600 · only with DK/MGM backup.", results)
    if page == "Methods:Exact":
        show_player_cards("match", "🎯 Perfect Sync", "Same number across books. Perfect sync 🎯 — still not TAKE by itself.", results)
    if page == "Methods:Names":
        st.markdown('<div class="meth-hero"><h3>💅 Name Map</h3><p>Cute extra across different teams. Not the green light.</p></div>', unsafe_allow_html=True)
        show_player_cards("same_init", "💅 Same Initials", "Same first+last initial · different teams", results)
        show_player_cards("cross", "🔄 Cross Initials", "One last initial = other first initial · different teams", results)
        show_player_cards("last", "👩‍👧 Same Last Name", "Exact last name · different teams", results)
        show_player_cards("first", "👯 Same First Name", "Exact first name · different teams", results)
    if page == "Methods:Signals":
        show_player_cards("signal", "📡 Multi-Book Radar", "Same method lighting up on more than one book. Most books first.", results)
    if page == "Lines:Moves":
        st.markdown("""
        <style>
        .mv-hero{background:linear-gradient(135deg,#4c0519,#3b0764);border:1px solid #fb7185;border-radius:22px;padding:16px 18px;margin-bottom:12px;box-shadow:0 0 22px rgba(251,113,133,.25)}
        .mv-hero h3{font-family:'Playfair Display',serif;color:#fff;margin:0 0 6px;font-size:1.4rem}
        .mv-hero p{color:#fecdd3;margin:0;font-size:.88rem}
        .mv-up{border-color:#fb7185!important;box-shadow:0 0 14px rgba(239,68,68,.2)}
        .mv-down{border-color:#4ade80!important;box-shadow:0 0 14px rgba(74,222,128,.2)}
        .mv-arrow{font-size:1.2rem}
        </style>
        """, unsafe_allow_html=True)
        st.markdown(
            '<div class="mv-hero"><h3>Market Motion 💸 — Who’s Moving and Why</h3>'
            "<p>Up = odds lengthened (less likely). Down = odds shortened (more likely).</p>"
            '<p style="margin-top:6px;color:#fda4af">Odds in Motion 💸 — fetch-to-fetch magic.</p></div>',
            unsafe_allow_html=True,
        )
        lines_dashboard_strip(results)
        ups = aggregate_by_player([r for r in results if r["type"] == "hist" and r.get("move_dir") == "up"])
        downs = aggregate_by_player([r for r in results if r["type"] == "hist" and r.get("move_dir") == "down"])
        st.markdown("#### Top movers")
        t1, t2 = st.columns(2)
        with t1:
            st.caption("Biggest climbs")
            for r in ups[:3]:
                st.markdown(f'<div class="card mv-up"><span class="mv-arrow">⬆</span> <b>{r["label"]}</b><div class="note">{r["reason"]}</div></div>', unsafe_allow_html=True)
        with t2:
            st.caption("Biggest crashes")
            for r in downs[:3]:
                st.markdown(f'<div class="card mv-down"><span class="mv-arrow">⬇</span> <b>{r["label"]}</b><div class="note">{r["reason"]}</div></div>', unsafe_allow_html=True)
        left, right = st.columns(2)
        with left:
            st.markdown("#### 🔴 UP")
            if not ups:
                st.info("Nobody lengthened.")
            for r in ups[:16]:
                st.markdown(
                    f'<div class="card mv-up" title="Longer number = they cooled it"><span class="mv-arrow">⬆</span> '
                    f'<b>{r["label"]}</b><div class="note">{r["reason"]}</div></div>',
                    unsafe_allow_html=True,
                )
        with right:
            st.markdown("#### 🟢 DOWN")
            if not downs:
                st.info("Nobody shortened.")
            for r in downs[:16]:
                st.markdown(
                    f'<div class="card mv-down" title="Shorter number = they heated it"><span class="mv-arrow">⬇</span> '
                    f'<b>{r["label"]}</b><div class="note">{r["reason"]}</div></div>',
                    unsafe_allow_html=True,
                )
        heat = Counter()
        for r in ups + downs:
            blob = str(r.get("reason") or "")
            for lab, key in (("DK", "DK"), ("FD", "FD"), ("MGM", "MGM"), ("HardRock", "HardRock"), ("Fanatics", "Fanatics"), ("Caesars", "Caesars")):
                if lab.lower() in blob.lower() or key.lower() in blob.lower():
                    heat[lab] += 1
        if heat:
            chips = "".join(f'<span class="tag">{k} {n}</span>' for k, n in heat.most_common())
            st.markdown(f'<div class="card"><b>Movement heatmap</b><div style="margin-top:6px">{chips}</div></div>', unsafe_allow_html=True)
    if page == "Lines:Trends":
        st.markdown(
            '<div class="mv-hero"><h3>Pattern Detector 💅</h3>'
            "<p>FD sitting under MGM is the crush. FD sitting on top is the fade.</p></div>",
            unsafe_allow_html=True,
        )
        lines_dashboard_strip(results)
        good = sorted([r for r in results if r["type"] == "trend" and r.get("trend_kind") == "good"], key=lambda r: r.get("gap", 0), reverse=True)
        fade = [r for r in results if r["type"] == "trend" and r.get("trend_kind") == "fade"]
        g_items = aggregate_by_player(good)
        f_items = aggregate_by_player(fade)
        strength = min(100, 20 + len(g_items) * 8)
        st.markdown(
            f'<div class="card"><b>Trend strength</b> · {strength}/100'
            f'<div class="bf-meter"><span style="width:{strength}%;background:#22c55e"></span></div>'
            f'<div class="note">{len(g_items)} FD-under-MGM · {len(f_items)} fade</div></div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 💚 Finally showed up 💅")
            if not g_items:
                st.info("No FD-under-MGM crush yet.")
            for r in g_items[:15]:
                st.markdown(
                    f'<div class="card mv-down" title="FD cheaper than MGM"><b>{r["label"]}</b>'
                    f'<div class="note">{r["reason"]}</div></div>',
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown("#### 🔴 Ghosted energy")
            if not f_items:
                st.info("Nothing to fade.")
            for r in f_items[:15]:
                st.markdown(
                    f'<div class="card mv-up" title="Leave it"><b>{r["label"]}</b>'
                    f'<div class="note">{r["reason"]}</div></div>',
                    unsafe_allow_html=True,
                )
    if page == "Lines:Late":
        st.markdown(
            '<div class="mv-hero"><h3>Ghost Radar 👻</h3>'
            "<p>Ghosted by the book 👻 — gone from DK / FD / MGM vs last fetch or Lock.</p></div>",
            unsafe_allow_html=True,
        )
        lines_dashboard_strip(results)
        late_items = aggregate_by_player([r for r in results if r["type"] == "late"])
        heat = Counter()
        for r in late_items:
            blob = str(r.get("reason") or "")
            for lab in ("DK", "FD", "MGM", "HardRock", "Fanatics", "Caesars"):
                if lab.lower() in blob.lower():
                    heat[lab] += 1
        if heat:
            chips = "".join(f'<span class="tag">{k} {n}</span>' for k, n in heat.most_common())
            st.markdown(f'<div class="card"><b>Missing heatmap</b><div style="margin-top:6px">{chips}</div></div>', unsafe_allow_html=True)
        if not late_items:
            st.info("Nobody ghosted. Cute.")
        else:
            cols = st.columns(2)
            for i, r in enumerate(late_items[:24]):
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="card" title="Missing vs last snapshot"><b>👻 {r["label"]}</b>'
                        f'<div class="note">{r["reason"]}</div></div>',
                        unsafe_allow_html=True,
                    )
    if page == "Lines:Lock":
        st.markdown('<div class="queen-banner">🔒 Pregame Lock · open / now / close</div>', unsafe_allow_html=True)
        st.markdown("#### Run It Recap")
        st.caption(
            "One row per unique name. Hits only is the default vibe. "
            "Did it go? = the homer happened. Times logged = we saved that name more than once. "
            "Not extra bombs."
        )
        render_run_it_recap()
        st.markdown("#### Pregame prices")
        st.caption(
            "Open = first pull (never changes) · Now = latest pregame fetch · "
            "Close = frozen when the book drops off the feed (often at first pitch)."
        )
        lock = lock_for_sport()
        if not lock:
            st.info(f"No {active_sport()} lock yet. Fetch this sport pregame.")
        else:
            q = st.text_input("Filter", key="lock_q")
            show_moved = st.checkbox("Only show open -> now/close movers", value=False, key="lock_movers")
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
                        bit += f"<br>-> now {format_odds(latest)}" + (f" <small>({tL})</small>" if tL else "") + f" ({d:+d})"
                    if close is not None:
                        if close != first:
                            moved = True
                        d2 = int(close) - int(first)
                        bit += f"<br>-> close {format_odds(close)}" + (f" <small>({tC})</small>" if tC else "") + f" ({d2:+d})"
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
            "Sort best-odds-first shows the longest numbers on top - not the most likely HRs."
        )
        lock = lock_for_sport()
        if not lock:
            st.info(f"Fetch {active_sport()} pregame so Lock has prices, then search here.")
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
                    ["Best odds first (highest)", "Lowest first", "Name A-Z"],
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

            # Book = All -> one card per player (all books under them)
            # Book = specific -> one row per matching book line
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
                    st.info("Nothing matched - loosen filters.")
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
                    st.info("Nothing matched - loosen filters.")
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
        site_section_open(
            "🔒 LOCK",
            "Lock Lab",
            sport_cfg()["lock_caption"] + " Open / Now / Close are the last pregame prices we saved before a book vanished.",
        )
        st.markdown('<div class="queen-banner">🧠 Lock Lab · Who went & what Lock had</div>', unsafe_allow_html=True)
        lab = build_lock_lab()
        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{lab["hr_count"]}</div><div class="petty-label">{sport_cfg()["lock_count"]}</div></div>
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
            st.info(f"Insights appear after {sport_cfg()['hits']} match Lock.")

        hit_word = sport_cfg()["hits"]
        st.markdown(f"#### Endings on today's {hit_word}")
        chips = []
        for (bl, end), cnt in sorted((lab.get("book_end_counter") or {}).items(), key=lambda x: -x[1])[:14]:
            hot = end in (0, 25, 50, 75, 10) or cnt >= 2
            chips.append(
                f'<span class="trend-chip {"hot" if hot else ""}">{bl} {end:02d}: '
                f'<span class="chip-count">{cnt}</span></span>'
            )
        st.markdown("".join(chips) if chips else f"_(No Lock ↔ {hit_word} matches yet)_", unsafe_allow_html=True)

        st.markdown("#### Our tags that showed up")
        tag_chips = []
        for tag, cnt in sorted((lab.get("tag_counter") or {}).items(), key=lambda x: -x[1])[:16]:
            tag_chips.append(
                f'<div class="rate-chip"><div class="rate-pct">{cnt}</div>'
                f'<div class="rate-name">{tag}</div></div>'
            )
        st.markdown("".join(tag_chips) if tag_chips else "_(None)_", unsafe_allow_html=True)

        st.markdown("#### Who went · most tags first")
        if not lab["matched"]:
            st.info(f"No {sport_cfg()['hit']} names matched Lock. Fetch pre-kick so Lock fills, then grade HIT.")
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
        site_section_close()

    if page == "Grade:Tracker":
        site_section_open(
            "📡 LEARN",
            "Tracker",
            "Hit rates after we grade. Board TAKE and Shop TAKE both count. Small n stays hidden. "
            "If TAKE % sits on top of WATCH %, the green list is too fat — raise the floor next week.",
        )
        st.markdown('<div class="queen-banner">📡 Tracker</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box"><b>How to read this.</b> '
            "Board green = Run it, baddie (source take_it). Shop TAKE/LEAN = the number we would buy. "
            "Watch = eyes only. Grade HIT/MISS or the rates stay frozen. "
            "Banner “on our list” = box-score names that were take_it, watch, shop_take, or shop_lean.</div>",
            unsafe_allow_html=True,
        )
        sport_rows = results_for_sport()
        n_sport = len([r for r in sport_rows if r.get("result") in ("HIT", "MISS")])
        n_all = len([r for r in load_results() if r.get("result") in ("HIT", "MISS")])
        n_pend = len([r for r in sport_rows if r.get("result") == "PENDING" and r.get("date") in (today_az(), today_mlb_date())])
        n_take_pend = len([r for r in sport_rows if r.get("result") == "PENDING" and r.get("source") == "take_it" and r.get("date") in (today_az(), today_mlb_date())])
        other = "MLB" if active_sport() == "NFL" else "NFL"
        n_other = max(0, n_all - n_sport)
        st.caption(
            f"**{active_sport()} only** — {n_sport} graded {sport_cfg().get('hits', 'plays')}. "
            f"{other} ({n_other} graded) is hidden while this sport is selected. "
            f"n &lt; {tracker_min_n()} hidden unless it is a core family. "
            "HOT = n≥8 and beats this sport’s TAKE baseline (not a 4-play fluke)."
        )
        today_rows = [r for r in sport_rows if r.get("date") == today_az() and r.get("result") in ("HIT", "MISS")]
        today_hits = [r for r in today_rows if r.get("result") == "HIT"]
        if today_hits:
            meth_c, book_c, end_c = Counter(), Counter(), Counter()
            long_hits = []
            overlap = 0
            for r in today_hits:
                ms = [normalize_method_name(m) for m in (r.get("methods") or []) if normalize_method_name(m) not in TRACKER_BLOCKLIST]
                for m in ms:
                    meth_c[m] += 1
                if len(ms) >= 2:
                    overlap += 1
                book_c[book_label(r.get("best_book"))] += 1
                end = r.get("ending")
                if end is None and r.get("best_price") is not None:
                    end = last_two(r["best_price"])
                if end is not None:
                    end_c[f"{int(end):02d}"] += 1
                try:
                    if abs(int(r.get("best_price"))) >= 700:
                        long_hits.append(f"{r.get('player')} {format_odds(r.get('best_price'))}")
                except Exception:
                    pass
            st.markdown("#### What stood out today")
            bits = []
            if meth_c:
                bits.append("Methods on hits: " + ", ".join(f"{k} {n}" for k, n in meth_c.most_common(5)))
            if book_c:
                bits.append("Books: " + ", ".join(f"{k} {n}" for k, n in book_c.most_common(4)))
            if end_c:
                bits.append("Endings: " + ", ".join(f"{k} {n}" for k, n in end_c.most_common(5)))
            bits.append(f"{overlap} hits wore 2+ tags")
            if long_hits:
                bits.append("Long prices that cashed: " + ", ".join(long_hits[:4]))
            for line in bits:
                st.markdown(f'<div class="info-box">{line}</div>', unsafe_allow_html=True)
        else:
            st.info(
                f"No {active_sport()} HITs graded yet. "
                f"{n_pend} PENDING rows are already saved for today "
                f"({n_take_pend} Run It / take_it). "
                "Open Grade → Results and tap Auto-grade, or HIT/MISS. "
                "Tracker stays empty until those flip off PENDING. "
                "MLB and NFL never share a Tracker."
            )
        baseline, baseline_n = take_it_baseline_rate(sport_rows)
        if baseline is not None:
            st.markdown(
                f'<div class="info-box"><b>Baseline TAKE IT:</b> {baseline:.0f}% '
                f'(n={baseline_n}). Signal methods above this get a green border.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="info-box">No graded TAKE IT yet - baseline appears after HIT/MISS.</div>',
                unsafe_allow_html=True,
            )

        def chips_from_stats(stats, min_n=None, compare_baseline=False):
            if min_n is None:
                min_n = tracker_min_n()
            out = []
            base = baseline if baseline is not None else 11.0
            for name, s in sorted(
                stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                always = str(name) in TRACKER_ALWAYS
                if t < min_n and not always:
                    continue
                pct = 100 * s["hit"] / t
                delta = pct - base
                hot = pct > max(15, base) and t >= 8
                beat = compare_baseline and pct > base + 0.5 and t >= 8
                cls = "rate-chip beat" if beat or hot else "rate-chip"
                sign = "+" if delta >= 0 else ""
                badge = ' <span class="tag tag-strong">HOT</span>' if hot else ""
                thin = " · thin n" if t < 8 else ""
                beat_html = f'<div class="rate-beat">{sign}{delta:.0f} Δ vs {base:.0f}%</div>'
                out.append(
                    f'<div class="{cls}">'
                    f'<div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{name}{badge}</div>'
                    f'<div class="rate-n">{s["hit"]} hit · {s["miss"]} miss · {t} plays{thin}</div>'
                    f"{beat_html}</div>"
                )
            return out

        method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats, score_stats = build_tracker_stats(sport_rows)

        st.markdown("#### By Petty Score lane")
        st.caption(
            "Higher lane is not automatically better. "
            "HOT only if n≥8 and the rate beats this sport’s TAKE baseline. "
            "If 85–100 is under that line, do not treat the score as a ticket."
        )
        chips = chips_from_stats(score_stats, compare_baseline=True)
        st.markdown(
            "".join(chips) if chips else f"_(Need graded plays with n >= {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        # Signal method = Girl Magic tags (why we cared)
        st.markdown("#### By signal method")
        st.caption("How the tagged names actually graded - not which window you clicked.")
        chips = chips_from_stats(method_stats, compare_baseline=True)
        st.markdown(
            "".join(chips) if chips else f"_(Need graded plays with n >= {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        # Best book = where the logged best_price lived
        st.markdown("#### By best book we took")
        st.caption("Which sportsbook held the best price on the graded row - separate from the signal tag.")
        chips = chips_from_stats(book_stats, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else f"_(Need n >= {TRACKER_MIN_N})_",
            unsafe_allow_html=True,
        )

        st.markdown("#### By ending on best price")
        st.caption("Last two digits of the best_price we logged (not MGM-only unless that was best).")
        chips = chips_from_stats(ending_stats, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else f"_(Need n >= {TRACKER_MIN_N})_",
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
        st.caption("Every posted book on the row when we logged it - DK 10, MGM 25, HR 00, etc.")
        chips = chips_from_stats(book_end_stats, min_n=15, compare_baseline=False)
        st.markdown(
            "".join(chips) if chips else "_(Fills as new logs store every book price)_",
            unsafe_allow_html=True,
        )
        site_section_close()
    if page == "Grade:Results":
        st.markdown('<div class="queen-banner">📊 Results — two books</div>', unsafe_allow_html=True)
        st.caption("Tickets = names we told people to play. Research = methods / watches we grade so the tricks can move.")
        if st.button("⚡ Run auto-grade now", type="primary"):
            with st.spinner("MLB..."):
                h, m, s, msg = auto_grade_pending()
            st.success(f"{h} HIT · {m} MISS · {s} open - {msg}")
            st.rerun()
        rows = results_for_sport()
        n_all = len(rows)
        n_pending_all = sum(1 for r in rows if r.get("result") == "PENDING")
        n_today = sum(1 for r in rows if r.get("date") == today_az())
        src = st.session_state.get("_results_source", "?")
        gh_st = st.session_state.get("_results_gh_status", "unconfigured")
        gh_save = st.session_state.get("_results_gh_save", "-")
        lock_src = st.session_state.get("_pregame_source", "?")
        lock_n = len(lock_for_sport())
        hist_src = st.session_state.get("_history_source", "?")
        hist_save = st.session_state.get("_history_gh_save", "-")
        secrets_ok = "yes" if _gh_configured() else "NO - add GITHUB_TOKEN + GITHUB_REPO"
        st.caption(
            f"{n_all} logged · {n_pending_all} waiting · {n_today} today · "
            f"source={src} · GH load={gh_st} · GH save={gh_save} · "
            f"lock={lock_n} ({lock_src}) · hist={hist_src}/{hist_save} · secrets={secrets_ok}"
        )
        if not _gh_configured():
            st.warning(
                "GitHub secrets missing - Results, Lock, and movement history wipe on reboot. "
                "Add GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH in Streamlit Secrets."
            )
        elif n_all == 0:
            st.info(
                "No rows yet. Fetch **pregame** so TAKE IT / WATCH log here, then auto-grade after games. "
                "If you had data before, check that girl_magic_results.json exists in your GitHub repo."
            )
        today_only = st.checkbox("Today only", value=False)
        src_f = st.radio(
            "Book",
            ["🎟️ Tickets", "🔬 Research", "All"],
            horizontal=True,
            key="results_src_filter",
        )
        rows_view = [r for r in rows if r.get("date") == today_az()] if today_only else rows
        if active_sport() == "NFL":
            rows_view = [
                r for r in rows_view
                if not is_nfl_qb(r.get("player") or "")
            ]
        ticket_src = ("take_it", "shop_take", "manual_hr")
        research_src = ("watch", "shop_lean")
        if src_f.startswith("🎟️"):
            rows_view = [r for r in rows_view if r.get("source") in ticket_src]
        elif src_f.startswith("🔬"):
            rows_view = [r for r in rows_view if r.get("source") in research_src]
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
            if st.button("<- Prev", disabled=page <= 0):
                st.session_state["pending_page"] = page - 1
                st.rerun()
        with n2:
            if st.button("Next ->", disabled=end >= total_p):
                st.session_state["pending_page"] = page + 1
                st.rerun()
        for r in pending[start:end]:
            rid = r["id"]
            endg = r.get("ending")
            end_s = f" ends {int(endg):02d}" if endg is not None else ""
            src_lab = {"take_it": "Board TAKE IT", "watch": "Board WATCH", "shop_take": "Shop TAKE", "shop_lean": "Shop LEAN"}.get(r.get("source"), r.get("source") or "")
            st.markdown(f"**{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}{end_s} · {src_lab}")
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
            src_lab = {"take_it": "Board TAKE IT", "watch": "Board WATCH", "shop_take": "Shop TAKE", "shop_lean": "Shop LEAN"}.get(r.get("source"), r.get("source") or "")
            st.markdown(f"{icon} **{r['player']}** · {format_odds(r.get('best_price'))} {book_label(r.get('best_book'))}{end_s} · {src_lab}{auto}")
            if st.button("↩️ Undo", key=f"undo_{rid}"):
                undo_result(rid, r.get("source"))
                st.rerun()
    if page == "Grade:Backtest":
        st.markdown('<div class="queen-banner">🧪 Backtest · TAKE IT vs WATCH</div>', unsafe_allow_html=True)
        st.caption("Unique names only — not every duplicate row from Fetch. Needs a few days of HIT/MISS before the % means much.")
        rows_bt = results_for_sport()
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
            st.info("No graded TAKE IT / WATCH rows yet. Fetch -> let WATCH log -> auto-grade after games.")
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
        st.caption(
            "Old weeks logged almost nobody as WATCH — that 0% is leftover, not today’s box. "
            "EV / Kelly chips alone are not a Watch method."
        )
        chips_wa = []
        for name, s in sorted(method_by_src["watch"].items(), key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"]))):
            t = s["hit"] + s["miss"]
            if t < 5:
                continue
            if name in ("EV Support", "Kelly Support", "EV Premium", "Kelly Premium", "EV Caution", "Kelly Caution"):
                continue
            pct = 100 * s["hit"] / t
            chips_wa.append(
                f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                f'<div class="rate-name">{name}</div>'
                f'<div class="rate-n">{s["hit"]}H · {s["miss"]}M · n={t}</div></div>'
            )
        st.markdown("".join(chips_wa) if chips_wa else "_(Need more graded WATCH)_", unsafe_allow_html=True)

        st.caption("Coverage = share of MLB HRs that were on WATCH/TAKE that day (see banner). Aim: TAKE IT hit rate > WATCH > random.")


    if page == "Grade:Shop":
        st.markdown('<div class="queen-banner">🛒 Shop report card</div>', unsafe_allow_html=True)
        st.caption(
            "This is the price side only. Shop TAKE / LEAN log even if the same name is on The Board. "
            "Board Backtest stays methods-only."
        )
        rows_sh = results_for_sport()
        overall_s, daily_s, book_s, end_s, buck_s, n_shop = build_shop_grade_stats(rows_sh, days=14)

        def fmt_rate(h, m, t, pct):
            if t == 0 or pct is None:
                return "-"
            return f"{pct:.0f}% · {h}H / {m}M · n={t}"

        tk = overall_s.get("shop_take", (0, 0, 0, None))
        ln = overall_s.get("shop_lean", (0, 0, 0, None))
        tk_pct = f"{tk[3]:.0f}" if tk[3] is not None else "-"
        ln_pct = f"{ln[3]:.0f}" if ln[3] is not None else "-"
        st.markdown(f"""
        <div class="petty-row">
            <div class="petty-box"><div class="petty-num">{tk_pct}</div><div class="petty-label">SHOP TAKE %</div></div>
            <div class="petty-box"><div class="petty-num">{tk[2]}</div><div class="petty-label">TAKE n</div></div>
            <div class="petty-box"><div class="petty-num">{ln_pct}</div><div class="petty-label">SHOP LEAN %</div></div>
            <div class="petty-box"><div class="petty-num">{ln[2]}</div><div class="petty-label">LEAN n</div></div>
            <div class="petty-box"><div class="petty-num">{n_shop}</div><div class="petty-label">Graded 14d</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Last 14 days")
        if not daily_s:
            st.info("No graded Shop TAKE / LEAN yet. Fetch pregame → Shop logs TAKE/LEAN → auto-grade after games.")
        else:
            for day in daily_s:
                st.markdown(
                    f'<div class="card"><b>{day["date"]}</b><br>'
                    f'Shop TAKE: {fmt_rate(*day["shop_take"])}<br>'
                    f'Shop LEAN: {fmt_rate(*day["shop_lean"])}</div>',
                    unsafe_allow_html=True,
                )

        def chips_from(stats, min_n=8):
            out = []
            for name, s in sorted(
                stats.items(),
                key=lambda x: -(x[1]["hit"] / max(1, x[1]["hit"] + x[1]["miss"])),
            ):
                t = s["hit"] + s["miss"]
                if t < min_n:
                    continue
                pct = 100 * s["hit"] / t
                out.append(
                    f'<div class="rate-chip"><div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{name}</div>'
                    f'<div class="rate-n">{s["hit"]}H · {s["miss"]}M · n={t}</div></div>'
                )
            return out

        st.markdown("#### By best book we bought")
        chips = chips_from(book_s)
        st.markdown("".join(chips) if chips else "_(Need more graded Shop rows)_", unsafe_allow_html=True)

        st.markdown("#### By ending on Shop best price")
        chips = chips_from(end_s)
        st.markdown("".join(chips) if chips else "_(Need more graded endings)_", unsafe_allow_html=True)

        st.markdown("#### By price bucket")
        chips = chips_from(buck_s, min_n=6)
        st.markdown("".join(chips) if chips else "_(Need more graded prices)_", unsafe_allow_html=True)
        st.caption("Shop TAKE should beat Shop LEAN if the gap-vs-fair call is real. Ignore tiny n.")

    if page == "Grade:Vibe":
        st.markdown("### Board vibe")
        st.caption("Are today's numbers all the same flavor, or mixed? Low score = copy-paste board. Not who goes yard.")
        lookat_box(
            "🔢 Benford on this page",
            "Higher score = real energy. Lower score = forced numbers. Confirm the pond. The Board still clears the name.",
        )
        if not HAS_BENFORD:
            st.warning("Upload benford.py next to app.py.")
        else:
            live_all, live_best = [], []
            if df is not None and not getattr(df, "empty", True):
                try:
                    live_all = [int(x) for x in df["price"].dropna().tolist()]
                except Exception:
                    live_all = []
                shop_rows = build_shop_board(df)
                live_best = [r["best"] for r in shop_rows if r.get("best") is not None]
            lock = st.session_state.get("pregame_lock") or load_pregame()
            lock_px = []
            if isinstance(lock, dict):
                for rec in lock.values() if not isinstance(next(iter(lock.values()), None), dict) or True else []:
                    pass
                # lock shape: player -> {books: {bk: {price}}}
                for rec in lock.values():
                    if not isinstance(rec, dict):
                        continue
                    books = rec.get("books") or {}
                    for info in books.values():
                        if isinstance(info, dict) and info.get("price") is not None:
                            try:
                                lock_px.append(int(info["price"]))
                            except Exception:
                                pass
                        elif isinstance(info, (int, float)):
                            lock_px.append(int(info))
            graded = []
            hits_only = []
            for r in load_results():
                if r.get("result") not in ("HIT", "MISS"):
                    continue
                if r.get("best_price") is None:
                    continue
                try:
                    px = int(r["best_price"])
                except Exception:
                    continue
                graded.append(px)
                if r.get("result") == "HIT":
                    hits_only.append(px)
            pack = analyze_many({
                "live_all_posted": live_all,
                "live_best": live_best,
                "lock_prices": lock_px,
                "graded_best": graded,
                "graded_hits": hits_only,
            })
            sets = pack.get("sets") or {}
            for name, res in sets.items():
                score = res.get("benford_score", 0)
                st.markdown(
                    f'<div class="card">'
                    f'<div class="card-kicker">{res.get("alignment_label")}</div>'
                    f'<span class="score-pill">{score:.2f}</span>'
                    f'<div class="card-name">{name}</div>'
                    f'<div class="card-meta">n={res.get("n")} · MAD {res.get("mad")} · {res.get("alignment_note")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("#### Raw JSON")
            st.json(pack)
            st.caption("Most natural: %s · Most artificial: %s" % (pack.get("most_natural"), pack.get("most_artificial")))

    if page == "Analytics:":
        # Display-only recap. Does not change TAKE IT / fetch / grade math.
        st.markdown("""
        <style>
        .pa-hero{background:linear-gradient(90deg,#db2777,#7c3aed);border-radius:18px;padding:16px 18px;margin-bottom:12px;box-shadow:0 0 24px rgba(236,72,153,.25)}
        .pa-hero h3{font-family:'Playfair Display',serif;margin:0;color:#fff;font-size:1.55rem}
        .pa-quote{color:#fce7f3;font-style:italic;margin:6px 0 0;font-size:.92rem}
        .pa-card{background:linear-gradient(180deg,#1a1024,#120818);border:1px solid #3b1d4a;border-radius:18px;padding:14px 16px;margin-bottom:12px;box-shadow:0 0 18px rgba(168,85,247,.18)}
        .pa-h{font-size:.82rem;letter-spacing:1.2px;text-transform:uppercase;color:#f9a8d4;font-weight:800;margin:0 0 8px}
        .pa-sub{font-size:.68rem;color:#c4b5d6;margin:-2px 0 10px}
        .pa-grid{display:flex;flex-wrap:wrap;gap:8px}
        .pa-chip{min-width:108px;background:#221033;border:1px solid #6d28d9;border-radius:14px;padding:8px 10px;text-align:center;box-shadow:0 0 12px rgba(236,72,153,.2)}
        .pa-chip.top{border-color:#f472b6;box-shadow:0 0 16px rgba(244,114,182,.45)}
        .pa-chip .n{font-size:1.15rem;font-weight:800;background:linear-gradient(90deg,#f472b6,#a855f7);-webkit-background-clip:text;color:transparent}
        .pa-chip .l{font-size:.72rem;color:#e9d5ff;font-weight:700}
        .pa-chip .p{font-size:.62rem;color:#c4b5d6}
        .pa-day{flex:1;min-width:160px;background:#1a1024;border:1px solid #7c3aed;border-radius:16px;padding:10px 12px}
        .pa-day h4{margin:0 0 4px;color:#f9a8d4;font-size:.88rem}
        .pa-row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:.84rem}
        .pa-bar{height:8px;border-radius:99px;background:#2a2038;flex:1;overflow:hidden}
        .pa-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#f472b6,#a855f7);box-shadow:0 0 8px rgba(244,114,182,.45)}
        .pa-n{font-weight:800;color:#f9a8d4;min-width:28px;text-align:right}
        .pa-pct{color:#c4b5d6;font-size:.72rem}
        .pa-foot{text-align:center;color:#f9a8d4;font-size:.78rem;margin:18px 0 8px;opacity:.9}
        @keyframes pa-spark{0%{opacity:.5}50%{opacity:1}100%{opacity:.5}}
        .pa-spark{animation:pa-spark 2.4s ease-in-out infinite}
        </style>
        """, unsafe_allow_html=True)
        hero_take = "Run it, baddie" if petty_on() else "TAKE IT"
        st.markdown(
            '<div class="pa-hero pa-spark"><h3>Petty Analytics</h3>'
            '<p class="pa-quote">If the odds look ugly, they probably lying.</p>'
            f'<p class="pa-quote" style="font-size:.75rem;opacity:.85">Recap only. {hero_take} rules did not change.</p></div>',
            unsafe_allow_html=True,
        )

        rows = results_for_sport() or []
        today = today_az()
        try:
            end = datetime.strptime(today, "%Y-%m-%d").date()
        except Exception:
            end = datetime.now().date()
        start = end - timedelta(days=6)
        last_start = start - timedelta(days=7)
        last_end = start - timedelta(days=1)

        def _row_day(r):
            d = str(r.get("date") or "")[:10]
            try:
                return datetime.strptime(d, "%Y-%m-%d").date()
            except Exception:
                return None

        def _in(r, a, b):
            dd = _row_day(r)
            return dd is not None and a <= dd <= b

        def _ending(r):
            endn = r.get("ending")
            if endn is None:
                endn = last_two(r.get("best_price"))
            try:
                return f"{int(endn):02d}" if endn is not None else None
            except Exception:
                return None

        window = st.selectbox("Compare", ["This week vs last week", "This week only"], key="pa_window")
        focus_src = st.selectbox(
            "Log slice",
            ["All graded", "Board TAKE IT / WATCH", "Shop TAKE / LEAN"],
            key="pa_src",
        )
        week = [r for r in rows if _in(r, start, end)]
        prevw = [r for r in rows if _in(r, last_start, last_end)]
        if focus_src.startswith("Board"):
            week = [r for r in week if r.get("source") in ("take_it", "watch")]
            prevw = [r for r in prevw if r.get("source") in ("take_it", "watch")]
        elif focus_src.startswith("Shop"):
            week = [r for r in week if r.get("source") in ("shop_take", "shop_lean")]
            prevw = [r for r in prevw if r.get("source") in ("shop_take", "shop_lean")]

        hits = [r for r in week if r.get("result") == "HIT"]
        graded = [r for r in week if r.get("result") in ("HIT", "MISS")]
        prev_hits = [r for r in prevw if r.get("result") == "HIT"]
        prev_graded = [r for r in prevw if r.get("result") in ("HIT", "MISS")]
        bomb = "TD" if active_sport() == "NFL" else "HR"
        bombs = "TDs" if active_sport() == "NFL" else "HRs"

        def _unique_hits(hit_rows):
            seen, out = set(), []
            for r in hit_rows:
                pl = clean_name(r.get("player") or "")
                dd = str(r.get("date") or "")[:10]
                key = (pl.lower(), dd)
                if not pl or key in seen:
                    continue
                seen.add(key)
                out.append(r)
            return out
        hits_u = _unique_hits(hits)
        prev_hits_u = _unique_hits(prev_hits)
        if active_sport() == "NFL":
            hits_u = [r for r in hits_u if not is_nfl_qb(r.get("player") or "")]
            prev_hits_u = [r for r in prev_hits_u if not is_nfl_qb(r.get("player") or "")]

        def pack_hits(hit_rows, graded_rows):
            endings = Counter(); books = Counter(); buckets = Counter()
            families = Counter(); methods_c = Counter(); names = Counter()
            end_g = Counter(); book_g = Counter(); buck_g = Counter(); meth_g = Counter()
            fade = Counter(); cross = Counter()
            for r in hit_rows:
                e = _ending(r)
                if e:
                    endings[e] += 1
                books[book_label(r.get("best_book"))] += 1
                bkt = price_bucket(r.get("best_price"))
                if bkt:
                    buckets[bkt] += 1
                if r.get("player"):
                    names[r["player"]] += 1
                seen_fam = set()
                for m in r.get("methods") or []:
                    nm = normalize_method_name(m)
                    methods_c[nm] += 1
                    fam = petty_family_for_method(nm)
                    if fam and fam not in seen_fam:
                        families[fam] += 1
                        seen_fam.add(fam)
                    if fam:
                        cross[(fam, nm)] += 1
            for r in graded_rows:
                e = _ending(r)
                if e:
                    end_g[e] += 1
                book_g[book_label(r.get("best_book"))] += 1
                bkt = price_bucket(r.get("best_price"))
                if bkt:
                    buck_g[bkt] += 1
                for m in r.get("methods") or []:
                    nm = normalize_method_name(m)
                    meth_g[nm] += 1
                    if r.get("result") == "MISS" and (str(m).startswith("FADE") or m == "Multi-book Lengthen"):
                        if r.get("player"):
                            fade[r["player"]] += 1
            return endings, books, buckets, families, methods_c, names, end_g, book_g, buck_g, meth_g, fade, cross

        endings, books, buckets, families, methods_c, names, end_g, book_g, buck_g, meth_g, fade, cross = pack_hits(hits_u, graded)
        names = Counter()
        for r in hits_u:
            if r.get("player"):
                names[r["player"]] += 1
        wd_hits, wd_grad = Counter(), Counter()
        wd_book_hits, wd_book_grad = Counter(), Counter()
        wd_end_hits = Counter()
        for r in hits_u:
            dd = _row_day(r)
            if not dd:
                continue
            day = dd.strftime("%A")
            wd_hits[day] += 1
            bk = book_label(r.get("best_book"))
            if bk:
                wd_book_hits[(day, bk)] += 1
            e = _ending(r)
            if e is not None:
                wd_end_hits[(day, e)] += 1
        for r in graded:
            dd = _row_day(r)
            if not dd:
                continue
            day = dd.strftime("%A")
            wd_grad[day] += 1
            bk = book_label(r.get("best_book"))
            if bk:
                wd_book_grad[(day, bk)] += 1
        p_end, p_book, p_buck, p_fam, p_meth, p_names, *_rest = pack_hits(prev_hits, prev_graded)

        def arrow(now, then):
            if window.endswith("only") or then == 0 and now == 0:
                return ""
            if now > then:
                return " ^"
            if now < then:
                return " v"
            return " ="

        def rate(n_hit, n_all):
            if not n_all:
                return "—"
            return f"{100 * n_hit / n_all:.0f}%"

        def bar_row(label, n, mx, extra="", crown=False):
            w = 0 if mx <= 0 else int(100 * n / mx)
            cr = "TOP · " if crown else ""
            return (
                f'<div class="pa-row"><span>{cr}{label}</span>'
                f'<div class="pa-bar"><div class="pa-fill" style="width:{w}%"></div></div>'
                f'<span class="pa-n">{n}</span><span class="pa-pct">{extra}</span></div>'
            )

        def section_html(title, subtitle, items, mx, rate_map=None, prev_map=None):
            chips = []
            for i, (k, n) in enumerate(items):
                extra = ""
                if rate_map is not None:
                    extra = rate(n, rate_map.get(k, 0))
                if prev_map is not None:
                    extra += arrow(n, prev_map.get(k, 0))
                top = " top" if i == 0 else ""
                chips.append(
                    f'<div class="pa-chip{top}"><div class="n">{n}</div>'
                    f'<div class="l">{k}</div><div class="p">{extra}</div></div>'
                )
            body = '<div class="pa-grid">' + "".join(chips) + "</div>" if chips else '<div class="pa-pct">None yet</div>'
            return f'<div class="pa-card"><div class="pa-h">{title}</div><div class="pa-sub">{subtitle}</div>{body}</div>'

        week_rate = rate(len(hits), len(graded))
        prev_rate = rate(len(prev_hits), len(prev_graded))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{bombs} this week", len(hits_u), delta=len(hits_u) - len(prev_hits_u) if not window.endswith("only") else None)
        c2.metric("Graded", len(graded))
        c3.metric("Hit rate", week_rate, delta=None if window.endswith("only") else f"last {prev_rate}")
        c4.metric("Repeat names", sum(1 for n in names.values() if n >= 2))

        filter_opts = ["(all)"]
        filter_opts += [f"ending:{k}" for k, _ in endings.most_common(8)]
        filter_opts += [f"book:{k}" for k, _ in books.most_common(6)]
        filter_opts += [f"method:{k}" for k, _ in methods_c.most_common(8)]
        filter_opts += [f"player:{k}" for k, _ in names.most_common(8) if k]
        chosen = st.selectbox("Focus a line (filters the recap text below)", filter_opts, key="pa_focus")

        def matches_focus(r):
            if chosen == "(all)":
                return True
            kind, val = chosen.split(":", 1)
            if kind == "ending":
                return _ending(r) == val
            if kind == "book":
                return book_label(r.get("best_book")) == val
            if kind == "method":
                return val in {normalize_method_name(m) for m in (r.get("methods") or [])}
            if kind == "player":
                return r.get("player") == val
            return True

        focus_hits = [r for r in hits if matches_focus(r)]
        if chosen != "(all)":
            st.caption(f"Focus {chosen}: {len(focus_hits)} {bomb}s this slice")

        # streaks: consecutive HIT dates
        by_player_days = defaultdict(set)
        for r in rows:
            if r.get("result") != "HIT" or not r.get("player"):
                continue
            dd = _row_day(r)
            if dd:
                by_player_days[r["player"]].add(dd)
        streaks = {}
        for pl, days in by_player_days.items():
            if not days:
                continue
            cur = 0
            d = end
            while d in days:
                cur += 1
                d = d - timedelta(days=1)
            if cur >= 2:
                streaks[pl] = cur

        left, right = st.columns(2)
        mx_e = max(endings.values() or [1])
        mx_bk = max(books.values() or [1])
        mx_bu = max(buckets.values() or [1])
        mx_f = max(families.values() or [1])
        mx_m = max(methods_c.values() or [1])
        with left:
            st.markdown(section_html(
                "Hot Endings", f"Last two digits on unique {bomb}s — % is hit rate in that ending",
                endings.most_common(8), mx_e, end_g, p_end,
            ), unsafe_allow_html=True)
            st.markdown(section_html(
                "Who is Paying the Bills", "Top books - best-price book on the HIT row",
                books.most_common(8), mx_bk, book_g, p_book,
            ), unsafe_allow_html=True)
            st.markdown(section_html(
                "Money Lanes", f"Price lane on unique {bomb}s — % = hits / graded in that lane",
                buckets.most_common(8), mx_bu, buck_g, p_buck,
            ), unsafe_allow_html=True)
            if active_sport() == "NFL":
                order = ("Thursday", "Sunday", "Monday")
            else:
                order = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
            day_cards = []
            nfl_label = {"Thursday": "TNF", "Sunday": "Sunday", "Monday": "MNF"}
            for d in order:
                books_d = sorted([(b, n) for (day, b), n in wd_book_hits.items() if day == d], key=lambda x: -x[1])
                ends_d = sorted([(e, n) for (day, e), n in wd_end_hits.items() if day == d], key=lambda x: -x[1])
                top_b = ", ".join(f"{b} {n}" for b, n in books_d[:3]) or "quiet"
                top_e = ", ".join(f"{int(e):02d}" if str(e).isdigit() else str(e) for e, n in ends_d[:3]) or "—"
                n_h, n_g = wd_hits[d], wd_grad[d]
                pct = f"{100 * n_h / n_g:.0f}%" if n_g else "—"
                title = nfl_label.get(d, d) if active_sport() == "NFL" else d
                day_cards.append(
                    f'<div class="pa-day"><h4>{title}</h4>'
                    f'<div class="n" style="font-size:1.2rem;font-weight:800;color:#f9a8d4">{n_h} {bomb}s</div>'
                    f'<div class="p">Books: {top_b}</div>'
                    f'<div class="p">Ends: {top_e} · {pct} of graded</div></div>'
                )
            st.markdown(
                f'<div class="pa-card"><div class="pa-h">What cashed</div>'
                f'<div class="pa-sub">{"TNF / Sunday / MNF" if active_sport()=="NFL" else "Weekdays"} — books and endings, not raw volume</div>'
                f'<div class="pa-grid">{"".join(day_cards)}</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            picks = [
                (k, n) for k, n in names.most_common()
                if k and n >= 2 and not (active_sport() == "NFL" and is_nfl_qb(k))
            ]
            pick_rows = []
            for i, (pl, n) in enumerate(picks[:12]):
                pick_rows.append(bar_row(f"{pl} · {n} {bombs} this window", n, max((x[1] for x in picks), default=1), "", crown=(i == 0)))
            picks_html = "".join(pick_rows) if pick_rows else '<div class="pa-pct">None yet</div>'
            st.markdown(
                '<div class="pa-card"><div class="pa-h">Repeat Offenders</div>'
                f'<div class="pa-sub">One {bomb} per player per date. Duplicates dropped. NFL week-1: 2+ days, not 4 bombs in one game.</div>'
                + picks_html +
                '</div>',
                unsafe_allow_html=True,
            )
            st.markdown(section_html(
                "The Girl Magic Pantheon", "Petty Families - one family counted once per HIT",
                families.most_common(6), mx_f, None, p_fam,
            ), unsafe_allow_html=True)
            st.markdown(section_html(
                "Top methods", "Tag volume on HIT rows (a HR can wear more than one)",
                methods_c.most_common(10), mx_m, meth_g, p_meth,
            ), unsafe_allow_html=True)

        st.markdown("**Family x method crossover**")
        top_m = [m for m, _ in methods_c.most_common(6)]
        top_f = [f for f, _ in families.most_common(4)]
        if top_m and top_f:
            lines = []
            for fam in top_f:
                bits = [f"{m} {cross.get((fam, m), 0)}" for m in top_m if cross.get((fam, m), 0)]
                if bits:
                    lines.append(f"- **{fam}** — " + " · ".join(bits))
            st.markdown("\n".join(lines) if lines else "_No overlap yet_")
        else:
            st.caption("Need more graded HRs for the matrix.")

        if fade:
            st.markdown("**Fade list** (MISS rows that already wore a fade / lengthen tag)")
            st.write(", ".join(f"{k} ({n})" for k, n in fade.most_common(8)))

        recap_lines = [
            f"Girl Magic Petty Analytics · {today}",
            f"Slice: {focus_src} · {window}",
            f"HR {len(hits)} / graded {len(graded)} · rate {week_rate}",
            "Top endings: " + ", ".join(f"{k} {n}" for k, n in endings.most_common(5)),
            "Top books: " + ", ".join(f"{k} {n}" for k, n in books.most_common(5)),
            "Top buckets: " + ", ".join(f"{k} {n}" for k, n in buckets.most_common(5)),
            "Families: " + ", ".join(f"{k} {n}" for k, n in families.most_common(4)),
            "Methods: " + ", ".join(f"{k} {n}" for k, n in methods_c.most_common(6)),
            "Picks: " + ", ".join(f"{k} {n}" for k, n in picks[:8]),
            "If the odds look ugly, they probably lying.",
        ]
        st.download_button(
            "Export Petty Analytics Weekly Recap",
            "\n".join(recap_lines),
            file_name=f"petty_analytics_{today}.txt",
            mime="text/plain",
        )
        st.markdown(
            '<div class="pa-foot">Data graded by Girl Magic Odds - powered by petty intuition and math.</div>',
            unsafe_allow_html=True,
        )

    if page == "Numerology:":
        st.markdown("""
        <style>
        .num-ritual{background:linear-gradient(135deg,#3b0764 0%,#831843 55%,#1e1b4b 100%);border:1px solid #f472b6;border-radius:22px;padding:18px 20px;margin-bottom:12px;box-shadow:0 0 28px rgba(236,72,153,.25)}
        .num-ritual h3{font-family:'Playfair Display',serif;color:#fff;margin:0;font-size:1.55rem}
        .num-ritual .big{font-family:'Playfair Display',serif;font-size:4rem;line-height:1;color:#fbcfe8;text-shadow:0 0 18px #ec4899}
        .num-ritual p{color:#fce7f3;margin:6px 0 0;font-size:.9rem}
        .num-quote{color:#f9a8d4;font-style:italic;font-size:.82rem;margin-top:8px}
        .num-chip{display:inline-block;background:#2a1040;border:1px solid #e879f9;color:#fbcfe8;border-radius:999px;padding:3px 10px;margin:2px;font-size:.72rem;font-weight:700}
        .num-chip:hover{box-shadow:0 0 12px #f472b6}
        .num-hot{border-color:#fbbf24;color:#fde68a}
        </style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="queen-banner">🔮 Numerology · odds first</div>', unsafe_allow_html=True)
        cfg = sport_cfg()
        try:
            default_d = datetime.strptime(today_az(), "%Y-%m-%d").date()
        except Exception:
            default_d = datetime.now().date()
        cdate, csearch = st.columns([1, 2])
        with cdate:
            pick = st.date_input("Date", value=default_d, key="num_date")
        with csearch:
            q = st.text_input("Player", placeholder="search", key="num_search")
        day_n, raw_sum, formula, master = _num_date_number(pick)
        day_key = day_n  # already 1-9
        sport_line = "Kickoff number" if active_sport() == "NFL" else "First-pitch number"
        master_line = (
            f'<p style="color:#fde68a;font-size:.78rem;margin:4px 0 0">Master {master} stays as a footnote only. We use <b>{day_key}</b>.</p>'
            if master else ""
        )
        st.markdown(
            f'<div class="num-ritual"><div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">'
            f'<div class="big">{day_key}</div>'
            f'<div><h3>{sport_line}</h3>'
            f'<p>{formula} · {cfg["label"]}</p>'
            f'<p><b>{_NUM_SOFT.get(day_key, "")}</b></p>'
            f'{master_line}'
            f'<div class="num-quote">The number is the vibe. The price is the receipt. We don’t green a name just because the math is cute.</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        method_map = {}
        for item in (ev_board or []) + (watch_board or []) + (coverage_board or []):
            method_map[item.get("player")] = item.get("methods") or []
        odds_rows = st.session_state.get("odds") or []
        ndf = pd.DataFrame(odds_rows) if odds_rows else pd.DataFrame()

        plays = []
        if not ndf.empty and "player" in ndf.columns:
            for p, g in ndf.groupby("player"):
                nn = _num_name_number(p)
                try:
                    best = int(g["price"].max())
                except Exception:
                    best = None
                end = last_two(best) if best is not None else None
                end_n = _num_reduce(end, False) if end is not None else None
                meths = method_map.get(p) or []
                # infer method-ish from price if flags empty
                hooks = list(meths)
                if end == 10:
                    hooks.append("ends 10")
                if end in (0, 25, 50, 75):
                    hooks.append(f"classic {end:02d}")
                if end_n == day_key:
                    hooks.append(f"ending → {day_key}")
                if nn == day_key:
                    hooks.append(f"name → {day_key}")
                name_hit = nn == day_key
                price_hit = end_n == day_key
                method_hit = bool(meths)
                # only keep if odds hook exists
                if not (price_hit or method_hit or end in (0, 10, 25, 50, 75)):
                    if not q.strip():
                        continue
                why = []
                if name_hit and price_hit:
                    why.append(f"Name #{nn} and price {format_odds(best)} both reduce to today's {day_key}")
                elif name_hit and method_hit:
                    why.append(f"Name #{nn} matches today · tags: {', '.join(meths[:3])}")
                elif price_hit:
                    why.append(f"Price {format_odds(best)} ends {end:02d} → {end_n} = today")
                elif method_hit:
                    why.append("Method tag only — number is extra, not the reason")
                elif end in (0, 10, 25, 50, 75):
                    why.append(f"Classic book ending {end:02d} on {format_odds(best)}")
                else:
                    why.append("Search only")
                score = (3 if name_hit and price_hit else 0) + (2 if name_hit and method_hit else 0) + (2 if price_hit else 0) + (1 if method_hit else 0)
                plays.append({
                    "Player": p,
                    "Price": format_odds(best) if best is not None else "—",
                    "End": f"{end:02d}" if end is not None else "—",
                    "Name#": nn,
                    "End#": end_n,
                    "Tags": ", ".join(list(dict.fromkeys(hooks))[:4]),
                    "Why": why[0],
                    "_score": score,
                })
        if q.strip():
            plays = [r for r in plays if q.lower() in r["Player"].lower()]

        hot = [r for r in plays if r["_score"] >= 3]
        mid = [r for r in plays if r["_score"] == 2]
        st.markdown(
            f'<div class="petty-row">'
            f'<div class="petty-box"><div class="petty-num">{len(hot)}</div><div class="petty-label">NAME + PRICE</div></div>'
            f'<div class="petty-box"><div class="petty-num">{len(mid)}</div><div class="petty-label">ONE HOOK</div></div>'
            f'<div class="petty-box"><div class="petty-num">{len(plays)}</div><div class="petty-label">ON THIS LIST</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if HAS_NFL_MATH and active_sport() == "NFL":
            st.markdown(NFL_MATH_BLURB)
            st.markdown(
                '<span class="num-chip num-hot">00 / 10 / 20 / 25 / 50 / 70 / 75 / 90</span>'
                '<span class="num-chip">TD +115+ · sweet +150-450</span>'
                '<span class="num-chip">FD under MGM 25-80 only</span>'
                '<span class="num-chip">MGM signal · never the ticket</span>'
                '<span class="num-chip">Name+price is flavor</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="num-chip num-hot">10 / 25 / 50 / 75 / 90</span>'
                '<span class="num-chip">+400s +500s +600s</span>'
                '<span class="num-chip">DK 10 · MGM 25/50 · FD 600</span>'
                '<span class="num-chip">Benford boost</span>'
                '<span class="num-chip">Name+price boost</span>',
                unsafe_allow_html=True,
            )
        elite = [e for e in (ev_board or []) if e.get("is_bet")]
        if elite:
            st.markdown("#### Petty Picks 💋")
            st.caption("Already cleared TAKE. Number is the bow, not the reason.")
            pk = st.columns(min(3, len(elite[:3])))
            for i, item in enumerate(elite[:6]):
                with pk[i % len(pk)]:
                    st.markdown(
                        f'<div class="card bet"><div class="card-kicker">PETTY PICK</div>'
                        f'<div class="card-name">{item["player"]}</div>'
                        f'<div class="card-line"><b>{format_odds(item.get("best_price"))}</b> {book_label(item.get("best_book"))}</div>'
                        f'<div class="note">{item.get("num_tag") or ""}</div></div>',
                        unsafe_allow_html=True,
                    )

        view = st.radio("Show", ["Name + price", "Has a hook", "Search all hooks"], horizontal=True, key="num_view")
        if view == "Name + price":
            show = hot
        elif view == "Has a hook":
            show = hot + mid
        else:
            show = plays
        show = sorted(show, key=lambda x: (-x["_score"], x["Player"]))[:24]
        if not show:
            st.info("Fetch the slate. Cute math with no price is just a diary entry.")
        else:
            cols = st.columns(2)
            for i, r in enumerate(show):
                tag_bits = [t.strip() for t in str(r.get("Tags") or "").split(",") if t.strip()][:4]
                tags_html = "".join(f'<span class="tag tag-family">{t}</span>' for t in tag_bits)
                vibe = "NAME + PRICE" if r["_score"] >= 3 else "HOOK"
                meter = make_meter(min(5, max(1, r["_score"])), "high" if r["_score"] >= 3 else "mid")
                with cols[i % 2]:
                    st.markdown(
                        f'<div class="card">'
                        f'<div class="card-kicker">{vibe}</div>'
                        f'<span class="score-pill">#{r["Name#"]}</span>'
                        f'<div class="card-name">{r["Player"]}</div>'
                        f'<div class="card-line"><b>{r["Price"]}</b> · ends {r["End"]} → #{r["End#"]}</div>'
                        f'{meter}'
                        f'<div style="margin-top:6px">{tags_html}</div>'
                        f'<div class="card-foot">{r["Why"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            st.caption("Name# = letters. End# = last two of the price. Today’s number is flavor. TAKE IT still lives on the Board.")

    if page == "Code:":
        site_section_open(
            "📖 WORDS",
            "How We Run It",
            "Same language as the Glossary. Manifesto, not a manual. Recipes stay on the cards.",
        )
        st.markdown("""
        <style>
        .how-hero{background:linear-gradient(110deg,#db2777,#7c3aed,#4c1d95);background-size:180% 180%;animation:heroShimmer 14s ease-in-out infinite;border-radius:22px;padding:18px 20px;margin-bottom:12px;border:1px solid #f9a8d4}
        .how-hero h3{font-family:'Playfair Display',serif;color:#fff;margin:0;font-size:1.4rem}
        .how-hero p{color:#fce7f3;margin:6px 0 0;font-size:.88rem}
        .how-tier{color:#f9a8d4;font-size:.72rem;letter-spacing:1.4px;text-transform:uppercase;font-weight:800;margin:16px 0 8px}
        .how-box{background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:12px 14px;margin-bottom:10px;font-size:.86rem;line-height:1.5}
        .how-box b{color:#fbcfe8}
        </style>
        """, unsafe_allow_html=True)
        quotes = [
            "If the odds look ugly, they probably lying.",
            "Green is the list. Gray is not a personality test.",
            "We grade so tomorrow is smarter. Tonight stays petty.",
            "Shop is the price. Board is the name. Don't mix the assignment.",
            "First pitch hits, the chase ends.",
        ]
        try:
            q_i = datetime.strptime(today_az(), "%Y-%m-%d").timetuple().tm_yday % len(quotes)
        except Exception:
            q_i = 0
        st.markdown(
            '<div class="how-hero"><h3>Girl Magic — How We Run It</h3>'
            f'<p>Quote of the day: {quotes[q_i]}</p>'
            "<p>New here? Read the walkthrough under this box. Then open Glossary 2.0. You do not need our slang to use the math.</p></div>",
            unsafe_allow_html=True,
        )
        with st.expander("👋 How to use this site if you don’t know us", expanded=True):
            st.markdown(
                "1. **Fetch** the slate. Nothing moves until that happens.\n"
                "2. **Alignment** = data + odds in one card. Hover a word if you don’t know it. "
                "This is the scouting report. It is **not** the bet slip.\n"
                "3. **Run It** = the Board. Green names are the ticket list. Gray is homework. "
                "The number next to the name is the **Board score**, not Align.\n"
                "4. **Money Talks** = Shop. Which book to buy and whether the number is **mispriced** "
                "(too long vs the pack = value, too short = tax).\n"
                "5. **Need One** = 0.5 rush / catch / reception props. Separate from homers and TDs.\n"
                "6. **Receipts** = did yesterday’s greens actually go. This is how we adjust.\n"
                "7. **How We Roll** = this page. Glossary at the bottom. Search any word on a card.\n"
                "8. **Weekly loop** — Receipts grades every logged Take and Watch. Tracker splits hit rate by tag "
                "(DK 10, MGM groups, B365 over HardRock, Fanatics over pack, HardRock over pack). "
                "If a stamp is cold for a week, it stays support or we fade it. Nothing is set-and-forget.\n\n"
                "**Mispriced line:** the number is off the pack. Longer than the other books = they may be "
                "giving extra juice. Shorter than the pack = you’re paying a tax. We stamp those. "
                "Support stamps (B365 over HardRock / MGM, Fanatics or HardRock over the pack) are "
                "*look at it* energy. They do not green a ticket alone.\n\n"
                "MLB ticket = **0.5 HR only**. NFL Align ticket = **plus-money Anytime TD only**."
            )
        st.markdown(
            '<div class="how-box">'
            + (
                "We only play <b>Anytime TD</b> on this lane — one score, one vibe. "
                if active_sport() == "NFL"
                else "We only play <b>0.5 HR Over</b> — one homer, one vibe. "
            )
            + "Green names are gospel. Gray is homework. Eyes mean watch it, don’t force the ticket. "
            "Grade so tomorrow gets tighter — not so we guess tonight.</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="how-tier">🌀 Daily Flow</div>', unsafe_allow_html=True)
        with st.expander("💅 Morning run — load the slate, fetch the vibe, clear the list", expanded=True):
            st.markdown(
                "1. Sidebar → **Load games**. Don’t overthink it. Get the slate up.\n"
                "2. Pick today’s cards. Leave filler out. We don’t chase extras.\n"
                "3. **Fetch.** Only moment new odds and Lock snapshots save.\n"
                "4. Leave **Grab lineups on fetch** on so bench / DNP names don’t clog the Board.\n"
                "5. Read **green** first. Gray and eyes are not a dare."
            )
        with st.expander("💅 The Board — green, gray, eyes"):
            st.markdown(
                "- **Green / TAKE IT / run it, baddie** — cleared the list. We actually play this.\n"
                "- **Gray / PASS** — tags fired. Score hold didn’t land. Homework, not a ticket.\n"
                "- **Eyes / WATCH** — watch it, don’t force the ticket. Log it for grade.\n"
                "- **Queen cleared it** — same as green. Personality line, not a second scoring system.\n\n"
                "**Petty Score** ranks the stack. 85+ can **score hold** a green when Benford / numerology miss. It cannot invent a green.\n"
                "**Edge** = gap from the pack. Big edge with no **Priority** + 2 **Premium** is still gray.\n"
                "Petty Mode changes the words. It does not change the math."
            )
        with st.expander("💋 After the games — grade like grown women"):
            st.markdown(
                "- **Results** — logged TAKE / WATCH / Shop go PENDING → HIT or MISS. Undo exists.\n"
                "- **Log a HR** — someone went who wasn’t on the Board. Still log them.\n"
                "- **Auto-grade** reads box scores. Fix misses.\n"
                "- Don’t invent a new trick mid-slate. Tracker talks tomorrow."
            )

        st.markdown('<div class="how-tier">🧠 System Logic</div>', unsafe_allow_html=True)
        with st.expander("Tags fire methods. Methods unlock TAKE. Priority tags clear greens."):
            st.markdown(
                "- **Priority** — can unlock TAKE. You still need 2 Premium.\n"
                "- **Premium / Core** — counts toward the floor (DK 10, FD Rhythm, MGM 25, Multi-book Shorten, Caesars Stamp, HardRock Heater, Fanatics Rogue, EV Premium, Kelly Premium).\n"
                "- **Support** — Books Tight, Exact Match, MGM 50/00, Fanatics Drift. Shown. Never greens alone.\n"
                "- Family chips (Classic / Pressure / Drama / Cute) are vibe folders. Cute is never why you fire.\n"
                "- Exact recipes stay on the cards. This page is the map."
            )
        with st.expander("Shop vs Board — two different jobs"):
            st.markdown(
                "- **Board** = who cleared the list.\n"
                "- **Shop** = which book and number to buy (fair line + gap + EV / Kelly).\n"
                "- Long-ball Shop: TAKE gap ≥ 35, LEAN ≥ 25.\n"
                "- Same name can be green on the Board and DON’T in Shop. Don’t mix the assignment.\n"
                "- If Shop says DON’T, don’t talk yourself into it."
            )
        with st.expander("The other rooms"):
            st.markdown(
                "- **Digits / MGM / DK / FD** — pattern rooms. MGM groups same team only (25 / 50 / 75 / Exact).\n"
                "- **Names** — only if a book method also fired. Prefer different teams.\n"
                "- **Trend Lab** — Heating / Cooling / Chaotic. Does not change TAKE math.\n"
                "- **Moves** — 500+ only.\n"
                "- **Lock** — last pregame number before the book vanished."
            )
        with st.expander("Lock — names vanish after first pitch"):
            st.markdown(
                "Books pull numbers once it’s live. Fetch writes **Lock**.\n\n"
                "- **Open** first look · **Now** latest pregame · **Close** last number before vanish.\n"
                "First pitch hits, the chase ends."
            )
        with st.expander("Tracker, Backtest, Analytics — receipts only"):
            st.markdown(
                "- **Tracker** — hit rate by tag / book / ending. Ignore tiny n.\n"
                "- **Backtest** — TAKE should beat WATCH.\n"
                "- **Analytics / What’s Going Today** — what already went. Not tonight’s Board."
            )
        with st.expander("Books we actually use"):
            st.markdown(
                "- **Tickets:** DK, FD, HardRock, Fanatics, Caesars Stamp.\n"
                "- **MGM Signal** — grouping tell. Not the ticket.\n"
                "- Bet365 is wired when the feed sends it.\n"
                "- Other books compare only. They do not unlock TAKE."
            )

        st.markdown('<div class="how-tier">💋 Culture + Rules</div>', unsafe_allow_html=True)
        with st.expander("House rules — nobody gets cute"):
            st.markdown(
                "- Only **0.5 HR Over**. No 2+ . No unders. Rarely under +200. Long-ball is +500+.\n"
                "- Green is the list. Everything else is homework.\n"
                "- Two Premium + one Priority still beats one cute name match.\n"
                "- **Score hold** at 85. Queen commentary is mood, not math.\n"
                "- Secrets stay on the cards. This page is the map, not the vault."
            )
        st.markdown("#### Glossary 2.0")
        st.caption("This is the only glossary. Search it. Hover Align cards for the same words.")
        render_mini_glossary()
        site_section_close()

    st.markdown(
        '<div class="footer"><div class="footer-ticker">✨ Girl Magic Odds — fluent in chaos, powered by precision · '
        "💥 Hot Porch = bombs fly · 🔥 Live Air = ball carries · 🌬️ Neutral = average · 🧊 Cold Porch = balls die · "
        "Board picks the name · Shop picks the number · Grade keeps us honest ✨</div></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
