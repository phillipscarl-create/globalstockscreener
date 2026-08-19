import io
import requests
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Stock Screener", layout="wide")
st.title("📈 Global Stock Screener")


# --- CACHED DATA FETCHERS ---

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Fetches S&P 500 ticker list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    return df['Symbol'].tolist()


@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    """Fetches stock history directly from Yahoo Finance endpoints with custom headers."""
    # Convert symbol formatting if necessary (e.g., BRK.B to BRK-B for Yahoo)
    formatted_symbol = symbol.replace('.', '-')
    
    url = f"https://query1.finance.yahoo.com/v7/finance/download/{formatted_symbol}?period1=0&period2=9999999999&interval=1d&events=history"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise ValueError(f"Server returned status code {response.status_code}. Symbol may be invalid.")
        
    df = pd.read_csv(io.StringIO(response.text))
    
    if df.empty or 'Close' not in df.columns:
        raise ValueError("No price data found for this symbol.")
        
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.sort_index(ascending=True, inplace=True)
    
    # Return last 250 trading days (~1 year)
    return df.tail(250)


# --- INTERFACE ---

st.sidebar.header("Screener Settings")

# Fetch Tickers
try:
    available_tickers = get_sp500_tickers()
except Exception:
    available_tickers = ["MMM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

selected_ticker = st.sidebar.selectbox("Select Ticker Symbol", available_tickers, index=0)

st.subheader(f"Data Analysis: {selected_ticker}")

# Fetch & Render Stock Data
try:
    with st.spinner("Loading price history..."):
        df = get_stock_data(selected_ticker)
        
        # Calculate Key Metrics
        latest_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Latest Close", f"${latest_close:.2f}")
        col2.metric("1-Day Change ($)", f"${change:.2f}")
        col3.metric("1-Day Change (%)", f"{pct_change:.2f}%")
        
        # Render Price Chart
        st.write("### 1-Year Price History")
        st.line_chart(df['Close'])
        
        # Raw Data Table
        with st.expander("View Raw Historical Data"):
            st.dataframe(df.sort_index(ascending=False))

except Exception as e:
    st.error(f"Could not load data for **{selected_ticker}**.")
    st.caption(f"Details: {e}")
