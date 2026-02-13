import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="Pro Stock Dashboard", layout="wide")
st.title("📈 Pro Financial Dashboard")

# --- CACHED DATA FETCHING ---
@st.cache_data(ttl=600)
def get_data(symbol):
    try:
        # Fetch data
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None
        
        # Standardize columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Technicals
        df['EMA8'] = df['Close'].ewm(span=8).mean()
        df['EMA21'] = df['Close'].ewm(span=21).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()
        
        curr = df['Close'].iloc[-1]
        ema200 = df['EMA200'].iloc[-1]
        prev_w = df['Close'].iloc[-5] if len(df) > 5 else df['Close'].iloc[0]
        
        # Color Logic: Bullish if price > EMA200
        status = "BULLISH" if curr > ema200 else "BEARISH"
        status_color = "green" if status == "BULLISH" else "red"

        return {
            "df": df.tail(60), # Last 60 days for chart
            "price": curr,
            "delta": ((curr - prev_w)/prev_w)*100,
            "status": status,
            "color": status_color,
            "high52": df['High'].max(),
            "low52": df['Low'].min(),
            "vol": df['Volume'].iloc[-1],
            "tech": {
                "EMA 8": df['EMA8'].iloc[-1],
                "EMA 21": df['EMA21'].iloc[-1],
                "EMA 200": ema200
            }
        }
    except: return None

# --- SETTINGS ---
with st.sidebar:
    st.header("Settings")
    tickers_input = st.text_area("Enter Tickers (comma separated)", "AAPL, MSFT, TSLA, BTC-USD, NVDA")
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

# --- DISPLAY GRID ---
if tickers:
    grid = st.columns(2) # 2 columns look better with charts
    for idx, ticker in enumerate(tickers):
        with grid[idx % 2]:
            with st.container(border=True):
                data = get_data(ticker)
                if data:
                    # Header with Color Coding
                    c1, c2 = st.columns([2, 1])
                    c1.subheader(f"{ticker}")
                    c2.markdown(f":{data['color']}[**{data['status']}**]")
                    
                    # Main Metrics
                    st.metric("Price", f"${data['price']:.2f}", f"{data['delta']:.2f}% (5d)")
                    
                    # Small Candlestick Chart
                    fig = go.Figure(data=[go.Candlestick(
                        x=data['df'].index,
                        open=data['df']['Open'],
                        high=data['df']['High'],
                        low=data['df']['Low'],
                        close=data['df']['Close'],
                        name="Price"
                    )])
                    fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    # Additional Info Table
                    info_cols = st.columns(2)
                    info_cols[0].write(f"**52W High:** ${data['high52']:.2f}")
                    info_cols[0].write(f"**52W Low:** ${data['low52']:.2f}")
                    info_cols[1].write(f"**Vol:** {data['vol']:.0f}")
                    
                    with st.expander("View EMAs"):
                        st.table(pd.DataFrame(data['tech'].items(), columns=["Metric", "Value"]).set_index("Metric"))
                else:
                    st.error(f"Could not load {ticker}")
