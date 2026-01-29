import streamlit as st
import pandas as pd
import swisseph as swe
import requests
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIGURATION (Dark Mode & Security) ---
st.set_page_config(page_title="QUANTUM SNIPER v6.0", page_icon="ojo", layout="wide")

# Custom "Hacker" UI Styling
st.markdown("""
    <style>
    .stApp {background-color: #050505;}
    div.stButton > button {width: 100%; background-color: #00FF99; color: black; font-weight: bold; border: none;}
    .metric-container {background-color: #111; padding: 15px; border-radius: 5px; border: 1px solid #333;}
    h1, h2, h3 {font-family: 'Roboto Mono', monospace; color: #E0E0E0;}
    span {font-family: 'Roboto Mono', monospace;}
    
    /* Sniper Box Styling */
    .sniper-box {border: 2px solid #00FF99; padding: 20px; border-radius: 10px; background-color: #001100;}
    .trap-box {border: 2px solid #FF3333; padding: 20px; border-radius: 10px; background-color: #110000;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SECURITY PROTOCOL ---
def check_password():
    if st.session_state.get('password_correct', False): return True
    st.markdown("## 🔒 RESTRICTED ENVIRONMENT")
    pwd = st.text_input("ENTER DECRYPTION KEY", type="password")
    if st.button("ACCESS MAINFRAME"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state['password_correct'] = True
            st.rerun()
        else: st.error("⛔ INVALID CREDENTIALS")
    return False

if not check_password(): st.stop()

# --- 3. ASTRO-QUANT ENGINE ---
LAT, LON = 30.7333, 76.7794 # Chandigarh

def get_market_physics(planet_id, target_date=None):
    if target_date is None: target_date = datetime.now()
    jd = swe.julday(target_date.year, target_date.month, target_date.day, target_date.hour + target_date.minute/60.0)
    
    pos, _ = swe.calc_ut(jd, planet_id)
    sun, _ = swe.calc_ut(jd, swe.SUN)
    
    # PHYSICS LOGIC
    dist = abs(pos[0] - sun[0])
    is_interference = dist < 14.0 # Combust
    is_latency = pos[3] < 0       # Retrograde

    return {"strength": round(dist, 2), "noise": is_interference, "lag": is_latency}

def check_volatility_window():
    # Rahu Kaal Check (Thursday 1:30-3:00 PM)
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if now.weekday() == 3 and 13 <= now.hour < 15:
        if now.hour == 13 and now.minute < 30: return False
        return True
    return False

# --- 4. DATA FEED ---
def get_price(ticker):
    try:
        url = f"https://indian-stock-market-api.vercel.app/stock/{ticker}"
        data = requests.get(url, timeout=3).json()
        return float(data['lastPrice'].replace(',', ''))
    except: return 0.0

# --- 5. SCORING & SELECTION ---
# Expanded List for Sniper Opportunities
SECTORS = {
    "⚡ GRID ALPHA (Power)": {"Planet": swe.SUN, "Ticker": "NTPC"},
    "🏗️ GRID BETA (Realty)": {"Planet": swe.MARS, "Ticker": "DLF"},
    "💰 GRID GAMMA (Bank)": {"Planet": swe.JUPITER, "Ticker": "SBIN"}, # Added SBI
    "🚗 GRID DELTA (Auto)": {"Planet": swe.VENUS, "Ticker": "TATAMOTORS"},
    "🛢️ GRID EPSILON (Oil)": {"Planet": swe.SATURN, "Ticker": "RELIANCE"} # Added Reliance
}

def calculate_score(physics, is_volatility):
    score = 65 # Neutral Baseline
    
    # 1. Signal Quality (Combustion)
    if physics['noise']: score -= 35 
    elif physics['strength'] > 20: score += 15 
    
    # 2. Trend Stability (Retrograde)
    if physics['lag']: score -= 20
    
    # 3. Environment (Rahu Kaal)
    if is_volatility: score -= 25 # Heavy Penalty
    
    return max(0, min(100, score))

# --- 6. DASHBOARD UI ---
st.title("QUANTUM SNIPER v6.0")
st.caption(f"SYSTEM STATUS: ONLINE | {datetime.now().strftime('%H:%M:%S')}")

# TABS
tab_sniper, tab_market, tab_tmrw = st.tabs(["🎯 SNIPER SCOPE", "📊 FULL MARKET GRID", "🔮 FUTURE MODEL"])

# GLOBAL CALCULATION (Run once for all tabs)
results = []
is_volatility = check_volatility_window()

for name, data in SECTORS.items():
    physics = get_market_physics(data['Planet'])
    score = calculate_score(physics, is_volatility)
    price = get_price(data['Ticker'])
    
    # Determine Signal
    signal = "NEUTRAL"
    if score >= 80: signal = "LONG"
    elif score <= 30: signal = "SHORT"
    
    results.append({
        "Name": name,
        "Ticker": data['Ticker'],
        "Price": price,
        "Score": score,
        "Signal": signal,
        "Physics": physics
    })

# --- TAB 1: SNIPER SCOPE (The 1-2 Trades) ---
with tab_sniper:
    if st.button("ACTIVATE TARGET LOCK", type="primary"):
        # Filter for Extreme Scores Only (Top Tier)
        snipers = [r for r in results if r['Score'] >= 80 or r['Score'] <= 30]
        
        if not snipers:
            st.info("🔭 NO SNIPER TARGETS DETECTED.")
            st.markdown("System is holding fire. Market conditions are choppy. **DO NOT FORCE A TRADE.**")
        else:
            st.success(f"🎯 TARGET ACQUIRED: {len(snipers)} ASSET(S)")
            
            for item in snipers[:2]: # Show max 2 to prevent overtrading
                # Dynamic Coloring
                is_long = item['Signal'] == "LONG"
                color = "#00FF99" if is_long else "#FF3333"
                direction = "🟢 EXECUTE LONG" if is_long else "🔴 EXECUTE SHORT"
                box_class = "sniper-box" if is_long else "trap-box"
                
                st.markdown(f"""
                <div style="border: 2px solid {color}; padding: 20px; border-radius: 10px; background-color: #050505; margin-bottom: 20px;">
                    <h2 style="color: {color}; margin:0;">{item['Ticker']}</h2>
                    <h3 style="color: white; margin:0;">{direction}</h3>
                    <hr style="border-color: #333;">
                    <p style="font-family: monospace; font-size: 1.2rem;">
                    ENTRY PRICE: ₹{item['Price']}<br>
                    CONFIDENCE: {item['Score']}%<br>
                    SIGNAL INTEGRITY: {'CLEAN' if not item['Physics']['noise'] else 'NOISY'}
                    </p>
                </div>
                """, unsafe_allow_html=True)

# --- TAB 2: FULL GRID (For Context) ---
with tab_market:
    st.write("Full Sector Scan (For Analysis Only)")
    col1, col2 = st.columns(2)
    for i, item in enumerate(results):
        with (col1 if i % 2 == 0 else col2):
            st.metric(
                label=f"{item['Name']} ({item['Ticker']})",
                value=f"₹{item['Price']}",
                delta=f"{item['Score']}/100"
            )
            st.progress(item['Score']/100)

# --- TAB 3: TOMORROW (Prediction) ---
with tab_tmrw:
    st.info("Simulating T+1 Market Conditions...")
    tmrw_date = datetime.now() + timedelta(days=1)
    
    col1, col2 = st.columns(2)
    for i, (name, data) in enumerate(SECTORS.items()):
        p_tmrw = get_market_physics(data['Planet'], tmrw_date)
        s_tmrw = calculate_score(p_tmrw, False)
        
        verdict = "BULLISH" if s_tmrw > 60 else "BEARISH" if s_tmrw < 40 else "SIDEWAYS"
        color = "green" if s_tmrw > 60 else "red"
        
        with (col1 if i % 2 == 0 else col2):
            st.markdown(f"**{name}**")
            st.markdown(f"Bias: :{color}[{verdict}] ({s_tmrw}%)")
            if p_tmrw['noise']: st.caption("⚠️ Interference Detect")
            st.divider()