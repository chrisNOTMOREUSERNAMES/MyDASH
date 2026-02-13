import streamlit as st
import pandas as pd
import yfinance as yf

# Page Config
st.set_page_config(page_title="Global Stock Dashboard", layout="wide")
st.title("📈 Live Financial Dashboard")

# --- SETTINGS ---
with st.expander("🛠️ Dashboard Settings - Enter Tickers", expanded=False):
    cols = st.columns(5)
    tickers = []
    default = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMD", "BTC-USD", "ETH-USD", "SPY", "QQQ"]
    for i in range(15):
        val = default[i] if i < len(default) else ""
        with cols[i % 5]:
            t = st.text_input(f"Ticker {i+1}", value=val, key=f"t_{i}")
            if t: tickers.append(t.upper())

# --- CACHED DATA FETCHING (Prevents Yahoo Errors) ---
@st.cache_data(ttl=600) # Only fetch from Yahoo every 10 mins
def get_data(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None
        
        # FIX: Remove MultiIndex if present (common yfinance error)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Technical Indicators
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        
        curr = df['Close'].iloc[-1]
        prev_w = df['Close'].iloc[-5] if len(df) > 5 else df['Close'].iloc[0]
        
        return {
            "price": curr,
            "delta": ((curr - prev_w)/prev_w)*100,
            "tech": {"EMA 8": df['EMA8'].iloc[-1], "EMA 21": df['EMA21'].iloc[-1], "EMA 200": df['EMA200'].iloc[-1]}
        }
    except: return None

# --- DISPLAY GRID ---
st.divider()
if tickers:
    grid = st.columns(3)
    for idx, ticker in enumerate(tickers):
        with grid[idx % 3]:
            with st.container(border=True):
                data = get_data(ticker)
                if data:
                    st.subheader(ticker)
                    st.metric("Price", f"${data['price']:.2f}", f"{data['delta']:.2f}% (Weekly)")
                    st.table(pd.DataFrame(data['tech'].items(), columns=["Metric", "Value"]).set_index("Metric"))
                else:
                    st.error(f"{ticker} not found")
