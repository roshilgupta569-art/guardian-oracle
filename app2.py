import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta
import pytz

# ================= BASIC SETUP =================
st.set_page_config(page_title="ASTRO INTRADAY TERMINAL", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp {background:#0E1117}
.card {background:#111;padding:15px;border-radius:10px;margin-bottom:10px}
.green {color:#2ECC71;font-weight:bold}
.red {color:#E74C3C;font-weight:bold}
.yellow {color:#F1C40F;font-weight:bold}
.big {font-size:22px;font-weight:bold}
.center {text-align:center}
</style>
""", unsafe_allow_html=True)

IST = pytz.timezone("Asia/Kolkata")

# ================= PASSWORD =================
def check_password():
    if st.session_state.get("ok"): return True
    pwd = st.text_input("ENTER PASSWORD", type="password")
    if st.button("LOGIN"):
        if pwd == st.secrets["general"]["password"]:
            st.session_state["ok"] = True
            st.rerun()
    return False

if not check_password(): st.stop()

# ================= ASTRO CORE =================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60)

def planet_strength(pid, dt):
    jd = julian(dt)
    p,_ = swe.calc_ut(jd, pid)
    s,_ = swe.calc_ut(jd, swe.SUN)
    dist = abs(p[0]-s[0])
    if dist > 180: dist = 360-dist
    return {"combust": dist < 14, "retro": p[3] < 0}

def moon_data(dt):
    jd = julian(dt)
    m,_ = swe.calc_ut(jd, swe.MOON)
    s,_ = swe.calc_ut(jd, swe.SUN)
    phase = abs(m[0]-s[0])
    if phase > 180: phase = 360-phase
    return m[3], phase

# ================= RAHU KAAL =================
RAHU = {0:(7,9),1:(9,10.5),2:(12,13.5),3:(13.5,15),4:(10.5,12)}

def rahu_active(dt):
    if dt.weekday() not in RAHU: return False
    a,b = RAHU[dt.weekday()]
    t = dt.hour + dt.minute/60
    return a <= t <= b

# ================= VOLATILITY =================
def pvi(dt):
    jd = julian(dt)
    moon,_ = swe.calc_ut(jd, swe.MOON)
    mars,_ = swe.calc_ut(jd, swe.MARS)
    sun,_ = swe.calc_ut(jd, swe.SUN)
    angle = abs(moon[0]-sun[0])
    if angle > 180: angle = 360-angle
    v = 40
    if moon[3] > 12.8: v += 15
    if angle < 20 or abs(angle-90)<12 or abs(angle-180)<12: v += 15
    if mars[3] > 0.6: v += 10
    return min(100, v)

# ================= HERO PICK (DAY LOCKED) =================
def hero_pick_for_day(day_dt):
    speed, _ = moon_data(day_dt)
    if speed > 13.2: return "BANKNIFTY"
    if speed < 12.2: return "NIFTY"
    return "FINNIFTY"

def get_hero(dt):
    key = dt.strftime("%Y-%m-%d")
    if "hero_day" not in st.session_state or st.session_state.hero_day != key:
        st.session_state.hero_day = key
        st.session_state.hero = hero_pick_for_day(dt.replace(hour=9, minute=15))
    return st.session_state.hero

# ================= TRADE ENGINE =================
def trade_state(dt):
    speed, phase = moon_data(dt)
    vol = pvi(dt)
    merc = planet_strength(swe.MERCURY, dt)

    score = 50
    if speed > 12.8: score += 10
    if phase < 25 or phase > 155: score -= 10
    if merc["retro"]: score -= 10
    if merc["combust"]: score -= 10
    if rahu_active(dt): score -= 10
    score += (vol-50)*0.3

    if score >= 60:
        return "DIRECTIONAL TRADE", score
    if score >= 48:
        return "SCALP TRADE", score
    return "AVOID / WAIT", score

def direction_bias(dt):
    phys = planet_strength(swe.JUPITER, dt)
    if phys["retro"]: return "PUT BIAS"
    if phys["combust"]: return "RANGE"
    return "CALL BIAS"

# ================= TIME WINDOWS =================
def trade_window(dt):
    t = dt.hour + dt.minute/60
    if 9.2 <= t <= 10.3: return "OPENING MOMENTUM"
    if 11.2 <= t <= 12.5: return "MIDDAY MOVE"
    if 14.1 <= t <= 15.1: return "POWER HOUR"
    return "LOW EDGE"

# ================= MODE TOGGLE =================
mode = st.sidebar.radio("MODE", ["LIVE", "BACKTEST"])

if mode == "LIVE":
    now = datetime.now(IST)
else:
    date = st.sidebar.date_input("Date")
    time = st.sidebar.time_input("Time")
    now = datetime.combine(date, time).replace(tzinfo=IST)

hero = get_hero(now)
state, conf = trade_state(now)
bias = direction_bias(now)
vol = pvi(now)
window = trade_window(now)

# ================= HOME =================
st.title("📈 ASTRO INTRADAY TERMINAL")
st.caption(now.strftime("%d %b %Y | %H:%M IST"))

c1,c2,c3,c4 = st.columns(4)
c1.metric("TRADE STATE", state)
c2.metric("CONFIDENCE", int(conf))
c3.metric("VOLATILITY", vol)
c4.metric("HERO PICK", hero)

st.progress(vol/100)
st.markdown(f"<div class='card big center'>{window}</div>", unsafe_allow_html=True)

if state == "AVOID / WAIT":
    st.warning("🚫 STAY OUT — MARKET NOT PAYING")
elif state == "SCALP TRADE":
    st.info(f"⚡ SCALP ONLY | {bias}")
else:
    st.success(f"🔥 DIRECTIONAL | {bias} on {hero}")

# ================= OPTIONS DESK =================
st.divider()
st.subheader("🧾 OPTIONS DESK")

if state == "DIRECTIONAL TRADE":
    st.markdown("**Strategy:** Buy ATM options, trail winners")
elif state == "SCALP TRADE":
    st.markdown("**Strategy:** Quick scalps, partial profits")
else:
    st.markdown("**Strategy:** No option buying")

st.markdown(f"**Bias:** {bias}")
st.markdown(f"**Avoid new trades during:** LOW EDGE windows")

# ================= STOCKS DESK =================
st.divider()
st.subheader("📊 INTRADAY STOCK BIAS")

stocks = ["RELIANCE", "HDFC BANK", "ICICI BANK", "INFY", "TCS"]
for s in stocks:
    st.markdown(f"- **{s}** → {bias} till {window}")

# ================= BACKTEST TABLE =================
if mode == "BACKTEST":
    st.divider()
    st.subheader("🧪 SIGNAL REPLAY (15-MIN)")
    t = now.replace(hour=9, minute=15)
    rows = []
    while t.hour < 15 or (t.hour==15 and t.minute<=15):
        s,c = trade_state(t)
        rows.append({
            "Time": t.strftime("%H:%M"),
            "State": s,
            "Bias": direction_bias(t),
            "Volatility": pvi(t)
        })
        t += timedelta(minutes=15)
    st.dataframe(rows, use_container_width=True)

st.success("System loaded. Trade discipline > signals. 😈📈")
