import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import requests
import pandas as pd
import altair as alt

# ================== 1. INSTITUTIONAL UI ==================
st.set_page_config(
    page_title="GUARDIAN ORACLE v20",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #000000;}
    
    /* ANALYST LOG STYLE */
    .oracle-log {
        font-family: 'Courier New', monospace;
        background-color: #0d1117;
        border-left: 3px solid #D4AF37;
        padding: 15px;
        color: #CCC;
        font-size: 14px;
        margin-bottom: 20px;
    }
    .log-step {margin-bottom: 5px; color: #888;}
    .log-final {font-weight: bold; color: #FFF; margin-top: 10px;}
    
    /* CARDS */
    .hero-card {
        background: linear-gradient(180deg, #151515 0%, #0a0a0a 100%);
        border: 1px solid #333;
        border-top: 3px solid #00E676; /* Signal Color */
        padding: 24px;
        border-radius: 6px;
    }
    .metric-box {
        background-color: #111; border: 1px solid #222; 
        padding: 15px; border-radius: 6px; text-align: center;
    }
    
    /* TEXT */
    .ticker-huge {font-size: 48px; font-weight: 800; color: #FFF; letter-spacing: -1px;}
    .label {font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}
    .value-green {color: #00E676; font-weight: bold;}
    .value-red {color: #FF1744; font-weight: bold;}
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] { background-color: #000; border-bottom: 1px solid #333; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #D4AF37; border-bottom: 2px solid #D4AF37; }
</style>
""", unsafe_allow_html=True)

# ================== 2. SECURITY ==================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("ORACLE ACCESS KEY", type="password")
    if st.button("CONNECT MIND"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")
LAT, LON = 30.7333, 76.7794 # Chandigarh
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

# ================== 3. DATA MATRIX ==================
SECTOR_MAP = {
    "BANK": swe.MERCURY, "IT": swe.SATURN, "AUTO": swe.VENUS, "PHARMA": swe.SUN, 
    "FMCG": swe.MOON, "METALS": swe.MARS, "ENERGY": swe.SUN, "REALTY": swe.MARS, 
    "TELECOM": NODE_ID, "FINANCE": swe.JUPITER
}

STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "FMCG": ["ITC", "HUL"],
    "METALS": ["TATASTEEL", "JSWSTEEL"],
    "ENERGY": ["NTPC", "POWERGRID", "RELIANCE"],
    "REALTY": ["DLF"],
    "PHARMA": ["SUNPHARMA"]
}

NIFTY_DB = []
for sec, ticks in STOCKS.items():
    for t in ticks:
        NIFTY_DB.append({"Ticker": t, "Sector": sec, "Ruler": SECTOR_MAP[sec]})

# ================== 4. THE THINKING ENGINE (ASTRO) ==================
def get_planet_name(pid):
    names = {swe.SUN:"SUN", swe.MOON:"MOON", swe.MARS:"MARS", swe.MERCURY:"MERCURY", 
             swe.JUPITER:"JUPITER", swe.VENUS:"VENUS", swe.SATURN:"SATURN", NODE_ID:"RAHU"}
    return names.get(pid, "Unknown")

def get_current_hora(date_obj):
    # Accurate Sunrise Calculation
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12)
    rise = swe.rise_trans(jd, swe.SUN, LON, LAT, rsmi=swe.CALC_RISE)[1][0]
    
    # Convert to DT
    y, m, d, h_dec = swe.revjul(rise)
    h, mn = int(h_dec), int((h_dec - int(h_dec)) * 60)
    sunrise = pytz.utc.localize(datetime(y, m, d, h, mn)).astimezone(IST)
    
    # Hora Logic (1 hr from sunrise)
    elapsed = (date_obj - sunrise).total_seconds() / 3600
    if elapsed < 0: elapsed = 0
    hora_idx = int(elapsed) % 7
    
    # Chaldean Sequence
    day_lords = [swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.SUN]
    day_lord = day_lords[date_obj.weekday()]
    
    chaldean = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
    start_idx = chaldean.index(day_lord)
    current_ruler = chaldean[(start_idx + hora_idx) % 7]
    
    return current_ruler, day_lord

# ================== 5. THE ANALYST MIND (TEXT GEN) ==================
def generate_analysis(stock, hora_ruler, day_lord, user_dob):
    """
    This function simulates my thinking process.
    It returns a structured log of the decision logic.
    """
    stock_ruler = stock['Ruler']
    user_lord = swe.VENUS # Hardcoded for Roshil (Friday born)
    
    r_name = get_planet_name(stock_ruler)
    h_name = get_planet_name(hora_ruler)
    d_name = get_planet_name(day_lord)
    
    log = []
    score = 50
    
    # STEP 1: GLOBAL CONTEXT
    log.append(f"📡 **SCANNING:** {stock['Ticker']} ({stock['Sector']})")
    log.append(f"⚙️ **RULER:** {r_name} | **HORA:** {h_name}")
    
    # STEP 2: PERSONAL RESONANCE
    # Venus (User) loves Mercury, Saturn, Rahu.
    if stock_ruler == swe.VENUS:
        score += 20
        log.append("👤 **BIO-MATCH:** PERFECT. Stock matches your Venus energy.")
    elif stock_ruler in [swe.MERCURY, swe.SATURN, NODE_ID]:
        score += 15
        log.append("👤 **BIO-MATCH:** HIGH. Friendly planet for you.")
    elif stock_ruler in [swe.SUN, swe.MOON]:
        score -= 10
        log.append("⚠️ **BIO-CONFLICT:** Stock ruler conflicts with Venus.")
    else:
        log.append("👤 **BIO-MATCH:** NEUTRAL.")
        
    # STEP 3: TIMING (HORA)
    if stock_ruler == hora_ruler:
        score += 30
        log.append(f"⚡ **TIMING:** JACKPOT. {h_name} Hora aligns with {r_name} Stock.")
    elif stock_ruler == day_lord:
        score += 10
        log.append(f"📅 **THEME:** Stock matches Day Lord ({d_name}). Good support.")
    else:
        log.append(f"⏳ **TIMING:** Wait. Current Hora ({h_name}) is indifferent.")
        
    # VERDICT
    if score > 80: verdict = "ROCKET ENTRY 🚀"
    elif score > 60: verdict = "ACCUMULATE ✅"
    else: verdict = "WATCH / AVOID ⛔"
    
    return log, verdict, score

# ================== 6. LIVE DATA ==================
def get_live_price(ticker):
    try:
        url = f"https://indian-stock-market-api.vercel.app/stock/{ticker}"
        data = requests.get(url, timeout=0.5).json()
        return float(data['lastPrice'].replace(',', '')), float(data['pChange'])
    except: return 0.0, 0.0

# ================== 7. APP INTERFACE ==================
# Sidebar
st.sidebar.markdown("### 🕹️ COMMAND")
sel_date = st.sidebar.date_input("Date", datetime.now(IST))
sim_time = datetime.now(IST).time()
if sel_date != datetime.now(IST).date():
    sim_time = st.sidebar.slider("Sim Time", time(9,15), time(15,30), time(9,15))
    
current_dt = datetime.combine(sel_date, sim_time).replace(tzinfo=IST)
hora_ruler, day_lord = get_current_hora(current_dt)

# FIND BEST STOCK
best_stock = None
best_score = -1
best_log = []
best_verdict = ""

for s in NIFTY_DB:
    log, verd, scor = generate_analysis(s, hora_ruler, day_lord, datetime(2006, 2, 17))
    if scor > best_score:
        best_score = scor
        best_stock = s
        best_log = log
        best_verdict = verd

price, chg = get_live_price(best_stock['Ticker'])

# MAIN DISPLAY
st.title("GUARDIAN: ANALYST MODE")
st.caption(f"USER: ROSHIL GUPTA | CALIBRATION: VENUS (FRI) | {current_dt.strftime('%d %b %H:%M')}")

# LAYOUT: LEFT (DATA), RIGHT (THINKING)
col_left, col_right = st.columns([1, 1.2])

with col_left:
    # HERO CARD
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">CURRENT ALPHA PICK</div>
        <div class="ticker-huge">{best_stock['Ticker']}</div>
        <div class="label">{best_stock['Sector']}</div>
        <br>
        <div class="row-flex">
            <div>
                <div class="label">PRICE</div>
                <div class="value-large">₹{price}</div>
            </div>
            <div style="text-align:right;">
                <div class="label">SIGNAL</div>
                <div class="value-large" style="color:{'#00E676' if best_score>70 else '#CCC'}">{best_verdict}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # METRICS GRID
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""<div class="metric-box"><div class="label">ACTIVE HORA</div><div class="value-med">{get_planet_name(hora_ruler)}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-box"><div class="label">CONFIDENCE</div><div class="value-med">{int(best_score)}%</div></div>""", unsafe_allow_html=True)

with col_right:
    st.markdown("### 🧠 ORACLE ANALYSIS LOG")
    # PRINTING THE THINKING PROCESS
    log_html = ""
    for line in best_log:
        log_html += f"<div class='log-step'>{line}</div>"
    
    st.markdown(f"""
    <div class="oracle-log">
        {log_html}
        <div class="log-final">>> FINAL VERDICT: {best_verdict}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # INTRADAY CHART
    st.markdown("### 📉 MOMENTUM FORECAST")
    timeline = []
    t_iter = datetime.combine(sel_date, time(9,15)).replace(tzinfo=IST)
    while t_iter < datetime.combine(sel_date, time(15,30)).replace(tzinfo=IST):
        h, _ = get_current_hora(t_iter)
        _, _, s = generate_analysis(best_stock, h, day_lord, datetime(2006, 2, 17))
        timeline.append({"Time": t_iter.strftime("%H:%M"), "Score": s})
        t_iter += timedelta(minutes=15)
        
    df = pd.DataFrame(timeline)
    c = alt.Chart(df).mark_line(color='#D4AF37').encode(
        x='Time', y=alt.Y('Score', scale=alt.Scale(domain=[40, 100]))
    ).properties(height=200)
    st.altair_chart(c, use_container_width=True)

# TABS (ARSENAL)
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["NIFTY OPTIONS", "BANK NIFTY", "ROCKET STOCKS"])

with tab1:
    bias = "BULLISH" if hora_ruler in [swe.JUPITER, swe.MARS, swe.SUN] else "BEARISH"
    st.info(f"NIFTY VIEW: {bias} (Based on {get_planet_name(hora_ruler)} Hora)")
    
with tab2:
    bn_bias = "ROCKET" if hora_ruler in [swe.MERCURY, swe.JUPITER] else "CHOPPY"
    st.info(f"BANK NIFTY VIEW: {bn_bias}")

with tab3:
    st.write("Other High Probability Setups:")
    cols = st.columns(4)
    valid = [s for s in NIFTY_DB if s['Ticker'] != best_stock['Ticker']]
    count = 0
    for s in valid:
        _, _, sc = generate_analysis(s, hora_ruler, day_lord, datetime(2006, 2, 17))
        if sc > 70:
            with cols[count % 4]:
                st.markdown(f"**{s['Ticker']}** ({int(sc)}%)")
            count += 1