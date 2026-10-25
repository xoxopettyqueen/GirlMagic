# -*- coding: utf-8 -*-
"""
Girl Magic Odds 2.0 — restored morning build.
"""
import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path

st.set_page_config(page_title="Girl Magic Odds 2.0", page_icon="✨", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp{background:#0c0c10!important;color:#fff!important;font-family:'Inter',sans-serif!important}
.hero{background:linear-gradient(90deg,#FF3EBF,#C77DFF,#7B2CBF)!important;border-radius:20px;padding:18px 22px;margin-bottom:12px;color:#fff}
.hero h1{margin:0;font-size:1.75rem;font-weight:700}
.hero p{margin:4px 0 0;color:#F5E9FF}
.card{background:#15151b;border:1px solid #2a2a33;border-radius:14px;padding:11px 13px;margin-bottom:10px}
.card.take-card{border-color:#FF3EBF}
.player{font-size:1.1rem;font-weight:700}
.meta{color:#aaa;font-size:.7rem}
.prop{font-size:.85rem;font-weight:600;color:#FF3EBF;text-transform:uppercase}
.true-ev{font-weight:700;color:#FF3EBF}
.game-header{font-size:1.05rem;font-weight:700;color:#FF3EBF;margin:16px 0 8px}
</style>
""", unsafe_allow_html=True)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
BDL_BASE = "https://api.balldontlie.io/nba/v1"
LEDGER = Path("odds_ledger.json")
SHARPNESS = Path("book_sharpness.json")
WEIGHTS_FILE = Path("auto_weights.json")
MY_BOOKS = {
    "fanduel":"FD","draftkings":"DK","betmgm":"MGM","bet365":"365",
    "williamhill_us":"CZR","fanatics":"FAN","espnbet":"SCR","hardrockbet":"HR",
    "hardrockbet_az":"HR","hardrockbet_oh":"HR","hardrockbet_fl":"HR",
    "pinnacle":"PIN","circa":"CIR","bookmaker":"BM",
}
BOOK_FULL = {"FD":"FanDuel","DK":"DraftKings","MGM":"BetMGM","365":"Bet365","CZR":"Caesars","FAN":"Fanatics","SCR":"theScore","HR":"Hard Rock","PIN":"Pinnacle","CIR":"Circa","BM":"Bookmaker"}
BASE_WEIGHTS = {"PIN":3.5,"CIR":3.0,"BM":2.8,"FD":2.0,"DK":1.8,"365":2.0,"MGM":1.4,"CZR":1.3,"FAN":1.2,"SCR":1.1,"HR":1.1}

def secret(name):
    try:
        return st.secrets.get(name, "") or ""
    except Exception:
        return ""

def implied(price):
    try:
        p = int(price)
        return 100/(p+100) if p > 0 else abs(p)/(abs(p)+100)
    except Exception:
        return None

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default

def save_json(path, data):
    try:
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

def load_auto_weights():
    out = BASE_WEIGHTS.copy()
    out.update(load_json(WEIGHTS_FILE, {}) or {})
    return out

def weighted_fair_prob(book_prices, weights=None):
    weights = weights or load_auto_weights()
    weighted, total_w = [], 0.0
    for bk, price in (book_prices or {}).items():
        w = float(weights.get(bk, 1.0) or 1.0)
        imp = implied(price)
        if w > 0 and imp and 0 < imp < 1:
            weighted.append(imp * w)
            total_w += w
    if not weighted or not total_w:
        return None
    return max(0.05, min(0.85, sum(weighted) / total_w))

def compute_true_ev(best_price, fair_prob):
    if not fair_prob or best_price is None:
        return None
    try:
        decimal = (best_price / 100 + 1) if int(best_price) > 0 else (100 / abs(int(best_price)) + 1)
        return round(max(-20, min(80, (fair_prob * decimal - 1) * 100)), 1)
    except Exception:
        return None

def normalize_book(key):
    k = str(key or "").lower()
    for needle, name in (("pinnacle","pinnacle"),("circa","circa"),("bookmaker","bookmaker"),("bet365","bet365"),("fanatic","fanatics"),("hardrock","hardrockbet"),("espnbet","espnbet"),("score","espnbet"),("draftking","draftkings"),("fanduel","fanduel"),("betmgm","betmgm"),("williamhill","williamhill_us"),("caesar","williamhill_us")):
        if needle in k:
            return name
    return k

def fetch_events(api_key, sport_key):
    r = requests.get(f"{ODDS_API_BASE}/sports/{sport_key}/events", params={"apiKey": api_key}, timeout=15)
    if r.status_code == 200:
        return r.json() or [], ""
    return [], f"events {r.status_code}"

def fetch_odds(api_key, sport_key, event_id, markets):
    r = requests.get(
        f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds",
        params={"apiKey": api_key, "regions": "us", "markets": markets, "oddsFormat": "american"},
        timeout=20,
    )
    if r.status_code == 200:
        return r.json(), ""
    return None, f"odds {r.status_code} {(r.text or '')[:60]}"

def parse_plays(data, sport):
    if not data:
        return []
    event = f"{data.get('away_team')} @ {data.get('home_team')}"
    plays = []
    for book in data.get("bookmakers") or []:
        bk = normalize_book(book.get("key"))
        if bk not in MY_BOOKS:
            continue
        short = MY_BOOKS[bk]
        for market in book.get("markets") or []:
            mkey = (market.get("key") or "").lower()
            prop_type = None
            if sport == "NBA":
                if "assist" in mkey: prop_type = "Assists"
                elif "point" in mkey and "rebound" not in mkey and "assist" not in mkey: prop_type = "Points"
                elif "rebound" in mkey and "point" not in mkey and "assist" not in mkey: prop_type = "Rebounds"
                elif "double_double" in mkey: prop_type = "DoubleDouble"
            else:
                if "anytime_td" in mkey: prop_type = "Anytime TD"
                elif "reception" in mkey or "receiving" in mkey: prop_type = "Rec Yards"
            if not prop_type:
                continue
            for o in market.get("outcomes") or []:
                name = str(o.get("name") or "").lower()
                if prop_type in ("DoubleDouble", "Anytime TD"):
                    if "yes" not in name:
                        continue
                    player = o.get("description") or o.get("name")
                    line = 0.5 if prop_type == "Anytime TD" else 1.0
                else:
                    if "over" not in name:
                        continue
                    player = o.get("description") or o.get("name")
                    try:
                        line = float(o.get("point"))
                    except Exception:
                        continue
                try:
                    price = int(o.get("price"))
                except Exception:
                    continue
                if not player:
                    continue
                plays.append({"sport": sport, "event": event, "player": player, "prop": prop_type, "line": line, "price": price, "book": short})
    return plays


def parse_sgo(ev, sport):
    teams = ev.get("teams") or {}
    away = ((teams.get("away") or {}).get("names") or {}).get("long") or ""
    home = ((teams.get("home") or {}).get("names") or {}).get("long") or ""
    event = f"{away} @ {home}"
    plays = []
    for odd in (ev.get("odds") or {}).values():
        if odd.get("statEntityID") in ("all", "home", "away", None):
            continue
        if odd.get("sideID") not in ("over", "yes"):
            continue
        stat = odd.get("statID") or ""
        prop = {"points": "Points", "assists": "Assists", "rebounds": "Rebounds", "receiving_yards": "Rec Yards"}.get(stat)
        if "touchdown" in stat:
            prop = "Anytime TD"
        if not prop:
            continue
        pid = odd.get("playerID") or odd.get("statEntityID") or ""
        name = " ".join(w.capitalize() for w in pid.split("_")[:-2]) or pid
        for bk, row in (odd.get("byBookmaker") or {}).items():
            short = MY_BOOKS.get(normalize_book(bk))
            if not short:
                continue
            try:
                price = int(str(row.get("odds")).replace("+", ""))
            except Exception:
                continue
            line = row.get("overUnder")
            try:
                line = float(line) if line is not None else (0.5 if prop == "Anytime TD" else None)
            except Exception:
                line = None
            if line is None:
                continue
            plays.append({"sport": sport, "event": event, "player": name, "prop": prop, "line": line, "price": price, "book": short})
    return plays


def best_cards(plays):
    by = defaultdict(list)
    for p in plays:
        by[(p["sport"], p["player"], p["prop"], round(p["line"], 1), p["event"])].append(p)
    cards = []
    for group in by.values():
        best = max(group, key=lambda x: x["price"])
        book_prices = {g["book"]: g["price"] for g in group}
        prices = list(book_prices.values())
        med = sorted(prices)[len(prices)//2]
        gap = round((best["price"] - med) / med * 100, 1) if med else 0
        fair = weighted_fair_prob(book_prices)
        tev = compute_true_ev(best["price"], fair)
        cards.append({**best, "book_prices": book_prices, "median": int(med), "ev_gap": gap, "true_ev": tev, "decision": "TAKE" if (tev or 0) >= 3 else "LEAN"})
    cards.sort(key=lambda x: -(x.get("true_ev") or -999))
    return cards

def main():
    st.markdown('<div class="hero"><h1>Girl Magic Odds 2.0</h1><p>SportsGameOdds feed. Be a better bettor.</p></div>', unsafe_allow_html=True)
    if "odds 401" in str(st.session_state.get("note") or ""):
        st.session_state["note"] = ""
    api_key = secret("ODDS_API_KEY") or st.text_input("Odds API Key", type="password")
    if not api_key:
        st.info("Add ODDS_API_KEY to secrets, or paste it above.")
        return
    sport = "NBA" if "NBA" in st.radio("Lane", ["NBA", "NFL"], horizontal=True) else "NFL"
    sgo = secret("SPORTSGAMEODDS_API_KEY")
    if st.button("Pull the board", type="primary", use_container_width=True):
        with st.spinner("Pulling SportsGameOdds…"):
            if not sgo:
                st.session_state["note"] = "Add SPORTSGAMEODDS_API_KEY to secrets."
                st.session_state[f"cards_{sport}"] = []
            else:
                league = "NBA" if sport == "NBA" else "NFL"
                odds_ids = (
                    "points-PLAYER_ID-game-ou-over,assists-PLAYER_ID-game-ou-over,rebounds-PLAYER_ID-game-ou-over"
                    if sport == "NBA" else
                    "receiving_yards-PLAYER_ID-game-ou-over,anytime_touchdown-PLAYER_ID-game-yn-yes"
                )
                r = requests.get(
                    "https://api.sportsgameodds.com/v2/events",
                    params={"apiKey": sgo, "leagueID": league, "oddsAvailable": "true", "oddIDs": odds_ids, "limit": 15},
                    timeout=30,
                )
                plays = []
                if r.status_code == 200:
                    for ev in (r.json() or {}).get("data") or []:
                        plays.extend(parse_sgo(ev, sport))
                    note = f"SGO {r.status_code} · {len(plays)} prices"
                else:
                    note = f"SGO {r.status_code}: {(r.text or '')[:80]}"
                cards = best_cards(plays)
                st.session_state[f"cards_{sport}"] = cards
                st.session_state["note"] = note + f" · {len(cards)} cards"
    cards = st.session_state.get(f"cards_{sport}") or []
    if st.session_state.get("note"):
        st.warning(st.session_state["note"])
    if not cards:
        st.info("Pull the board.")
        return
    cards = [c for c in cards if (c.get("price") or 0) >= 500 and (c.get("true_ev") or 0) >= 3]
    st.markdown(f"**{len(cards)} plays.** +500 and edge 3% or more. One book longer than the blend.")
    cols = st.columns(2)
    for i, c in enumerate(cards[:40]):
        html = (
            f'<div class="card take-card"><div class="player">{c["player"]}</div>'
            f'<div class="meta">{c["event"]}</div><div class="prop">{c["prop"]} o{c["line"]}</div>'
            f'<div>Best {c["price"]:+d} {c["book"]} · pack {c["median"]:+d}</div>'
            f'<div class="true-ev">Gap {c["ev_gap"]}% · Edge {c["true_ev"]}%</div>'
            f'<div class="meta">{c["book"]} is longest versus the blend.</div></div>'
        )
        with cols[i % 2]:
            st.markdown(html, unsafe_allow_html=True)

try:
    main()
except Exception as e:
    st.error(f"App error: {e
