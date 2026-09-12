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
.quote-bar{background:#1a1024;border:1px solid #db2777;border-radius:14px;padding:8px 14px;margin:0 0 10px;color:#fbcfe8;font-size:.82rem;letter-spacing:.2px}
.site-hero{
  background:linear-gradient(110deg,#2a1040 0%,#6d28d9 38%,#db2777 72%,#4c1d95 100%);
  background-size:180% 180%;
  animation:heroShimmer 14s ease-in-out infinite;
  border:1px solid #f9a8d4;border-radius:28px;padding:26px 26px 20px;
  margin:0 0 16px;box-shadow:0 20px 48px rgba(76,29,149,.38);
}
@keyframes heroShimmer{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.site-hero-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.site-kicker{color:#f9a8d4;font-size:.68rem;font-weight:800;letter-spacing:2.4px;text-transform:uppercase;margin:0 0 6px}
.site-title{font-family:'Playfair Display',serif;font-size:2.25rem;line-height:1.05;color:#fff;margin:0 0 8px;text-shadow:0 6px 18px rgba(15,6,24,.45);animation:titleIn .6s ease-out}
.site-sub{color:#fce7f3;font-size:.98rem;margin:0 0 8px;max-width:720px;line-height:1.55;animation:fadeUp .7s ease-out .12s both}
.site-live{color:#f9a8d4;font-size:.78rem;margin:0 0 12px}
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
.card.site-card .card-meta{font-size:.78rem;color:#c4b5d6;margin-bottom:8px}
.price-row{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin:6px 0 4px}
.price-big{font-size:1.22rem;font-weight:800;color:#6ee7b7}
.price-book{font-size:.78rem;color:#e9d5ff}
.method-group{margin-top:8px;padding-top:8px;border-top:1px solid #2a2038}
.queen-line{color:#f9a8d4;font-style:italic;font-size:.78rem;margin-top:8px}
.tag-group-lab{color:#c4b5d6;font-size:.58rem;letter-spacing:1.2px;text-transform:uppercase;margin:8px 0 3px}
.motion-line{font-size:.72rem;font-weight:800;margin:6px 0;padding:4px 8px;border-radius:999px;display:inline-block;border:1px solid #64748b}
.card-hot{box-shadow:0 0 22px rgba(244,114,182,.4);animation:heatPulse 2.4s ease-in-out infinite}
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
}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SGO_BASE = "https://api.sportsgameodds.com/v2"
MLB_STATS = "https://statsapi.mlb.com/api/v1"
REGIONS = "us,us2"
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
        "sgo": False,
        "days": 8,
        "when": "Kickoff",
        "lock_caption": "NFL Lock Lab uses TD prices we saved pre-kick. No MLB homers on this side.",
        "lock_count": "NFL TD",
        "shop_empty": "Fetch Anytime TD first - Shop fills from the NFL slate.",
    },
}

def active_sport():
    s = st.session_state.get("sport", "MLB")
    return s if s in SPORT_CFG else "MLB"

def sport_cfg():
    return SPORT_CFG[active_sport()]

HISTORY_FILE = "girl_magic_history.json"
RESULTS_FILE = "girl_magic_results.json"
PREGAME_FILE = "girl_magic_pregame.json"
HISTORY_MAX_AGE_HOURS = 18
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"
PREFERRED = {"fanduel", "draftkings", "betmgm", "hardrockbet", "caesars", "fanatics"}
CORE_BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings", "betmgm": "BetMGM", "fanatics": "Fanatics"}
# Ticket = book we buy. MGM is signal-only (11% as ticket vs 13% baseline).
TICKET_BOOKS = {"draftkings", "fanduel", "hardrockbet", "fanatics"}
VALUE_BOOKS = {"draftkings", "fanduel", "hardrockbet", "fanatics"}
VALUE_BOOK_LABELS = {"DK", "FD", "HardRock", "Fanatics"}
SIGNAL_ONLY_BOOKS = {"betmgm"}
# Odds API uses different keys for the same books - map only
BOOK_ALIASES = {
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
    if "bet365" in k or k in ("365", "b365"):
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
SCORE_SOFT_TAKE = 70      # petty score hold: keep TAKE if 70+ even when Benford/Num miss

# PRIORITY = must have >=1 to unlock TAKE IT
# Tracker 9/10: MGM-as-ticket 11% (−1). MGM 50 book×ending 7% (−5). MGM 00 8%.
# Keep MGM 25 / Exact / FD / DK as unlocks. 50s and 00s are tags only.
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
}
FD_ENDINGS = (10, 20, 30, 60, 70, 90)
MGM_ENDINGS = (0, 25, 50, 75)

def is_core_method(m):
    """Premium only - support/noise do not inflate core_count."""
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
    """NFL Anytime TD: +115 and up. No 799 cap — long TDs have hit."""
    try:
        p = abs(int(best_price))
    except Exception:
        return False
    return p >= 115

def qualifies_take_it(core_count, methods, edge=0, best_price=None, book_prices=None, best_book=None, score=0):
    """MLB: elite +400-699 + hot end + priority. NFL: 2 premium + priority-or-hot-end on TD prices.
    Petty score ≥ 70 can also clear when edge is only EDGE_SOFT (still needs 2 premium + priority)."""
    ms = {normalize_method_name(m) for m in (methods or [])}
    if core_count < METHODS_MIN:
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
    if bk and bk not in TAKE_STRONG_BOOKS:
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
        # same idea as MLB: 2 premium + (priority OR hot ending OR fat petty score)
        return pri or hot or sc >= SCORE_SOFT_TAKE
    if not pri and sc < SCORE_SOFT_TAKE:
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
        (core >= METHODS_MIN, f"2+ premium methods ({core})"),
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
    return (
        f'<div class="quote-bar">Quote of the day: {daily_quote()}</div>'
        '<div class="site-hero"><div class="site-hero-top"><div>'
        '<p class="site-kicker">You’re entering Girl Magic Odds — pick your lane</p>'
        '<div class="site-title">Girl Magic Odds</div>'
        '<p class="site-sub">Where intuition meets petty precision.<br>'
        'We only play 0.5 HR Over — because chaos pays better.<br>'
        'Green names are gospel. Everything else? Homework.</p>'
        f'<p class="site-live">Last fetch {live} — {breathe}.</p>'
        '<div class="site-chips">'
        f'<span class="site-chip sport">{sport}</span>'
        f'<span class="site-chip">{slate_label}</span>'
        f'<span class="site-chip">{games_n} games loaded</span>'
        f'<span class="site-chip">Lock {lock_n}</span>'
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
    ("💖", "score hold", "Petty Score 70+. Keeps a green when Benford or numerology miss. Never invents one."),
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


def render_mini_glossary():
    st.markdown("### 💅 Girl Magic Glossary")
    st.markdown("**Shhh. This is the language.**")
    st.caption("You weren’t supposed to see this, but since you’re here — learn it, use it, don’t talk too loud about it.")
    st.markdown("Welcome to the language of the Board — the slang, the signals, the chaos, the math, and the petty. If you can speak this, you can roll with us.")
    st.markdown("**🔖 Tags**")
    st.markdown(
        "- **FD Pattern** — FanDuel’s rhythm. +400 or higher ending 10/20/30/60/70/90.\n"
        "- **FD 90 / 50 / 40** — those exact FD endings. Don’t ask why, just know they hit.\n"
        "- **MGM 25** — BetMGM same-team group ending 25.\n"
        "- **MGM Exact** — same MGM price, same team.\n"
        "- **DK 10** — DraftKings ends in 10.\n"
        "- **Multi-book Shorten** — price dropped on 2+ books. Somebody knows something.\n"
        "- **Books Tight** — ticket books within 50 points. That’s pressure.\n"
        "- **Caesars Classic / HardRock Heater / Fanatics Rogue** — the long ticket on a hot ending. If you see it, you didn’t hear it from me."
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
    """0-100 stack score. Feeds TAKE IT (70+ can hold a green)."""
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
    alerts = []
    for r in results or []:
        meths = r.get("methods") or []
        if r.get("type") == "mgm_exact" or "MGM Exact" in meths:
            alerts.append(f"MGM Exact · {r.get('label')}")
        if "Multi-book Shorten" in meths:
            alerts.append(f"Multi-book Shorten · {r.get('label')}")
        reason = str(r.get("reason") or "")
        if "FD under MGM" in meths and ("by 1" in reason or "100" in reason):
            try:
                # only shout 100+
                if "by 1" in reason or "by 10" in reason or "by 11" in reason or "by 12" in reason:
                    pass
            except Exception:
                pass
            import re as _re
            m = _re.search(r"by (\d+)", reason)
            if m and int(m.group(1)) >= 100:
                alerts.append(f"FD under MGM by {m.group(1)} · {r.get('label')}")
    for item in ev_board or []:
        ms = set(item.get("methods") or [])
        if "DK 10" in ms and ("FD Pattern" in ms or "FD 600" in ms):
            alerts.append(f"DK 10 + FD Pattern · {item.get('player')}")
        bf = item.get("benford") or {}
        if str(bf.get("tag", "")).lower() == "fake":
            alerts.append(f"Benford Fake · {item.get('player')}")
        books = item.get("book_prices") or {}
        fd, mgm = books.get("fanduel"), books.get("betmgm")
        if fd is not None and mgm is not None and int(mgm) - int(fd) >= 100:
            alerts.append(f"FD under MGM by {int(mgm) - int(fd)} · {item.get('player')}")
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
SHOP_GAP_TAKE_LONG = 35
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
        vtags = value_method_tags(ev, kelly_f)
        if klabel == "SKIP" and action == "TAKE" and (kelly_f is None or kelly_f <= 0):
            action, why, cls = "LEAN", why + " · Kelly skip (thin edge)", "shop-lean"
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
            "kelly_u": ku, "kelly_label": klabel, "kelly_full": kfull,
        })
    rows.sort(key=lambda x: (-x.get("edge", 0), x.get("player") or ""))
    return rows


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


def trend_chip_html(item):
    css = item.get("trend_motion_css") or "motion-stable"
    icon = item.get("trend_motion_icon") or "🧊"
    return (
        f'<div class="trend-line">'
        f'<span class="trend-chip {css}">{icon} {item.get("trend_motion") or "Stable"}</span>'
        f'<div class="trend-mean">{item.get("trend_motion_meaning") or ""}</div>'
        f'<span class="trend-meta">{item.get("trend_motion_detail") or ""}</span>'
        f'<div class="trend-meta">Method · {item.get("trend_method")}</div>'
        f'<div class="trend-meta">Ending · {item.get("trend_ending")} · Bucket · {item.get("trend_bucket")}</div>'
        f'<div class="trend-meta">Team · {item.get("trend_team")} · Book · {item.get("trend_book")}</div>'
        "</div>"
    )


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
        "Green means best ticket. Red means short vs fair. Everything else is homework."
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
        book_f = st.selectbox("Best book", book_opts, key="shop_best_book", help="Ticket we would actually buy.")
    with c2:
        has_f = st.selectbox("Has book", book_opts, key="shop_has_book", help="Must have this book posted.")
    ends = sorted({f"{int(r['ending']):02d}" for r in shop if r.get("ending") is not None})
    with c3:
        end_f = st.multiselect("Best ends in", ends, key="shop_ends", help="Last two of the ticket.")
    st.caption("💸 Math")
    c4, c5, c6 = st.columns(3)
    with c4:
        min_gap = st.slider("Min gap vs fair", 0, 300, 0, 10, key="shop_min_gap", help="Best minus fair line.")
    with c5:
        min_books = st.selectbox("Min books posted", [1, 2, 3, 4, 5], index=0, key="shop_min_books")
    buckets = sorted({r.get("bucket") for r in shop if r.get("bucket")})
    with c6:
        buck_f = st.multiselect("Price bucket", buckets, key="shop_buckets")
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
    with st.expander("Long-ball math sample — fair / gap / EV / Kelly / call", expanded=False):
        take_n = sum(1 for r in shop if r.get("action") == "TAKE")
        lean_n = sum(1 for r in shop if r.get("action") == "LEAN")
        long_n = sum(1 for r in shop if abs(int(r.get("best") or 0)) >= 500)
        st.caption(
            f"{take_n} TAKE · {lean_n} LEAN · {long_n} at +500+. "
            "Fair = weighted books + cushion (or avg+15). Gap = best − fair. "
            "Long-ball TAKE gap ≥ 35, LEAN ≥ 25."
        )
        lines = []
        for r in shop[:80]:
            ev = r.get("ev")
            kf = r.get("kelly_frac")
            ev_s = f"{ev:+.3f}" if ev is not None else "—"
            k_s = f"{kf:+.3f}" if kf is not None else "—"
            tags = ", ".join(r.get("value_tags") or [])
            reasons = shop_block_reasons(r)
            lines.append(
                f"- **{r.get('player')}** · best {format_odds(r.get('best'))} {book_label(r.get('best_book'))} "
                f"· fair {format_odds(r.get('fair'))} ({r.get('fair_mode')}) · gap **{int(r.get('edge') or 0):+d}** "
                f"· EV {ev_s} · Kelly {k_s} · {tags} · **{r.get('action')}** · {'; '.join(reasons[:4])}"
            )
        st.markdown("\n".join(lines) if lines else "_No shop rows._")
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
        call_txt = petty_label(act)
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
            f'<td>{r.get("kelly_label") or "—"}</td>'
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
        f'<div class="card-meta">{n} numbers in this pile. Green = cash pond. Red = fade.</div>'
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


def lookat_box(title, body):
    st.markdown(
        f'<div class="how-box"><b>{title}</b><div class="note" style="margin-top:6px">{body}</div></div>',
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
        "Score closer to 1.0 = natural energy. Closer to 0.0 = forced numbers. "
        "Use Benford to confirm the pond before you buy the ticket. Board still picks the name.",
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
        f'<div class="note">{live_res.get("n") or 0} live prices in the pile</div></div>',
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
        "Book Piles show which sportsbooks are giving clean, natural long-ball numbers today. "
        "Look for green in +400–+600. Avoid red in +1000+.",
    )
    st.markdown("#### Benford vs Board")
    c1, c2 = st.columns(2)
    with c1:
        _benford_card(live_res, "Live board prices")
    with c2:
        _benford_card(hits_res, "History hits")
    lookat_box(
        "🧠 More Piles — is today normal or weird?",
        "Today = live vibe. Lock = pregame truth. History = what actually hits. "
        "If Today and History agree, the pond is clean. If Lock disagrees, the book tried to fake it.",
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
        "The Board picks the name. The Book Piles pick the pond. Benford picks the energy. "
        "All three agree → TAKE. Two agree → LEAN. One agrees → WATCH. None → DON’T. "
        "When all three agree, run it.",
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
    if b in ("untagged", "unknown", "-", ""): return "Untagged"
    return b.title() if b else "Untagged"

def fold_name(name):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


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

def _strip_game_clock(s):
    """'Away @ Home · 10:36 AM' -> 'Away @ Home' so fetch filter doesn't drop games."""
    s = str(s or "").strip()
    if " · " in s:
        left, right = s.rsplit(" · ", 1)
        if any(ch.isdigit() for ch in right) and ("am" in right.lower() or "pm" in right.lower() or ":" in right):
            return left.strip()
    return s


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
def fetch_nfl_td_scorers():
    """Anytime TD scorers from ESPN public scoreboard + game summary. No extra paid API."""
    scorers, finished = set(), set()
    try:
        day = datetime.strptime(today_az(), "%Y-%m-%d").strftime("%Y%m%d")
    except Exception:
        day = datetime.now().strftime("%Y%m%d")
    try:
        sb = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
            params={"dates": day}, timeout=15,
        ).json()
    except Exception as e:
        return set(), set(), f"ESPN scoreboard fail: {e}"
    events = sb.get("events") or []
    done_ids = []
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0]
        status = ((comp.get("status") or {}).get("type") or {})
        eid = ev.get("id")
        if status.get("completed") or str(status.get("name") or "").upper() in ("STATUS_FINAL", "STATUS_FINAL_OVERTIME"):
            if eid:
                done_ids.append(str(eid))
    for eid in done_ids[:20]:
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
            for ath in play.get("athletesInvolved") or []:
                n = ath.get("displayName") or ath.get("fullName")
                if n:
                    scorers.add(clean_name(n))
            # passing TD: first athlete is often the passer — still an anytime scorer only if they crossed
            # boxscore rushing/receiving TDs are cleaner
        box = ((sm.get("boxscore") or {}).get("players") or [])
        for team_block in box:
            for stat_group in team_block.get("statistics") or []:
                name = str(stat_group.get("name") or stat_group.get("label") or "").lower()
                keys = [str(k).lower() for k in (stat_group.get("labels") or stat_group.get("names") or [])]
                td_idx = None
                for i, k in enumerate(keys):
                    if k in ("td", "tds", "touchdowns"):
                        td_idx = i
                        break
                if td_idx is None and "rush" not in name and "receiv" not in name and "return" not in name:
                    continue
                for ath in stat_group.get("athletes") or []:
                    n = (ath.get("athlete") or {}).get("displayName")
                    if n:
                        finished.add(clean_name(n))
                    stats = ath.get("stats") or []
                    if td_idx is not None and td_idx < len(stats):
                        try:
                            if float(stats[td_idx]) >= 1:
                                if n:
                                    scorers.add(clean_name(n))
                        except Exception:
                            pass
    return scorers, finished, f"ESPN NFL {len(done_ids)} final · {len(scorers)} TD names"


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
            blob = str(row.get("market") or row.get("sport") or "").lower()
            if blob and "td" not in blob and "nfl" not in blob:
                skipped += 1
                continue
        elif str(row.get("market") or "") == "anytime_td":
            skipped += 1
            continue
        player = row.get("player") or ""
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


def build_whats_going_today(rows):
    """Today's MLB HRs + ending/book from grades or Lock (best among DK/FD/MGM/HardRock).
    Not the same as MGM pair methods - those stay pair/trio-only on the Board.
    """
    today = today_az()
    if active_sport() == "NFL":
        hr_names, _final, _msg = [], False, "NFL mode · MLB homers off"
    else:
        hr_names, _final, _msg = fetch_mlb_hr_hitters()

    todays = [r for r in rows if r.get("date") == today]
    if active_sport() == "NFL":
        def _is_nfl_row(r):
            m = str(r.get("market") or r.get("sport") or "").lower()
            return "td" in m or "nfl" in m or m == "anytime_td"
        hits_logged = [r for r in todays if r.get("result") == "HIT" and _is_nfl_row(r)]
        graded = [r for r in todays if r.get("result") in ("HIT", "MISS") and _is_nfl_row(r)]
        our_list = [r for r in todays if r.get("source") in ("take_it", "watch") and _is_nfl_row(r)]
    else:
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
    if active_sport() == "NFL":
        pair_list = []
        mlb_hr = 0
        on_list = 0
        hit_ends = Counter()
        for r in rows:
            blob = str(r.get("market") or r.get("sport") or "").lower()
            if r.get("date") != today_az():
                continue
            if "td" not in blob and "nfl" not in blob:
                continue
            if r.get("source") in ("take_it", "watch"):
                on_list += 1
            if r.get("result") != "HIT":
                continue
            mlb_hr += 1
            bl = book_label(r.get("best_book") or "")
            end = r.get("ending")
            if end is None:
                end = last_two(r.get("best_price"))
            if bl and end is not None:
                hit_ends[(bl, int(end))] += 1
        by_book = defaultdict(list)
        for (bl, end), cnt in hit_ends.items():
            by_book[bl].append((int(end), int(cnt)))
        for bl in by_book:
            by_book[bl].sort(key=lambda x: (-x[1], x[0]))
        by_book = dict(by_book)
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
        empty_msg = "No NFL TDs graded yet. Mark HIT on Results and this banner fills." if active_sport() == "NFL" else "No endings matched yet"
        body = '<div style="font-size:0.78rem;opacity:0.85;margin-top:4px">%s</div>' % empty_msg

    pair_note = ""
    if pair_list:
        bits = ["%02d:%s" % (e, c) for e, c in pair_list[:5]]
        pair_note = (
            '<div style="margin-top:8px;font-size:0.72rem;color:#fcd34d">'
            'MGM pair/trio only (method): %s'
            '</div>' % (" · ".join(bits))
        )

    cfg = sport_cfg()
    title = "What's Going Today · %s" % active_sport()
    if active_sport() == "NFL":
        sub = "%s %s scored today · %s were on our list · chips = graded TDs only" % (mlb_hr, cfg["hits"], on_list)
    else:
        sub = (
            "%s %s · %s on our list · best price among DK/FD/MGM/HardRock "
            "(not MGM pair rules)"
        ) % (mlb_hr, cfg["hits"], on_list)
    html = (
        '<div class="trends-today" style="padding:12px 14px">'
        '<div class="trends-today-header" style="margin-bottom:4px">'
        '<div class="trends-today-title">%s</div>'
        '<div class="trends-today-sub">%s</div>'
        '</div>%s%s</div>'
    ) % (title, sub, body, pair_note)
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

@st.cache_data(ttl=180, show_spinner=False)
def _fetch_events_oddsapi_cached(api_key, sport_key="baseball_mlb"):
    r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_events_oddsapi(api_key, sport_key=None):
    sport_key = sport_key or sport_cfg()["key"]
    try:
        return _fetch_events_oddsapi_cached(api_key, sport_key)
    except Exception as e:
        st.error(f"Odds API events error: {e}")
        return []

def fetch_odds_oddsapi(api_key, event_id, sport_key=None, market=None):
    cfg = sport_cfg()
    sport_key = sport_key or cfg["key"]
    market = market or cfg["market"]
    # Fanatics is region=us, key=fanatics (paid). Ask for it by name too.
    # Alternate HR market is still filtered to Over 0.5 in flatten.
    markets = market
    if market == "batter_home_runs":
        markets = "batter_home_runs,batter_home_runs_alternate"
    books = ",".join([
        "fanduel", "draftkings", "betmgm", "fanatics",
        "hardrockbet", "hardrockbet_az", "hardrockbet_oh", "hardrockbet_fl",
        "caesars", "williamhill_us",
    ])
    try:
        r = requests.get(
            f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
            params={
                "apiKey": api_key,
                "regions": REGIONS,
                "markets": markets,
                "oddsFormat": "american",
                "bookmakers": books,
            },
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
            if mkey and not is_hr and not is_td:
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
                if price > MAX_HR_AMERICAN:
                    continue
                if is_td and abs(int(price)) < 115:
                    continue
                if is_blocked_player(player):
                    continue
                rows.append({"event": event, "book": bk, "player": player, "price": price, "point": 0.5, "team": "", "source": "oddsapi", "sport": "NFL" if is_td else "MLB"})
    return rows, found

def fetch_sgo_hr_props(sgo_key):
    rows, found = [], set()
    try:
        cursor = None
        pages = 0
        while pages < 6:
            pages += 1
            params = {"apiKey": sgo_key, "leagueID": "MLB", "oddsAvailable": "true", "limit": 50}
            if cursor:
                params["cursor"] = cursor
            r = requests.get(f"{SGO_BASE}/events", params=params, timeout=25)
            if r.status_code != 200:
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
                        try:
                            price = int(str(price).replace("+", ""))
                        except Exception:
                            continue
                        if price > MAX_HR_AMERICAN:
                            continue
                        if is_blocked_player(pname):
                            continue
                        found.add(b)
                        rows.append({"event": event_name, "book": b, "player": pname, "price": price, "point": 0.5, "team": team, "source": "sgo"})
            cursor = payload.get("nextCursor") or payload.get("next_cursor")
            if not cursor:
                break
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
    sgo_rows, sgo_found = [], set()
    if sport_cfg().get("sgo"):
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

        if best_b == "fanatics" and pack and best_p - pack_hi >= 40 and abs(best_p) >= 500:
            if end in TAKE_HOT_ENDS or end in (10, 60):
                _add("Fanatics Rogue", f"Fanatics longest by {best_p - pack_hi} at {format_odds(best_p)}")
            else:
                _add("Fanatics Drift", f"Fanatics off cluster by {best_p - pack_hi}")
        elif best_b == "fanatics" and pack and pack_hi - best_p >= 40:
            _add("Fanatics Drift", "Fanatics short vs ticket pack")
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
        if lineup_names and len(lineup_names) >= 40 and name_in_lineup(player, lineup_names) is False: continue
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
            "method_count": core_count, "team": team_map.get(player, ""),
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
        # PASS / TAKE IT pool: 2+ PREMIUM core (support tags do not count)
        if core_count < METHODS_MIN:
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
        if count_core_methods(ms) >= NAME_METHODS_MIN and _has_strong(ms)
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
    """Keep today's slate in AZ/ET, plus already-started cards still on the feed."""
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
    # already underway / just finished still counts as today's card
    if dt <= now + timedelta(hours=6) and dt >= now - timedelta(hours=8):
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
        hr_names = _todays_nfl_td_names()
        mlb_msg = (
            f"{len(hr_names)} graded NFL TD HIT(s) today. "
            "Mark HIT on Results so Lock Lab can match pre-kick prices."
            if hr_names else
            "No graded NFL TDs yet. Grade HIT on Results (or Log a TD) — Lock already has pre-kick prices."
        )
    else:
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
    _lock_n = len(st.session_state.get("pregame_lock") or {})
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
    st.markdown(
        '<div class="how-to site-guide"><b>How to use this site:</b> '
        'Load games in the sidebar, then Fetch. '
        'Board = who is cleared. Shop = which number to buy. '
        'Grade after the games so tomorrow is smarter. '
        'Pink words are personality. Green cards are the decision.</div>',
        unsafe_allow_html=True,
    )
    if "onboard_step" not in st.session_state:
        st.session_state["onboard_step"] = "welcome"
    step = st.session_state.get("onboard_step") or "welcome"
    if step == "welcome":
        st.info("Girl Magic Odds speaks its own language. Learn the code, then roll the slate.")
        st.caption("Before you roll, read the Glossary — it explains the tags, methods, and phrases you’ll see everywhere.")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("💅 Glossary First", type="primary", use_container_width=True):
                st.session_state["onboard_step"] = "glossary"
                st.rerun()
        with b2:
            if st.button("🎲 I already know the vibe", use_container_width=True):
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
        st.markdown('<div class="petty-banner">💅 Petty Mode ON — words get louder. Math does not change.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="petty-off-banner">Plain labels on. Same Board rules.</div>', unsafe_allow_html=True)
    st.markdown("""
    <style>
    .tag-family{background:#2a1040;color:#f9a8d4;border-color:#e879f9}
    .alert-strip{background:#3b0764;border:1px solid #f472b6;border-radius:12px;padding:8px 12px;margin:8px 0 12px;font-size:.82rem}
    .petty-note{color:#e9d5ff;font-size:.72rem;margin-top:3px}
    </style>
    """, unsafe_allow_html=True)
    lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
    _ag = f"auto_grade_ran_{active_sport()}"
    if not st.session_state.get(_ag):
        try:
            pending_n = sum(1 for r in load_results() if r.get("result") == "PENDING")
            if pending_n:
                with st.spinner(f"Auto-grading {pending_n} pending..."):
                    h, m, s, msg = auto_grade_pending()
                st.session_state[_ag] = True
                if h or m:
                    st.caption(f"⚡ Auto-grade: {h} HIT · {m} MISS · {s} still open")
            else:
                st.session_state[_ag] = True
        except Exception:
            st.session_state[_ag] = True
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

        default_sel = [x for x in st.session_state.get("selected_games", []) if x in options]
        raw_n = st.session_state.get("events_raw_count") or len(events)
        st.caption(f"Showing {len(events)} today · API listed {raw_n}")
        chosen = st.multiselect(
            "Games",
            list(options.keys()),
            default=default_sel,
        )
        s1, s2 = st.columns(2)
        with s1:
            if st.button("Select all", use_container_width=True):
                st.session_state["selected_games"] = list(options.keys())
                st.rerun()
        with s2:
            if st.button("Clear", use_container_width=True):
                st.session_state["selected_games"] = []
                st.rerun()
        st.session_state["selected_games"] = chosen
        manual_fetch = st.button("Fetch", type="primary", use_container_width=True)
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
    prev_df = pd.DataFrame(prev) if prev else None
    selected_events = st.session_state.get("last_selected") or chosen or []
    new_fetch = st.session_state.pop("new_fetch", False)
    results, ev_board, fallen, watch_board, coverage_board = (
        run_flags(df, prev_df, record_history=new_fetch, selected_events=selected_events)
        if not df.empty else ([], [], [], [], [])
    )
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
            # Same for MLB + NFL: Benford/Num boost the score, they do not kill a green.
            # Score < 50 with no elite confirm gets leaned off. 70+ holds.
            if item.get("is_bet") and not elite_take_ok(item) and sc < 50:
                item["is_bet"] = False
                item["why"] = (item.get("why") or "") + " · LEAN — score too thin without Benford/Num"
            elif item.get("is_bet") and sc >= SCORE_SOFT_TAKE and not elite_take_ok(item):
                item["why"] = (item.get("why") or "") + " · petty score hold"
    if ev_board or watch_board:
        log_bet_this(ev_board, watch_board)
    if not df.empty:
        log_shop_calls(df)
    method_stats, book_stats, ending_stats, bucket_stats, number_stats, book_end_stats, score_stats = build_tracker_stats(load_results())
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
    team_picks = apply_team_picks(ev_board, watch_only, coverage_only)
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
    MAIN_TABS = ["Board", "Shop", "Trend Lab", "Digits", "Methods", "Lines", "Grade", "Analytics", "Numerology", "Code"]
    NAV_LABELS = {
        "Board": "Board 💋",
        "Shop": "Shop 🛍️",
        "Trend Lab": "Trend Lab 📈",
        "Digits": "Benford Energy 🔢",
        "Methods": "Pattern Lab 🧩",
        "Lines": "Motion 💸",
        "Grade": "Grade 🧾",
        "Analytics": "Heat 🔥",
        "Numerology": "Magic Math 🔮",
        "Code": "How We Run It",
        "DK": "DK 🎯", "MGM": "MGM 🎰", "FD": "FD 💙", "Exact": "Exact 🎯",
        "Names": "Names 💅", "Signals": "Signals 📡",
        "Moves": "Moves 💸", "Trends": "Trends 💅", "Late": "Ghosts 👻",
        "Lock": "Lock 🔒", "Search": "Search",
        "Lock Lab": "Lock Lab", "Tracker": "Tracker", "Results": "Results",
        "Backtest": "Backtest",
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
    if main == "Methods":
        sub = st.radio("Methods", ["DK", "MGM", "FD", "Exact", "Names", "Signals"], horizontal=True, label_visibility="collapsed", key="sub_methods", format_func=lambda x: NAV_LABELS.get(x, x))
    elif main == "Lines":
        sub = st.radio("Lines", ["Moves", "Trends", "Late", "Lock", "Search"], horizontal=True, label_visibility="collapsed", key="sub_lines", format_func=lambda x: NAV_LABELS.get(x, x))
    elif main == "Grade":
        sub = st.radio("Grade", ["Lock Lab", "Tracker", "Results", "Backtest", "Shop"], horizontal=True, label_visibility="collapsed", key="sub_grade", format_func=lambda x: NAV_LABELS.get(x, x))
    page = f"{main}:{sub or ''}"
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
                "- 💅 Hover a pink or green tag if you need the language. Otherwise trust the math."
            )
        elite = [e for e in ev_board if e.get("is_bet")]
        if elite:
            st.markdown("#### Petty Picks")
            st.caption("Elite TAKE only — ending + bucket + method + book + Authentic + name+price.")
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
                ["TAKE IT", "TEAM PICK", "PASS", "WATCH"],
                default=["TAKE IT", "TEAM PICK"],
                key="board_kinds_main",
                help="TAKE IT — cleared play list. TEAM PICK — squad energy only.",
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
            st.session_state["board_kinds_main"] = ["TAKE IT", "TEAM PICK"]
            st.session_state["board_min_score_main"] = 0
            st.session_state["board_sort_main"] = sport_cfg()["when"]
            st.session_state["board_when_main"] = "All times"
            st.session_state["board_name_main"] = ""
            for k in ("qf_hot", "qf_long", "qf_petty85", "qf_cool", "qf_chaos"):
                st.session_state[k] = False
            st.rerun()
        st.caption("If it disappeared, it wasn’t meant for you.")
        st.markdown("</div>", unsafe_allow_html=True)

        def _render_board_card(item, label, cls):
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
            ck = f"{item.get('player')}_{label}_{str(item.get('event') or '')[:18]}"
            with st.expander("Explain this card", expanded=False, key=f"ex_{ck}"):
                st.write(explain_card_text(item, label))
            if queen:
                try:
                    with st.popover("What Queen means"):
                        render_queen_glossary()
                        st.caption(queen)
                except Exception:
                    with st.expander("What Queen means", expanded=False):
                        render_queen_glossary()
                        st.caption(queen)

        elite = [e for e in ev_board if e.get("is_bet")]
        st.markdown("#### Petty Picks")
        if elite:
            st.caption("Elite TAKE — ending + lane + method + book + Benford + name+price.")
            pc = st.columns(min(3, len(elite)))
            for i, item in enumerate(elite[:6]):
                with pc[i % len(pc)]:
                    _render_board_card(item, "TAKE IT", "bet")
        else:
            st.caption("Nobody cleared every accuracy gate today." if active_sport() != "NFL" else "NFL lane is open — if this is still empty, fetch Anytime TD again.")

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
            st.info("Fetch while pregame - board fills when methods fire.")
        else:
            st.markdown('<div class="board-wrap"><h3 class="game-head">Cleared names</h3></div>', unsafe_allow_html=True)
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
                if time_win == "All times":
                    return True
                t = _resolve_commence(game_name)
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
                    st.caption("On the slate · no TAKE IT or team pick yet.")

            if passes and "PASS" in show_kinds:
                shown_p = [x for x in passes if _keep_card(x)]
                st.markdown('<div class="board-wrap"><h3 class="game-head">Pass</h3></div>', unsafe_allow_html=True)
                if not shown_p:
                    st.caption("No PASS names match the filters.")
                else:
                    cols = st.columns(2)
                    for idx, item in enumerate(shown_p):
                        with cols[idx % 2]:
                            _render_board_card(item, "PASS", "skip")

            if "WATCH" in show_kinds:
                st.markdown('<div class="board-wrap"><h3 class="game-head">Watch</h3></div>', unsafe_allow_html=True)
                shown_w = [x for x in watches if _keep_card(x)]
                if not shown_w:
                    st.caption("No WATCH names match the filters.")
                else:
                    cols = st.columns(2)
                    for idx, item in enumerate(shown_w[:40]):
                        with cols[idx % 2]:
                            _render_board_card(item, "WATCH", "watch-card")

            st.markdown('<div class="board-wrap"><h3 class="game-head">Coverage · support tags only</h3></div>', unsafe_allow_html=True)
            st.caption(
                "75s · 00s · Stayed alone · Last one left · Exact / tight - "
                "support tags only. Never upgrades to TAKE IT without priority + edge."
            )
            if not coverage_only:
                st.caption("No support-only names right now.")
            else:
                cols = st.columns(2)
                for idx, item in enumerate(coverage_only[:40]):
                    with cols[idx % 2]:
                        _render_board_card(item, "COVERAGE", "watch-card")
            with st.expander("Board diagnostic (is_bet / score / methods) — math not changed", expanded=False):
                lines = []
                for item in (ev_board or [])[:80]:
                    lines.append(
                        f"- {item.get('player')} · is_bet={item.get('is_bet')} · "
                        f"score={item.get('score')} · edge={item.get('edge')} · "
                        f"best={format_odds(item.get('best_price'))} {book_label(item.get('best_book'))} · "
                        f"methods={item.get('methods')}"
                    )
                st.markdown("\n".join(lines) if lines else "_No Board rows. Fetch first._")
                st.caption(
                    f"TAKE count={sum(1 for x in (ev_board or []) if x.get('is_bet'))} · "
                    f"PASS={sum(1 for x in (ev_board or []) if not x.get('is_bet'))} · "
                    f"WATCH pool={len(watch_board or [])}"
                )
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
        st.caption(
            "Open = first pull (never changes) · Now = latest pregame fetch · "
            "Close = frozen when the book drops off the feed (often at first pitch)."
        )
        lock = st.session_state.get("pregame_lock") or load_pregame()
        if not lock:
            st.info("Fetch pregame to build lock.")
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
            "Hit rates after we grade. Small samples stay hidden. This is yesterday talking — not tonight’s Board.",
        )
        st.markdown('<div class="queen-banner">📡 Tracker</div>', unsafe_allow_html=True)
        st.caption(
            f"{sport_cfg()['label']} + all graded sports in one file. "
            f"n &lt; {TRACKER_MIN_N} hidden unless it is a core family. "
            "HOT = over 15%. Δ is vs TAKE IT baseline."
        )
        today_rows = [r for r in load_results() if r.get("date") == today_az() and r.get("result") in ("HIT", "MISS")]
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
            st.info("Grade a HIT today and this strip fills. Same Tracker for HR and TD.")
        baseline, baseline_n = take_it_baseline_rate(load_results())
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

        def chips_from_stats(stats, min_n=TRACKER_MIN_N, compare_baseline=False):
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
                hot = pct > 15
                beat = compare_baseline and pct > base + 0.5
                cls = "rate-chip beat" if beat or hot else "rate-chip"
                sign = "+" if delta >= 0 else ""
                badge = ' <span class="tag tag-strong">HOT</span>' if hot else ""
                thin = " · thin n" if t < min_n else ""
                beat_html = f'<div class="rate-beat">{sign}{delta:.0f} Δ vs {base:.0f}%</div>'
                out.append(
                    f'<div class="{cls}">'
                    f'<div class="rate-pct">{pct:.0f}%</div>'
                    f'<div class="rate-name">{name}{badge}</div>'
                    f'<div class="rate-n">{s["hit"]} hit · {s["miss"]} miss · {t} plays{thin}</div>'
                    f"{beat_html}</div>"
                )
            return out

        st.markdown("#### By Petty Score lane")
        st.caption("Does a higher score actually hit more? Grade TAKE / PASS so these fill in.")
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
        st.markdown('<div class="queen-banner">📊 Results</div>', unsafe_allow_html=True)
        if st.button("⚡ Run auto-grade now", type="primary"):
            with st.spinner("MLB..."):
                h, m, s, msg = auto_grade_pending()
            st.success(f"{h} HIT · {m} MISS · {s} open - {msg}")
            st.rerun()
        rows = load_results()
        n_all = len(rows)
        n_pending_all = sum(1 for r in rows if r.get("result") == "PENDING")
        n_today = sum(1 for r in rows if r.get("date") == today_az())
        src = st.session_state.get("_results_source", "?")
        gh_st = st.session_state.get("_results_gh_status", "unconfigured")
        gh_save = st.session_state.get("_results_gh_save", "-")
        lock_src = st.session_state.get("_pregame_source", "?")
        lock_n = len(st.session_state.get("pregame_lock") or load_pregame())
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
            "Log type",
            ["All", "Board (TAKE IT / WATCH)", "Shop (TAKE / LEAN)"],
            horizontal=True,
            key="results_src_filter",
        )
        rows_view = [r for r in rows if r.get("date") == today_az()] if today_only else rows
        if src_f.startswith("Board"):
            rows_view = [r for r in rows_view if r.get("source") in ("take_it", "watch")]
        elif src_f.startswith("Shop"):
            rows_view = [r for r in rows_view if r.get("source") in ("shop_take", "shop_lean")]
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


    if page == "Grade:Shop":
        st.markdown('<div class="queen-banner">🛒 Shop report card</div>', unsafe_allow_html=True)
        st.caption(
            "This is the price side only. Shop TAKE / LEAN log even if the same name is on The Board. "
            "Board Backtest stays methods-only."
        )
        rows_sh = load_results()
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
        .pa-card{background:#16101f;border:1px solid #2a2038;border-radius:16px;padding:12px 14px;margin-bottom:10px}
        .pa-h{font-size:.78rem;letter-spacing:1px;text-transform:uppercase;color:#f9a8d4;font-weight:800;margin:0 0 8px}
        .pa-sub{font-size:.62rem;color:#9ca3af;margin:-4px 0 8px}
        .pa-row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:.84rem}
        .pa-bar{height:6px;border-radius:99px;background:#2a2038;flex:1;overflow:hidden}
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

        rows = load_results() or []
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

        endings, books, buckets, families, methods_c, names, end_g, book_g, buck_g, meth_g, fade, cross = pack_hits(hits, graded)
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
            rows_h = []
            for i, (k, n) in enumerate(items):
                extra = ""
                if rate_map is not None:
                    extra = rate(n, rate_map.get(k, 0))
                if prev_map is not None:
                    extra += arrow(n, prev_map.get(k, 0))
                rows_h.append(bar_row(k, n, mx, extra, crown=(i == 0)))
            body = "".join(rows_h) if rows_h else '<div class="pa-pct">None yet</div>'
            return f'<div class="pa-card"><div class="pa-h">{title}</div><div class="pa-sub">{subtitle}</div>{body}</div>'

        week_rate = rate(len(hits), len(graded))
        prev_rate = rate(len(prev_hits), len(prev_graded))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HRs this week", len(hits), delta=len(hits) - len(prev_hits) if not window.endswith("only") else None)
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
            st.caption(f"Focus {chosen}: {len(focus_hits)} HR this slice")

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
                "Hot Endings", "Top endings - count of HRs - hit rate vs all graded with that ending",
                endings.most_common(8), mx_e, end_g, p_end,
            ), unsafe_allow_html=True)
            st.markdown(section_html(
                "Who is Paying the Bills", "Top books - best-price book on the HIT row",
                books.most_common(8), mx_bk, book_g, p_book,
            ), unsafe_allow_html=True)
            st.markdown(section_html(
                "Money Lanes", "Top buckets - efficiency = HR / graded in that lane",
                buckets.most_common(8), mx_bu, buck_g, p_buck,
            ), unsafe_allow_html=True)
        with right:
            picks = [(k, n) for k, n in names.most_common() if k and n >= 2]
            pick_rows = []
            for i, (pl, n) in enumerate(picks[:12]):
                st_s = f" - {streaks[pl]}-day streak" if pl in streaks else ""
                pick_rows.append(bar_row(f"{pl}{st_s}", n, max((x[1] for x in picks), default=1), "", crown=(i == 0)))
            picks_html = "".join(pick_rows) if pick_rows else '<div class="pa-pct">None yet</div>'
            st.markdown(
                '<div class="pa-card"><div class="pa-h">Repeat Offenders</div>'
                '<div class="pa-sub">Petty Picks (2+ hits)</div>'
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
            "<p>We don’t chase vibes. We chase value. The Board clears names. The Shop picks numbers. Everything else is homework.</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="how-box">'
            "We only play <b>0.5 HR Over</b> — one homer, one vibe. "
            "Green names are gospel. Gray is homework. Eyes mean watch it, don’t force the ticket. "
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
                "**Petty Score** ranks the stack. 70+ can **score hold** a green when Benford / numerology miss. It cannot invent a green.\n"
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
                "- **Score hold** at 70. Queen commentary is mood, not math.\n"
                "- Secrets stay on the cards. This page is the map, not the vault."
            )
        with st.expander("💅 Girl Magic Glossary — same language as the welcome flow"):
            render_mini_glossary()
        st.caption("Need the language? That’s the Glossary — it’s how the math talks.")
        st.caption("Manual only. Tags live on the cards. Recipes stay off this page.")
        site_section_close()

    st.markdown(
        '<div class="footer">👑 Girl Magic · She Got Game · Boss Bitch · HBIC · Me & My Girls We Rolling<br>'
        '<span style="font-size:.75rem;color:#c4b5d6">Board picks the name. Shop picks the number. Grade keeps us honest.</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
