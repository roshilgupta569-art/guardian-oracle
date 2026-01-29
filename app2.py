# =========================
# GUARDIAN HORIZON v23
# MULTI-HERO + REAL DATA
# =========================

import streamlit as st
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import hashlib
from io import StringIO

# ---------- REAL DATA ----------
import yfinance as yf

# ================= UI CONFIG =================
st.set_page_config(
    page_title="GUARDIAN HORIZON v23",
    page_icon="🦅",
    layout="wide"
)

st.markdown("""
<style>
.stApp {background:#000;}
.hero-card {background:#0d1117;border:1px solid #30363d;border-top:3px solid #00E676;
padding:20px;border-radius:8px;}
.metric {background:#0d1117;border:1px solid #30363d;padding:14px;border-radius:6px;text-align:center;}
.label {font-size:11px;color:#8b949e;text-transform:uppercase;}
.big {font-size:34px;font-weight:800;}
.buy {color:#00E676;}
.sell {color:#f85149;}
.wait {color:#8b949e;}
.log {font-family:Consolas;background:#0d1117;border-left:3px solid #D4AF37;
padding:12px;height:150px;overflow:auto;}
</style>
""", unsafe_allow_html=True)

# ================= CONSTANTS =================
IST = pytz.timezone("Asia/Kolkata")

STOCKS = {
    "BANK": ["HDFCBANK","ICICIBANK","AXISBANK","KOTAKBANK"],
    "IT": ["TCS","INFY","HCLTECH","WIPRO"],
    "AUTO": ["TATAMOTORS","MARUTI","M&M"],
    "FMCG": ["ITC","HUL"],
    "METAL": ["TATASTEEL","JSWSTEEL"],
    "ENERGY": ["RELIANCE","NTPC"]
}

OPTIONS_INDEX = ["NIFTY","BANKNIFTY"]

# ================= UTIL =================
def market_open(dt):
    return time(9,15) <= dt.time() <= time(15,30)

def entropy(key):
    h = int(hashlib.md5(key.encode()).hexdigest(),16)
    return (h % 11) - 5

def time_block(dt):
    return dt.hour*60 + dt.minute

# ================= REAL PRICE =================
@st.cache_data(ttl=60)
def get_ltp(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            return round(data["Close"].iloc[-1], 2)
    except:
        pass
    return None

# ================= MULTI-HERO (DAY LOCKED) =================
@st.cache_data
def get_day_heroes(date_obj):
    scored = []
    for sector, stocks in STOCKS.items():
        base = 60 + entropy(sector + str(date_obj))
        for s in stocks:
            score = base + entropy(s)
            scored.append((s, sector, score))
    scored.sort(key=lambda x:x[2], reverse=True)
    return scored[:3]

# ================= INTRADAY ENGINE =================
def intraday_signal(ticker, dt):
    if not market_open(dt):
        return "NO TRADE", 0, ["Market closed"]

    base = 70
    pulse = entropy(ticker + str(time_block(dt)))
    time_bias = 0

    t = time_block(dt)
    if 555 <= t <= 630: time_bias += 10
    if 750 <= t <= 840: time_bias += 15
    if t >= 870: time_bias -= 10

    score = base + pulse + time_bias
    log = [f"Base:{base}",f"Pulse:{pulse}",f"TimeBias:{time_bias}"]

    if score >= 95: return "BUY", score, log
    if score <= 60: return "SELL / AVOID", score, log
    return "WAIT", score, log

# ================= OPTIONS =================
def options_signal(index, dt):
    bias = entropy(index + str(time_block(dt)))
    if bias >= 3: return f"{index} CE BUY"
    if bias <= -3: return f"{index} PE BUY"
    return "NO TRADE"

# ================= BACKTEST =================
def run_backtest(date_obj, ticker):
    rows = []
    t = datetime.combine(date_obj, time(9,15)).replace(tzinfo=IST)
    end = datetime.combine(date_obj, time(15,30)).replace(tzinfo=IST)

    while t <= end:
        act, sc, _ = intraday_signal(ticker, t)
        rows.append({"Time":t.strftime("%H:%M"),"Action":act,"Score":sc})
        t += timedelta(minutes=15)

    return pd.DataFrame(rows)

# ================= SIDEBAR =================
st.sidebar.title("CONTROL")
mode = st.sidebar.radio("MODE",["LIVE","BACKTEST"])

if mode=="LIVE":
    current_dt = datetime.now(IST)
else:
    d = st.sidebar.date_input("Date",datetime.now(IST))
    t = st.sidebar.slider("Time",time(9,15),time(15,30),time(9,15),step=timedelta(minutes=15))
    current_dt = datetime.combine(d,t).replace(tzinfo=IST)

# ================= HEROES =================
heroes = get_day_heroes(current_dt.date())

# ================= DASHBOARD =================
st.title("🦅 GUARDIAN HORIZON v23")
st.caption(current_dt.strftime("%d %b %Y %H:%M IST"))

cols = st.columns(3)

for i,(ticker,sector,_) in enumerate(heroes):
    action, score, log = intraday_signal(ticker,current_dt)
    ltp = get_ltp(ticker)

    with cols[i]:
        st.markdown(f"""
        <div class="hero-card">
        <div class="label">HERO #{i+1}</div>
        <div class="big">{ticker}</div>
        <div class="label">{sector}</div>
        <div class="label">LTP</div>
        <div class="value">{ltp if ltp else "—"}</div>
        <div class="label">ACTION</div>
        <div class="{ 'buy' if action=='BUY' else 'sell' if 'SELL' in action else 'wait' }">{action}</div>
        <div class="label">SCORE</div>
        <div>{score}</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ================= DETAILS =================
tabs = st.tabs(["📊 INTRADAY","🧨 OPTIONS","🧪 BACKTEST"])

with tabs[0]:
    df = run_backtest(current_dt.date(), heroes[0][0])
    st.line_chart(df.set_index("Time")["Score"])

with tabs[1]:
    for idx in OPTIONS_INDEX:
        st.markdown(f"**{idx}** → {options_signal(idx,current_dt)}")

with tabs[2]:
    df = run_backtest(current_dt.date(), heroes[0][0])
    st.dataframe(df,use_container_width=True)
    buf = StringIO()
    df.to_csv(buf,index=False)
    st.download_button("⬇️ Download CSV",buf.getvalue(),file_name="backtest.csv",mime="text/csv")
