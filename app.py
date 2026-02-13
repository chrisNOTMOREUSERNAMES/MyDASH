import streamlit as st
import pandas as pd
import yfinance as yf

# Page Config
st.set_page_config(page_title="Technical Comparison Dashboard", layout="wide")
st.title("📊 4-EMA Benchmark Analysis")

# --- DATA FETCHING & CALCULATIONS ---
@st.cache_data(ttl=600)
def get_analysis(symbol, interval):
    try:
        # Fetch max history for the 600 EMA
        df = yf.download(symbol, period="max", interval=interval, progress=False)
        if df.empty or len(df) < 2: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. Base Indicators
        df['EMA4'] = df['Close'].ewm(span=4, adjust=False).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA100'] = df['Close'].rolling(window=100).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['EMA250'] = df['Close'].ewm(span=250, adjust=False).mean()
        df['EMA600'] = df['Close'].ewm(span=600, adjust=False).mean()
        
        # Bollinger Bands
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        df['BB_Top'] = sma20 + (std20 * 2)
        df['BB_Bot'] = sma20 - (std20 * 2)

        last = df.iloc[-1]
        ema4 = last['EMA4']

        # 2. Comparison Logic Function
        def compare(target_val, name):
            if pd.isna(target_val):
                return {"name": name, "status": "N/A", "dist_val": 0, "dist_pct": 0, "color": "white"}
            
            diff = ema4 - target_val
            pct = (diff / target_val) * 100
            is_above = diff > 0
            
            return {
                "name": name,
                "status": "YES" if is_above else "NO",
                "dist_val": diff,
                "dist_pct": pct,
                "color": "green" if is_above else "red",
                "target_price": target_val
            }

        # 3. Build Comparison List
        comparisons = [
            compare(last['SMA100'], "100 SMA"),
            compare(last['SMA200'], "200 SMA"),
            compare(last['EMA250'], "250 EMA"),
            compare(last['EMA600'], "600 EMA"),
            compare(last['SMA50'], "50 SMA"),
            compare(last['BB_Top'], "Upper BB"),
            compare(last['BB_Bot'], "Lower BB"),
        ]

        # Streak Logic
        is_green = (df['Close'] > df['Open']).tolist()
        last_color = is_green[-1]
        streak = 0
        for i in reversed(is_green):
            if i == last_color: streak += 1
            else: break
        
        # Special Condition: BB Bottom > SMA 50
        cond_bb_sma = last['BB_Bot'] > last['SMA50']

        return {
            "price": last['Close'],
            "ema4": ema4,
            "streak": streak if last_color else -streak,
            "comparisons": comparisons,
            "cond_bb": "YES" if cond_bb_sma else "NO",
            "cond_bb_color": "green" if cond_bb_sma else "red"
        }
    except:
        return None

# --- UI SETTINGS ---
with st.sidebar:
    st.header("Dashboard Settings")
    raw_tickers = st.text_area("Tickers (comma separated)", "AAPL, MSFT, TSLA, BTC-USD, NVDA, SPY")
    tickers = [t.strip().upper() for t in raw_tickers.split(",") if t.strip()]

# --- DISPLAY LOOP ---
if tickers:
    grid = st.columns(2)
    for idx, ticker in enumerate(tickers):
        with grid[idx % 2]:
            with st.container(border=True):
                st.header(f"{ticker}")
                t_d, t_w, t_m = st.tabs(["Daily", "Weekly", "Monthly"])
                
                for tab, interval in zip([t_d, t_w, t_m], ["1d", "1wk", "1mo"]):
                    with tab:
                        data = get_analysis(ticker, interval)
                        if data:
                            # 1. Main Metrics
                            c1, c2 = st.columns(2)
                            s_color = "green" if data['streak'] > 0 else "red"
                            c1.markdown(f"**Streak:** :{s_color}[{data['streak']:+d}]")
                            c1.markdown(f"**4 EMA:** `${data['ema4']:.2f}`")
                            c2.markdown(f"**BB Bot > SMA 50?** :{data['cond_bb_color']}[{data['cond_bb']}]")
                            
                            st.write("---")
                            st.write("**4 EMA vs. Indicators:**")
                            
                            # 2. Detailed Comparisons
                            for comp in data['comparisons']:
                                col_name, col_status, col_dist = st.columns([1.5, 1, 3])
                                
                                col_name.write(f"**{comp['name']}**")
                                col_status.markdown(f":{comp['color']}[{comp['status']}]")
                                
                                # Formatting the dollar and percentage string
                                dist_str = f"{comp['dist_val']:+.2f} ({comp['dist_pct']:+.2f}%)"
                                col_dist.markdown(f":{comp['color']}[{dist_str}]")
                                
                        else:
                            st.error("Insufficient historical data for this timeframe.")
