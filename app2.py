import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import yfinance as yf
import google.generativeai as genai

# ================= 1. SYSTEM CONFIG =================
st.set_page_config(
    page_title="GUARDIAN v30: OMNI-SCANNER",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #000;}
    
    /* CARDS */
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
    
    /* AI BOX */
    .ai-box {
        background-color: #0d1117; border-left: 4px solid #a855f7;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
        font-family: 'Consolas', monospace; font-size: 14px; color: #CCC;
    }
    
    /* TEXT */
    .label {font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}
    .ticker-huge {font-size: 38px; font-weight: 800; color: #FFF; line-height: 1;}
    .score-green {color: #00FF99; font-weight: bold;}
    .score-gold {color: #D4AF37; font-weight: bold;}
    .score-gray {color: #666; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ================= 2. SECURITY & CONSTANTS =================
def check_password():
    if st.session_state.get("auth", False): return True
    # Graceful fail if secrets missing
    if "general" not in st.secrets:
        st.warning("⚠️ SECURITY BYPASS: Running in Dev Mode (Add secrets to lock).")
        return True
    
    pwd = st.text_input("ACCESS KEY", type="password")
    if st.button("UNLOCK"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")
LAT, LON = 30.7333, 76.7794 # Chandigarh
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

# ROSHIL'S BIO-CALIBRATION (Venus Lord)
USER_LORD = swe.VENUS 

SECTOR_MAP = {
    "AUTO": swe.VENUS, "IT": swe.SATURN, "BANK": swe.MERCURY, "PSU": swe.JUPITER,
    "PHARMA": swe.SUN, "FMCG": swe.MOON, "METALS": swe.MARS, 
    "TELECOM": NODE_ID, "ENERGY": swe.SUN
}

# EXPANDED UNIVERSE (20+ Stocks)
STOCKS_DB = [
    {"Ticker": "TATAMOTORS", "Sector": "AUTO"}, {"Ticker": "MARUTI", "Sector": "AUTO"}, {"Ticker": "M&M", "Sector": "AUTO"},
    {"Ticker": "TCS", "Sector": "IT"}, {"Ticker": "INFY", "Sector": "IT"}, {"Ticker": "HCLTECH", "Sector": "IT"},
    {"Ticker": "HDFCBANK", "Sector": "BANK"}, {"Ticker": "ICICIBANK", "Sector": "BANK"}, {"Ticker": "AXISBANK", "Sector": "BANK"},
    {"Ticker": "SBIN", "Sector": "PSU"}, {"Ticker": "PNB", "Sector": "PSU"},
    {"Ticker": "ITC", "Sector": "FMCG"}, {"Ticker": "HUL", "Sector": "FMCG"},
    {"Ticker": "TATASTEEL", "Sector": "METALS"}, {"Ticker": "JSWSTEEL", "Sector": "METALS"}, {"Ticker": "HINDALCO", "Sector": "METALS"},
    {"Ticker": "RELIANCE", "Sector": "ENERGY"}, {"Ticker": "NTPC", "Sector": "ENERGY"}, {"Ticker": "POWERGRID", "Sector": "ENERGY"},
    {"Ticker": "SUNPHARMA", "Sector": "PHARMA"}, {"Ticker": "CIPLA", "Sector": "PHARMA"},
    {"Ticker": "BHARTIARTL", "Sector": "TELECOM"}
]

# Attach Rulers
for s in STOCKS_DB:
    s['Ruler'] = SECTOR_MAP[s['Sector']]

# ================= 3. ASTRO ENGINE =================
def get_sunrise(date_obj):
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12)
    rise = swe.rise_trans(jd, swe.SUN, "", swe.FLG_SWIEPH, swe.CALC_RISE, (LON, LAT, 0.0))[1][0]
    y, m, d, h_dec = swe.revjul(rise)
    return pytz.utc.localize(datetime(y, m, d, int(h_dec), int((h_dec % 1) * 60))).astimezone(IST)

def get_hora_lord(current_dt):
    sunrise = get_sunrise(current_dt)
    if current_dt < sunrise: return "SUN", sunrise 
    
    day_lords = [swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.SUN]
    day_lord = day_lords[current_dt.weekday()]
    
    chaldean = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
    start_idx = chaldean.index(day_lord)
    
    hours_passed = int((current_dt - sunrise).total_seconds() / 3600)
    current_ruler = chaldean[(start_idx + hours_passed) % 7]
    
    return current_ruler, day_lord

def get_planet_name(pid):
    return {swe.SUN:"SUN", swe.MOON:"MOON", swe.MARS:"MARS", swe.MERCURY:"MERCURY", 
            swe.JUPITER:"JUPITER", swe.VENUS:"VENUS", swe.SATURN:"SATURN", NODE_ID:"RAHU"}.get(pid, "UKN")

# ================= 4. SIGNAL & AI ENGINES =================
@st.cache_data(ttl=60)
def get_ltp(ticker):
    try:
        t = yf.Ticker(ticker + ".NS")
        data = t.history(period="1d", interval="1m")
        return round(data["Close"].iloc[-1], 2) if not data.empty else 0.0
    except: return 0.0

def calculate_score(stock, h_lord, d_lord):
    score = 50
    # 1. Day Lord Match (Theme)
    if stock['Ruler'] == d_lord: score += 15
    # 2. Hora Match (Timing - CRITICAL)
    if stock['Ruler'] == h_lord: score += 30
    # 3. Bio Match (Venus)
    if stock['Ruler'] == USER_LORD: score += 20
    
    status = "SNIPER" if score >= 90 else "ACCUMULATE" if score >= 70 else "WAIT"
    return score, status

def ask_ai_scan(top_stock, score, h_lord):
    try:
        if "GEMINI_KEY" not in st.secrets: return "AI KEY MISSING."
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Market Scan Result: Top Pick is {top_stock['Ticker']} ({top_stock['Sector']}).
        Score: {score}/100. Active Hora: {get_planet_name(h_lord)}.
        Write 1 concise sentence advising a trader on this specific setup.
        """
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

# CALCULATE ENVIRONMENT
h_lord, d_lord = get_hora_lord(now)
h_name = get_planet_name(h_lord)

st.title(f"GUARDIAN v30 • {now.strftime('%H:%M')}")
st.caption(f"ACTIVE HORA: {h_name} | DAY LORD: {get_planet_name(d_lord)}")

# --- THE OMNI-SCANNER ---
# Rank all 25 stocks instantly
ranked_stocks = []
for s in STOCKS_DB:
    sc, stat = calculate_score(s, h_lord, d_lord)
    ranked_stocks.append({**s, "Score": sc, "Status": stat})

ranked_stocks.sort(key=lambda x: x['Score'], reverse=True)
top_pick = ranked_stocks[0]

# --- AI INSIGHT ---
if mode == "LIVE MARKET":
    with st.spinner("AI Scanning Market..."):
        ai_msg = ask_ai_scan(top_pick, top_pick['Score'], h_lord)
    st.markdown(f'<div class="ai-box"><b>🦅 STRATEGIST:</b> {ai_msg}</div>', unsafe_allow_html=True)

# --- HERO SECTION (TOP PICK) ---
ltp = get_ltp(top_pick['Ticker']) if mode == "LIVE MARKET" else "---"
c1, c2 = st.columns([1.5, 1])

with c1:
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">MARKET LEADER (ALGO RANK #1)</div>
        <div class="ticker-huge">{top_pick['Ticker']}</div>
        <div class="label" style="color:#D4AF37; margin-top:5px;">{top_pick['Sector']} | RULER: {get_planet_name(top_pick['Ruler'])}</div>
        <hr style="border-color:#333;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div><div class="label">PRICE</div><div style="font-size:24px; font-weight:700;">₹{ltp}</div></div>
            <div style="text-align:right;"><div class="label">CONFIDENCE</div><div style="font-size:24px; font-weight:800; color:#00FF99;">{top_pick['Score']}%</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">CURRENT ALIGNMENT</div>
        <div style="font-size:20px; font-weight:bold; color:#FFF;">{h_name} HORA</div>
        <div style="font-size:12px; color:#888; margin-bottom:15px;">Governs: {get_planet_name(top_pick['Ruler'])} Sector</div>
        
        <div class="label">VERDICT</div>
        <div style="font-size:28px; font-weight:bold; color:{'#00FF99' if top_pick['Score']>80 else '#D4AF37'};">
            {top_pick['Status']}
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- SCANNER TABS ---
t1, t2 = st.tabs(["📡 MULTI-ASSET RADAR", "📊 P&L SIMULATOR"])

with t1:
    st.markdown("### ⚡ LIVE OPPORTUNITIES")
    # Display Top 9 Stocks in a Grid
    cols = st.columns(3)
    for i, s in enumerate(ranked_stocks[:9]):
        col_class = "score-green" if s['Score'] >= 90 else "score-gold" if s['Score'] >= 70 else "score-gray"
        with cols[i % 3]:
            st.markdown(f"""
            <div class="scanner-card">
                <div>
                    <div style="color:#FFF; font-weight:bold;">{s['Ticker']}</div>
                    <div class="label">{s['Sector']}</div>
                </div>
                <div class="{col_class}">{s['Score']}%</div>
            </div>
            """, unsafe_allow_html=True)

with t2:
    if mode == "BACKTEST LAB":
        st.info("P&L Simulation active for Historical Data.")
        # (P&L Logic placeholder from v28 - safe to keep lightweight here)
        st.write(f"Simulating entry for {top_pick['Ticker']} at start of {h_name} Hora...")
    else:
        st.info("Switch to BACKTEST LAB to verify historical profits.")