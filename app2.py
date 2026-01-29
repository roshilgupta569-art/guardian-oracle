import streamlit as st
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import yfinance as yf
import google.generativeai as genai
import swisseph as swe

# ================= 1. VEDIC CONFIGURATION =================
st.set_page_config(
    page_title="GUARDIAN v26: VEDIC TRUTH",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #050505;}
    
    /* VEDIC HERO CARD */
    .hero-card {
        background: linear-gradient(180deg, #120a1f 0%, #1e1233 100%); /* Deep Purple */
        border: 1px solid #4a306e;
        border-top: 3px solid #d4af37; /* Gold for Astrology */
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
    }
    
    /* AI BOX */
    .ai-box {
        background-color: #0d1117;
        border-left: 4px solid #a855f7;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
        font-family: 'Consolas', monospace; font-size: 14px; color: #CCC;
    }
    
    /* BADGES */
    .sniper-badge {background: #004400; color: #00FF99; padding: 5px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #00FF99;}
    .trap-badge {background: #440000; color: #FF3333; padding: 5px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #FF3333;}
    .wait-badge {background: #222; color: #888; padding: 5px 10px; border-radius: 4px; font-weight: bold; border: 1px solid #444;}
    
    /* TEXT */
    .label {font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px;}
    .value-huge {font-size: 42px; font-weight: 800; color: #FFF; line-height: 1;}
    .value-med {font-size: 24px; font-weight: 700; color: #FFF;}
    .astro-text {color: #d4af37; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ================= 2. VEDIC DATABASE =================
IST = pytz.timezone("Asia/Kolkata")
LAT, LON = 19.0760, 72.8777 # Mumbai (Default for NSE)

# PLANETARY RULERS (The Truth)
RULERS = {
    "BANK": "MERCURY",   # Mercury rules Trade/Money
    "IT": "SATURN",      # Saturn rules Tech/Structure
    "AUTO": "VENUS",     # Venus rules Luxury/Vehicles
    "FMCG": "MOON",      # Moon rules Liquids/Food
    "METAL": "MARS",     # Mars rules Fire/Metal
    "ENERGY": "SUN",     # Sun rules Power/Light
    "REALTY": "MARS",    # Mars rules Land
    "PSU": "JUPITER"     # Jupiter rules Treasury
}

STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK"],
    "IT": ["TCS", "INFY", "HCLTECH"],
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "FMCG": ["ITC", "HUL"],
    "METAL": ["TATASTEEL", "JINDALSTEL"],
    "ENERGY": ["NTPC", "POWERGRID", "RELIANCE"]
}

# ================= 3. ASTRO ENGINE (pyswisseph) =================
def get_sunrise(date_obj):
    """Calculates Precise Sunrise for HORA calculation"""
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12)
    rise = swe.rise_trans(
        jd, swe.SUN, "", swe.FLG_SWIEPH, swe.CALC_RISE, (LON, LAT, 0.0)
    )[1][0]
    y, m, d, h_dec = swe.revjul(rise)
    h, mn = int(h_dec), int((h_dec - int(h_dec)) * 60)
    return pytz.utc.localize(datetime(y, m, d, h, mn)).astimezone(IST)

def get_hora_lord(current_dt):
    """
    Returns the Planet Ruling the current hour (Hora).
    This is the KEY to filtering fake signals.
    """
    sunrise = get_sunrise(current_dt)
    
    # Check if pre-market (use previous day's logic if needed, or wait)
    if current_dt < sunrise: return "WAIT", sunrise
    
    # 1 Hora = approx 1 hour (simplified for intraday)
    # Accurate Vedic sequence:
    # Day Lord starts 1st Hora. Then: Sun->Ven->Mer->Mon->Sat->Jup->Mar
    # Note: This is the speed order (Chaldean)
    
    weekday = current_dt.weekday() # 0=Mon
    day_lords = ["MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "SUN"]
    day_lord = day_lords[weekday]
    
    # Chaldean Sequence
    seq = ["SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY", "MOON"]
    
    # Find start index
    start_idx = seq.index(day_lord)
    
    # Hours since sunrise
    hours_passed = int((current_dt - sunrise).total_seconds() / 3600)
    
    current_ruler = seq[(start_idx + hours_passed) % 7]
    return current_ruler, sunrise

def get_next_sniper_time(target_planet, current_dt):
    """
    Calculates exactly WHEN the target planet's Hora starts.
    """
    sunrise = get_sunrise(current_dt)
    weekday = current_dt.weekday()
    day_lords = ["MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "SUN"]
    day_lord = day_lords[weekday]
    seq = ["SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY", "MOON"]
    start_idx = seq.index(day_lord)
    
    # Scan next 12 hours
    for i in range(12):
        ruler = seq[(start_idx + i) % 7]
        if ruler == target_planet:
            sniper_time = sunrise + timedelta(hours=i)
            if sniper_time > current_dt:
                return sniper_time.strftime("%H:%M")
    return "TOMORROW"

# ================= 4. SIGNAL ENGINE =================
@st.cache_data(ttl=60)
def get_ltp(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        df = ticker.history(period="1d", interval="1m")
        return round(df["Close"].iloc[-1], 2)
    except: return 0.0

def analyze_stock(ticker, sector, current_dt):
    stock_planet = RULERS[sector]
    current_hora, sunrise = get_hora_lord(current_dt)
    
    # LOGIC 1: DAY LORD FILTER
    # Example: If Thursday (Jupiter), Bank stocks are naturally stronger.
    weekday = current_dt.weekday()
    day_lords = ["MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "SUN"]
    day_lord = day_lords[weekday]
    
    day_strength = 0
    if stock_planet == day_lord: day_strength = 20
    
    # LOGIC 2: HORA FILTER (THE TRUTH FILTER)
    # If Hora Planet matches Stock Planet -> SNIPER ENTRY
    # If Hora Planet is Enemy -> FAKE SIGNAL
    
    status = "WAIT"
    css = "wait-badge"
    
    if stock_planet == current_hora:
        status = "SNIPER ENTRY"
        css = "sniper-badge"
    elif day_strength > 0:
        status = "ACCUMULATE"
        css = "sniper-badge" # Softer green
    else:
        # Enemy Logic (Simplified)
        enemies = {
            "SUN": ["SATURN", "VENUS"],
            "MOON": ["MERCURY", "SATURN"], 
            "MARS": ["MERCURY"],
            "MERCURY": ["MOON"],
            "JUPITER": ["MERCURY", "VENUS"],
            "VENUS": ["SUN", "MOON"],
            "SATURN": ["SUN", "MOON", "MARS"]
        }
        if current_hora in enemies.get(stock_planet, []):
            status = "TRAP / FAKE"
            css = "trap-badge"
            
    # CALCULATE NEXT ENTRY
    entry_time = get_next_sniper_time(stock_planet, current_dt)
    
    return status, css, entry_time, stock_planet, current_hora

# ================= 5. AI STRATEGIST =================
def ask_ai(ticker, status, entry_time, planet):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are a Vedic Financial Astrologer.
        Stock: {ticker} (Ruled by {planet}).
        Signal: {status}.
        Next Alignment Time: {entry_time}.
        
        Write 1 sentence. If Signal is TRAP, warn user to wait for {entry_time}. 
        If SNIPER, tell them the planetary alignment is perfect.
        """
        return model.generate_content(prompt).text
    except: return "AI Disconnected."

# ================= 6. DASHBOARD =================
# SIDEBAR
st.sidebar.title("🕉️ VEDIC CONTROL")
mode = st.sidebar.radio("MODE", ["LIVE MARKET", "BACKTEST LAB"])

if mode == "LIVE MARKET":
    curr_dt = datetime.now(IST)
    st.sidebar.success(f"LIVE: {curr_dt.strftime('%H:%M:%S')}")
else:
    d = st.sidebar.date_input("Date", datetime.now(IST))
    t = st.sidebar.slider("Time", time(9,15), time(15,30), time(11,0))
    curr_dt = datetime.combine(d, t).replace(tzinfo=IST)

# HEADER
hora, _ = get_hora_lord(curr_dt)
day_lords = ["MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "SUN"]
day_lord = day_lords[curr_dt.weekday()]

st.title(f"GUARDIAN v26: VEDIC TRUTH")
st.caption(f"DAY LORD: {day_lord} | CURRENT HORA: {hora} (The Time Ruler)")

# MAIN LOGIC
# We select the "Day Hero" based on the Day Lord first
primary_sector = "BANK" # Default
for sec, ruler in RULERS.items():
    if ruler == day_lord:
        primary_sector = sec
        break

hero_stock = STOCKS[primary_sector][0] # Pick leader of that sector

# Analyze Hero
status, css, entry, planet, h_lord = analyze_stock(hero_stock, primary_sector, curr_dt)
ltp = get_ltp(hero_stock) if mode == "LIVE MARKET" else "---"

# AI Insight
if mode == "LIVE MARKET":
    with st.spinner("Consulting the Stars..."):
        ai_msg = ask_ai(hero_stock, status, entry, planet)
    st.markdown(f'<div class="ai-box"><b>🔮 ASTRO-STRATEGIST:</b> {ai_msg}</div>', unsafe_allow_html=True)

# HERO CARD
c1, c2 = st.columns([1.5, 1])
with c1:
    st.markdown(f"""
    <div class="hero-card">
        <div style="display:flex; justify-content:space-between;">
            <div class="label">DAY'S TRUE HERO (BASED ON {day_lord})</div>
            <div class="astro-text">{planet} POWER</div>
        </div>
        <div class="value-huge">{hero_stock}</div>
        <div class="value-med" style="color:#AAA;">{primary_sector}</div>
        <div class="value-med">₹{ltp}</div>
        <br>
        <div class="label">VEDIC VERDICT</div>
        <div class="{css}">{status}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    # THE TIME TO ENTER WIDGET
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">⏳ SNIPER ENTRY CLOCK</div>
        <div style="font-size:32px; font-weight:bold; color:#d4af37; margin-bottom:10px;">
            {entry}
        </div>
        <div style="font-size:14px; color:#CCC;">
            This is when the <b>{planet} HORA</b> begins.
        </div>
        <hr style="border-color:#444;">
        <div style="font-size:12px; color:#888;">
            CURRENT RULER: <b style="color:#FFF">{h_lord}</b><br>
            STOCK RULER: <b style="color:#FFF">{planet}</b><br>
            MATCH: {'✅ YES' if h_lord == planet else '❌ NO (Wait)'}
        </div>
    </div>
    """, unsafe_allow_html=True)

# TABS
st.markdown("### 🔭 DEEP DIVE")
t1, t2 = st.tabs(["⚡ INTRADAY SCANNER", "📜 HORA SCHEDULE"])

with t1:
    st.caption("Scanning all sectors against Current Hora...")
    cols = st.columns(3)
    
    # Scan all stocks
    idx = 0
    for sec, stock_list in STOCKS.items():
        for s in stock_list:
            if s == hero_stock: continue
            
            stat, badge, ent, p, _ = analyze_stock(s, sec, curr_dt)
            
            # Show only matches or strong stocks
            if "SNIPER" in stat or "ACCUMULATE" in stat:
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div style="background:#111; border:1px solid #333; padding:15px; border-radius:8px; margin-bottom:10px;">
                        <div style="color:#FFF; font-weight:bold;">{s}</div>
                        <div style="font-size:12px; color:#d4af37;">Rules: {p}</div>
                        <div style="margin-top:5px;"><span class="{badge}">{stat}</span></div>
                        <div style="font-size:12px; color:#888; margin-top:5px;">Enter at: {ent}</div>
                    </div>
                    """, unsafe_allow_html=True)
                idx += 1
    if idx == 0:
        st.info("No planets align right now. Market is in conflict. Wait for the next Hora.")

with t2:
    st.caption("Planetary Hours for Today")
    sunrise = get_sunrise(curr_dt)
    day_lords = ["MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "SUN"]
    day_lord = day_lords[curr_dt.weekday()]
    seq = ["SATURN", "JUPITER", "MARS", "SUN", "VENUS", "MERCURY", "MOON"]
    start_idx = seq.index(day_lord)
    
    times = []
    for i in range(12):
        ruler = seq[(start_idx + i) % 7]
        start_t = sunrise + timedelta(hours=i)
        end_t = start_t + timedelta(hours=1)
        
        # Formatting
        active = start_t <= curr_dt < end_t
        bg = "#222200" if active else "#111"
        border = "#d4af37" if active else "#333"
        
        st.markdown(f"""
        <div style="background:{bg}; border:1px solid {border}; padding:10px; border-radius:5px; margin-bottom:5px; display:flex; justify-content:space-between;">
            <div style="color:#FFF;">{start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}</div>
            <div style="color:#d4af37; font-weight:bold;">{ruler} HORA</div>
            <div style="color:#888;">{'👈 ACTIVE' if active else ''}</div>
        </div>
        """, unsafe_allow_html=True)