import io
import requests
import pandas as pd
import streamlit as st
from alpha_vantage.timeseries import TimeSeries

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Global Stock Screener", layout="wide")
st.title("📈 Global Stock Screener")

# --- SECRETS & API SETUP ---
API_KEY = st.secrets.get("L1FUDEKZCUN8OIY5")
# Fetches the key whether it was saved as top-level OR under [general]
API_KEY = (
    st.secrets.get("ALPHA_VANTAGE_KEY") 
    or st.secrets.get("general", {}).get("ALPHA_VANTAGE_KEY")
)

if not API_KEY:
    st.error("⚠️ `ALPHA_VANTAGE_KEY` is missing in Streamlit Secrets. Go to App Settings -> Secrets to add it.")
    st.stop()

if not API_KEY:
    st.error("⚠️ `ALPHA_VANTAGE_KEY` is missing in Streamlit Secrets. Go to App Settings -> Secrets to add it.")
    st.stop()


# --- CACHED DATA FETCHERS ---

@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Fetches S&P 500 ticker list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(response.text))
    df = tables[0]
    # Return tickers with dots preserved for Alpha Vantage format (e.g. BRK.B)
    return df['Symbol'].tolist()


@st.cache_data(ttl=86400)
def get_stock_data(symbol):
    """
    Fetches daily stock history using Alpha Vantage.
    Cached for 24 hours to preserve your free 25 daily API calls.
    """
    ts = TimeSeries(key=API_KEY, output_format='pandas')
    
    # Try daily adjusted first, fallback to standard daily
    try:
        data, _ = ts.get_daily_adjusted(symbol=symbol)
    except Exception:
        data, _ = ts.get_daily(symbol=symbol)
        
    if data.empty:
        raise ValueError("No data returned from Alpha Vantage.")

    # Clean up column names (Alpha Vantage returns '1. open', '4. close', etc.)
    data.columns = [col.split('. ')[-1] for col in data.columns]
    
    # Sort dates chronologically
    data.sort_index(ascending=True, inplace=True)
    return data


# --- USER INTERFACE ---

st.sidebar.header("Screener Settings")

# Load S&P 500 Ticker Dropdown
try:
    available_tickers = get_sp500_tickers()
except Exception:
    available_tickers = ["MMM", "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]

selected_ticker = st.sidebar.selectbox("Select Ticker Symbol", available_tickers, index=0)

st.subheader(f"Data Analysis: {selected_ticker}")

# Process Stock Search
try:
    with st.spinner(f"Fetching Alpha Vantage data for {selected_ticker}..."):
        df = get_stock_data(selected_ticker)
        
        # Identify Close column (handles 'close' or 'adjusted close')
        close_col = 'adjusted close' if 'adjusted close' in df.columns else 'close'
        
        # Calculate Key Metrics
        latest_close = df[close_col].iloc[-1]
        prev_close = df[close_col].iloc[-2]
        change = latest_close - prev_close
        pct_change = (change / prev_close) * 100
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Latest Close", f"${latest_close:.2f}")
        col2.metric("1-Day Change ($)", f"${change:.2f}")
        col3.metric("1-Day Change (%)", f"{pct_change:.2f}%")
        
        # Plot Stock Price
        st.write("### Price History")
        st.line_chart(df[close_col])
        
        # Raw Data Table
        with st.expander("View Raw Historical Data"):
            st.dataframe(df.sort_index(ascending=False))

except Exception as e:
    st.error(f"Could not load data for **{selected_ticker}**.")
    st.warning(
        "**Possible Causes:**\n"
        "1. **25 Calls/Day Limit:** Alpha Vantage free tier allows only 25 requests daily.\n"
        "2. **Rate Limit:** More than 5 requests were sent in 1 minute.\n"
        "3. **Key Error:** The API key is invalid or pending activation."
    )
    # Prints the actual technical detail from Alpha Vantage
    st.code(f"Detailed Error: {e}")
