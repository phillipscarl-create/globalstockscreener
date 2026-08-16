import io
import time
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# Page setup
st.set_page_config(page_title="Global Equity Investment Model", layout="wide")
st.title("📈 Global Equity Investment & Superinvestor Dashboard")


# --- DATA FETCHING FUNCTIONS ---
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    """Scrapes S&P 500 tickers with a custom User-Agent to bypass HTTP 403 errors."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    payload = pd.read_html(io.StringIO(response.text))
    df = payload[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()


@st.cache_data(ttl=86400)
@st.cache_data(ttl=86400)
@st.cache_data(ttl=86400)
def get_ftse100_tickers():
    """Fetches FTSE 100 tickers safely with a fallback hardcoded list if Wikipedia fails."""
    url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        payload = pd.read_html(io.StringIO(response.text))

        # Search through all parsed tables to find the table with tickers
        ftse_table = None
        for table in payload:
            # Look for common FTSE column names across Wikipedia revisions
            cols = [str(c).lower() for c in table.columns]
            if any(
                k in cols
                for k in ["epic", "ticker", "ticker symbol", "symbol", "company"]
            ):
                ftse_table = table
                break

        if ftse_table is not None:
            # Find the specific column containing the ticker symbols
            ticker_col = None
            for c in ftse_table.columns:
                if str(c).lower() in ["epic", "ticker", "ticker symbol", "symbol"]:
                    ticker_col = c
                    break

            if ticker_col is not None:
                raw_tickers = ftse_table[ticker_col].astype(str).tolist()
                clean_tickers = []
                for t in raw_tickers:
                    # Clean spacing and ensure correct format for Yahoo Finance
                    t_clean = t.strip().upper().replace(".", "-")
                    if t_clean and t_clean != "NAN":
                        if not t_clean.endswith(".L"):
                            t_clean = f"{t_clean}.L"
                        clean_tickers.append(t_clean)
                if len(clean_tickers) > 50:
                    return clean_tickers
    except Exception as e:
        print(f"Wikipedia fetch failed: {e}")

    # FALLBACK LIST: Top FTSE 100 blue-chips if Wikipedia scraping fails
    fallback_ftse = [
        "SHEL.L",
        "AZN.L",
        "HSBA.L",
        "ULVR.L",
        "BP.L",
        "GSK.L",
        "RIO.L",
        "REL.L",
        "DGE.L",
        "BATS.L",
        "LSEG.L",
        "PRU.L",
        "AAL.L",
        "BARC.L",
        "LLOY.L",
        "VOD.L",
        "NG.L",
        "TSCO.L",
        "CRH.L",
        "ABDN.L",
    ]
    return fallback_ftse
def analyze_stock(
    ticker_symbol, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe
):
    """Analyzes value and quality compounding metrics for a stock."""
    ticker = yf.Ticker(ticker_symbol)
    try:
        info = ticker.info
        cash_flow = ticker.cashflow

        # Extract Metrics
        pe_ratio = info.get("trailingPE", None)
        pb_ratio = info.get("priceToBook", None)
        debt_to_equity = info.get("debtToEquity", None)
        if debt_to_equity is not None:
            debt_to_equity = debt_to_equity / 100

        current_ratio = info.get("currentRatio", None)
        market_cap = info.get("marketCap", None)
        company_name = info.get("shortName", ticker_symbol)
        roe = info.get("returnOnEquity", None)

        # Calculate Free Cash Flow Yield
        fcf_yield = None
        if not cash_flow.empty:
            ocf = cash_flow.iloc[:, 0].get("Operating Cash Flow", 0)
            capex = cash_flow.iloc[:, 0].get("Capital Expenditures", 0)
            fcf = ocf + capex
            if market_cap and fcf:
                fcf_yield = (fcf / market_cap) * 100

        # Scoring Logic (Max score = 6)
        score = 0
        if pe_ratio and 0 < pe_ratio <= max_pe:
            score += 1
        if pb_ratio and 0 < pb_ratio <= max_pb:
            score += 1
        if debt_to_equity is not None and debt_to_equity <= max_de:
            score += 1
        if current_ratio and current_ratio >= min_cr:
            score += 1
        if fcf_yield and fcf_yield >= min_fcf:
            score += 1
        if roe and roe >= (min_roe / 100):
            score += 1

        return {
            "Ticker": ticker_symbol,
            "Name": company_name,
            "P/E Ratio": round(pe_ratio, 2) if pe_ratio else None,
            "P/B Ratio": round(pb_ratio, 2) if pb_ratio else None,
            "Debt/Equity": round(debt_to_equity, 2) if debt_to_equity else None,
            "Current Ratio": round(current_ratio, 2) if current_ratio else None,
            "FCF Yield (%)": round(fcf_yield, 2) if fcf_yield else None,
            "ROE (%)": round(roe * 100, 2) if roe else None,
            "Value Score": f"{score}/6",
            "Raw Score": score,
        }
    except Exception:
        return None


# --- APP NAVIGATION TABS ---
tab1, tab2 = st.tabs(["🔍 Value & Quality Screener", "🏛️ Superinvestor Tracker"])

# ================= TAB 1: SCREENER =================
with tab1:
    st.sidebar.header("1. Market Selection")
    market = st.sidebar.selectbox(
        "Choose Index", ["S&P 500 (US)", "FTSE 100 (UK)"]
    )
    scan_limit = st.sidebar.number_input(
        "Number of stocks to scan", min_value=5, max_value=500, value=20, step=5
    )

    st.sidebar.header("2. Model Thresholds")
    max_pe = st.sidebar.slider("Max P/E Ratio", 5.0, 40.0, 20.0)
    max_pb = st.sidebar.slider("Max P/B Ratio", 0.5, 5.0, 2.0)
    max_de = st.sidebar.slider("Max Debt-to-Equity", 0.1, 3.0, 1.0)
    min_cr = st.sidebar.slider("Min Current Ratio", 0.5, 3.0, 1.5)
    min_fcf = st.sidebar.slider("Min FCF Yield (%)", 0.0, 15.0, 5.0)
    min_roe = st.sidebar.slider(
        "Min ROE / Capital Efficiency (%)", 0.0, 30.0, 15.0
    )

    if st.button("🚀 Run Market Scanner"):
        if "S&P 500" in market:
            tickers = get_sp500_tickers()[:scan_limit]
        else:
            tickers = get_ftse100_tickers()[:scan_limit]

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, t in enumerate(tickers):
            status_text.text(f"Scanning {i+1} of {len(tickers)}: {t}...")
            res = analyze_stock(
                t, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe
            )
            if res:
                results.append(res)
            progress_bar.progress((i + 1) / len(tickers))
            time.sleep(0.2)

        status_text.text("Scan completed!")

        df = pd.DataFrame(results)
        if not df.empty:
            df_sorted = df.sort_values(by="Raw Score", ascending=False).drop(
                columns=["Raw Score"]
            )
            st.subheader("📊 Model Scan Results")
            st.dataframe(df_sorted, use_container_width=True)

            csv = df_sorted.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name="stock_screener_results.csv",
                mime="text/csv",
            )
        else:
            st.warning("No data retrieved.")

# ================= TAB 2: SUPERINVESTOR TRACKER =================
with tab2:
    st.header("Institutional & Superinvestor Activity")
    st.write(
        "Track key portfolio holdings and market headlines for high-profile investors."
    )

    investor_portfolios = {
        "Berkshire Hathaway (Warren Buffett)": [
            "AAPL",
            "AXP",
            "KO",
            "BAC",
            "GOOGL",
        ],
        "Pershing Square (Bill Ackman)": ["MSFT", "AMZN", "BN", "UBER", "QSR"],
        "Bridgewater Associates (Ray Dalio / Macro)": [
            "SPY",
            "IVV",
            "NVDA",
            "EMR",
            "WMT",
        ],
        "Fundsmith (Terry Smith - UK Quality Value)": [
            "MSFT",
            "IDXX",
            "VISA",
            "PM",
            "NVO",
        ],
    }

    selected_investor = st.selectbox(
        "Select Superinvestor", list(investor_portfolios.keys())
    )
    tickers_to_track = investor_portfolios[selected_investor]

    st.subheader(f"Key Holdings for {selected_investor}")

    portfolio_data = []
    for ticker in tickers_to_track:
        t = yf.Ticker(ticker)
        info = t.info
        portfolio_data.append(
            {
                "Ticker": ticker,
                "Company": info.get("shortName", "N/A"),
                "Price": info.get("currentPrice", info.get("regularMarketPrice")),
                "P/E Ratio": info.get("trailingPE"),
                "Market Cap ($B)": round(info.get("marketCap", 0) / 1e9, 2)
                if info.get("marketCap")
                else "N/A",
                "52W High": info.get("fiftyTwoWeekHigh"),
                "52W Low": info.get("fiftyTwoWeekLow"),
            }
        )

    df_investor = pd.DataFrame(portfolio_data)
    st.dataframe(df_investor, use_container_width=True)

    st.subheader(f"Recent Headlines for {selected_investor}'s Primary Holding")
    primary_ticker = tickers_to_track[0]
    ticker_obj = yf.Ticker(primary_ticker)
    news = ticker_obj.news

    if news:
        for article in news[:5]:
            # Handles different news format outputs from yfinance
            title = article.get("title", article.get("headline", "Article"))
            link = article.get("link", article.get("url", "#"))
            publisher = article.get(
                "publisher", article.get("source", "Yahoo Finance")
            )

            st.markdown(f"**[{title}]({link})**")
            st.caption(f"Source: {publisher}")
            st.divider()
    else:
        st.write("No recent news found.")
