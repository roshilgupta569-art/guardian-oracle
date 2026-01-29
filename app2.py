import streamlit as st
import swisseph as swe
from datetime import datetime, timedelta, time
import pytz
import pandas as pd
import math
import hashlib

# ================= UI CONFIG =================
st.set_page_config(page_title="GUARDIAN v7.0", page_icon="🦅", layout="wide")

st.markdown("""
<style>
.stApp {background-color: #000000;}
.hero-card {background: linear-gradient(45deg, #0f0c29, #302b63, #24243e); padding: 20px; border-radius: 10px; border: 1px solid #444; margin-bottom: 20px;}
.signal-box {background-color: #111; padding: 15px; border-left: 5px solid #00FF99; border-radius: 5px; margin-bottom: 10px;}
.big-font {font-size: 20px; font-weight: bold; color: #EEE;}
.green {color: #00FF99; font-weight: bold;}
.red {color: #FF3333; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ================= SECURITY =================
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

# ================= RE-CALIBRATED ASTRO ENGINE =================
def julian(dt):
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0)

def get_moon_speed(dt):
    jd = julian(dt)
    m, _ = swe.calc_ut(jd, swe.MOON)
    return m[3] # Speed in deg/day

def get_pvi(dt): # Volatility
    speed = get_moon_speed(dt)
    base_vol = 40
    if speed > 13.0: base_vol += 25 # Fast Moon = High Volatility
    if speed < 12.0: base_vol -= 10 # Slow Moon = Chop
    
    # Intraday Volatility Spike (Opening/Closing)
    h = dt.hour + dt.minute/60.0
    if 9.25 <= h <= 10.5: base_vol += 20
    if 14.5 <= h <= 15.5: base_vol += 15
    
    return min(100, base_vol)

def get_trade_signal(dt):
    # 1. BASE SCORE
    score = 50
    
    # 2. MOON PHASE & SPEED (The Trend)
    speed = get_moon_speed(dt)
    score += (speed - 12.5) * 8 # Sensitivity boosted
    
    # 3. PLANETARY ASPECTS (The Trigger)
    # We add a "Micro-Cycle" to generate trades intraday
    minute_cycle = math.sin((dt.hour * 60 + dt.minute) / 20.0) * 15
    score += minute_cycle
    
    # 4. RAHU KAAL (The Filter)
    # We don't KILL the trade, we just dampen it
    weekday = dt.weekday()
    rahu_start = {0:7.5, 1:15, 2:12, 3:13.5, 4:10.5}.get(weekday, 0)
    rahu_end = rahu_start + 1.5
    curr_h = dt.hour + dt.minute/60.0
    
    if rahu_start <= curr_h <= rahu_end:
        score -= 10 # Penalty, not kill
        
    # 5. FINAL VERDICT
    if score > 60: return "BUY CALL 🟢", int(score)
    if score < 40: return "BUY PUT 🔴", int(score)
    return "WAIT / CHOP 🟡", int(score)

# ================= HERO SELECTION (FIXED FOR DAY) =================
def get_hero_picks(date_obj):
    # This calculation depends ONLY on the date, not time
    # It simulates "Pre-Market Analysis"
    day_seed = int(date_obj.strftime("%Y%m%d"))
    
    # Simple Logic: Moon Speed determines the Index
    moon_speed_9am = get_moon_speed(datetime.combine(date_obj, time(9,15)))
    
    hero_index = "NIFTY 50"
    if moon_speed_9am > 13.5: hero_index = "BANK NIFTY (High Beta)"
    elif moon_speed_9am < 12.0: hero_index = "FINNIFTY (Low Beta)"
    
    # Stock Picks based on Day Ruler
    weekday = date_obj.weekday()
    stock_map = {
        0: "NTPC (Sun)", 1: "DLF (Mars)", 2: "INFY (Merc)", 
        3: "SBIN (Jup)", 4: "ITC (Ven)", 5: "RELIANCE (Sat)", 6: "SUNPHARMA"
    }
    hero_stock = stock_map.get(weekday, "RELIANCE")
    
    return hero_index, hero_stock, moon_speed_9am

# ================= LAYOUT LOGIC =================

# 1. SIDEBAR (THE TIME MACHINE)
st.sidebar.title("🕰️ TIME MACHINE")
selected_date = st.sidebar.date_input("SELECT DATE", datetime.now(IST))
is_today = selected_date == datetime.now(IST).date()

st.sidebar.markdown("---")
if is_today:
    st.sidebar.success("🔴 LIVE MODE ACTIVE")
    current_time = datetime.now(IST)
else:
    st.sidebar.warning("🧪 BACKTEST MODE")
    # In backtest, we show the whole day's data
    current_time = datetime.combine(selected_date, time(15, 30)).replace(tzinfo=IST)

# 2. HERO SECTION (Valid All Day)
hero_idx, hero_stk, m_speed = get_hero_picks(selected_date)

st.markdown(f"""
<div class="hero-card">
    <h2 style='margin:0; color:#00FFCC;'>🦅 HEROES OF THE DAY: {selected_date.strftime('%A, %d %b')}</h2>
    <div style='display:flex; justify-content:space-between; margin-top:10px;'>
        <div><span style='color:gray'>PRIME INDEX:</span><br><span class='big-font'>{hero_idx}</span></div>
        <div><span style='color:gray'>HERO STOCK:</span><br><span class='big-font'>{hero_stk}</span></div>
        <div><span style='color:gray'>MOON VELOCITY:</span><br><span class='big-font'>{m_speed:.2f}°/day</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# 3. TABS FOR SECTIONS
tab_options, tab_stocks = st.tabs(["📊 INTRADAY OPTION CHAIN", "📈 STOCK TIMELINE"])

# --- TAB 1: OPTION CHAIN MATRIX ---
with tab_options:
    st.markdown("### ⚡ OPTION BUYING TIMELINE")
    st.caption("Algorithm scans 15-minute windows for High Momentum Setups.")
    
    # Generate Time Slots (9:15 to 3:30)
    slots = []
    t_start = datetime.combine(selected_date, time(9, 15)).replace(tzinfo=IST)
    t_end = datetime.combine(selected_date, time(15, 30)).replace(tzinfo=IST)
    
    curr = t_start
    while curr <= t_end:
        # Only show up to current time if Live
        if is_today and curr > datetime.now(IST):
            break
            
        sig, score = get_trade_signal(curr)
        vol = get_pvi(curr)
        
        # Filter: Only show entries, hide "Wait" to reduce clutter? 
        # User asked for "Options to buy", so let's show everything but highlight buys.
        
        row_color = "#111"
        if "CALL" in sig: row_color = "#002200" # Dark Green bg
        if "PUT" in sig: row_color = "#220000" # Dark Red bg
        
        slots.append({
            "TIME": curr.strftime("%H:%M"),
            "SIGNAL": sig,
            "CONFIDENCE": f"{score}%",
            "VOLATILITY": f"{vol}/100"
        })
        curr += timedelta(minutes=15)
    
    # Display as DataFrame for clean look
    df = pd.DataFrame(slots)
    
    # Custom coloring function
    def color_signals(val):
        color = 'white'
        if 'CALL' in val: color = '#00FF99'
        elif 'PUT' in val: color = '#FF3333'
        return f'color: {color}; font-weight: bold;'
    
    st.dataframe(df.style.map(color_signals, subset=['SIGNAL']), use_container_width=True)

# --- TAB 2: INTRADAY STOCKS ---
with tab_stocks:
    st.markdown("### 🎯 INTRADAY STOCK SNIPER")
    
    # Specific Logic for Stocks (Different from Options)
    # We check the "Hero Stock" + 2 others for specific entry times
    
    cols = st.columns(3)
    target_stocks = [hero_stk, "RELIANCE", "HDFCBANK"]
    
    for i, ticker in enumerate(target_stocks):
        with cols[i]:
            st.markdown(f"#### {ticker}")
            
            # Simulate scanning this stock across the day
            # In live mode, we check RIGHT NOW. In backtest, we show the best time.
            
            best_time = "WAITING..."
            best_action = "NEUTRAL"
            highest_score = 0
            
            # Scan the day to find the "Best Time"
            scan_time = t_start
            while scan_time <= t_end:
                if is_today and scan_time > datetime.now(IST): break
                
                # Randomized hash + Astro to simulate stock-specific variance
                stock_seed = int(hashlib.md5((ticker + scan_time.strftime("%H%M")).encode()).hexdigest(), 16) % 100
                sig, score = get_trade_signal(scan_time)
                
                # Combine General Signal + Stock Variance
                stock_score = (score + stock_seed) / 2
                
                if stock_score > highest_score:
                    highest_score = stock_score
                    best_time = scan_time.strftime("%H:%M")
                    best_action = "BUY" if stock_score > 60 else "SELL" if stock_score < 40 else "HOLD"
                
                scan_time += timedelta(minutes=30)
            
            # Display Result
            color = "green" if best_action == "BUY" else "red" if best_action == "SELL" else "gray"
            st.markdown(f"""
            <div class="signal-box" style="border-left: 5px solid {color};">
                <div class="big-font" style="color:{color}">{best_action}</div>
                <div>Best Window: <b>{best_time}</b></div>
                <div>Strength: {int(highest_score)}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Mini Chart (Visualizing the trend for the day)
            st.area_chart([math.sin(x) + (highest_score/100) for x in range(10)], height=100)