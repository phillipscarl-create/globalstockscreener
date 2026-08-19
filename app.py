import io
import requests
import pandas as pd
import streamlit as st
from alpha_vantage.timeseries import TimeSeries

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Stock Screener", layout="wide")
st.title("📈 Global Stock Screener")

# --- SECRETS & API SETUP ---
API_KEY = st.secrets.get("ALPHA_VANTAGE_KEY")

if not API_KEY:
    st.error("⚠️ `ALPHA_VANTAGE_KEY` not found in Streamlit Secrets. Please add it under Settings -> Secrets.")
    st.stop()


# --- CACHED DATA FETCHING FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Fetches S&P 500 ticker list from Wikipedia using lxml parser."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    
    # Wrap in StringIO to avoid pandas deprecation warning
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    
    # Return list of tickers (cleaning dots for Alpha Vantage format)
tickers = df['Symbol'].tolist()
    return tickers


@st.cache_data(ttl=86400)
def get_stock_data(symbol):
    """Fetches daily stock history from Alpha Vantage."""
    ts = TimeSeries(key=API_KEY, output_format='pandas')
    data, meta_data = ts.get_daily_adjusted(symbol=symbol)
    
    # Rename Alpha Vantage columns to clean titles
    data.columns = [col.split('. ')[1] for col in data.columns]
    return data


# --- APP INTERFACE ---

st.sidebar.header("Screener Settings")

# Ticker Selection
try:
    available_tickers = get_sp500_tickers()
except Exception as e:
    st.warning(f"Could not load S&P 500 list from Wikipedia. Falling back to default list. Error: {e}")
    available_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

selected_ticker = st.sidebar.selectbox("Select Ticker Symbol", available_tickers)

st.subheader(f"Data Analysis for: {selected_ticker}")

# Fetch Stock Data
if st.button("Fetch Stock Data") or selected_ticker:
    with st.spinner("Fetching data from Alpha Vantage..."):
        try:
            df = get_stock_data(selected_ticker)
            
            # Display Latest Metrics
            latest_close = df['close'].iloc[0]
            prev_close = df['close'].iloc[1]
            change = latest_close - prev_close
            pct_change = (change / prev_close) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Latest Close", f"${latest_close:.2f}")
            col2.metric("Change ($)", f"${change:.2f}")
            col3.metric("Change (%)", f"{pct_change:.2f}%")
            
            # Display Chart
            st.write("### 1-Year Adjusted Closing Price")
            st.line_chart(df['close'])
            
            # Raw Data Expander
            with st.expander("View Raw Data Table"):
                st.dataframe(df)
                
        except Exception as e:
            st.error(
                f"Could not fetch data for **{selected_ticker}**. "
                "You may have reached Alpha Vantage's 25 request/day free limit or the symbol is invalid."
            )
            st.caption(f"Technical error: {e}")
