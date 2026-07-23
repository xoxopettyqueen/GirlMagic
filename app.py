"""
Girl Magic – SportsGameOdds DEBUG version
Just to see the raw response
"""

import streamlit as st
import pandas as pd
import requests
import json

st.set_page_config(page_title="Girl Magic Debug", page_icon="💖", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #1a0a1f 0%, #2d1b3d 50%, #1f0f2e 100%); color: #fce7f3; }
    h1, h2, h3 { color: #f9a8d4 !important; }
    .stButton > button {
        background: linear-gradient(90deg, #ec4899, #a855f7) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = "https://api.sportsgameodds.com/v2"

def get_api_key():
    key = st.secrets.get("SGO_API_KEY", "")
    if not key:
        key = st.sidebar.text_input("SportsGameOdds API Key", type="password")
    return key

def main():
    st.title("💖 Girl Magic – Debug Mode")
    st.caption("Showing raw SportsGameOdds response")

    api_key = get_api_key()
    if not api_key:
        st.warning("Add your key")
        st.stop()

    if st.button("Fetch Raw MLB Data 💫", type="primary"):
        params = {
            "apiKey": api_key,
            "leagueID": "MLB",
            "oddsAvailable": "true",
            "limit": 5
        }
        try:
            r = requests.get(f"{API_BASE}/events", params=params, timeout=25)
            st.write(f"**Status code:** {r.status_code}")
            st.write(f"**Headers:** {dict(r.headers)}")

            try:
                data = r.json()
                st.success("Got JSON response")
                st.json(data)          # ← this shows the full structure
            except:
                st.write("Raw text:")
                st.code(r.text[:3000])
        except Exception as e:
            st.error(f"Request failed: {e}")

if __name__ == "__main__":
    main()
