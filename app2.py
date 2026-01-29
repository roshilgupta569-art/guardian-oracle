import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta
import pytz

# ================= UI CONFIG =================
st.set_page_config(page_title="ASTRO OPTIONS PROOF TERMINAL", page_icon="📈", layout="wide")

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

IST = pytz.timezone("Asia/Kolkata")

# ================= ASTRO CORE =================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60)

def planet_strength(pid, dt):
    jd = julian(dt)
    p,_ = swe.calc_ut(jd, pid)
    s,_ = swe.calc_ut(jd, swe.SUN)

    dist = abs(p[0]-s[0])
    if dist > 180: dist = 360 - dist

    return {
        "combust": dist < 14,
        "retro": p[3] < 0
    }

def moon_strength(dt):
    jd = julian(dt)
    m,_ = swe.calc_ut(jd, swe.MOON)
    s,_ = swe.calc_ut(jd, swe.SUN)

    phase = abs(m[0]-s[0])
    if phase > 180: phase = 360 - phase

    return m[3] > 12.5, round(m[3],2), round(phase,2)

# ================= RAHU KAAL =================
RAHU = {0:(7,9),1:(9,10.5),2:(12,13.5),3:(13.5,15),4:(10.5,12)}

def is_rahu(dt):
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
    if moon[3] > 13.5: v += 20
    if angle < 15 or abs(angle-90)<10 or abs(angle-180)<10: v += 20
    if mars[3] > 0.7: v += 10

    return min(100, v)

# ================= OPTION BIAS =================
def option_bias(dt, planet):
    phys = planet_strength(planet, dt)
    moon_ok, speed, _ = moon_strength(dt)
    vol = pvi(dt)
    rahu = is_rahu(dt)

    score = 50
    if not phys["combust"]: score += 10
    if phys["retro"]: score -= 20
    if moon_ok: score += 10
    score += (vol-50)*0.3
    if rahu: score -= 15

    if score >= 65: return "BUY CALL", int(score)
    if score <= 35: return "BUY PUT", int(score)
    return "NO TRADE", int(score)

# ================= HERO STOCK (FIXED) =================
def hero_stock_of_day(dt):
    moon_ok, speed, _ = moon_strength(dt)
    if speed > 13.5: return "BANKNIFTY"
    if speed < 12: return "NIFTY"
    return "FINNIFTY"

# ================= PICK TIMING =================
def best_trade_window(dt):
    hour = dt.hour + dt.minute/60
    if 9.25 <= hour <= 10.15: return "🔥 OPENING MOMENTUM"
    if 11.15 <= hour <= 12.30: return "🎯 MIDDAY TREND"
    if 14.15 <= hour <= 15.10: return "⚡ POWER HOUR"
    return "⛔ NO EDGE WINDOW"

# ================= EXPIRY TRAP =================
def expiry_trap(dt):
    if dt.weekday() != 3: return False
    mercury = planet_strength(swe.MERCURY, dt)
    moon_ok, speed, phase = moon_strength(dt)

    trap = 0
    if mercury["combust"]: trap += 30
    if speed < 12: trap += 25
    if phase < 20 or phase > 160: trap += 20
    if is_rahu(dt): trap += 25

    return trap >= 60

# ================= BACKTEST ENGINE =================
def backtest(date, start, end):
    rows = []
    t = datetime.combine(date, start).replace(tzinfo=IST)
    end_t = datetime.combine(date, end).replace(tzinfo=IST)

    while t <= end_t:
        bias, score = option_bias(t, swe.JUPITER)
        rows.append({
            "Time": t.strftime("%H:%M"),
            "Bias": bias,
            "Confidence": score,
            "Volatility": pvi(t),
            "Rahu": is_rahu(t),
            "Expiry Trap": expiry_trap(t)
        })
        t += timedelta(minutes=15)
    return rows

# ================= LIVE DASHBOARD =================
now = datetime.now(IST)

bias, conf = option_bias(now, swe.JUPITER)
vol = pvi(now)
hero = hero_stock_of_day(now)
window = best_trade_window(now)

st.title("📈 ASTRO OPTIONS PROOF TERMINAL")
st.caption(now.strftime("%d %b %Y | %H:%M IST"))

c1,c2,c3,c4 = st.columns(4)
c1.metric("RIGHT NOW", bias)
c2.metric("CONFIDENCE", f"{conf}%")
c3.metric("VOLATILITY", vol)
c4.metric("HERO STOCK", hero)

st.progress(vol/100)

st.markdown(f"<div class='card big center'>{window}</div>", unsafe_allow_html=True)

if bias == "NO TRADE" or vol < 45 or "NO EDGE" in window:
    st.warning("🚫 DO NOT TRADE NOW — CAPITAL PROTECTION MODE")
else:
    st.success(f"✅ ACTIONABLE: {bias} on {hero}")

if expiry_trap(now):
    st.error("☠️ EXPIRY DAY ASTRO TRAP — SCALP ONLY OR STAY OUT")

# ================= BACKTEST MODE =================
st.divider()
st.subheader("🧪 BACKTEST PROOF MODE")

colA,colB,colC = st.columns(3)
date = colA.date_input("Select Date")
start = colB.time_input("Start Time", value=datetime.strptime("09:15","%H:%M").time())
end = colC.time_input("End Time", value=datetime.strptime("15:15","%H:%M").time())

if st.button("RUN BACKTEST"):
    data = backtest(date, start, end)
    st.dataframe(data, use_container_width=True)

st.info("""
HOW TO USE BACKTEST:
• Pick any past date  
• See what signal system gave at each 15-min slot  
• Match with chart manually  
• This builds REAL confidence  
""")

st.success("Terminal fully armed. Discipline decides profits. 😈📈")
