import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# Page Config
st.set_page_config(page_title="Technical Comparison Dashboard", layout="wide")
st.title("📊 4-EMA Benchmark Analysis")

# --- DATA FETCHING & CALCULATIONS ---
@st.cache_data(ttl=600)
def get_analysis(symbol, interval):
    try:
        df = yf.download(symbol, period="max", interval=interval, progress=False)
        if df.empty or len(df) < 25: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. Base Indicators
        df['EMA4'] = df['Close'].ewm(span=4, adjust=False).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA100'] = df['Close'].rolling(window=100).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['EMA250'] = df['Close'].ewm(span=250, adjust=False).mean()
        df['EMA600'] = df['Close'].ewm(span=600, adjust=False).mean()
        
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        df['BB_Top'] = sma20 + (std20 * 2)
        df['BB_Bot'] = sma20 - (std20 * 2)

        curr_p = df['Close'].iloc[-1]
        curr_top = df['BB_Top'].iloc[-1]
        curr_bot = df['BB_Bot'].iloc[-1]

        # 2. BB Proximity & Crossing Logic
        def get_bb_proximity(price, top, bot):
            # Within 1% or Crossed
            top_dist = abs(price - top) / top
            bot_dist = abs(price - bot) / bot
            
            upper_alert = "NORMAL"
            upper_col = "gray"
            if price >= top: 
                upper_alert = "CROSSED ABOVE"
                upper_col = "green"
            elif top_dist <= 0.01:
                upper_alert = "NEAR TOP (1%)"
                upper_col = "orange"

            lower_alert = "NORMAL"
            lower_col = "gray"
            if price <= bot:
                lower_alert = "CROSSED BELOW"
                lower_col = "red"
            elif bot_dist <= 0.01:
                lower_alert = "NEAR BOT (1%)"
                lower_col = "orange"
                
            return upper_alert, upper_col, lower_alert, lower_col

        u_alert, u_col, l_alert, l_col = get_bb_proximity(curr_p, curr_top, curr_bot)

        # 3. Consecutive Touches/Outside Logic
        def count_consecutive(prices, tops, bottoms):
            upper_streak = 0
            lower_streak = 0
            
            # Check Upper
            for i in range(len(prices)-1, -1, -1):
                if prices.iloc[i] >= tops.iloc[i]: upper_streak += 1
                else: break
                
            # Check Lower
            for i in range(len(prices)-1, -1, -1):
                if prices.iloc[i] <= bottoms.iloc[i]: lower_streak += 1
                else: break
            
            return upper_streak, lower_streak

        u_streak, l_streak = count_consecutive(df['Close'], df['BB_Top'], df['BB_Bot'])

        # 4. Volatility & Stochastic
        df['BB_Width'] = ((df['BB_Top'] - df['BB_Bot']) / sma20) * 100
        curr_w = df['BB_Width'].iloc[-1]
        vol_status = "EXPANDING 📈" if curr_w > df['BB_Width'].iloc[-2] else "TIGHTENING 📉"
        
        low_5 = df['Low'].rolling(window=5).min()
        high_5 = df['High'].rolling(window=5).max()
        df['%K'] = (df['Close'] - low_5) / (high_5 - low_5) * 100
        stoch_v = df['%K'].iloc[-1]
        stoch_dir = "UP 📈" if stoch_v > df['%K'].iloc[-2] else "DOWN 📉"

        # Last Cross Scan
        last_cross_type = "None"; last_cross_date = "N/A"
        for i in range(len(df)-2, 1, -1):
            p_v = df['%K'].iloc[i]; c_v = df['%K'].iloc[i+1]
            if p_v > 80 and c_v <= 80:
                last_cross_type = "Below 80"; last_cross_date = df.index[i+1].strftime('%Y-%m-%d'); break
            if p_v < 20 and c_v >= 20:
                last_cross_type = "Above 20"; last_cross_date = df.index[i+1].strftime('%Y-%m-%d'); break

        last = df.iloc[-1]
        def compare(target_val, name):
            if pd.isna(target_val): return {"name": name, "val": 0, "status": "N/A", "s_color": "gray", "d_val": 0, "d_pct": 0, "d_color": "gray"}
            diff = curr_p - target_val
            pct = (diff / target_val) * 100
            s_val = "-" if name == "4 EMA" else ("YES" if last['EMA4'] > target_val else "NO")
            s_col = "gray" if name == "4 EMA" else ("green" if last['EMA4'] > target_val else "red")
            return {"name": name, "val": target_val, "status": s_val, "s_color": s_col, "d_val": diff, "d_pct": pct, "d_color": "green" if diff >= 0 else "red"}

        comparisons = [compare(last['EMA4'], "4 EMA"), compare(last['EMA20'], "20 EMA"), compare(last['SMA50'], "50 SMA"), compare(last['SMA100'], "100 SMA"), compare(last['SMA200'], "200 SMA"), compare(last['EMA250'], "250 EMA"), compare(last['EMA600'], "600 EMA"), compare(last['BB_Top'], "Upper BB"), compare(last['BB_Bot'], "Lower BB")]

        streak = 0
        is_green = (df['Close'] > df['Open']).tolist()
        for i in reversed(is_green):
            if i == is_green[-1]: streak += 1
            else: break

        return {
            "price": curr_p, "ema4": last['EMA4'], "pe_diff": curr_p - last['EMA4'], "pe_pct": ((curr_p-last['EMA4'])/last['EMA4'])*100, 
            "pe_color": "green" if curr_p >= last['EMA4'] else "red", "streak": streak if is_green[-1] else -streak, 
            "comparisons": comparisons, "stoch_val": stoch_v, "stoch_dir": stoch_dir, "stoch_dir_col": "green" if stoch_dir == "UP 📈" else "red",
            "last_cross_type": last_cross_type, "last_cross_date": last_cross_date,
            "bw_pct": curr_w, "vol_status": vol_status, "vol_color": "orange" if curr_w > df['BB_Width'].iloc[-2] else "cyan",
            "u_alert": u_alert, "u_col": u_col, "l_alert": l_alert, "l_col": l_col,
            "u_streak": u_streak, "l_streak": l_streak
        }
    except: return None

# --- UI ---
with st.sidebar:
    st.header("Settings")
    raw_tickers = st.text_area("Tickers", "AAPL, MSFT, TSLA, BTC-USD, NVDA, SPY")
    tickers = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]

if tickers:
    grid = st.columns(2)
    for idx, ticker in enumerate(tickers):
        with grid[idx % 2]:
            with st.container(border=True):
                st.header(ticker)
                t_d, t_w, t_m = st.tabs(["Daily", "Weekly", "Monthly"])
                for tab, interval in zip([t_d, t_w, t_m], ["1d", "1wk", "1mo"]):
                    with tab:
                        data = get_analysis(ticker, interval)
                        if data:
                            c1, c2 = st.columns(2)
                            s_color = "green" if data['streak'] > 0 else "red"
                            c1.markdown(f"**Streak:** :{s_color}[{data['streak']:+d}] | **Price:** `${data['price']:.2f}`")
                            c1.markdown(f"**vs. 4EMA:** :{data['pe_color']}[{data['pe_diff']:+.2f} ({data['pe_pct']:+.2f}%)]")
                            
                            lc_color = "green" if "Above 20" in data['last_cross_type'] else "red"
                            c2.markdown(f"**Stoch:** `{data['stoch_val']:.1f}` | :{data['stoch_dir_col']}[{data['stoch_dir']}]")
                            c2.markdown(f"**Last Cross:** :{lc_color}[{data['last_cross_date']}]")

                            # --- NEW BOLLINGER ANALYSIS AREA ---
                            st.markdown("### 🫧 Bollinger Analysis")
                            b1, b2, b3 = st.columns(3)
                            b1.markdown(f"**Vol:** :{data['vol_color']}[{data['vol_status']}]")
                            b1.markdown(f"**Width:** `{data['bw_pct']:.1f}%`")
                            
                            b2.markdown(f"**Upper:** :{data['u_col']}[{data['u_alert']}]")
                            b2.markdown(f"**Streak:** `{data['u_streak']} bars`")
                            
                            b3.markdown(f"**Lower:** :{data['l_col']}[{data['l_alert']}]")
                            b3.markdown(f"**Streak:** `{data['l_streak']} bars`")
                            
                            st.divider()
                            h1, h2, h3 = st.columns([2.2, 1.3, 2.5])
                            h1.write("**Indicator (Value)**"); h2.write("**4 EMA Above?**"); h3.write("**$ and % Above Price**")
                            for comp in data['comparisons']:
                                col_name, col_status, col_dist = st.columns([2.2, 1.3, 2.5])
                                col_name.write(f"{comp['name']} (`${comp['val']:.2f}`)")
                                col_status.markdown(f":{comp['s_color']}[**{comp['status']}**]")
                                col_dist.markdown(f":{comp['d_color']}[{comp['d_val']:+.2f} ({comp['d_pct']:+.2f}%)]")
                        else: st.error(f"Data unavailable for {ticker}.")
