import time
import pandas as pd
import streamlit as st
import yfinance as yf
import feedparser

# Page setup & Configuration
st.set_page_config(
    page_title="Global Equity Investment Dashboard",
    page_icon="📈",
    layout="wide",
)

# Custom CSS matching Courier Font & Dark Blue Glassmorphism Theme
st.markdown(
    """
    <style>
    /* Global Font Override to Courier */
    html, body, [class*="css"], .stApp, h1, h2, h3, h4, h5, h6, p, div, span, label, button, input, table {
        font-family: 'Courier New', Courier, monospace !important;
    }

    /* Container Styling */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Modern Dark Glass Cards */
    .guide-card, .ui-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
    }
    
    .reasoning-card {
        background-color: #111827;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.2);
    }
    
    /* Neon Accents */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700;
    }
    
    h4 {
        color: #38bdf8 !important;
    }

    /* Badges */
    .badge-perfect {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #10b981;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    .badge-high {
        background-color: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        border: 1px solid #0284c7;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }

    /* Primary Accent Buttons */
    .stButton>button {
        background-color: #38bdf8;
        color: #0f172a;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        padding: 0.6rem 1.5rem;
    }
    .stButton>button:hover {
        background-color: #7dd3fc;
        color: #0f172a;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 Global Equity Investment Dashboard")


# --- INDEX TICKER LISTS ---
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "BRK-B", "LLY", "AVGO", "JPM", "TSLA", "WMT", "UNH", "V", "XOM", "MA", "PG", "COST", "JNJ", "HD"]

@st.cache_data(ttl=86400)
def get_nasdaq100_tickers():
    return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD", "NFLX", "TMUS", "PEP", "ADBE", "CSCO", "INTC", "TXN", "CMCSA", "QCOM", "AMGN"]

@st.cache_data(ttl=86400)
def get_dow_tickers():
    return ["AAPL", "AMZN", "AXP", "BA", "CAT", "CSCO", "CVX", "DIS", "HD", "JNJ", "JPM", "MSFT", "V", "WMT", "IBM", "GS", "MCD", "MMM", "HON", "TRV"]

@st.cache_data(ttl=86400)
def get_ftse100_tickers():
    return ["SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L", "RIO.L", "REL.L", "DGE.L", "BATS.L", "LLOY.L", "BARC.L", "PRU.L", "NG.L", "VOD.L"]


# --- ROBUST DATA FETCHING USING YFINANCE ---
@st.cache_data(ttl=3600)
def fetch_stock_metrics(ticker_symbol):
    """Fetches key ticker metrics reliably via yfinance."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if not info or 'shortName' not in info and 'longName' not in info:
            return None
        return info
    except Exception:
        return None


@st.cache_data(ttl=1800)
def fetch_ticker_rss_news(symbol):
    """Fetches reliable ticker news via Google News RSS."""
    clean_symbol = symbol.replace(".L", "").replace("-", ".")
    rss_url = f"https://news.google.com/rss/search?q={clean_symbol}+stock&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(rss_url)
    articles = []
    
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", "News Article"),
            "link": entry.get("link", "#"),
            "published": entry.get("published", "Recent")[:16]
        })
    return articles


def analyze_stock(ticker_symbol, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe):
    info = fetch_stock_metrics(ticker_symbol)
    if not info:
        return None

    try:
        company_name = info.get("shortName") or info.get("longName") or ticker_symbol
        pe_ratio = info.get("trailingPE")
        pb_ratio = info.get("priceToBook")
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity is not None:
            debt_to_equity = debt_to_equity / 100.0
            
        current_ratio = info.get("currentRatio")
        market_cap = info.get("marketCap")
        roe = info.get("returnOnEquity")
        fcf = info.get("freeCashflow")

        fcf_yield = None
        if fcf and market_cap:
            fcf_yield = (fcf / market_cap) * 100.0

        score = 0
        reasons = []

        if pe_ratio and 0 < pe_ratio <= max_pe:
            score += 1
            reasons.append(f"P/E Ratio of {pe_ratio:.2f} (<= {max_pe:.1f})")
        if pb_ratio and 0 < pb_ratio <= max_pb:
            score += 1
            reasons.append(f"P/B Ratio of {pb_ratio:.2f} (<= {max_pb:.1f})")
        if debt_to_equity is not None and debt_to_equity <= max_de:
            score += 1
            reasons.append(f"Debt/Equity of {debt_to_equity:.2f} (<= {max_de:.1f})")
        if current_ratio and current_ratio >= min_cr:
            score += 1
            reasons.append(f"Current Ratio of {current_ratio:.2f} (>= {min_cr:.1f})")
        if fcf_yield and fcf_yield >= min_fcf:
            score += 1
            reasons.append(f"FCF Yield of {fcf_yield:.2f}% (>= {min_fcf:.1f}%)")
        if roe and roe >= (min_roe / 100.0):
            score += 1
            reasons.append(f"ROE of {roe*100:.2f}% (>= {min_roe:.1f}%)")

        return {
            "Ticker": ticker_symbol,
            "Name": company_name,
            "P/E Ratio": round(pe_ratio, 2) if pe_ratio else "N/A",
            "P/B Ratio": round(pb_ratio, 2) if pb_ratio else "N/A",
            "Debt/Equity": round(debt_to_equity, 2) if debt_to_equity is not None else "N/A",
            "Current Ratio": round(current_ratio, 2) if current_ratio else "N/A",
            "FCF Yield (%)": round(fcf_yield, 2) if fcf_yield else "N/A",
            "ROE (%)": round(roe * 100, 2) if roe else "N/A",
            "Value Score": f"{score}/6",
            "Raw Score": score,
            "Reasons": reasons,
        }
    except Exception:
        return None


# --- APP DASHBOARD ---
tab1, tab2 = st.tabs(["🔍 Value & Quality Screener", "🏛️ Superinvestor Tracker"])

# ================= TAB 1: SCREENER =================
with tab1:
    st.markdown(
        """
        <div class="guide-card">
            <h3>📖 User Guide & Factor Definitions</h3>
            <p style="color: #94a3b8;">
                This quantitative model scans stock constituents against financial metrics, scoring companies from 0 to 6 based on your parameters.
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; margin-top: 10px;">
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>P/E Ratio:</b> Share price vs net earnings.</div>
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>P/B Ratio:</b> Share price vs book asset value.</div>
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>Debt/Equity:</b> Total debt divided by equity capital.</div>
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>Current Ratio:</b> Short-term liquid assets vs liabilities.</div>
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>FCF Yield:</b> Free cash flow produced relative to market cap.</div>
                <div style="background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px;"><b>ROE (%):</b> Annual return generated on shareholder equity.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("1. Select Market Index")
    market = st.sidebar.selectbox("Market Index", ["S&P 500 (US)", "Nasdaq-100 (US Growth)", "Dow Jones (US)", "FTSE 100 (UK)"])
    scan_limit = st.sidebar.number_input("Number of stocks to scan", min_value=5, max_value=100, value=15, step=5)

    st.sidebar.header("2. Model Thresholds")
    max_pe = st.sidebar.slider("Max P/E Ratio", 5.0, 50.0, 25.0)
    max_pb = st.sidebar.slider("Max P/B Ratio", 0.5, 10.0, 4.0)
    max_de = st.sidebar.slider("Max Debt-to-Equity", 0.1, 3.0, 1.5)
    min_cr = st.sidebar.slider("Min Current Ratio", 0.5, 3.0, 1.0)
    min_fcf = st.sidebar.slider("Min FCF Yield (%)", 0.0, 15.0, 2.0)
    min_roe = st.sidebar.slider("Min ROE (%)", 0.0, 30.0, 10.0)

    if st.button("🚀 Run Market Scanner"):
        if "S&P 500" in market:
            tickers = get_sp500_tickers()[:scan_limit]
        elif "Nasdaq-100" in market:
            tickers = get_nasdaq100_tickers()[:scan_limit]
        elif "Dow" in market:
            tickers = get_dow_tickers()[:scan_limit]
        else:
            tickers = get_ftse100_tickers()[:scan_limit]

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, t in enumerate(tickers):
            status_text.text(f"Scanning {i+1} of {len(tickers)}: {t}...")
            res = analyze_stock(t, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe)
            if res:
                results.append(res)
            progress_bar.progress((i + 1) / len(tickers))
            time.sleep(0.01)

        status_text.text("Scan complete.")

        df = pd.DataFrame(results)
        if not df.empty:
            df_sorted = df.sort_values(by="Raw Score", ascending=False)

            st.subheader("📊 Scan Results")
            display_df = df_sorted.drop(columns=["Raw Score", "Reasons"])
            st.dataframe(display_df, use_container_width=True)

            top_performers = [r for r in results if r["Raw Score"] >= 4]

            st.subheader("🏆 Conviction Candidates")
            if top_performers:
                for stock in sorted(top_performers, key=lambda x: x["Raw Score"], reverse=True):
                    badge_class = "badge-perfect" if stock["Raw Score"] == 6 else "badge-high"
                    badge_label = f"SCORE ({stock['Value Score']})"

                    st.markdown(
                        f"""
                        <div class="reasoning-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4><b>{stock['Name']} ({stock['Ticker']})</b></h4>
                                <span class="{badge_class}">{badge_label}</span>
                            </div>
                            <ul style="margin-top: 10px; color: #cbd5e1;">
                                {"".join([f"<li>{r}</li>" for r in stock['Reasons']])}
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No stocks met top score criteria under these limits.")

            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results (CSV)", data=csv, file_name="screener_results.csv", mime="text/csv")

# ================= TAB 2: SUPERINVESTOR TRACKER =================
with tab2:
    st.header("Institutional & Superinvestor Tracking")

    investor_portfolios = {
        "Berkshire Hathaway (Warren Buffett)": ["AAPL", "AXP", "KO", "BAC", "OXY"],
        "Pershing Square (Bill Ackman)": ["MSFT", "AMZN", "BN", "UBER", "QSR"],
        "Himalaya Capital (Li Lu)": ["AAPL", "BAC", "BRK-B", "PDD"],
        "Pabrai Funds (Mohnish Pabrai)": ["AMR", "ARCH", "CONX"],
        "Akre Capital (Chuck Akre)": ["MA", "V", "AMT", "ODFL"],
        "Bridgewater Associates (Ray Dalio)": ["SPY", "IVV", "NVDA", "WMT"],
        "Fundsmith (Terry Smith)": ["MSFT", "IDXX", "VISA", "PM", "NVO"],
    }

    selected_investor = st.selectbox("Select Investor Portfolio", list(investor_portfolios.keys()))
    tickers_to_track = investor_portfolios[selected_investor]

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Portfolio Holdings Summary")
        portfolio_data = []
        
        for ticker in tickers_to_track:
            info = fetch_stock_metrics(ticker)
            if info:
                px = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
                pe = info.get("trailingPE")
                mc = info.get("marketCap")
                name = info.get("shortName") or info.get("longName") or ticker

                portfolio_data.append({
                    "Ticker": ticker,
                    "Company": name,
                    "Price": f"${px:,.2f}" if px else "N/A",
                    "P/E Ratio": round(pe, 2) if pe else "N/A",
                    "Market Cap ($B)": f"${round(mc / 1e9, 2)}B" if mc else "N/A",
                })
            else:
                portfolio_data.append({
                    "Ticker": ticker,
                    "Company": ticker,
                    "Price": "N/A",
                    "P/E Ratio": "N/A",
                    "Market Cap ($B)": "N/A"
                })

        if portfolio_data:
            st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)

    with col2:
        st.subheader("Live Holdings News")
        primary_ticker = tickers_to_track[0]
        st.caption(f"Showing updates for: **{primary_ticker}**")
        
        articles = fetch_ticker_rss_news(primary_ticker)
        if articles:
            for item in articles:
                st.markdown(
                    f"""
                    <div style="background: #111827; border: 1px solid #1f2937; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <a href="{item['link']}" target="_blank" style="color: #38bdf8; text-decoration: none; font-weight: bold; font-size: 0.9rem;">{item['title']}</a>
                        <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">Published: {item['published']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No current news available.")
