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
def get_ftse100_tickers():
    """Scrapes FTSE 100 tickers directly from Wikipedia's constituents table."""
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
        tables = pd.read_html(io.StringIO(response.text), match="EPIC")

        if tables:
            df = tables[0]
            raw_tickers = df["EPIC"].astype(str).tolist()

            clean_tickers = []
            for t in raw_tickers:
                t_clean = "".join(c for c in t if c.isalnum()).upper()
                if t_clean and not t_clean.isdigit():
                    clean_tickers.append(f"{t_clean}.L")

            if len(clean_tickers) >= 50:
                return clean_tickers
    except Exception as e:
        print(f"FTSE Scrape failed: {e}")

    # Fallback list of top UK constituents if scraping fails
    return [
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
        "NWG.L",
        "3IN.L",
    ]


def analyze_stock(
    ticker_symbol, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe
):
    """Analyzes value and quality metrics for a stock."""
    ticker = yf.Ticker(ticker_symbol)
    try:
        info = ticker.info
        if not info or "shortName" not in info:
            return None

        cash_flow = ticker.cashflow

        # Extract Metrics safely
        pe_ratio = info.get("trailingPE", None)
        pb_ratio = info.get("priceToBook", None)

        debt_to_equity = info.get("debtToEquity", None)
        if debt_to_equity is not None:
            debt_to_equity = debt_to_equity / 100

        current_ratio = info.get("currentRatio", None)
        market_cap = info.get("marketCap", None)
        company_name = info.get("shortName", ticker_symbol)
        roe = info.get("returnOnEquity", None)

        # Calculate Free Cash Flow Yield safely
        fcf_yield = None
        try:
            if cash_flow is not None and not cash_flow.empty:
                ocf = 0
                capex = 0
                if "Operating Cash Flow" in cash_flow.index:
                    ocf = cash_flow.loc["Operating Cash Flow"].iloc[0]
                elif "Total Cash From Operating Activities" in cash_flow.index:
                    ocf = cash_flow.loc[
                        "Total Cash From Operating Activities"
                    ].iloc[0]

                if "Capital Expenditures" in cash_flow.index:
                    capex = cash_flow.loc["Capital Expenditures"].iloc[0]

                fcf = ocf + capex
                if market_cap and fcf:
                    fcf_yield = (fcf / market_cap) * 100
        except Exception:
            fcf_yield = None

        # Scoring Logic (Max = 6)
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
            "P/E Ratio": round(pe_ratio, 2) if pe_ratio else "N/A",
            "P/B Ratio": round(pb_ratio, 2) if pb_ratio else "N/A",
            "Debt/Equity": round(debt_to_equity, 2)
            if debt_to_equity is not None
            else "N/A",
            "Current Ratio": round(current_ratio, 2) if current_ratio else "N/A",
            "FCF Yield (%)": round(fcf_yield, 2) if fcf_yield else "N/A",
            "ROE (%)": round(roe * 100, 2) if roe else "N/A",
            "Value Score": f"{score}/6",
            "Raw Score": score,
        }
    except Exception as e:
        print(f"Error analyzing {ticker_symbol}: {e}")
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
    min_cr = st.sidebar.slider("Min Current Ratio", 0.5, 3.0, 1.0)
    min_fcf = st.sidebar.slider("Min FCF Yield (%)", 0.0, 15.0, 3.0)
    min_roe = st.sidebar.slider(
        "Min ROE / Capital Efficiency (%)", 0.0, 30.0, 10.0
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
