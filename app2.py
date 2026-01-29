import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import hashlib
import requests

# ================== APP CONFIGURATION ==================
st.set_page_config(
    page_title="GUARDIAN v17 • COMMAND CENTER",
    page_icon="🦅",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {background-color: #000000;}
    
    /* CARD STYLES */
    .hero-card {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 25px; border-radius: 14px; border: 1px solid #444;
        margin-bottom: 20px;
    }
    .option-card {
        background-color: #0d1117; border: 1px solid #30363d; 
        padding: 15px; border-radius: 8px; margin-bottom: 10px;
    }
    
    /* TYPOGRAPHY */
    .score-big {font-size: 48px; font-weight: 900; color: #00FF99;}
    .ticker-big {font-size: 32px; font-weight: 800; color: #FFFFFF; margin-bottom: 5px;}
    .big-label {font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1px;}
    
    /* SIGNAL BOXES */
    .strike-box {background: #21262d; color: #c9d1d9; padding: 5px 10px; border-radius: 4px; font-family: monospace; font-size: 16px;}
    .buy-sig {color: #00FF99; font-weight: bold; font-size: 20px;}
    .sell-sig {color: #FF3333; font-weight: bold; font-size: 20px;}
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #111; border-radius: 4px; color: #888; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #222; color: #FFF; border: 1px solid #00FF99; }
</style>
""", unsafe_allow_html=True)

# ================== SECURITY ==================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("ENTER ACCESS KEY", type="password")
    if st.button("UNLOCK ARSENAL"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")

# ================== DATABASE & MAPPINGS ==================
NODE_ID = getattr(swe, 'MEAN_NODE', 10)

SECTOR_MAP = {
    "BANK": swe.MERCURY, "IT": swe.SATURN, "AUTO": swe.VENUS,
    "PHARMA": swe.SUN, "FMCG": swe.MOON, "METALS": swe.MARS,
    "ENERGY": swe.SUN, "FINANCE": swe.JUPITER, "TELECOM": NODE_ID
}

STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "PHARMA": ["SUNPHARMA", "DRREDDY"],
    "FMCG": ["ITC", "HUL"],
    "METALS": ["TATASTEEL", "JSWSTEEL"],
    "ENERGY": ["NTPC", "POWERGRID"],
    "FINANCE": ["BAJFINANCE", "LICI"],
    "TELECOM": ["BHARTIARTL"]
}

NIFTY_DB = []
for sec, ticks in STOCKS.items():
    for t in ticks:
        NIFTY_DB.append({"Ticker": t, "Sector": sec, "Ruler": SECTOR_MAP[sec]})

# ================== ASTRO CORE ==================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)

def planet_strength(pid, dt):
    jd = julian(dt)
    pos, _ = swe.calc_ut(jd, pid)
    sun, _ = swe.calc_ut(jd, swe.SUN)
    dist = abs(pos[0] - sun[0])
    
    score = 50
    if dist < 14.0: score -= 30
    if pos[3] < 0: score -= 15
    if dist > 60.0: score += 20
    return score

def moon_speed(dt):
    jd = julian(dt)
    m, _ = swe.calc_ut(jd, swe.MOON)
    return m[3]

# ================== PERSONAL RESONANCE ==================
def user_resonance(dob, pid):
    day_lord_map = {0: swe.MOON, 1: swe.MARS, 2: swe.MERCURY, 3: swe.JUPITER, 4: swe.VENUS, 5: swe.SATURN, 6: swe.SUN}
    user_lord = day_lord_map.get(dob.weekday())
    
    friends = {
        swe.SUN: [swe.MOON, swe.MARS, swe.JUPITER],
        swe.MOON: [swe.SUN, swe.MERCURY],
        swe.MARS: [swe.SUN, swe.MOON],
        swe.MERCURY: [swe.SUN, swe.VENUS],
        swe.JUPITER: [swe.SUN, swe.MOON],
        swe.VENUS: [swe.MERCURY, swe.SATURN],
        swe.SATURN: [swe.MERCURY, swe.VENUS],
        NODE_ID: [swe.MERCURY, swe.VENUS]
    }
    
    if pid == user_lord: return 50
    if pid in friends.get(user_lord, []): return 25
    return 0

def personal_multiplier(dob):
    h = dob.hour
    if 6 <= h <= 10: return 1.08
    if 11 <= h <= 15: return 1.12
    return 1.0

# ================== INTRADAY ENGINES ==================
def get_live_price(ticker):
    # Dummy logic for Strike calculation (since we don't have paid API)
    defaults = {"NIFTY": 24500, "BANKNIFTY": 52000, "RELIANCE": 3200}
    try:
        url = f"https://indian-stock-market-api.vercel.app/stock/{ticker}"
        data = requests.get(url, timeout=1).json()
        return float(data['lastPrice'].replace(',', ''))
    except:
        return defaults.get(ticker, 1000)

def get_atm_strike(spot, step=50):
    return round(spot / step) * step

def intraday_entropy(ticker, dt):
    block = (dt.minute // 15) * 15
    key = f"{ticker}{dt.strftime('%Y%m%d%H')}{block}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return ((h % 21) - 10) * 1.6

def calc_score(stock, dob, dt, noise=True):
    s = planet_strength(stock["Ruler"], dt)
    u = user_resonance(dob, stock["Ruler"])
    n = intraday_entropy(stock["Ticker"], dt) if noise else 0
    return s + u + n

def day_hero(dob, date_):
    bell = datetime.combine(date_, time(9, 15))
    best_stock = None
    best_score = -1
    for stock in NIFTY_DB:
        sc = calc_score(stock, dob, bell, noise=False)
        if sc > best_score:
            best_score = sc
            best_stock = stock
    return best_stock, best_score

def find_best_entry(date_obj, ticker, dob):
    # Scans the whole day to find peak time
    t_start = datetime.combine(date_obj, time(9, 15))
    t_end = datetime.combine(date_obj, time(15, 30))
    
    best_time = "NO TRADE"
    best_act = "AVOID"
    peak = 0
    
    # Create temp stock obj for calc
    temp_stock = {"Ticker": ticker, "Ruler": swe.MERCURY} # Default ruler for generic scan
    # Try to find real ruler
    for s in NIFTY_DB:
        if s['Ticker'] == ticker: temp_stock = s
    
    curr = t_start
    while curr <= t_end:
        score = calc_score(temp_stock, dob, curr, noise=True)
        if abs(score - 50) > abs(peak - 50):
            peak = score
            best_time = curr.strftime("%H:%M")
            if score > 105: best_act = "BUY / CALL"
            elif score < 85: best_act = "SELL / PUT"
        curr += timedelta(minutes=15)
        
    return best_time, best_act, peak

def btst_check(dob, date_):
    close_time = datetime.combine(date_, time(15, 30))
    open_time = datetime.combine(date_ + timedelta(days=1), time(9, 15))
    accel = moon_speed(open_time) > moon_speed(close_time)
    hero_tmr, score_tmr = day_hero(dob, date_ + timedelta(days=1))
    conf = score_tmr + (8 if accel else -6)
    
    if conf >= 110: return "YES", "STRONG ACCEL (+)", hero_tmr
    return "NO", "WEAK MOMENTUM (-)", hero_tmr

# ================== SIDEBAR ==================
st.sidebar.title("🧬 BIO-CALIBRATION")

# FIX: Added min_value to allow 2006 DOB
u_dob = st.sidebar.date_input("DATE OF BIRTH", datetime(2006, 6, 22), min_value=datetime(1950, 1, 1))
u_time = st.sidebar.time_input("TIME OF BIRTH", time(12, 0))
full_dob = datetime.combine(u_dob, u_time)

st.sidebar.markdown("---")
st.sidebar.title("🕰️ TIME CONTROL")
sel_date = st.sidebar.date_input("MISSION DATE", datetime.now(IST))
sim_time = datetime.now(IST).time()
if sel_date != datetime.now(IST).date():
    sim_time = st.sidebar.slider("BACKTEST TIME", time(9,15), time(15,30), time(9,15), step=timedelta(minutes=15))
now_dt = datetime.combine(sel_date, sim_time)

# ================== DASHBOARD ==================
st.title(f"🦅 GUARDIAN v17 • {sel_date.strftime('%A, %d %b')}")

# CALCS
hero, base = day_hero(u_dob, sel_date)
multiplier = personal_multiplier(full_dob)
live_score = calc_score(hero, u_dob, now_dt, noise=True) * multiplier
btst_sig, btst_reason, hero_tmr = btst_check(u_dob, sel_date)

# --- MAIN TABS ---
# These are the Main Tabs: Hero vs Intraday
tab_main, tab_intraday = st.tabs(["🚀 HERO CENTER", "⚡ INTRADAY TERMINAL"])

# TAB 1: HERO CENTER
with tab_main:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        state = "⏳ WAIT"
        css = "wait"
        if live_score >= 115: state = "🚀 SNIPER ENTRY"; css = "enter"
        elif live_score >= 100: state = "🛡️ HOLD"; css = "hold"
        elif live_score <= 85: state = "⛔ AVOID"; css = "avoid"
        
        st.markdown(f"""
        <div class="hero-card">
            <div class="big-label">TODAY'S PERSONAL HERO</div>
            <div class="ticker-big">{hero['Ticker']}</div>
            <div class="big-label" style="color:#AAA;">{hero['Sector']} | STRENGTH: {int(live_score)}</div>
            <hr style="border-color:#444;">
            <div style="background:#111; padding:10px; border-radius:5px; text-align:center; font-weight:bold; color:#FFF; border:1px solid #333;">
                STATUS: {state}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        is_yes = btst_sig == "YES"
        btst_col = "#00FF99" if is_yes else "#FF3333"
        st.markdown(f"""
        <div class="option-card" style="border-left:5px solid {btst_col};">
            <div class="big-label">BTST SIGNAL</div>
            <div style="font-size:28px; font-weight:900; color:{btst_col};">{btst_sig}</div>
            <div class="big-label" style="margin-top:5px;">TOMORROW: {hero_tmr['Ticker']}</div>
        </div>
        """, unsafe_allow_html=True)

# TAB 2: INTRADAY TERMINAL (THE STRATEGY SUB-TABS)
with tab_intraday:
    # These are the Sub-Tabs you asked for
    t1, t2, t3 = st.tabs(["NIFTY OPTIONS", "BANK NIFTY", "ROCKET STOCKS"])
    
    # 1. NIFTY OPTIONS
    with t1:
        spot_n = get_live_price("NIFTY")
        t_n, act_n, s_n = find_best_entry(sel_date, "NIFTY", u_dob)
        atm_n = get_atm_strike(spot_n, 50)
        type_n = "CE" if "BUY" in act_n else "PE"
        
        st.markdown(f"""
        <div class="option-card">
            <div style="display:flex; justify-content:space-between;">
                <div><span class="big-label">INDEX SPOT</span><br><span style="color:#FFF; font-weight:bold; font-size:20px;">{spot_n}</span></div>
                <div style="text-align:right;"><span class="big-label">BEST ENTRY</span><br><span style="color:#FFCC00; font-weight:bold; font-size:20px;">⏰ {t_n}</span></div>
            </div>
            <hr style="border-color:#333;">
            <div style="font-size:24px; font-weight:bold; color:{'#00FF99' if 'BUY' in act_n else '#FF3333'};">{act_n}</div>
            <div style="margin-top:10px;">
                <span class="big-label">STRATEGY:</span> <span class="strike-box">{atm_n} {type_n}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. BANK NIFTY OPTIONS
    with t2:
        spot_b = get_live_price("BANKNIFTY")
        t_b, act_b, s_b = find_best_entry(sel_date, "BANKNIFTY", u_dob)
        atm_b = get_atm_strike(spot_b, 100)
        type_b = "CE" if "BUY" in act_b else "PE"
        
        st.markdown(f"""
        <div class="option-card">
            <div style="display:flex; justify-content:space-between;">
                <div><span class="big-label">INDEX SPOT</span><br><span style="color:#FFF; font-weight:bold; font-size:20px;">{spot_b}</span></div>
                <div style="text-align:right;"><span class="big-label">BEST ENTRY</span><br><span style="color:#FFCC00; font-weight:bold; font-size:20px;">⏰ {t_b}</span></div>
            </div>
            <hr style="border-color:#333;">
            <div style="font-size:24px; font-weight:bold; color:{'#00FF99' if 'BUY' in act_b else '#FF3333'};">{act_b}</div>
            <div style="margin-top:10px;">
                <span class="big-label">STRATEGY:</span> <span class="strike-box">{atm_b} {type_b}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. ROCKET STOCKS
    with t3:
        st.markdown("### 📈 MOMENTUM SCANNER")
        cols = st.columns(3)
        idx = 0
        
        # Scan Top Liquid Stocks
        watchlist = ["RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "TATASTEEL"]
        
        found_any = False
        for stk in watchlist:
            t, act, s = find_best_entry(sel_date, stk, u_dob)
            # Filter: Only show GOOD signals (>105 buy or <85 sell)
            if s > 110 or s < 80:
                found_any = True
                color = "#00FF99" if "BUY" in act else "#FF3333"
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div class="option-card">
                        <div style="color:{color}; font-weight:bold; font-size:18px;">{stk}</div>
                        <div style="font-size:12px; color:#888;">Entry: {t}</div>
                        <div style="font-weight:bold; color:#FFF;">CONF: {int(s)}%</div>
                        <div style="font-size:12px; color:{color};">{act}</div>
                    </div>
                    """, unsafe_allow_html=True)
                idx += 1
        
        if not found_any:
            st.info("🚫 No High-Conviction setups detected yet. Market is sideways.")