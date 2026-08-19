import io
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from polygon import RESTClient

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Stock Screener", layout="wide")
st.title("📈 Global Stock Screener")

# --- SECRETS & API SETUP ---
API_KEY = st.secrets.get("POLYGON_KEY") or st.secrets.get("general", {}).get("POLYGON_KEY")

if not API_KEY:
    st.error("⚠️ `POLYGON_KEY` is missing in Streamlit Secrets. Go to App Settings -> Secrets to add it.")
    st.stop()

client = RESTClient(api_key=API_KEY)


# --- CACHED DATA FETCHERS ---

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Fetches S&P 500 ticker list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    return df['Symbol'].tolist()


@st.cache_data(ttl=3600)
def get_stock_data(symbol):
    """Fetches 1 year of daily historical prices from Polygon.io."""
    # Convert symbol formatting for Polygon (e.g. BRK.B to BRK.B)
    formatted_symbol = symbol.replace('-', '.')
    
    # Calculate date range for past 1 year
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    aggs = []
    for agg in client.list_aggs(
        ticker=formatted_symbol,
        multiplier=1,
        timespan="day",
        from_=from_date,
        to=to_date,
        limit=5000
    ):
        aggs.append({
            "Date": pd.to_datetime(agg.timestamp, unit="ms"),
            "Open": agg.open,
            "High": agg.high,
            "Low": agg.low,
            "Close": agg.close,
            "Volume": agg.volume
        })
        
    if not aggs:
        raise ValueError(f"No price data returned for {symbol}.")
        
    df = pd.DataFrame(aggs)
    df.set_index("Date", inplace=True)
    df.sort_index(ascending=True, inplace=True)
    return df


# --- USER INTERFACE ---

st.sidebar.header("Screener Settings")

# Ticker Selection
try:
    available_tickers = get_sp500_tickers()
except Exception:
    available_tickers = ["MMM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

selected_ticker = st.sidebar.selectbox("Select Ticker Symbol", available_tickers, index=0)

st.subheader(f"Data Analysis: {selected_ticker}")

# Fetch & Render Stock Data
try:
    with st.spinner(f"Loading Polygon data for {selected_ticker}..."):
        df = get_stock_data(selected_ticker)
        
        # Key Metrics
        latest_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Latest Close", f"${latest_close:.2f}")
        col2.metric("1-Day Change ($)", f"${change:.2f}")
        col3.metric("1-Day Change (%)", f"{pct_change:.2f}%")
        
        # Price Chart
        st.write("### 1-Year Price History")
        st.line_chart(df['Close'])
        
        # Data Table
        with st.expander("View Raw Historical Data"):
            st.dataframe(df.sort_index(ascending=False))

except Exception as e:
    st.error(f"Could not load data for **{selected_ticker}**.")
    st.caption(f"Error Details: {e}")
