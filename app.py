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
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean() # NEW: 20 EMA
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA100'] = df['Close'].rolling(window=100).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['EMA250'] = df['Close'].ewm(span=250, adjust=False).mean()
        df['EMA600'] = df['Close'].ewm(span=600, adjust=False).mean()
        
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        df['BB_Bot'] = sma20 - (std20 * 2)

        last = df.iloc[-1]
        curr_price = last['Close']
        ema4 = last['EMA4']

        # 2. Price vs 4 EMA Calculation
        price_ema_diff = curr_price - ema4
        price_ema_pct = (price_ema_diff / ema4) * 100
        pe_color = "green" if price_ema_diff >= 0 else "red"

        # 3. Convergence Logic (BB Bot vs SMA 50)
        dist_bb_sma = last['BB_Bot'] - last['SMA50']
        bb_slope = (df['BB_Bot'].iloc[-1] - df['BB_Bot'].iloc[-4]) / 3
        sma_slope = (df['SMA50'].iloc[-1] - df['SMA50'].iloc[-4]) / 3
        
        closure_rate = sma_slope - bb_slope if dist_bb_sma < 0 else bb_slope - sma_slope
        
        est_periods = "N/A"
        if closure_rate > 0 and abs(dist_bb_sma) > 0:
            est_periods = f"{int(abs(dist_bb_sma) / closure_rate)} {interval.replace('1', '')}s"
        elif dist_bb_sma > 0:
            est_periods = "Above SMA50"
        else:
            est_periods = "Moving Away"

        # 4. Comparison Logic Function
        def compare(target_val, name):
            if pd.isna(target_val): 
                return {"name": name, "val": 0, "status": "N/A", "dist_val": 0, "dist_pct": 0, "color": "white"}
            diff_from_price = curr_price - target_val
            pct_from_price = (diff_from_price / target_val) * 100
            ema_above = ema4 > target_val
            return {
                "name": name, 
                "val": target_val,
                "status": "YES" if ema_above else "NO", 
                "dist_val": diff_from_price, 
                "dist_pct": pct_from_price, 
                "color": "green" if ema_above else "red"
            }

        comparisons = [
            compare(last['EMA20'], "20 EMA"), # Added to list
            compare(last['SMA50'], "50 SMA"), 
            compare(last['SMA100'], "100 SMA"), 
            compare(last['SMA200'], "200 SMA"),
            compare(last['EMA250'], "250 EMA"), 
            compare(last['EMA600'], "600 EMA"),
            compare(last['BB_Bot'], "Lower BB")
        ]

        # Streak
        is_green = (df['Close'] > df['Open']).tolist()
        streak = 0
        for i in reversed(is_green):
            if i == is_green[-1]: streak += 1
            else: break

        return {
            "price": curr_price,
            "ema4": ema4,
            "pe_diff": price_ema_diff,
            "pe_pct": price_ema_pct,
            "pe_color": pe_color,
            "streak": streak if is_green[-1] else -streak,
            "comparisons": comparisons,
            "cond_bb": "YES" if dist_bb_sma > 0 else "NO",
            "cond_bb_color": "green" if dist_bb_sma > 0 else "red",
            "bb_dist": dist_bb_sma,
            "est_cross": est_periods
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
                            
                            c2.markdown(f"**BB Bot > SMA 50?** :{data['cond_bb_color']}[{data['cond_bb']}]")
                            c2.markdown(f"**Gap to SMA 50:** `{data['bb_dist']:.2f}`")
                            c2.markdown(f"**Est. Cross in:** ` {data['est_cross']} `")
                            
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
