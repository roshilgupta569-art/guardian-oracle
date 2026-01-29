import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import yfinance as yf
import google.generativeai as genai

# ================= 1. CONFIGURATION =================
st.set_page_config(
    page_title="GUARDIAN v31: STABLE CORE",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #000;}
    .hero-card {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d; border-top: 3px solid #D4AF37;
        padding: 20px; border-radius: 10px; margin-bottom: 15px;
    }
    .scanner-card {
        background: #111; border: 1px solid #333; 
        padding: 15px; border-radius: 6px; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .ai-box {
        background-color: #0d1117; border-left: 4px solid #a855f7;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
        font-family: 'Consolas', monospace; font-size: 14px; color: #CCC;
    }
    .label {font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}
    .ticker-huge {font-size: 38px; font-weight: 800; color: #FFF; line-height: 1;}
    .score-green {color: #00FF99; font-weight: bold;}
    .score-gold {color: #D4AF37; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ================= 2. SECURITY & CONSTANTS =================
def check_password():
    if st.session_state.get("auth", False): return True
    if "general" not in st.secrets:
        st.warning("⚠️ RUNNING IN DEV MODE (NO PASSWORD)")
        return True
    
    pwd = st.text_input("ACCESS KEY", type="password")
    if st.button("UNLOCK"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")
# Chandigarh Coordinates (Must be float)
LAT = 30.7333
LON = 76.7794
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

# Bio-Calibration (Venus)
USER_LORD = swe.VENUS 

SECTOR_MAP = {
    "AUTO": swe.VENUS, "IT": swe.SATURN, "BANK": swe.MERCURY, "PSU": swe.JUPITER,
    "PHARMA": swe.SUN, "FMCG": swe.MOON, "METALS": swe.MARS, 
    "TELECOM": NODE_ID, "ENERGY": swe.SUN
}

STOCKS_DB = [
    {"Ticker": "TATAMOTORS", "Sector": "AUTO"}, {"Ticker": "MARUTI", "Sector": "AUTO"},
    {"Ticker": "TCS", "Sector": "IT"}, {"Ticker": "INFY", "Sector": "IT"},
    {"Ticker": "HDFCBANK", "Sector": "BANK"}, {"Ticker": "ICICIBANK", "Sector": "BANK"},
    {"Ticker": "SBIN", "Sector": "PSU"}, {"Ticker": "ITC", "Sector": "FMCG"},
    {"Ticker": "TATASTEEL", "Sector": "METALS"}, {"Ticker": "RELIANCE", "Sector": "ENERGY"},
    {"Ticker": "SUNPHARMA", "Sector": "PHARMA"}, {"Ticker": "BHARTIARTL", "Sector": "TELECOM"}
]

for s in STOCKS_DB:
    s['Ruler'] = SECTOR_MAP[s['Sector']]

# ================= 3. ASTRO ENGINE (FIXED) =================
def get_sunrise(date_obj):
    """
    Calculates sunrise with strict type enforcement to prevent TypeError.
    """
    try:
        # 1. Force Date to Noon UTC to avoid date skipping
        jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12.0)
        
        # 2. Strict Float Tuple for Geopos (Longitude, Latitude, Height)
        geopos = (float(LON), float(LAT), 0.0)
        
        # 3. Calculate Rise
        rise = swe.rise_trans(
            jd, 
            swe.SUN, 
            "", 
            swe.FLG_SWIEPH, 
            swe.CALC_RISE, 
            geopos
        )[1][0]
        
        # 4. Convert to IST
        y, m, d, h_dec = swe.revjul(rise)
        h = int(h_dec)
        mn = int((h_dec - h) * 60)
        dt_utc = datetime(y, m, d, h, mn)
        return pytz.utc.localize(dt_utc).astimezone(IST)
        
    except Exception as e:
        # Fail-safe: Return 6:00 AM IST if astro calc fails
        return datetime.combine(date_obj, time(6, 0)).replace(tzinfo=IST)

def get_hora_lord(current_dt):
    sunrise = get_sunrise(current_dt)
    
    # Handle pre-market (before sunrise)
    if current_dt < sunrise: 
        return "SUN", swe.SUN, sunrise 
    
    day_lords = [swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.SUN]
    day_lord = day_lords[current_dt.weekday()]
    
    # Chaldean Order
    chaldean = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
    start_idx = chaldean.index(day_lord)
    
    # Calculate Hora Index (1 Hora ~= 1 Hour)
    hours_passed = int((current_dt - sunrise).total_seconds() / 3600)
    
    current_ruler = chaldean[(start_idx + hours_passed) % 7]
    return get_planet_name(current_ruler), current_ruler, sunrise

def get_planet_name(pid):
    return {swe.SUN:"SUN", swe.MOON:"MOON", swe.MARS:"MARS", swe.MERCURY:"MERCURY", 
            swe.JUPITER:"JUPITER", swe.VENUS:"VENUS", swe.SATURN:"SATURN", NODE_ID:"RAHU"}.get(pid, "UKN")

# ================= 4. LOGIC ENGINE =================
@st.cache_data(ttl=60)
def get_ltp(ticker):
    try:
        t = yf.Ticker(ticker + ".NS")
        data = t.history(period="1d", interval="1m")
        return round(data["Close"].iloc[-1], 2) if not data.empty else 0.0
    except: return 0.0

def calculate_score(stock, h_lord_id, d_lord_id):
    score = 50
    # Day Theme
    if stock['Ruler'] == d_lord_id: score += 15
    # Hora Timing (Critical)
    if stock['Ruler'] == h_lord_id: score += 30
    # Bio Match
    if stock['Ruler'] == USER_LORD: score += 20
    
    status = "SNIPER" if score >= 90 else "ACCUMULATE" if score >= 70 else "WAIT"
    return score, status

def ask_ai(ticker, score, h_lord_name):
    try:
        if "GEMINI_KEY" not in st.secrets: return "AI Key Missing."
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Stock: {ticker}. Score: {score}/100. Hora: {h_lord_name}. Give 1 sentence of trading advice."
        return model.generate_content(prompt).text
    except: return "AI Offline."

# ================= 5. APP LAYOUT =================
st.sidebar.title("🦅 GUARDIAN")
mode = st.sidebar.radio("MODE", ["LIVE MARKET", "BACKTEST LAB"])

if mode == "LIVE MARKET":
    now = datetime.now(IST)
else:
    d = st.sidebar.date_input("Date", datetime.now(IST))
    t = st.sidebar.slider("Time", time(9,15), time(15,30), time(10,0))
    now = datetime.combine(d, t).replace(tzinfo=IST)

# 1. CALCULATE STATE
h_name, h_id, sunrise = get_hora_lord(now)
day_lords = [swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.SUN]
d_id = day_lords[now.weekday()]
d_name = get_planet_name(d_id)

st.title(f"GUARDIAN v31 • {now.strftime('%H:%M')}")
st.caption(f"ACTIVE HORA: {h_name} | DAY LORD: {d_name}")

# 2. SCAN & RANK
ranked = []
for s in STOCKS_DB:
    sc, stat = calculate_score(s, h_id, d_id)
    ranked.append({**s, "Score": sc, "Status": stat})
ranked.sort(key=lambda x: x['Score'], reverse=True)
top = ranked[0]

# 3. AI INSIGHT
if mode == "LIVE MARKET":
    with st.spinner("AI Scanning..."):
        ai_msg = ask_ai(top['Ticker'], top['Score'], h_name)
    st.markdown(f'<div class="ai-box"><b>STRATEGIST:</b> {ai_msg}</div>', unsafe_allow_html=True)

# 4. TOP PICK CARD
ltp = get_ltp(top['Ticker']) if mode == "LIVE MARKET" else "---"
c1, c2 = st.columns([1.5, 1])

with c1:
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">ALGO LEADER</div>
        <div class="ticker-huge">{top['Ticker']}</div>
        <div class="label" style="color:#D4AF37; margin-top:5px;">{top['Sector']}</div>
        <hr style="border-color:#333;">
        <div style="display:flex; justify-content:space-between;">
            <div><div class="label">PRICE</div><div style="font-size:24px; font-weight:700;">₹{ltp}</div></div>
            <div style="text-align:right;"><div class="label">CONFIDENCE</div><div style="font-size:24px; font-weight:800; color:#00FF99;">{top['Score']}%</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">ALIGNMENT</div>
        <div style="font-size:20px; font-weight:bold; color:#FFF;">{h_name} HORA</div>
        <div class="label" style="margin-top:10px;">VERDICT</div>
        <div style="font-size:28px; font-weight:bold; color:{'#00FF99' if top['Score']>80 else '#D4AF37'};">
            {top['Status']}
        </div>
    </div>
    """, unsafe_allow_html=True)

# 5. SCANNER TABS
t1, t2 = st.tabs(["📡 RADAR", "📊 P&L SIM"])

with t1:
    cols = st.columns(3)
    for i, s in enumerate(ranked[:9]):
        col_cls = "score-green" if s['Score'] >= 90 else "score-gold"
        with cols[i % 3]:
            st.markdown(f"""
            <div class="scanner-card">
                <div>
                    <div style="color:#FFF; font-weight:bold;">{s['Ticker']}</div>
                    <div class="label">{s['Sector']}</div>
                </div>
                <div class="{col_cls}">{s['Score']}%</div>
            </div>
            """, unsafe_allow_html=True)

with t2:
    if mode == "BACKTEST LAB":
        st.info(f"Simulating Trade: Buy {top['Ticker']} at {now.strftime('%H:%M')}")
    else:
        st.info("Switch to BACKTEST mode to run P&L simulations.")