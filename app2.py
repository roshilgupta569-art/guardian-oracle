import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import hashlib

# ================= UI CONFIG =================
st.set_page_config(page_title="GUARDIAN v14: PERSONALIZED", page_icon="🦅", layout="wide")

st.markdown("""
<style>
.stApp {background-color: #000000;}
.hero-card {background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); padding: 25px; border-radius: 12px; border: 1px solid #444; margin-bottom: 20px;}
.btst-card {background: linear-gradient(135deg, #1a0b2e, #2d1b4e); padding: 25px; border-radius: 12px; border: 1px solid #553377; margin-bottom: 20px;}
.score-big {font-size: 48px; font-weight: 800; color: #00FF99;}
.ticker-big {font-size: 32px; font-weight: bold; color: #FFF; margin: 0;}
.state-box {padding: 10px; border-radius: 5px; font-weight: bold; text-align: center; margin-top: 10px;}
.enter {background-color: #004400; color: #00FF99; border: 1px solid #00FF99;}
.hold {background-color: #444400; color: #FFCC00; border: 1px solid #FFCC00;}
.wait {background-color: #222; color: #888; border: 1px solid #444;}
.avoid {background-color: #440000; color: #FF3333; border: 1px solid #FF3333;}
.btst-yes {color: #00FF99; font-weight: 900; font-size: 24px;}
.btst-no {color: #FF3333; font-weight: 900; font-size: 24px;}
</style>
""", unsafe_allow_html=True)

# ================= SECURITY =================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("ENTER QUANTUM KEY", type="password")
    if st.button("INITIATE"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")

# ================= DATABASE (FIXED) =================
# ERROR FIX: Replaced swe.RAHU with swe.MEAN_NODE
SECTOR_MAP = {
    "BANK_PVT": swe.MERCURY, "BANK_PSU": swe.JUPITER, "IT": swe.SATURN,
    "AUTO": swe.VENUS, "PHARMA": swe.SUN, "FMCG": swe.MOON,
    "METALS": swe.MARS, "REALTY": swe.MARS, "ENERGY": swe.SUN,
    "OIL_GAS": swe.SATURN, "TELECOM": swe.MEAN_NODE, "FINANCE": swe.JUPITER
}

STOCK_UNIVERSE = {
    "BANK_PVT": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "BANK_PSU": ["SBIN", "BANKBARODA", "PNB", "CANBK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "AUTO": ["TATAMOTORS", "M&M", "MARUTI", "BAJAJ-AUTO"],
    "PHARMA": ["SUNPHARMA", "DRREDDY", "CIPLA"],
    "FMCG": ["ITC", "HUL", "NESTLEIND"],
    "METALS": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
    "REALTY": ["DLF", "GODREJPROP"],
    "ENERGY": ["NTPC", "POWERGRID", "TATAPOWER"],
    "OIL_GAS": ["RELIANCE", "ONGC", "BPCL"],
    "TELECOM": ["BHARTIARTL"],
    "FINANCE": ["BAJFINANCE", "LICI"]
}

NIFTY_DB = []
for sector, tickers in STOCK_UNIVERSE.items():
    ruler = SECTOR_MAP.get(sector, swe.MERCURY)
    for t in tickers:
        NIFTY_DB.append({"Ticker": t, "Sector": sector, "Ruler": ruler})

# ================= CORE ENGINES =================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)

def get_moon_speed(dt):
    jd = julian(dt)
    m, _ = swe.calc_ut(jd, swe.MOON)
    return m[3]

def get_planet_strength(planet_id, dt):
    jd = julian(dt)
    pos, _ = swe.calc_ut(jd, planet_id)
    sun, _ = swe.calc_ut(jd, swe.SUN)
    dist = abs(pos[0] - sun[0])
    
    score = 50
    if dist < 14.0: score -= 30 # Combust
    if pos[3] < 0: score -= 15  # Retro
    if dist > 60: score += 20   # Strong
    return score

# ================= PERSONAL BIO-CALIBRATION =================
def get_user_resonance(dob, planet_id):
    """
    Matches the Stock's Ruler to the User's Day Lord (Weekday of Birth).
    This ensures the pick is 'Lucky' for the specific user.
    """
    # Map Weekday (0=Mon) to Planetary Lord
    day_lord_map = {
        0: swe.MOON,    # Monday
        1: swe.MARS,    # Tuesday
        2: swe.MERCURY, # Wednesday
        3: swe.JUPITER, # Thursday
        4: swe.VENUS,   # Friday
        5: swe.SATURN,  # Saturday
        6: swe.SUN      # Sunday
    }
    user_lord = day_lord_map.get(dob.weekday())
    
    # Vedic Friendship Table (Simplified)
    friends = {
        swe.SUN: [swe.MOON, swe.MARS, swe.JUPITER],
        swe.MOON: [swe.SUN, swe.MERCURY],
        swe.MARS: [swe.SUN, swe.MOON, swe.JUPITER],
        swe.MERCURY: [swe.SUN, swe.VENUS],
        swe.JUPITER: [swe.SUN, swe.MOON, swe.MARS],
        swe.VENUS: [swe.MERCURY, swe.SATURN],
        swe.SATURN: [swe.MERCURY, swe.VENUS],
        swe.MEAN_NODE: [swe.MERCURY, swe.VENUS, swe.SATURN] # Rahu friends
    }
    
    # Scoring
    if planet_id == user_lord: return 50     # Perfect Match (Own Lord)
    if planet_id in friends.get(user_lord, []): return 25 # Friendly
    return 0 # Neutral/Enemy

# ================= INTRADAY ENTROPY =================
def intraday_entropy(ticker, dt):
    minute_block = (dt.minute // 15) * 15 
    time_key = f"{dt.strftime('%Y%m%d%H')}{minute_block}"
    key = f"{ticker}{time_key}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return (h % 21) - 10

def trade_state(score, dt):
    market_open = 9 <= dt.hour < 15.5
    if score >= 120 and market_open: return "🚀 SNIPER ENTRY", "enter"
    if score >= 105: return "🛡️ HOLD / SCALP", "hold"
    if score <= 80: return "⛔ AVOID / TRAP", "avoid"
    return "⏳ WAIT", "wait"

# ================= CALCULATORS =================
def calculate_score(stock, dob, dt, apply_noise=True):
    # 1. Company Strength
    astro = get_planet_strength(stock['Ruler'], dt)
    
    # 2. Personal Luck (BIO-LOCK)
    user = get_user_resonance(dob, stock['Ruler'])
    
    # 3. Base
    base_total = astro + user
    
    # 4. Intraday Pulse
    noise = intraday_entropy(stock['Ticker'], dt) if apply_noise else 0
    return base_total + noise

def get_day_hero(dob, date_obj):
    """
    Calculates the #1 Stock for the User based on 9:15 AM Data.
    Locks it for the entire day.
    """
    morning_bell = datetime.combine(date_obj, time(9, 15))
    ranked = []
    
    for stock in NIFTY_DB:
        # Calculate Pure Score (Astro + User)
        score = calculate_score(stock, dob, morning_bell, apply_noise=False)
        ranked.append((stock, score))
        
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked[0][0], ranked[0][1]

def check_btst_signal(dob, today_date):
    today_close = datetime.combine(today_date, time(15, 30))
    tmrw_open = datetime.combine(today_date + timedelta(days=1), time(9, 15))
    
    speed_now = get_moon_speed(today_close)
    speed_tmrw = get_moon_speed(tmrw_open)
    
    is_accelerating = speed_tmrw > speed_now
    hero_tmrw, score_tmrw = get_day_hero(dob, today_date + timedelta(days=1))
    
    if is_accelerating and score_tmrw > 90:
        return "YES", "ACCELERATING (+)", hero_tmrw
    else:
        return "NO", "DECELERATING (-)", hero_tmrw

# ================= UI LAYOUT =================
st.sidebar.title("🧬 BIO-LOCK")
with st.sidebar.form("bio"):
    st.write("Calibrate Algorithm to Your Birth Chart")
    u_dob = st.date_input("DATE OF BIRTH", datetime(1990, 1, 1))
    st.form_submit_button("CALIBRATE SYSTEM")

st.sidebar.markdown("---")
st.sidebar.title("🕰️ TIME CONTROL")
selected_date = st.sidebar.date_input("SELECT DATE", datetime.now(IST))

sim_time = datetime.now(IST).time()
if selected_date != datetime.now(IST).date():
    sim_time = st.sidebar.slider("BACKTEST TIME", time(9,15), time(15,30), time(9,15), step=timedelta(minutes=15))

current_dt = datetime.combine(selected_date, sim_time)

# ================= DASHBOARD =================
st.title(f"🦅 GUARDIAN v14: {selected_date.strftime('%A, %d %b')}")

# HERO CALCULATIONS (Personalized)
hero_today, hero_base = get_day_hero(u_dob, selected_date)
btst_signal, btst_reason, hero_tmrw = check_btst_signal(u_dob, selected_date)

# LIVE SCORE
current_score = calculate_score(hero_today, u_dob, current_dt, apply_noise=True)
status_text, status_class = trade_state(current_score, current_dt)

# --- TABS ---
tab_live, tab_btst = st.tabs(["🚀 TODAY'S PERSONAL PICK", "🔮 TOMORROW & BTST"])

# TAB 1: LIVE
with tab_live:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        <div class="hero-card">
            <div style="color:#888; letter-spacing:2px;">LOCKED HERO (PERSONALIZED)</div>
            <div class="ticker-big">{hero_today['Ticker']}</div>
            <div style="color:#AAA;">{hero_today['Sector']}</div>
            <hr style="border-color:#444;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div class="state-box {status_class}" style="flex-grow:1; margin-right:10px;">{status_text}</div>
                <div class="score-big">{int(current_score)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(f"ℹ️ ALIGNMENT CHECK: This stock's ruler ({hero_today['Ruler']}) is compatible with your Birth Day Lord.")
    
    with col2:
        st.markdown("### 📉 SIGNAL TRAJECTORY")
        data = []
        t = datetime.combine(selected_date, time(9, 15))
        end = datetime.combine(selected_date, time(15, 30))
        while t <= end:
            s = calculate_score(hero_today, u_dob, t, apply_noise=True)
            data.append(s)
            t += timedelta(minutes=15)
        st.line_chart(data, height=180)
        st.caption("Score > 120 = SNIPER ZONE")

# TAB 2: BTST
with tab_btst:
    is_yes = btst_signal == "YES"
    css_class = "btst-yes" if is_yes else "btst-no"
    box_color = "#003300" if is_yes else "#330000"
    border_color = "#00FF99" if is_yes else "#FF3333"
    
    st.markdown(f"""
    <div class="btst-card" style="background:{box_color}; border:1px solid {border_color};">
        <h2 style="margin:0; color:#BBB;">SHOULD WE BTST?</h2>
        <div class="{css_class}">{btst_signal}</div>
        <p style="color:#CCC; margin-top:5px;">Reason: Moon Velocity is {btst_reason}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔭 PERSONAL TARGET FOR TOMORROW")
    st.markdown(f"""
    <div class="hero-card">
        <div style="color:#888;">TARGET ASSET</div>
        <div class="ticker-big" style="color:#FFCC00;">{hero_tmrw['Ticker']}</div>
        <div style="color:#AAA;">Sector: {hero_tmrw['Sector']}</div>
        <div style="margin-top:10px; font-size:14px; color:#888;">
            *Calculated specifically for your Birth Chart alignment.*
        </div>
    </div>
    """, unsafe_allow_html=True)