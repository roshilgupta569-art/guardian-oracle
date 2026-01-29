import streamlit as st
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import hashlib
import yfinance as yf
import google.generativeai as genai

# ================= UI CONFIG =================
st.set_page_config(
    page_title="GUARDIAN v24: AI CONNECTED",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {background-color: #000000;}
    
    /* AI BOX STYLE */
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
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
    }
    
    /* TEXT */
    .label {font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}
    .ticker-text {font-size: 28px; font-weight: 800; color: #FFF;}
    .price-text {font-size: 24px; font-weight: 700; color: #e6edf3;}
    
    /* BADGES */
    .badge {padding: 6px 12px; border-radius: 4px; font-weight: 800; font-size: 14px; text-align: center; width: 100%; margin-top: 10px;}
    .buy-badge {background-color: #0f3d24; color: #2ea043; border: 1px solid #2ea043;}
    .sell-badge {background-color: #3d1214; color: #ff5555; border: 1px solid #ff5555;}
    .wait-badge {background-color: #1f2328; color: #8b949e; border: 1px solid #30363d;}
</style>
""", unsafe_allow_html=True)

# ================= CONSTANTS =================
IST = pytz.timezone("Asia/Kolkata")

STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "FMCG": ["ITC", "HUL"],
    "METAL": ["TATASTEEL", "JSWSTEEL"],
    "ENERGY": ["RELIANCE", "NTPC"]
}

# ================= AI ENGINE (THE BRAIN) =================
def init_ai_mind():
    # Try to grab the API Key from Streamlit Secrets
    try:
        api_key = st.secrets["GEMINI_KEY"]
        genai.configure(api_key=api_key)
        return True
    except:
        return False

def ask_the_oracle(ticker, sector, price, score, action):
    """
    Sends the data to Gemini and gets a strategic response.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are a ruthless, high-frequency trading algorithm named Guardian.
        Analyze this live setup concisely (max 50 words).
        
        Data:
        - Stock: {ticker} ({sector})
        - Price: {price}
        - Algo Score: {score}/100
        - Signal: {action}
        
        If Signal is BUY, explain why momentum is building.
        If Signal is SELL, warn about the breakdown.
        If Signal is WAIT, tell me to be patient.
        Use trading terminology. Be direct.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "⚠️ AI DISCONNECTED: Update API Key in Secrets."

# ================= UTILS =================
def entropy(key):
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return (h % 11) - 5

def time_block(dt):
    return dt.hour * 60 + dt.minute

@st.cache_data(ttl=60)
def get_ltp(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty: return round(data["Close"].iloc[-1], 2)
    except: pass
    return 0.00

@st.cache_data
def get_day_heroes(date_obj):
    scored = []
    for sector, stocks in STOCKS.items():
        base = 60 + entropy(sector + str(date_obj))
        for s in stocks:
            score = base + entropy(s)
            scored.append((s, sector, score))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:3]

def intraday_signal(ticker, dt):
    # Deterministic Signal Logic
    if not (time(9,15) <= dt.time() <= time(15,30)):
        return "MARKET CLOSED", 0
    
    base = 70
    pulse = entropy(ticker + str(time_block(dt)))
    t = time_block(dt)
    
    # Time Bias
    time_bias = 0
    if 555 <= t <= 630: time_bias += 10 # Opening
    if 750 <= t <= 840: time_bias += 15 # Midday
    if t >= 870: time_bias -= 10 # Closing

    score = base + (pulse * 2) + time_bias
    
    if score >= 85: return "BUY / CALL", score
    if score <= 60: return "SELL / PUT", score
    return "WAIT / HOLD", score

# ================= APP LOGIC =================
st.sidebar.title("🦅 GUARDIAN AI")
mode = st.sidebar.radio("MODE", ["🔴 LIVE", "🧪 BACKTEST"])

if mode == "🔴 LIVE":
    current_dt = datetime.now(IST)
else:
    d = st.sidebar.date_input("Date", datetime.now(IST))
    t = st.sidebar.slider("Time", time(9,15), time(15,30), time(9,15))
    current_dt = datetime.combine(d, t).replace(tzinfo=IST)

st.title("GUARDIAN v24: AI CONNECTED")
st.markdown("---")

# CHECK CONNECTION
ai_active = init_ai_mind()
if not ai_active:
    st.warning("⚠️ AI NOT CONNECTED: Please add GEMINI_KEY to .streamlit/secrets.toml")

heroes = get_day_heroes(current_dt.date())

# 1. DISPLAY AI ANALYSIS FOR TOP HERO
top_hero, top_sec, _ = heroes[0]
action, score = intraday_signal(top_hero, current_dt)
ltp = get_ltp(top_hero)

if ai_active and mode == "🔴 LIVE":
    with st.spinner("🦅 Guardian AI is analyzing market structure..."):
        ai_analysis = ask_the_oracle(top_hero, top_sec, ltp, score, action)
    
    st.markdown(f"""
    <div class="ai-box">
        <div style="font-weight:bold; color:#a855f7; margin-bottom:5px;">🦅 GUARDIAN STRATEGIST (LIVE)</div>
        {ai_analysis}
    </div>
    """, unsafe_allow_html=True)

# 2. HERO CARDS
cols = st.columns(3)
for i, (ticker, sector, _) in enumerate(heroes):
    act, sc = intraday_signal(ticker, current_dt)
    curr_ltp = get_ltp(ticker) if mode == "🔴 LIVE" else "---"
    
    badge_cls = "wait-badge"
    if "BUY" in act: badge_cls = "buy-badge"
    elif "SELL" in act: badge_cls = "sell-badge"

    with cols[i]:
        st.markdown(f"""
        <div class="hero-card">
            <div class="label">HERO #{i+1}</div>
            <div class="ticker-text">{ticker}</div>
            <div class="label" style="color:#58a6ff;">{sector}</div>
            <div class="price-text">₹{curr_ltp}</div>
            <div class="badge {badge_cls}">{act}</div>
            <div style="text-align:right; font-size:12px; margin-top:5px; color:#888;">SCORE: {sc}</div>
        </div>
        """, unsafe_allow_html=True)

# 3. BACKTEST CHART
st.markdown("### 📉 MOMENTUM")
rows = []
t_iter = datetime.combine(current_dt.date(), time(9,15)).replace(tzinfo=IST)
while t_iter <= datetime.combine(current_dt.date(), time(15,30)).replace(tzinfo=IST):
    _, s = intraday_signal(heroes[0][0], t_iter)
    rows.append({"Time": t_iter.strftime("%H:%M"), "Score": s})
    t_iter += timedelta(minutes=15)
st.line_chart(pd.DataFrame(rows).set_index("Time"), color="#a855f7")