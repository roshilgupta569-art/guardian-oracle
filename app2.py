import streamlit as st
import pandas as pd
import swisseph as swe
import requests
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIGURATION (Clean Professional Mode) ---
st.set_page_config(page_title="ASTRO-ALGO TERMINAL", page_icon="📈", layout="wide")

# Professional UI Styling
st.markdown("""
    <style>
    .stApp {background-color: #0E1117;}
    div.stButton > button {width: 100%; background-color: #2E86C1; color: white; font-weight: bold; border-radius: 5px;}
    .bullish {color: #2ECC71; font-weight: bold;}
    .bearish {color: #E74C3C; font-weight: bold;}
    .neutral {color: #F1C40F; font-weight: bold;}
    .big-font {font-size: 20px !important;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SECURITY (Password) ---
def check_password():
    if st.session_state.get('password_correct', False): return True
    pwd = st.text_input("ENTER PASSWORD", type="password")
    if st.button("LOGIN"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state['password_correct'] = True
            st.rerun()
    return False

if not check_password(): st.stop()

# --- 3. DEEP ASTRO ENGINE (The Brain) ---
LAT, LON = 30.7333, 76.7794

def get_astro_strength(planet_id, target_date=None):
    if target_date is None: target_date = datetime.now()
    jd = swe.julday(target_date.year, target_date.month, target_date.day, target_date.hour + target_date.minute/60.0)
    
    pos, _ = swe.calc_ut(jd, planet_id)
    sun, _ = swe.calc_ut(jd, swe.SUN)
    
    # 1. COMBUSTION (Physics)
    dist = abs(pos[0] - sun[0])
    is_combust = dist < 14.0
    
    # 2. RETROGRADE (Motion)
    is_retro = pos[3] < 0 

    return {"dist": round(dist, 2), "combust": is_combust, "retro": is_retro}

def check_rahu_kaal():
    # Thursday 1:30-3:00 PM
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if now.weekday() == 3 and 13 <= now.hour < 15:
        if now.hour == 13 and now.minute < 30: return False
        return True
    return False

# --- 4. MARKET DATA FEED ---
def get_price(ticker):
    try:
        url = f"https://indian-stock-market-api.vercel.app/stock/{ticker}"
        data = requests.get(url, timeout=3).json()
        return float(data['lastPrice'].replace(',', ''))
    except: return 0.0

# --- 5. SCORING & SIGNALS ---
# Full Nifty 50 Heavyweights List
WATCHLIST = {
    "NIFTY 50": {"Planet": swe.SUN, "Ticker": "NIFTY 50"}, # Index
    "BANK NIFTY": {"Planet": swe.JUPITER, "Ticker": "NIFTY BANK"}, # Index
    "HDFC BANK": {"Planet": swe.JUPITER, "Ticker": "HDFCBANK"},
    "RELIANCE": {"Planet": swe.SATURN, "Ticker": "RELIANCE"},
    "ICICI BANK": {"Planet": swe.VENUS, "Ticker": "ICICIBANK"},
    "INFOSYS": {"Planet": swe.MERCURY, "Ticker": "INFY"},
    "ITC": {"Planet": swe.VENUS, "Ticker": "ITC"},
    "TCS": {"Planet": swe.SATURN, "Ticker": "TCS"},
    "L&T": {"Planet": swe.MARS, "Ticker": "LT"},
    "AXIS BANK": {"Planet": swe.JUPITER, "Ticker": "AXISBANK"},
    "NTPC": {"Planet": swe.SUN, "Ticker": "NTPC"},
    "DLF": {"Planet": swe.MARS, "Ticker": "DLF"},
    "TATA MOTORS": {"Planet": swe.VENUS, "Ticker": "TATAMOTORS"},
    "SBI": {"Planet": swe.JUPITER, "Ticker": "SBIN"}
}

def analyze_stock(data, is_rahu):
    physics = get_astro_strength(data['Planet'])
    
    # Base Score
    score = 60
    
    # Astro Logic
    if physics['combust']: score -= 35  # Weak
    elif physics['dist'] > 20: score += 15 # Strong
    
    if physics['retro']: score -= 20   # Unstable
    
    # Rahu Penalty
    if is_rahu: score -= 20
    
    # Final Signal
    signal = "NEUTRAL"
    if score >= 80: signal = "VERY BULLISH"
    elif score >= 65: signal = "BULLISH"
    elif score <= 30: signal = "VERY BEARISH"
    elif score <= 45: signal = "BEARISH"
    
    return {
        "score": max(0, min(100, score)),
        "signal": signal,
        "reason": "Combust" if physics['combust'] else "Strong" if physics['dist'] > 20 else "Neutral",
        "astro": physics
    }

# --- 6. DASHBOARD UI ---
st.title("📈 ASTRO-ALGO TERMINAL")
st.caption(f"LIVE MARKET DATA | {datetime.now().strftime('%H:%M:%S')}")

# Run Global Scan
results = []
is_rahu = check_rahu_kaal()

if is_rahu:
    st.error("⚠️ RAHU KAAL ACTIVE: Market is Volatile. Reduce Quantity.")

for name, data in WATCHLIST.items():
    try:
        price = get_price(data['Ticker'])
        analysis = analyze_stock(data, is_rahu)
        results.append({
            "Name": name, 
            "Price": price, 
            "Signal": analysis['signal'],
            "Score": analysis['score'],
            "Reason": analysis['reason']
        })
    except: pass

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🎯 SNIPER TRADES", "📊 NIFTY SCANNER", "🔮 TOMORROW & BTST"])

# TAB 1: SNIPER (Best 1-2 Trades)
with tab1:
    st.markdown("### 🔥 TODAY'S HIGH CONVICTION TRADES")
    
    # Filter for Extreme Scores (>80 or <30)
    snipers = [r for r in results if r['Score'] >= 80 or r['Score'] <= 30]
    
    if not snipers:
        st.info("No High-Probability setups right now. Market is choppy. Wait.")
    else:
        col1, col2 = st.columns(2)
        for i, trade in enumerate(snipers[:2]): # Max 2 trades
            with (col1 if i==0 else col2):
                color = "green" if "BULLISH" in trade['Signal'] else "red"
                action = "BUY / CALL" if "BULLISH" in trade['Signal'] else "SELL / PUT"
                
                st.markdown(f"""
                <div style="border: 2px solid {color}; padding: 15px; border-radius: 10px; background-color: #111;">
                    <h2 style="color: {color};">{trade['Name']}</h2>
                    <h3 style="color: white;">ACTION: {action}</h3>
                    <p>Price: ₹{trade['Price']}<br>
                    Logic: {trade['Reason']} Astro-Alignment<br>
                    Confidence: {trade['Score']}%</p>
                </div>
                """, unsafe_allow_html=True)

# TAB 2: NIFTY SCANNER (Categorized)
with tab2:
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown("#### 🚀 VERY BULLISH")
        for r in results:
            if r['Signal'] == "VERY BULLISH": 
                st.success(f"{r['Name']} ({r['Price']})")
                
    with c2:
        st.markdown("#### 🟢 BULLISH")
        for r in results:
            if r['Signal'] == "BULLISH": 
                st.info(f"{r['Name']} ({r['Price']})")
                
    with c3:
        st.markdown("#### 🔴 BEARISH")
        for r in results:
            if r['Signal'] == "BEARISH": 
                st.warning(f"{r['Name']} ({r['Price']})")
                
    with c4:
        st.markdown("#### 🩸 VERY BEARISH")
        for r in results:
            if r['Signal'] == "VERY BEARISH": 
                st.error(f"{r['Name']} ({r['Price']})")

# TAB 3: TOMORROW & BTST
with tab3:
    st.markdown("### 🔮 BTST & TOMORROW'S VIEW")
    
    # 1. BTST ANALYSIS (Moon Check)
    tmrw_date = datetime.now() + timedelta(days=1)
    
    # Check Moon Strength for Tomorrow
    moon_phys = get_astro_strength(swe.MOON, tmrw_date)
    is_moon_good = not moon_phys['combust'] # Simple logic for now
    
    btst_signal = "✅ BTST BUY" if is_moon_good else "❌ BTST AVOID"
    btst_color = "green" if is_moon_good else "red"
    
    st.markdown(f"""
    <div style="background-color: #222; padding: 10px; border-left: 5px solid {btst_color};">
        <h3>BTST DECISION: <span style="color:{btst_color}">{btst_signal}</span></h3>
        <p>Moon Phase Analysis for Tomorrow Open.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # 2. SECTOR PREDICTION
    st.markdown("#### 🏗️ SECTOR ROTATION (TOMORROW)")
    
    cols = st.columns(3)
    sectors = [("NTPC (Power)", swe.SUN), ("DLF (Realty)", swe.MARS), ("HDFC (Bank)", swe.JUPITER)]
    
    for i, (name, planet) in enumerate(sectors):
        phys = get_astro_strength(planet, tmrw_date)
        view = "STRONG" if not phys['combust'] else "WEAK"
        color = "green" if view == "STRONG" else "red"
        
        with cols[i]:
            st.markdown(f"**{name}**")
            st.markdown(f":{color}[**{view}**]")
            st.caption(f"Dist from Sun: {phys['dist']}°")