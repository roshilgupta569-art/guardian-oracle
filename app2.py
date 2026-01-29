import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import requests

# ================== CONFIG & UI ==================
st.set_page_config(page_title="GUARDIAN v18: HORA AUTHORITY", page_icon="🦅", layout="wide")

st.markdown("""
<style>
    .stApp {background-color: #000000;}
    .hero-card {background: linear-gradient(135deg, #1e1e1e, #2a2a2a); padding: 25px; border-radius: 12px; border: 1px solid #444; margin-bottom: 20px;}
    .hora-box {background-color: #111; padding: 15px; border-radius: 8px; border: 1px solid #333; text-align: center; margin-bottom: 10px;}
    .active-hora {border: 2px solid #00FF99; background-color: #002200;}
    .big-ticker {font-size: 36px; font-weight: 800; color: #FFF;}
    .signal-text {font-size: 24px; font-weight: bold;}
    .green {color: #00FF99;} .red {color: #FF3333;} .gray {color: #888;}
</style>
""", unsafe_allow_html=True)

# ================== SECURITY ==================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("ENTER ACCESS KEY", type="password")
    if st.button("CONNECT TO CORE"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")

# ================== HORA ENGINE (THE REAL TIMING) ==================
# Chandigarh Coordinates (Critical for accurate sunrise/hora)
LAT, LON = 30.7333, 76.7794 

def get_sunrise_sunset(date_obj):
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12)
    rise = swe.rise_trans(jd, swe.SUN, LON, LAT, rsmi=swe.CALC_RISE)[1][0]
    set_ = swe.rise_trans(jd, swe.SUN, LON, LAT, rsmi=swe.CALC_SET)[1][0]
    
    # Convert JD to IST Datetime
    def jd_to_dt(jd_val):
        y, m, d, h_dec = swe.revjul(jd_val)
        h = int(h_dec)
        mn = int((h_dec - h) * 60)
        dt_utc = datetime(y, m, d, h, mn)
        return pytz.utc.localize(dt_utc).astimezone(IST)
        
    return jd_to_dt(rise), jd_to_dt(set_)

def get_day_lord(dt):
    # 0=Mon (Moon), 1=Tue (Mars)... 6=Sun (Sun)
    # Mapping Weekday to Planet ID
    mapping = {0: swe.MOON, 1: swe.MARS, 2: swe.MERCURY, 3: swe.JUPITER, 4: swe.VENUS, 5: swe.SATURN, 6: swe.SUN}
    return mapping[dt.weekday()]

def calculate_horas(date_obj):
    sunrise, sunset = get_sunrise_sunset(date_obj)
    day_len = (sunset - sunrise).seconds / 60 # minutes
    hora_len = day_len / 12 # roughly 60 mins but varies
    
    # Chaldean Order: Saturn->Jupiter->Mars->Sun->Venus->Mercury->Moon
    chaldean_order = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
    
    # Find 1st Hora Lord (Day Lord)
    day_lord = get_day_lord(date_obj)
    start_idx = chaldean_order.index(day_lord)
    
    horas = []
    current_time = sunrise
    
    for i in range(12): # 12 Day Horas
        planet_idx = (start_idx + i) % 7 # Logic: Next planet in Chaldean order (reverse 6th)
        # Actually standard order is: Sun -> Ven -> Mer -> Moon -> Sat -> Jup -> Mars
        # But Hora sequence skips 3: Sun(1), Ven(6), Mer(4)...
        # Correct Hora Sequence: Sun, Ven, Mer, Moon, Sat, Jup, Mars
        
        # Simpler: The sequence is fixed based on Weekday.
        # Let's use a robust lookup for Hora sequence
        hora_seq = [
            swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON, swe.SATURN, swe.JUPITER, swe.MARS
        ]
        
        # Shift sequence so Day Lord is first
        lord_idx = hora_seq.index(day_lord)
        current_planet = hora_seq[(lord_idx + i) % 7]
        
        end_time = current_time + timedelta(minutes=hora_len)
        horas.append({
            "Start": current_time,
            "End": end_time,
            "Ruler": current_planet
        })
        current_time = end_time
        
    return horas

# ================== MAPPINGS ==================
# Safe Node Handling
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

PLANET_NAMES = {
    swe.SUN: "SUN", swe.MOON: "MOON", swe.MARS: "MARS", swe.MERCURY: "MERCURY",
    swe.JUPITER: "JUPITER", swe.VENUS: "VENUS", swe.SATURN: "SATURN", NODE_ID: "RAHU"
}

SECTOR_MAP = {
    "AUTO (Venus)": swe.VENUS, "IT (Saturn)": swe.SATURN, "BANK (Mercury)": swe.MERCURY,
    "PSU (Jupiter)": swe.JUPITER, "PHARMA (Sun)": swe.SUN, "FMCG (Moon)": swe.MOON,
    "REALTY (Mars)": swe.MARS, "OIL (Saturn)": swe.SATURN
}

STOCKS = {
    "AUTO (Venus)": ["TATAMOTORS", "MARUTI", "M&M"],
    "IT (Saturn)": ["TCS", "INFY", "HCLTECH"],
    "BANK (Mercury)": ["HDFCBANK", "ICICIBANK", "AXISBANK"],
    "PSU (Jupiter)": ["SBIN", "PNB"],
    "REALTY (Mars)": ["DLF", "GODREJPROP"],
    "PHARMA (Sun)": ["SUNPHARMA"],
    "FMCG (Moon)": ["ITC"]
}

# ================== MY LOGIC (THE BRAIN) ==================
def get_user_day_lord(dob):
    # 2006-02-17 was a Friday -> Venus
    mapping = {0: swe.MOON, 1: swe.MARS, 2: swe.MERCURY, 3: swe.JUPITER, 4: swe.VENUS, 5: swe.SATURN, 6: swe.SUN}
    return mapping[dob.weekday()]

def get_hero_stock(dob, date_obj):
    # Logic: The Hero Stock must match the User's Day Lord OR the Current Day Lord
    user_lord = get_user_day_lord(dob) # Venus for you
    current_day_lord = get_day_lord(date_obj) # Varies daily
    
    # Priority: If User Lord matches Day Lord -> SUPER DAY. 
    # If not, prioritize Current Day Lord (Market Trend).
    
    target_planet = current_day_lord
    
    # Find sector matching target planet
    best_sector = None
    for sec, ruler in SECTOR_MAP.items():
        if ruler == target_planet:
            best_sector = sec
            break
            
    # Pick liquid stock
    stock = STOCKS.get(best_sector, ["RELIANCE"])[0]
    return stock, best_sector, target_planet

def get_live_price(ticker):
    try:
        url = f"https://indian-stock-market-api.vercel.app/stock/{ticker}"
        data = requests.get(url, timeout=1).json()
        return float(data['lastPrice'].replace(',', ''))
    except: return 0.0

# ================== SIDEBAR ==================
st.sidebar.title("🧬 BIO-LINK")
u_dob = st.sidebar.date_input("DOB", datetime(2006, 2, 17)) # Defaulted to your date
st.sidebar.markdown("---")
st.sidebar.title("🕰️ HORA CONTROL")
sel_date = st.sidebar.date_input("DATE", datetime.now(IST))

# Time Simulation
sim_time = datetime.now(IST).time()
if sel_date != datetime.now(IST).date():
    sim_time = st.sidebar.slider("TIME TRAVEL", time(9,15), time(15,30), time(9,15), step=timedelta(minutes=15))
    
current_dt = datetime.combine(sel_date, sim_time).replace(tzinfo=IST)

# ================== DASHBOARD ==================
st.title(f"🦅 GUARDIAN v18: {sel_date.strftime('%A')}")

# 1. CALCULATE HERO
hero_stk, hero_sec, hero_ruler = get_hero_stock(u_dob, sel_date)
live_price = get_live_price(hero_stk)

# 2. CALCULATE HORAS
horas = calculate_horas(sel_date)

# 3. FIND ACTIVE HORA
active_hora = None
active_ruler = None
for h in horas:
    # Basic check ignoring timezone complexity for display
    # (In real deployment, precise timezone matching is key)
    h_start_local = h['Start'].time()
    h_end_local = h['End'].time()
    
    if h_start_local <= sim_time < h_end_local:
        active_hora = h
        active_ruler = h['Ruler']
        break

# 4. DECISION ENGINE (MY MIND)
decision = "WAIT"
color = "gray"
reason = "Hora does not match Stock."

if active_ruler:
    # Logic: Does Hora Ruler match Stock Ruler?
    if active_ruler == hero_ruler:
        decision = "🔥 SNIPER BUY"
        color = "green"
        reason = f"DOUBLE RESONANCE: {PLANET_NAMES[active_ruler]} Hora + {PLANET_NAMES[hero_ruler]} Stock."
    # Logic: Is Hora Ruler a Friend?
    elif active_ruler in [swe.MERCURY, swe.SATURN] and hero_ruler == swe.VENUS:
        decision = "✅ ACCUMULATE"
        color = "green"
        reason = f"Friendly Support: {PLANET_NAMES[active_ruler]} supports {PLANET_NAMES[hero_ruler]}."
    elif active_ruler in [swe.SUN, swe.MOON] and hero_ruler == swe.VENUS:
        decision = "⛔ AVOID"
        color = "red"
        reason = f"Enemy Hora: {PLANET_NAMES[active_ruler]} conflicts with {PLANET_NAMES[hero_ruler]}."

# ================== UI DISPLAY ==================

col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown(f"""
    <div class="hero-card">
        <div style="color:#888;">TODAY'S CHOSEN ONE</div>
        <div class="big-ticker">{hero_stk}</div>
        <div style="color:#CCC;">{hero_sec}</div>
        <div style="font-size:20px; color:#FFF; font-weight:bold;">₹{live_price}</div>
        <hr style="border-color:#444;">
        <div style="text-align:center;">
            <div style="font-size:14px; color:#888;">CURRENT STRATEGY</div>
            <div class="signal-text {color}">{decision}</div>
            <div style="font-size:12px; color:#CCC;">{reason}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ⚡ INTRADAY HORA SCHEDULE")
    st.caption("Trade only when the Hora Ruler (Right) matches the Stock Ruler.")
    
    # HORA TABLE
    for h in horas:
        r_name = PLANET_NAMES[h['Ruler']]
        s_time = h['Start'].strftime('%H:%M')
        e_time = h['End'].strftime('%H:%M')
        
        # Highlight Logic
        is_active = (h == active_hora)
        is_match = (h['Ruler'] == hero_ruler)
        
        bg = "#222"
        border = "#333"
        txt = "#888"
        
        if is_active:
            bg = "#002200"
            border = "#00FF99"
            txt = "#FFF"
        elif is_match:
            bg = "#222200" # Potential window
            border = "#FFCC00"
            txt = "#FFCC00"
            
        st.markdown(f"""
        <div style="background:{bg}; border:1px solid {border}; padding:10px; margin-bottom:5px; border-radius:5px; display:flex; justify-content:space-between;">
            <div style="color:{txt}; font-weight:bold;">{s_time} - {e_time}</div>
            <div style="color:{txt}; font-weight:bold;">{r_name} HORA</div>
            <div style="color:{txt};">{'🎯 TARGET' if is_match else ''} {'👈 NOW' if is_active else ''}</div>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("### ⚔️ ARSENAL")
    
    t1, t2 = st.tabs(["NIFTY", "BANK NIFTY"])
    
    with t1:
        st.info("NIFTY 50 OPTIONS")
        # Logic based on current Hora
        bias = "SIDEWAYS"
        if active_ruler in [swe.JUPITER, swe.SUN, swe.MARS]: bias = "BULLISH (Call)"
        elif active_ruler in [swe.SATURN, NODE_ID]: bias = "BEARISH (Put)"
        st.metric("HORA BIAS", bias)
        
    with t2:
        st.info("BANK NIFTY OPTIONS")
        # Bank Nifty loves Mercury & Jupiter
        bn_bias = "CHOPPY"
        if active_ruler in [swe.MERCURY, swe.JUPITER]: bn_bias = "ROCKET (Call)"
        st.metric("HORA BIAS", bn_bias)

    st.markdown("---")
    st.caption(f"Calibrated for {u_dob.strftime('%d-%b-%Y')} | Venus Energy")