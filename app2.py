import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import hashlib

# ================== APP CONFIG ==================
st.set_page_config(
    page_title="GUARDIAN v15 • PERSONAL ASTRO ENGINE",
    page_icon="🦅",
    layout="wide"
)

st.markdown("""
<style>
.stApp {background-color:#000000;}
.hero-card {background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);padding:25px;border-radius:14px;border:1px solid #444;}
.btst-card {background:linear-gradient(135deg,#1a0b2e,#2d1b4e);padding:25px;border-radius:14px;border:1px solid #553377;}
.score {font-size:52px;font-weight:900;color:#00FF99;}
.ticker {font-size:34px;font-weight:800;color:#FFFFFF;}
.state {padding:10px;border-radius:8px;font-weight:800;text-align:center;}
.enter {background:#003300;color:#00FF99;}
.hold {background:#444400;color:#FFCC00;}
.wait {background:#222;color:#AAAAAA;}
.avoid {background:#440000;color:#FF3333;}
</style>
""", unsafe_allow_html=True)

# ================== SECURITY ==================
def check_password():
    if st.session_state.get("auth", False):
        return True
    pwd = st.text_input("ENTER ACCESS KEY", type="password")
    if st.button("LOGIN"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["auth"] = True
            st.rerun()
    return False

if not check_password():
    st.stop()

IST = pytz.timezone("Asia/Kolkata")

# ================== DATABASE ==================
SECTOR_MAP = {
    "BANK": swe.MERCURY,
    "IT": swe.SATURN,
    "AUTO": swe.VENUS,
    "PHARMA": swe.SUN,
    "FMCG": swe.MOON,
    "METALS": swe.MARS,
    "ENERGY": swe.SUN,
    "FINANCE": swe.JUPITER,
    "TELECOM": swe.MEAN_NODE
}

STOCKS = {
    "BANK": ["HDFCBANK","ICICIBANK","AXISBANK","KOTAKBANK"],
    "IT": ["TCS","INFY","HCLTECH","WIPRO"],
    "AUTO": ["TATAMOTORS","MARUTI","M&M"],
    "PHARMA": ["SUNPHARMA","DRREDDY"],
    "FMCG": ["ITC","HUL","NESTLEIND"],
    "METALS": ["TATASTEEL","JSWSTEEL"],
    "ENERGY": ["NTPC","POWERGRID"],
    "FINANCE": ["BAJFINANCE","LICI"],
    "TELECOM": ["BHARTIARTL"]
}

NIFTY_DB = []
for sec, ticks in STOCKS.items():
    for t in ticks:
        NIFTY_DB.append({"Ticker":t,"Sector":sec,"Ruler":SECTOR_MAP[sec]})

# ================== ASTRO CORE ==================
def julian(dt):
    return swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60)

def planet_strength(pid, dt):
    jd = julian(dt)
    pos,_ = swe.calc_ut(jd,pid)
    sun,_ = swe.calc_ut(jd,swe.SUN)
    dist = abs(pos[0]-sun[0])
    score = 50
    if dist < 14: score -= 30
    if pos[3] < 0: score -= 15
    if dist > 60: score += 20
    return score

def moon_speed(dt):
    jd = julian(dt)
    m,_ = swe.calc_ut(jd,swe.MOON)
    return m[3]

# ================== PERSONAL LOGIC ==================
def user_resonance(dob, pid):
    day_lord = {
        0:swe.MOON,1:swe.MARS,2:swe.MERCURY,
        3:swe.JUPITER,4:swe.VENUS,5:swe.SATURN,6:swe.SUN
    }[dob.weekday()]
    friends = {
        swe.SUN:[swe.MOON,swe.MARS,swe.JUPITER],
        swe.MOON:[swe.SUN,swe.MERCURY],
        swe.MARS:[swe.SUN,swe.MOON],
        swe.MERCURY:[swe.SUN,swe.VENUS],
        swe.JUPITER:[swe.SUN,swe.MOON],
        swe.VENUS:[swe.MERCURY,swe.SATURN],
        swe.SATURN:[swe.MERCURY,swe.VENUS],
        swe.MEAN_NODE:[swe.MERCURY,swe.VENUS]
    }
    if pid == day_lord: return 50
    if pid in friends.get(day_lord,[]): return 25
    return 0

def personal_multiplier(dob):
    h = dob.hour if hasattr(dob,"hour") else 12
    if 6<=h<=10: return 1.08
    if 11<=h<=15: return 1.12
    if 16<=h<=20: return 1.05
    return 1.0

# ================== INTRADAY ENGINE ==================
def intraday_entropy(ticker, dt):
    block = (dt.minute//15)*15
    key = f"{ticker}{dt.strftime('%Y%m%d%H')}{block}"
    h = int(hashlib.md5(key.encode()).hexdigest(),16)
    return ((h%21)-10)*1.6

def is_market_open(dt):
    return time(9,15)<=dt.time()<=time(15,30)

def trade_state(score, dt):
    if not is_market_open(dt):
        return "⛔ MARKET CLOSED","avoid"
    if score>=115: return "🚀 SNIPER ENTRY","enter"
    if score>=100: return "🛡️ HOLD / SCALP","hold"
    if score<=85: return "⛔ AVOID / TRAP","avoid"
    return "⏳ WAIT","wait"

# ================== SCORING ==================
def calc_score(stock,dob,dt,noise=True):
    s = planet_strength(stock["Ruler"],dt)
    u = user_resonance(dob,stock["Ruler"])
    n = intraday_entropy(stock["Ticker"],dt) if noise else 0
    return s+u+n

def day_hero(dob,date_):
    bell = datetime.combine(date_,time(9,15))
    best=None;bs=-1
    for stc in NIFTY_DB:
        sc = calc_score(stc,dob,bell,False)
        if sc>bs:
            best=stc;bs=sc
    return best,bs

def btst_check(dob,date_):
    close = datetime.combine(date_,time(15,30))
    open_ = datetime.combine(date_+timedelta(days=1),time(9,15))
    accel = moon_speed(open_)>moon_speed(close)
    hero,sc = day_hero(dob,date_+timedelta(days=1))
    conf = sc+(8 if accel else -6)
    if conf>=110: return "YES","STRONG (+)",hero
    if conf>=95: return "MAYBE","MIXED (~)",hero
    return "NO","WEAK (-)",hero

# ================== SIDEBAR ==================
st.sidebar.title("🧬 PERSONAL CALIBRATION")
dob = st.sidebar.date_input("DATE OF BIRTH",datetime(1995,1,1))
sel_date = st.sidebar.date_input("DATE",datetime.now(IST))
sim_time = datetime.now(IST).time()
if sel_date!=datetime.now(IST).date():
    sim_time = st.sidebar.slider("TIME",time(9,15),time(15,30),time(9,15),step=timedelta(minutes=15))
now_dt = datetime.combine(sel_date,sim_time)

# ================== DASHBOARD ==================
hero,base = day_hero(dob,sel_date)
score = calc_score(hero,dob,now_dt,True)*personal_multiplier(datetime.combine(dob,time(12)))
state,css = trade_state(score,now_dt)
btst_sig,btst_reason,hero_tmr = btst_check(dob,sel_date)

st.title(f"🦅 GUARDIAN v15 • {sel_date.strftime('%A %d %b')}")

col1,col2 = st.columns([2,1])

with col1:
    st.markdown(f"""
    <div class="hero-card">
        <div class="ticker">{hero['Ticker']}</div>
        <div>{hero['Sector']}</div>
        <div class="state {css}">{state}</div>
        <div class="score">{int(score)}</div>
    </div>
    """,unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="btst-card">
        <h3>BTST</h3>
        <h2>{btst_sig}</h2>
        <p>{btst_reason}</p>
        <b>TOMORROW FOCUS:</b> {hero_tmr['Ticker']}
    </div>
    """,unsafe_allow_html=True)
