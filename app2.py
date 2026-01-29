import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import hashlib

# ================== APP CONFIGURATION ==================
st.set_page_config(
    page_title="GUARDIAN v15 • PERSONAL ASTRO ENGINE",
    page_icon="🦅",
    layout="wide"
)

# Dark Mode & Hacker UI
st.markdown("""
<style>
    .stApp {background-color: #000000;}
    
    /* CARD STYLES */
    .hero-card {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 25px; border-radius: 14px; border: 1px solid #444;
        box-shadow: 0 4px 15px rgba(0, 255, 153, 0.1);
        margin-bottom: 20px;
    }
    .btst-card {
        background: linear-gradient(135deg, #1a0b2e 0%, #2d1b4e 100%);
        padding: 25px; border-radius: 14px; border: 1px solid #553377;
        box-shadow: 0 4px 15px rgba(153, 0, 255, 0.1);
        margin-bottom: 20px;
    }
    
    /* TYPOGRAPHY */
    .score-big {font-size: 52px; font-weight: 900; color: #00FF99;}
    .ticker-big {font-size: 36px; font-weight: 800; color: #FFFFFF; margin-bottom: 5px;}
    .sub-text {font-size: 14px; color: #AAAAAA; text-transform: uppercase; letter-spacing: 1px;}
    
    /* STATE BOXES */
    .state-box {padding: 12px; border-radius: 8px; font-weight: 800; text-align: center; letter-spacing: 1px;}
    .enter {background: #003300; color: #00FF99; border: 1px solid #00FF99;}
    .hold {background: #444400; color: #FFCC00; border: 1px solid #FFCC00;}
    .wait {background: #222222; color: #AAAAAA; border: 1px solid #444444;}
    .avoid {background: #440000; color: #FF3333; border: 1px solid #FF3333;}
</style>
""", unsafe_allow_html=True)

# ================== SECURITY LAYER ==================
def check_password():
    if st.session_state.get("auth", False): return True
    pwd = st.text_input("ENTER ACCESS KEY", type="password")
    if st.button("UNLOCK TERMINAL"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

IST = pytz.timezone("Asia/Kolkata")

# ================== DATABASE & MAPPINGS ==================
# Safe Node Handling
NODE_ID = getattr(swe, 'MEAN_NODE', 10) # Fallback to 10 if constant missing

SECTOR_MAP = {
    "BANK": swe.MERCURY,
    "IT": swe.SATURN,
    "AUTO": swe.VENUS,
    "PHARMA": swe.SUN,
    "FMCG": swe.MOON,
    "METALS": swe.MARS,
    "ENERGY": swe.SUN,
    "FINANCE": swe.JUPITER,
    "TELECOM": NODE_ID
}

STOCKS = {
    "BANK": ["HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO"],
    "AUTO": ["TATAMOTORS", "MARUTI", "M&M"],
    "PHARMA": ["SUNPHARMA", "DRREDDY"],
    "FMCG": ["ITC", "HUL", "NESTLEIND"],
    "METALS": ["TATASTEEL", "JSWSTEEL"],
    "ENERGY": ["NTPC", "POWERGRID"],
    "FINANCE": ["BAJFINANCE", "LICI"],
    "TELECOM": ["BHARTIARTL"]
}

NIFTY_DB = []
for sec, ticks in STOCKS.items():
    for t in ticks:
        NIFTY_DB.append({"Ticker": t, "Sector": sec, "Ruler": SECTOR_MAP[sec]})

# ================== ASTRO CORE ENGINE ==================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)

def planet_strength(pid, dt):
    jd = julian(dt)
    pos, _ = swe.calc_ut(jd, pid)
    sun, _ = swe.calc_ut(jd, swe.SUN)
    
    # Physics Calculation
    dist = abs(pos[0] - sun[0])
    
    score = 50
    if dist < 14.0: score -= 30 # Combust (Weak)
    if pos[3] < 0: score -= 15  # Retrograde (Unstable)
    if dist > 60.0: score += 20 # Visible (Strong)
    
    return score

def moon_speed(dt):
    jd = julian(dt)
    m, _ = swe.calc_ut(jd, swe.MOON)
    return m[3]

# ================== PERSONAL RESONANCE ENGINE ==================
def user_resonance(dob, pid):
    """Matches Stock Ruler to User's Birth Day Lord"""
    weekday = dob.weekday() # 0=Mon
    
    day_lord_map = {
        0: swe.MOON, 1: swe.MARS, 2: swe.MERCURY,
        3: swe.JUPITER, 4: swe.VENUS, 5: swe.SATURN, 6: swe.SUN
    }
    user_lord = day_lord_map.get(weekday)
    
    # Friendship Matrix
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
    
    if pid == user_lord: return 50      # Jackpot Match
    if pid in friends.get(user_lord, []): return 25 # Friendly
    return 0 # Neutral/Enemy

def personal_multiplier(dob):
    """Boosts score based on 'Golden Hours' of birth"""
    h = dob.hour
    if 6 <= h <= 10: return 1.08  # Morning Born (Active)
    if 11 <= h <= 15: return 1.12 # Midday Born (Peak)
    if 16 <= h <= 20: return 1.05 # Evening Born (Stable)
    return 1.0

# ================== INTRADAY PULSE ENGINE ==================
def intraday_entropy(ticker, dt):
    """Generates 15-minute shifted noise pattern"""
    block = (dt.minute // 15) * 15
    key = f"{ticker}{dt.strftime('%Y%m%d%H')}{block}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return ((h % 21) - 10) * 1.6 # Noise Amplitude

def trade_state(score, dt):
    """Determines actionable signal"""
    # Market Hours Check (9:15 - 15:30)
    market_open = (time(9,15) <= dt.time() <= time(15,30))
    
    if not market_open:
        return "⛔ MARKET CLOSED", "avoid"
        
    if score >= 115: return "🚀 SNIPER ENTRY", "enter"
    if score >= 100: return "🛡️ HOLD / SCALP", "hold"
    if score <= 85: return "⛔ AVOID / TRAP", "avoid"
    return "⏳ WAIT", "wait"

# ================== MAIN CALCULATORS ==================
def calc_score(stock, dob, dt, noise=True):
    s = planet_strength(stock["Ruler"], dt)
    u = user_resonance(dob, stock["Ruler"])
    n = intraday_entropy(stock["Ticker"], dt) if noise else 0
    return s + u + n

def day_hero(dob, date_):
    """Locks the Hero Stock based on 9:15 AM data (Noise Free)"""
    bell = datetime.combine(date_, time(9, 15))
    best_stock = None
    best_score = -1
    
    for stock in NIFTY_DB:
        # Calculate Pure Base Score
        sc = calc_score(stock, dob, bell, noise=False)
        if sc > best_score:
            best_score = sc
            best_stock = stock
            
    return best_stock, best_score

def btst_check(dob, date_):
    """Analyzes Overnight Momentum"""
    close_time = datetime.combine(date_, time(15, 30))
    open_time = datetime.combine(date_ + timedelta(days=1), time(9, 15))
    
    # 1. Moon Acceleration
    accel = moon_speed(open_time) > moon_speed(close_time)
    
    # 2. Tomorrow's Hero Strength
    hero_tmr, score_tmr = day_hero(dob, date_ + timedelta(days=1))
    
    # 3. Final Verdict
    conf = score_tmr + (8 if accel else -6)
    
    if conf >= 110: return "YES", "STRONG MOON ACCEL (+)", hero_tmr
    if conf >= 95: return "MAYBE", "MIXED SIGNALS (~)", hero_tmr
    return "NO", "WEAK MOMENTUM (-)", hero_tmr

# ================== SIDEBAR CONTROLS ==================
st.sidebar.title("🧬 BIO-CALIBRATION")
st.sidebar.caption("Align Algorithm to Your Birth Chart")
u_dob = st.sidebar.date_input("DATE OF BIRTH", datetime(1990, 1, 1))
u_time = st.sidebar.time_input("TIME OF BIRTH", time(12, 0)) # Used for multiplier

# Merge DOB + Time for multiplier function
full_dob = datetime.combine(u_dob, u_time)

st.sidebar.markdown("---")
st.sidebar.title("🕰️ TIME MACHINE")
sel_date = st.sidebar.date_input("MISSION DATE", datetime.now(IST))

sim_time = datetime.now(IST).time()
if sel_date != datetime.now(IST).date():
    sim_time = st.sidebar.slider("BACKTEST TIME", time(9,15), time(15,30), time(9,15), step=timedelta(minutes=15))

now_dt = datetime.combine(sel_date, sim_time)

# ================== DASHBOARD DISPLAY ==================
# 1. Calculate Data
hero, base_score = day_hero(u_dob, sel_date)
# Apply Personal Multiplier to final live score
multiplier = personal_multiplier(full_dob)
live_score = calc_score(hero, u_dob, now_dt, noise=True) * multiplier

state_text, css_class = trade_state(live_score, now_dt)
btst_sig, btst_reason, hero_tmr = btst_check(u_dob, sel_date)

st.title(f"🦅 GUARDIAN v15 • {sel_date.strftime('%A, %d %b')}")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"""
    <div class="hero-card">
        <div class="sub-text">LOCKED HERO (PERSONALIZED)</div>
        <div class="ticker-big">{hero['Ticker']}</div>
        <div class="sub-text" style="color:#AAA;">{hero['Sector']} | RULER STRENGTH: {int(base_score)}</div>
        <hr style="border-color:#444;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div class="state-box {css_class}" style="flex-grow:1; margin-right:15px;">{state_text}</div>
            <div class="score-big">{int(live_score)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Signal Explanation
    if "SNIPER" in state_text:
        st.success(f"🔥 **ACTION:** {hero['Ticker']} is in a High-Probability Buy Zone for YOU.")
    elif "AVOID" in state_text:
        st.error(f"🛑 **ACTION:** Intraday noise is high. Stay away from {hero['Ticker']} for now.")

with col2:
    is_yes = btst_sig == "YES"
    btst_col = "#00FF99" if is_yes else "#FF3333"
    
    st.markdown(f"""
    <div class="btst-card">
        <div class="sub-text">BTST SIGNAL</div>
        <div style="font-size:32px; font-weight:900; color:{btst_col};">{btst_sig}</div>
        <p style="color:#CCC; font-size:14px; margin-top:5px;">{btst_reason}</p>
        <hr style="border-color:#553377;">
        <div class="sub-text">TOMORROW'S TARGET</div>
        <div style="font-size:24px; font-weight:bold; color:#FFF;">{hero_tmr['Ticker']}</div>
    </div>
    """, unsafe_allow_html=True)

# ================== FOOTER ==================
st.caption(f"System ID: {hashlib.md5(str(sel_date).encode()).hexdigest()[:8]} | Calibrated to User: {u_dob.strftime('%Y-%m-%d')}")