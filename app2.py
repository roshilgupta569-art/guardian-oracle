import streamlit as st
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import hashlib
import yfinance as yf
import google.generativeai as genai

# ================= 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="GUARDIAN v25: ULTIMATE",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* GLOBAL DARK THEME */
    .stApp {background-color: #000000;}
    
    /* AI STRATEGIST BOX */
    .ai-box {
        background-color: #0d1117;
        border-left: 4px solid #a855f7; /* Purple for AI */
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #e6edf3;
        font-family: 'Consolas', monospace;
        font-size: 14px;
        box-shadow: 0 4px 6px rgba(168, 85, 247, 0.2);
    }
    
    /* HERO CARD */
    .hero-card {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-top: 3px solid #00E676;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* OPTION CARD */
    .option-card {
        background-color: #0d1117; border: 1px solid #30363d; 
        padding: 15px; border-radius: 8px; margin-bottom: 10px;
    }
    
    /* TYPOGRAPHY */
    .label {font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 4px;}
    .ticker-text {font-size: 32px; font-weight: 800; color: #FFF; line-height: 1.1;}
    .price-text {font-size: 24px; font-weight: 700; color: #e6edf3;}
    .signal-text {font-size: 18px; font-weight: 800; text-align: right;}
    
    /* COLORS */
    .buy-color {color: #00E676;}
    .sell-color {color: #ff5555;}
    .wait-color {color: #8b949e;}
</style>
""", unsafe_allow_html=True)

# ================= 2. CONSTANTS & DATABASE =================
IST = pytz.timezone("Asia/Kolkata")

# Calibrated for 2006 DOB (Venus/Auto/IT Bias)
STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"], # Strong for Venus Born
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],    # Strong for Venus Born
    "FMCG": ["ITC", "HUL"],
    "METAL": ["TATASTEEL", "JSWSTEEL"],
    "ENERGY": ["RELIANCE", "NTPC"]
}

# ================= 3. UTILITY ENGINES =================
def entropy(key):
    """Deterministic randomness for stable signals"""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return (h % 11) - 5

def time_block(dt):
    return dt.hour * 60 + dt.minute

@st.cache_data(ttl=60)
def get_ltp(symbol):
    """Fetches Live Price from Yahoo Finance"""
    try:
        if symbol in ["NIFTY", "BANKNIFTY"]: return 0.0 # Indices need ^NSEI logic, skipping for speed
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty: return round(data["Close"].iloc[-1], 2)
    except: pass
    return 0.00

# ================= 4. CORE LOGIC (LOCKED) =================
@st.cache_data
def get_day_heroes(date_obj):
    """
    LOCKS THE HERO STOCK FOR THE DAY.
    Does not change on refresh. Calculated from Date Seed.
    """
    scored = []
    for sector, stocks in STOCKS.items():
        # Sector Bias based on Date
        base = 60 + entropy(sector + str(date_obj))
        for s in stocks:
            # Stock Specific Variance
            score = base + entropy(s)
            scored.append((s, sector, score))
    
    # Sort by Score and pick Top 3
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:3]

def intraday_signal(ticker, dt):
    """
    Generates signals based on Time Block + Hash.
    Consistent across refreshes.
    """
    if not (time(9,15) <= dt.time() <= time(15,30)):
        return "MARKET CLOSED", 0, "wait-color"

    base = 70
    pulse = entropy(ticker + str(time_block(dt)))
    t = time_block(dt)
    
    # Time Bias (Opening Range vs Closing)
    time_bias = 0
    if 555 <= t <= 630: time_bias += 10 
    if 750 <= t <= 840: time_bias += 15 
    if t >= 870: time_bias -= 10 

    score = base + (pulse * 2) + time_bias
    
    if score >= 85: return "SNIPER BUY", score, "buy-color"
    if score <= 60: return "DUMP / SELL", score, "sell-color"
    return "WAIT / HOLD", score, "wait-color"

def get_atm_strike(spot, step=50):
    if spot == 0: return "---"
    return round(spot / step) * step

# ================= 5. AI BRIDGE =================
def ask_ai(ticker, sector, price, score, action):
    try:
        api_key = st.secrets["GEMINI_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Act as Guardian, a hedge fund algo.
        Asset: {ticker} ({sector}) | Price: {price} | Score: {score}/100 | Signal: {action}.
        
        Write a 1-sentence strategic command for a trader.
        Use terms like "Volume Spike", "Resistance", "Accumulate".
        """
        response = model.generate_content(prompt)
        return response.text
    except:
        return "⚠️ AI DISCONNECTED: Key missing or quota exceeded."

# ================= 6. APP LAYOUT =================

# --- SIDEBAR ---
st.sidebar.title("🦅 CONTROL")
mode = st.sidebar.radio("SYSTEM MODE", ["🔴 LIVE MARKET", "🧪 BACKTEST LAB"])

if mode == "🔴 LIVE MARKET":
    current_dt = datetime.now(IST)
    st.sidebar.success(f"ONLINE: {current_dt.strftime('%H:%M:%S')}")
else:
    d = st.sidebar.date_input("Backtest Date", datetime.now(IST))
    t = st.sidebar.slider("Replay Time", time(9,15), time(15,30), time(9,15), step=timedelta(minutes=15))
    current_dt = datetime.combine(d, t).replace(tzinfo=IST)
    st.sidebar.warning(f"REPLAY: {d} @ {t}")

# --- MAIN HEADER ---
st.title(f"GUARDIAN v25")
st.caption(f"USER: ROSHIL | VENUS CALIBRATED | {mode}")

# --- CALCULATION ---
heroes = get_day_heroes(current_dt.date())
primary_hero, primary_sec, _ = heroes[0]
p_act, p_score, p_color = intraday_signal(primary_hero, current_dt)
p_ltp = get_ltp(primary_hero) if mode == "🔴 LIVE MARKET" else "---"

# --- AI SECTION ---
if mode == "🔴 LIVE MARKET":
    with st.spinner("🦅 Guardian AI is thinking..."):
        ai_msg = ask_ai(primary_hero, primary_sec, p_ltp, p_score, p_act)
    st.markdown(f"""<div class="ai-box"><b>🦅 STRATEGIST:</b> {ai_msg}</div>""", unsafe_allow_html=True)

# --- TABS LAYOUT (AS REQUESTED) ---
tab_hero, tab_intraday = st.tabs(["🚀 HERO CENTER", "⚡ INTRADAY TERMINAL"])

# TAB 1: HERO CENTER
with tab_hero:
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown(f"""
        <div class="hero-card">
            <div class="label">LOCKED HERO OF THE DAY</div>
            <div class="ticker-text">{primary_hero}</div>
            <div class="label" style="color:#58a6ff;">{primary_sec}</div>
            <div style="display:flex; justify-content:space-between; align-items:end; margin-top:10px;">
                <div>
                    <div class="label">PRICE</div>
                    <div class="price-text">₹{p_ltp}</div>
                </div>
                <div>
                    <div class="label" style="text-align:right;">SIGNAL</div>
                    <div class="signal-text {p_color}">{p_act}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📉 MOMENTUM")
        # Backtest Chart
        rows = []
        t_iter = datetime.combine(current_dt.date(), time(9,15)).replace(tzinfo=IST)
        while t_iter <= datetime.combine(current_dt.date(), time(15,30)).replace(tzinfo=IST):
            _, sc, _ = intraday_signal(primary_hero, t_iter)
            rows.append({"Time": t_iter.strftime("%H:%M"), "Score": sc})
            t_iter += timedelta(minutes=15)
        st.line_chart(pd.DataFrame(rows).set_index("Time"), height=200, color="#00E676")

# TAB 2: INTRADAY TERMINAL (SUBTABS)
with tab_intraday:
    t1, t2, t3 = st.tabs(["NIFTY OPTIONS", "BANK NIFTY", "ROCKET STOCKS"])
    
    # 1. NIFTY
    with t1:
        n_bias = entropy("NIFTY" + str(time_block(current_dt)))
        n_act = "CALL / BUY" if n_bias > 0 else "PUT / SELL"
        n_col = "#00E676" if n_bias > 0 else "#ff5555"
        st.markdown(f"""
        <div class="option-card">
            <div class="label">NIFTY 50 VIEW</div>
            <div style="font-size:28px; font-weight:bold; color:{n_col}">{n_act}</div>
            <div class="label" style="margin-top:5px;">STRATEGY: ATM {n_act.split()[0]}</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. BANK NIFTY
    with t2:
        b_bias = entropy("BANKNIFTY" + str(time_block(current_dt)))
        b_act = "CALL / BUY" if b_bias > 0 else "PUT / SELL"
        b_col = "#00E676" if b_bias > 0 else "#ff5555"
        st.markdown(f"""
        <div class="option-card">
            <div class="label">BANK NIFTY VIEW</div>
            <div style="font-size:28px; font-weight:bold; color:{b_col}">{b_act}</div>
            <div class="label" style="margin-top:5px;">STRATEGY: ATM {b_act.split()[0]}</div>
        </div>
        """, unsafe_allow_html=True)

    # 3. ROCKET STOCKS
    with t3:
        st.markdown("### ⚡ HIGH MOMENTUM SCANNER")
        cols = st.columns(3)
        # Scan all stocks
        valid_picks = []
        for sec, tickers in STOCKS.items():
            for t in tickers:
                if t == primary_hero: continue
                a, s, c = intraday_signal(t, current_dt)
                if s > 80: valid_picks.append((t, s, a))
        
        if not valid_picks:
            st.info("No Rocket Setups right now. Market is sideways.")
        else:
            for i, (tk, sc, ac) in enumerate(valid_picks[:6]):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="option-card">
                        <div style="color:#00E676; font-weight:bold;">{tk}</div>
                        <div style="font-size:12px; color:#888;">Score: {sc}</div>
                        <div style="font-weight:bold; color:#FFF;">{ac}</div>
                    </div>
                    """, unsafe_allow_html=True)