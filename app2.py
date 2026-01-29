import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import yfinance as yf
import google.generativeai as genai
import hashlib

# ================== 1. PROFESSIONAL UI CONFIG ==================
st.set_page_config(
    page_title="GUARDIAN v28: PROFIT ORACLE",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #000000;}
    .hero-card {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d; border-top: 3px solid #D4AF37;
        padding: 24px; border-radius: 10px; margin-bottom: 20px;
    }
    .ai-box {
        background-color: #0d1117; border-left: 4px solid #a855f7;
        padding: 15px; border-radius: 8px; margin-bottom: 20px;
        font-family: 'Consolas', monospace; font-size: 14px; color: #CCC;
    }
    .pnl-pos {color: #00FF99; font-weight: 800; font-size: 24px;}
    .pnl-neg {color: #FF3333; font-weight: 800; font-size: 24px;}
    .label {font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}
    .ticker-huge {font-size: 42px; font-weight: 800; color: #FFF; line-height: 1;}
</style>
""", unsafe_allow_html=True)

# ================== 2. SECURITY & CONSTANTS ==================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("TERMINAL ACCESS KEY", type="password")
    if st.button("AUTHENTICATE"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")
LAT, LON = 30.7333, 76.7794 # Chandigarh
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

# Calibrated for Feb 17, 2006 (Friday -> Venus Lord)
USER_LORD = swe.VENUS

SECTOR_MAP = {
    "AUTO": swe.VENUS, "IT": swe.SATURN, "BANK": swe.MERCURY,
    "PSU": swe.JUPITER, "PHARMA": swe.SUN, "FMCG": swe.MOON,
    "METALS": swe.MARS, "TELECOM": NODE_ID
}

STOCKS = {
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "IT": ["TCS", "INFY", "HCLTECH"],
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK"],
    "ENERGY": ["RELIANCE", "NTPC"]
}

# ================== 3. ASTRO-PHYSICS ENGINE ==================
def get_sunrise(date_obj):
    jd = swe.julday(date_obj.year, date_obj.month, date_obj.day, 12)
    rise = swe.rise_trans(jd, swe.SUN, "", swe.FLG_SWIEPH, swe.CALC_RISE, (LON, LAT, 0.0))[1][0]
    y, m, d, h_dec = swe.revjul(rise)
    return pytz.utc.localize(datetime(y, m, d, int(h_dec), int((h_dec % 1) * 60))).astimezone(IST)

def get_hora_lord(current_dt):
    sunrise = get_sunrise(current_dt)
    day_lords = [swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER, swe.VENUS, swe.SATURN, swe.SUN]
    day_lord = day_lords[current_dt.weekday()]
    chaldean = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
    start_idx = chaldean.index(day_lord)
    hours_passed = int((current_dt - sunrise).total_seconds() / 3600)
    if hours_passed < 0: hours_passed = 0
    return chaldean[(start_idx + hours_passed) % 7], day_lord

def get_planet_name(pid):
    return {swe.SUN:"SUN", swe.MOON:"MOON", swe.MARS:"MARS", swe.MERCURY:"MERCURY", 
            swe.JUPITER:"JUPITER", swe.VENUS:"VENUS", swe.SATURN:"SATURN", NODE_ID:"RAHU"}.get(pid, "UNKNOWN")

# ================== 4. PROFIT & SIGNAL ENGINES ==================
@st.cache_data(ttl=60)
def get_ltp(ticker):
    try:
        t = yf.Ticker(ticker + ".NS")
        data = t.history(period="1d", interval="1m")
        return round(data["Close"].iloc[-1], 2) if not data.empty else 0.0
    except: return 0.0

@st.cache_data
def get_pnl_data(ticker, date_obj, h_start, h_end):
    try:
        t = yf.Ticker(ticker + ".NS")
        df = t.history(start=date_obj, end=date_obj + timedelta(days=1), interval="1m")
        if df.empty: return None
        df.index = df.index.tz_convert(IST)
        entry = df.between_time(h_start.strftime("%H:%M"), (h_start + timedelta(minutes=5)).strftime("%H:%M"))
        exit = df.between_time((h_end - timedelta(minutes=5)).strftime("%H:%M"), h_end.strftime("%H:%M"))
        if entry.empty or exit.empty: return None
        buy, sell = entry['Open'].iloc[0], exit['Close'].iloc[-1]
        return {"buy": buy, "sell": sell, "pnl": round(((sell-buy)/buy)*100, 2), "pts": round(sell-buy, 2)}
    except: return None

def analyze_stock(stock, h_lord, d_lord):
    score = 50
    if stock['Ruler'] == USER_LORD: score += 20
    if stock['Ruler'] == h_lord: score += 30
    if stock['Ruler'] == d_lord: score += 10
    
    status = "SNIPER" if score >= 90 else "ACCUMULATE" if score >= 70 else "WAIT"
    color = "#00FF99" if score >= 90 else "#D4AF37" if score >= 70 else "#8b949e"
    return score, status, color

# ================== 5. AI STRATEGIST ==================
def ask_ai(ticker, score, status):
    try:
        genai.configure(api_key=st.secrets["GEMINI_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Algo: Guardian v28. Asset: {ticker}. Score: {score}. Signal: {status}. Give 1 sentence of ruthless market advice."
        return model.generate_content(prompt).text
    except: return "AI Offline. Check Secrets."

# ================== 6. APP INTERFACE ==================
st.sidebar.title("💰 ORACLE CONTROL")
mode = st.sidebar.radio("MODE", ["🔴 LIVE", "🧪 BACKTEST"])

if mode == "🔴 LIVE":
    now = datetime.now(IST)
else:
    d = st.sidebar.date_input("Select Date", datetime.now(IST) - timedelta(days=1))
    t = st.sidebar.slider("Select Time", time(9,15), time(15,30), time(11,0))
    now = datetime.combine(d, t).replace(tzinfo=IST)

h_lord, d_lord = get_hora_lord(now)
st.title(f"GUARDIAN v28 • {mode}")
st.caption(f"DAY LORD: {get_planet_name(d_lord)} | ACTIVE HORA: {get_planet_name(h_lord)}")

# FIND HERO
best_s, best_sc = None, -1
for sector, tickers in STOCKS.items():
    for t in tickers:
        s_obj = {"Ticker": t, "Sector": sector, "Ruler": SECTOR_MAP.get(sector, swe.MERCURY)}
        score, _, _ = analyze_stock(s_obj, h_lord, d_lord)
        if score > best_sc:
            best_sc = score
            best_s = s_obj

# EXECUTE
ltp = get_ltp(best_s['Ticker']) if mode == "🔴 LIVE" else "---"
score, status, color = analyze_stock(best_s, h_lord, d_lord)

if mode == "🔴 LIVE":
    with st.spinner("Consulting AI..."):
        st.markdown(f'<div class="ai-box"><b>🦅 STRATEGIST:</b> {ask_ai(best_s["Ticker"], score, status)}</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1.5, 1])
with c1:
    st.markdown(f"""
    <div class="hero-card">
        <div class="label">PRIMARY ALPHA PICK</div>
        <div class="ticker-huge">{best_s['Ticker']}</div>
        <div class="label" style="color:#D4AF37; margin-top:5px;">{best_s['Sector']} | CONFIDENCE: {score}%</div>
        <hr style="border-color:#333;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div><div class="label">LTP</div><div style="font-size:24px; font-weight:700;">₹{ltp}</div></div>
            <div style="text-align:right;"><div class="label">SIGNAL</div><div style="font-size:24px; font-weight:800; color:{color};">{status}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    if mode == "🧪 BACKTEST":
        st.markdown("### 💹 P&L VERIFICATION")
        sunrise = get_sunrise(now)
        chaldean = [swe.SATURN, swe.JUPITER, swe.MARS, swe.SUN, swe.VENUS, swe.MERCURY, swe.MOON]
        start_idx = chaldean.index(d_lord)
        
        # Find the specific hora for this stock
        for i in range(12):
            if chaldean[(start_idx + i) % 7] == best_s['Ruler']:
                h_start = sunrise + timedelta(hours=i)
                h_end = h_start + timedelta(hours=1)
                pnl = get_pnl_data(best_s['Ticker'], now.date(), h_start, h_end)
                if pnl:
                    p_cls = "pnl-pos" if pnl['pnl'] > 0 else "pnl-neg"
                    st.markdown(f"""
                    <div class="hero-card" style="border-top:3px solid {color};">
                        <div class="label">HORA WINDOW: {h_start.strftime('%H:%M')} - {h_end.strftime('%H:%M')}</div>
                        <div style="font-size:18px; margin-top:10px;">Entry: ₹{pnl['buy']} | Exit: ₹{pnl['sell']}</div>
                        <div class="{p_cls}" style="margin-top:10px;">{pnl['pnl']}% (₹{pnl['pts']})</div>
                    </div>
                    """, unsafe_allow_html=True)
                break
    else:
        st.info("Switch to BACKTEST mode to verify P&L of previous Sniper windows.")

# TABS
t1, t2 = st.tabs(["⚡ SECTOR SCANNER", "📜 HORA SCHEDULE"])
with t1:
    cols = st.columns(3)
    idx = 0
    for sector, tickers in STOCKS.items():
        for t in tickers:
            s_obj = {"Ticker": t, "Sector": sector, "Ruler": SECTOR_MAP.get(sector, swe.MERCURY)}
            sc, stat, clr = analyze_stock(s_obj, h_lord, d_lord)
            if sc >= 70:
                with cols[idx%3]:
                    st.markdown(f"**{t}** | Score: {sc}% | <span style='color:{clr}'>{stat}</span>", unsafe_allow_html=True)
                idx += 1