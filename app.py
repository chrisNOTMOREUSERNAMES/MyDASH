import streamlit as st
import pandas as pd
import yfinance as yf

# Page Config
st.set_page_config(page_title="Technical Analysis Dashboard", layout="wide")
st.title("📊 Multi-Timeframe Analysis")

# --- DATA FETCHING & CALCULATIONS ---
@st.cache_data(ttl=600)
def get_analysis(symbol, interval):
    try:
        # Fetch max period to ensure 600-period indicators have enough data
        df = yf.download(symbol, period="max", interval=interval, progress=False)
        if df.empty or len(df) < 2: return None
        
        # Flatten MultiIndex if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. Indicators
        df['EMA4'] = df['Close'].ewm(span=4, adjust=False).mean()
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA100'] = df['Close'].rolling(window=100).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['EMA250'] = df['Close'].ewm(span=250, adjust=False).mean()
        df['EMA600'] = df['Close'].ewm(span=600, adjust=False).mean()
        
        # Bollinger Bands (20-period)
        sma20 = df['Close'].rolling(window=20).mean()
        std20 = df['Close'].rolling(window=20).std()
        df['BB_Top'] = sma20 + (std20 * 2)
        df['BB_Bot'] = sma20 - (std20 * 2)

        # 2. Streak Counter (Green vs Red candles)
        # We look at the most recent candle and count backwards until the color changes
        is_green = (df['Close'] > df['Open']).tolist()
        last_color = is_green[-1]
        streak = 0
        for i in reversed(is_green):
            if i == last_color:
                streak += 1
            else:
                break
        final_streak = streak if last_color else -streak

        # 3. Last Row Data
        last = df.iloc[-1]
        
        # Condition A: BB Bottom > SMA 50
        cond_bb_sma = last['BB_Bot'] > last['SMA50']
        
        # Condition B: EMA 4 > (100SMA, 200SMA, 250EMA, 600EMA)
        # Check if 600 EMA exists (requires enough history)
        ema600_val = last['EMA600']
        if pd.isna(ema600_val):
            cond_ema4_all = "N/A (Insufficient Data)"
        else:
            cond_ema4_all = (last['EMA4'] > last['SMA100'] and 
                             last['EMA4'] > last['SMA200'] and 
                             last['EMA4'] > last['EMA250'] and 
                             last['EMA4'] > ema600_val)

        return {
            "price": last['Close'],
            "streak": final_streak,
            "cond_bb": cond_bb_sma,
            "cond_ema4": cond_ema4_all,
            "tech": {
                "4 EMA": last['EMA4'],
                "100 SMA": last['SMA100'],
                "200 SMA": last['SMA200'],
                "250 EMA": last['EMA250'],
                "600 EMA": last['EMA600'],
                "BB Top": last['BB_Top'],
                "BB Bottom": last['BB_Bot'],
                "50 SMA": last['SMA50']
            }
        }
    except Exception as e:
        return None

# --- UI SETTINGS ---
with st.expander("🛠️ Dashboard Settings - Enter Tickers", expanded=False):
    cols = st.columns(5)
    tickers = []
    default = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "BTC-USD", "SPY", "QQQ"]
    for i in range(10):
        val = default[i] if i < len(default) else ""
        with cols[i % 5]:
            t = st.text_input(f"Ticker {i+1}", value=val, key=f"t_{i}")
            if t: tickers.append(t.upper())

# --- DISPLAY LOOP ---
st.divider()
if tickers:
    # Use 2 columns for a better fit with all the new data points
    grid = st.columns(2)
    for idx, ticker in enumerate(tickers):
        with grid[idx % 2]:
            with st.container(border=True):
                st.header(f"{ticker}")
                
                # Create Tabs for timeframes
                tab_d, tab_w, tab_m = st.tabs(["Daily", "Weekly", "Monthly"])
                
                for tab, interval in zip([tab_d, tab_w, tab_m], ["1d", "1wk", "1mo"]):
                    with tab:
                        data = get_analysis(ticker, interval)
                        if data:
                            # Streak Display
                            s_color = "green" if data['streak'] > 0 else "red"
                            st.markdown(f"### Streak: :{s_color}[{data['streak']:+d}]")
                            
                            # YES/NO Highlighted Conditions
                            c1_color = "green" if data['cond_bb'] else "red"
                            c1_text = "YES" if data['cond_bb'] else "NO"
                            st.subheader(f"BB Bottom > SMA 50? :{c1_color}[{c1_text}]")

                            if isinstance(data['cond_ema4'], str):
                                st.warning(data['cond_ema4'])
                            else:
                                c2_color = "green" if data['cond_ema4'] else "red"
                                c2_text = "YES" if data['cond_ema4'] else "NO"
                                st.subheader(f"4 EMA > All (100, 200, 250, 600)? :{c2_color}[{c2_text}]")

                            # Technicals Table
                            st.table(pd.DataFrame(data['tech'].items(), columns=["Indicator", "Value"]).set_index("Indicator"))
                        else:
                            st.error(f"Data not available for {ticker} at this timeframe.")
