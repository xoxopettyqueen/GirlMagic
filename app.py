import streamlit as st
import pandas as pd
import requests
import sqlite3
from datetime import datetime, date
from pathlib import Path
from collections import defaultdict

st.set_page_config(
    page_title="Girl Magic Odds ✨",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 40%, #1f0f2e 100%); color: #fce7f3; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #2a1435 0%, #1c0d24 100%); border-right: 1px solid #a855f7; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button { background: linear-gradient(90deg, #ec4899, #a855f7) !important; color: white !important; border: none !important; border-radius: 12px !important; font-weight: 600 !important; }
    span[data-baseweb="tag"] { background-color: #db2777 !important; }
    .hot-card { background: linear-gradient(90deg, #831843, #4c1d95); border: 2px solid #f472b6; border-radius: 12px; padding: 14px 18px; margin: 10px 0; color: #fdf2f8; }
    .matchup-card { background: #2d1b3d; border: 1px solid #c084fc; border-radius: 10px; padding: 12px 16px; margin: 8px 0; color: #fce7f3; }
    .batter-card { background: #1f0f2e; border: 1px solid #a855f7; border-radius: 8px; padding: 10px 14px; margin: 6px 0; font-size: 0.9rem; }
    .launch-card { background: #2a1435; border: 1px solid #f472b6; border-radius: 10px; padding: 12px 16px; margin: 8px 0; }
</style>
""",
    unsafe_allow_html=True,
)

DB_PATH = Path("odds_data.db")
API_BASE = "https://api.the-odds-api.com/v4"
REGIONS = "us"
PREFERRED_BOOKS = ["betmgm", "draftkings", "bet365", "fanduel", "caesars", "pointsbet", "espn"]

SPORTS = {
    "NFL": "americanfootball_nfl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb",
}

PLAYER_PROP_MARKETS = {
    "NBA": ["player_points", "player_rebounds", "player_assists", "player_threes"],
    "NFL": ["player_pass_yds", "player_rush_yds", "player_receptions", "player_reception_yds", "player_anytime_td"],
    "MLB": ["batter_home_runs", "batter_hits", "batter_total_bases", "batter_rbis", "batter_runs_scored", "batter_strikeouts"],
}


@st.cache_data
def load_statcast_files():
    hitters = None
    exit_velo = None
    for name in ["stats.csv", "stats (1).csv"]:
        p = Path(name)
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "barrel_batted_rate" in df.columns or "hard_hit_percent" in df.columns:
                    hitters = df
                    break
            except:
                pass
    for name in ["exit_velocity.csv", "exit_velocity (1).csv"]:
        p = Path(name)
        if p.exists():
            try:
                df = pd.read_csv(p)
                if "avg_hit_speed" in df.columns or "brl_percent" in df.columns:
                    exit_velo = df
                    break
            except:
                pass
    return hitters, exit_velo


def normalize_name(name):
    if not name:
        return ""
    name = str(name).lower().strip()
    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name


def find_player_metrics(player_name, hitters_df, exit_df):
    if hitters_df is None and exit_df is None:
        return None
    target = normalize_name(player_name)
    result = {"matched": None}
    if hitters_df is not None:
        for _, row in hitters_df.iterrows():
            savant_name = normalize_name(row.get("last_name, first_name", ""))
            if target in savant_name or savant_name in target or (
                len(target.split()) > 0 and target.split()[-1] in savant_name
            ):
                result["matched"] = savant_name
                result["barrel"] = row.get("barrel_batted_rate", "-")
                result["hard_hit"] = row.get("hard_hit_percent", "-")
                result["best_speed"] = row.get("avg_best_speed", "-")
                result["sweet_spot"] = row.get("sweet_spot_percent", "-")
                result["xwoba"] = row.get("xwoba", "-")
                break
    if exit_df is not None:
        for _, row in exit_df.iterrows():
            savant_name = normalize_name(row.get("last_name, first_name", ""))
            if target in savant_name or savant_name in target or (
                len(target.split()) > 0 and target.split()[-1] in savant_name
            ):
                result["matched"] = result.get("matched") or savant_name
