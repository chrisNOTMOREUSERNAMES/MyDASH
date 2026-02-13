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
        if df.empty or len(df) < 50: return None
        
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
        df['BB_Top'] = sma20 + (std20 * 2) # Added Upper BB
        df['BB_Bot'] = sma20 - (std20 * 2)

        # 2. Slow Stochastic (5, 1) & Historical Cross Logic
        low_5 = df['Low'].rolling(window=5).min()
        high_5 = df['High'].rolling(window=5).max()
        df['%K'] = (df['Close'] - low_5) / (high_5 - low_5) * 100
        
        stoch_val = df['%K'].iloc[-1]
        prev_stoch = df['%K'].iloc[-2]
        
        # Direction Logic
        direction = "UP 📈" if stoch_val > prev_stoch else "DOWN 📉"
        dir_color = "green" if stoch_val > prev_stoch else "red"

        # Find Last Cross Backward Scan
        last_cross_type = "None"
        last_cross_date = "N/A"
        
        for i in range(len(df)-2, 1, -1):
            prev_val = df['%K'].iloc[i]
            curr_val = df['%K'].iloc[i+1]
            if prev_val > 80 and curr_val <= 80:
                last_cross_type = "Below 80"
                last_cross_date = df.index[i+1].strftime('%Y-%m-%d')
                break
            if prev_val < 20 and curr_val >= 20:
                last_cross_type = "Above 20"
                last_cross_date = df.index[i+1].strftime('%Y-%m-%d')
                break

        last = df.iloc[-1]
        curr_price = last['Close']
        ema4 = last['EMA4']

        # 3. Price vs 4 EMA & Convergence
        price_ema_diff = curr_price - ema4
        price_ema_pct = (price_ema_diff / ema4) * 100
        dist_bb_sma = last['BB_Bot'] - last['SMA50']
        
        bb_slope = (df['BB_Bot'].iloc[-1] - df['BB_Bot'].iloc[-4]) / 3
        sma_slope = (df['SMA50'].iloc[-1] - df['SMA50'].iloc[-4]) / 3
        closure_rate = sma_slope - bb_slope if dist_bb_sma < 0 else bb_slope - sma_slope
        
        if closure_rate > 0:
            est_periods = f"{int(abs(dist_bb_sma) / closure_rate)} {interval.replace('1', '')}s"
        else:
            est_periods = "N/A"

        # 4. Comparison Logic
        def compare(target_val, name):
            if pd.isna(target_val): 
                return {"name": name, "val": 0, "status": "N/A", "dist_val": 0, "dist_pct": 0, "color": "white"}
            
            diff = curr_price - target_val
            pct = (diff / target_val) * 100
            
            # Special case for 4 EMA: It can't be above itself for the status
            if name == "4 EMA":
                status = "-"
                color = "white"
            else:
                status = "YES" if ema4 > target_val else "NO"
                color = "green" if ema4 > target_val else "red"
                
            return {
                "name": name, 
                "val": target_val, 
                "status": status, 
                "dist_val": diff, 
                "dist_pct": pct, 
                "color": color
            }

        # Added 4 EMA and Upper BB to this list
        comparisons = [
            compare(last['EMA4'], "4 EMA"),
            compare(last['EMA20'], "20 EMA"),
            compare(last['SMA50'], "50 SMA"), 
            compare(last['SMA100'], "100 SMA"), 
            compare(last['SMA200'], "200 SMA"), 
            compare(last['EMA250'], "250 EMA"), 
            compare(last['EMA600'], "600 EMA"),
            compare(last['BB_Top'], "Upper BB"),
            compare(last['BB_Bot'], "Lower BB")
        ]

        # Streak Logic
        is_green = (df['Close'] > df['Open']).tolist()
        streak = 0
        for i in reversed(is_green):
            if i == is_green[-1]: streak += 1
            else: break

        return {
            "price": curr_price, "ema4": ema4, "pe_diff": price_ema_diff, "pe_pct": price_ema_pct, "pe_color": "green" if price_ema_diff >= 0 else "red",
            "streak": streak if is_green[-1] else -streak, "comparisons": comparisons,
            "cond_bb": "YES" if dist_bb_sma > 0 else "NO", "cond_bb_color": "green" if dist_bb_sma > 0 else "red", "bb_dist": dist_bb_sma, "est_cross": est_periods,
            "stoch_val": stoch_val, "stoch_dir": direction, "stoch_dir_color": dir_color,
            "last_cross_type": last_cross_type, "last_cross_date": last_cross_date
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
                            
                            c1.markdown(f"**Streak:** :{s_color}[{data['streak']:+d}]")
                            c1.markdown(f"**Price:** `${data['price']:.2f}` (4EMA: `${data['ema4']:.2f}`)")
                            c1.markdown(f"**vs. 4EMA:** :{data['pe_color']}[{data['pe_diff']:+.2f} ({data['pe_pct']:+.2f}%)]")
                            
                            lc_color = "green" if "Above 20" in data['last_cross_type'] else "red"
                            c2.markdown(f"**Stoch (5,1):** `{data['stoch_val']:.1f}` | :{data['stoch_dir_color']}[{data['stoch_dir']}]")
                            c2.markdown(f"**Last Cross:** :{lc_color}[{data['last_cross_type']}]")
                            c2.markdown(f"**Cross Date:** `{data['last_cross_date']}`")
                            
                            st.divider()
                            h1, h2, h3 = st.columns([2.2, 1.3, 2.5])
                            h1.write("**Indicator (Value)**"); h2.write("**4 EMA Above?**"); h3.write("**$ and % Above Price**")
                            for comp in data['comparisons']:
                                col_name, col_status, col_dist = st.columns([2.2, 1.3, 2.5])
                                col_name.write(f"{comp['name']} (`${comp['val']:.2f}`)")
                                col_status.markdown(f":{comp['color']}[**{comp['status']}**]")
                                col_dist.markdown(f":{comp['color']}[{comp['dist_val']:+.2f} ({comp['dist_pct']:+.2f}%)]")
                        else:
                            st.error("Insufficient data.")
