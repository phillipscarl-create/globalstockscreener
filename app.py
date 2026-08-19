import io
import time
import pandas as pd
import requests
import streamlit as st
import feedparser
from curl_cffi import requests as impersonate_requests

# Page setup & Configuration
st.set_page_config(
    page_title="Global Equity Investment Dashboard",
    page_icon="📈",
    layout="wide",
)

# Custom CSS matching the provided UI image (Deep Slate, Cyan Glow, Curved Cards)
st.markdown(
    """
    <style>
    /* Global Container Setup */
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Bar & Titles */
    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    /* Modern Glassmorphic Cards */
    .user-guide-box, .ui-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    
    /* Active Card Highlight matching UI image */
    .reasoning-card {
        background-color: #111827;
        border: 1px solid #0284c7;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.15);
    }
    
    /* Badges */
    .badge-perfect {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #10b981;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    
    .badge-high {
        background-color: rgba(56, 189, 248, 0.2);
        color: #38bdf8;
        border: 1px solid #0284c7;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }

    /* Primary Accent Buttons */
    .stButton>button {
        background-color: #38bdf8;
        color: #0f172a;
        font-weight: 700;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1.5rem;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #7dd3fc;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
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

st.title("📈 Global Equity Investment Model & Institutional Dashboard")


# --- SECURE DATA FETCHING FUNCTIONS ---

@st.cache_data(ttl=3600)
def fetch_yahoo_quote(symbol):
    """Fetches key ticker metrics using browser impersonation."""
    formatted_symbol = symbol.replace(".", "-")
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{formatted_symbol}?modules=defaultKeyStatistics,financialData,summaryDetail,price"
    
    try:
        r = impersonate_requests.get(url, impersonate="chrome120", timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("quoteSummary", {}).get("result")
        return result[0] if result else None
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    df = pd.read_html(io.StringIO(res.text))[0]
    return df["Symbol"].str.replace(".", "-", regex=False).tolist()


@st.cache_data(ttl=86400)
def get_nasdaq100_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(res.text))
    for t in tables:
        if "Ticker" in t.columns:
            return t["Ticker"].str.replace(".", "-", regex=False).tolist()
        if "Symbol" in t.columns:
            return t["Symbol"].str.replace(".", "-", regex=False).tolist()
    return ["AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD"]


@st.cache_data(ttl=86400)
def get_dow_tickers():
    url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(res.text))
    for t in tables:
        if "Symbol" in t.columns:
            return t["Symbol"].str.replace(".", "-", regex=False).tolist()
    return ["AAPL", "AMZN", "AXP", "BA", "CAT", "CSCO", "CVX", "DIS", "HD", "JNJ", "JPM", "MSFT", "V", "WMT"]


@st.cache_data(ttl=86400)
def get_ftse100_tickers():
    url = "https://en.wikipedia.org/wiki/FTSE_100_Index"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        tables = pd.read_html(io.StringIO(res.text), match="EPIC")
        if tables:
            df = tables[0]
            raw = df["EPIC"].astype(str).tolist()
            return [f"{''.join(c for c in t if c.isalnum()).upper()}.L" for t in raw if t and not t.isdigit()]
    except Exception:
        pass
    return ["SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L", "RIO.L", "REL.L", "DGE.L", "BATS.L"]


@st.cache_data(ttl=1800)
def fetch_ticker_rss_news(symbol):
    """Fetches reliable ticker news via Yahoo RSS Feed."""
    clean_symbol = symbol.replace(".L", "").replace("-", ".")
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean_symbol}&region=US&lang=en-US"
    
    feed = feedparser.parse(rss_url)
    articles = []
    
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", "News Article"),
            "link": entry.get("link", "#"),
            "published": entry.get("published", "Recent")
        })
    return articles


def analyze_stock(ticker_symbol, max_pe, max_pb, max_de, min_cr, min_fcf, min_roe):
    q_summary = fetch_yahoo_quote(ticker_symbol)
    if not q_summary:
        return None

    try:
        fin_data = q_summary.get("financialData", {})
        key_stats = q_summary.get("defaultKeyStatistics", {})
        sum_detail = q_summary.get("summaryDetail", {})
        price_info = q_summary.get("price", {})

        company_name = price_info.get("shortName", ticker_symbol)
        pe_ratio = sum_detail.get("trailingPE", {}).get("raw")
        pb_ratio = key_stats.get("priceToBook", {}).get("raw")
        
        de_raw = fin_data.get("debtToEquity", {}).get("raw")
        debt_to_equity = (de_raw / 100) if de_raw is not None else None
        
        current_ratio = fin_data.get("currentRatio", {}).get("raw")
        market_cap = price_info.get("marketCap", {}).get("raw")
        roe = fin_data.get("returnOnEquity", {}).get("raw")

        fcf_yield = None
        fcf_raw = fin_data.get("freeCashflow", {}).get("raw")
        if fcf_raw and market_cap:
            fcf_yield = (fcf_raw / market_cap) * 100

        score = 0
        reasons = []

        if pe_ratio and 0 < pe_ratio <= max_pe:
            score += 1
            reasons.append(f"P/E Ratio of {pe_ratio:.2f} (≤ {max_pe:.1f})")
        if pb_ratio and 0 < pb_ratio <= max_pb:
            score += 1
            reasons.append(f"P/B Ratio of {pb_ratio:.2f} (≤ {max_pb:.1f})")
        if debt_to_equity is not None and debt_to_equity <= max_de:
            score += 1
            reasons.append(f"Debt/Equity of {debt_to_equity:.2f} (≤ {max_de:.1f})")
        if current_ratio and current_ratio >= min_cr:
            score += 1
            reasons.append(f"Current Ratio of {current_ratio:.2f} (≥ {min_cr:.1f})")
        if fcf_yield and fcf_yield >= min_fcf:
            score += 1
            reasons.append(f"FCF Yield of {fcf_yield:.2f}% (≥ {min_fcf:.1f}%)")
        if roe and roe >= (min_roe / 100):
            score += 1
            reasons.append(f"ROE of {roe*100:.2f}% (≥ {min_roe:.1f}%)")

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


# --- APP TABS ---
tab1, tab2 = st.tabs(["🔍 Market Screener", "🏛️ Superinvestor Tracker"])

# ================= TAB 1: SCREENER =================
with tab1:
    st.markdown(
        """
        <div class="user-guide-box">
            <h3>📖 Quantitative Screener Framework</h3>
            <p>Scans index constituents across valuation, capital efficiency, leverage, and liquidity factors to score companies from <b>0 to 6</b>.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("1. Market Selection")
    market = st.sidebar.selectbox("Choose Index", ["S&P 500 (US)", "Nasdaq-100 (US Growth)", "Dow Jones (US Blue Chip)", "FTSE 100 (UK)"])
    scan_limit = st.sidebar.number_input("Number of stocks to scan", min_value=5, max_value=500, value=20, step=5)

    st.sidebar.header("2. Model Thresholds")
    max_pe = st.sidebar.slider("Max P/E Ratio", 5.0, 50.0, 22.0)
    max_pb = st.sidebar.slider("Max P/B Ratio", 0.5, 10.0, 3.0)
    max_de = st.sidebar.slider("Max Debt-to-Equity", 0.1, 3.0, 1.2)
    min_cr = st.sidebar.slider("Min Current Ratio", 0.5, 3.0, 1.0)
    min_fcf = st.sidebar.slider("Min FCF Yield (%)", 0.0, 15.0, 3.0)
    min_roe = st.sidebar.slider("Min ROE (%)", 0.0, 30.0, 12.0)

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
            time.sleep(0.02)

        status_text.text("Scan complete.")

        df = pd.DataFrame(results)
        if not df.empty:
            df_sorted = df.sort_values(by="Raw Score", ascending=False)

            st.subheader("📊 Scan Results")
            display_df = df_sorted.drop(columns=["Raw Score", "Reasons"])
            st.dataframe(display_df, use_container_width=True)

            top_performers = [r for r in results if r["Raw Score"] >= 5]

            st.subheader("🏆 High Conviction Candidates")
            if top_performers:
                for stock in sorted(top_performers, key=lambda x: x["Raw Score"], reverse=True):
                    badge_class = "badge-perfect" if stock["Raw Score"] == 6 else "badge-high"
                    badge_label = "PERFECT SCORE (6/6)" if stock["Raw Score"] == 6 else "HIGH CONVICTION (5/6)"

                    st.markdown(
                        f"""
                        <div class="reasoning-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h4><b>{stock['Name']} ({stock['Ticker']})</b></h4>
                                <span class="{badge_class}">{badge_label}</span>
                            </div>
                            <ul style="margin-top: 10px;">
                                {"".join([f"<li>{r}</li>" for r in stock['Reasons']])}
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No stocks met 5/6 or 6/6 criteria under these limits.")

            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results (CSV)", data=csv, file_name="screener_results.csv", mime="text/csv")

# ================= TAB 2: SUPERINVESTOR TRACKER =================
with tab2:
    st.header("Institutional & Superinvestor Tracking")

    investor_portfolios = {
        "Berkshire Hathaway (Warren Buffett)": ["AAPL", "AXP", "KO", "BAC", "OXY"],
        "Pershing Square (Bill Ackman)": ["MSFT", "AMZN", "BN", "UBER", "QSR"],
        "Himalaya Capital (Li Lu)": ["AAPL", "BAC", "BRK-B", "PDD"],
        "Pabrai Investment Funds (Mohnish Pabrai)": ["AMR", "ARCH", "CONX"],
        "Akre Capital Management (Chuck Akre)": ["MA", "V", "AMT", "ODFL"],
        "Bridgewater Associates (Ray Dalio)": ["SPY", "IVV", "NVDA", "WMT"],
        "Fundsmith (Terry Smith)": ["MSFT", "IDXX", "VISA", "PM", "NVO"],
    }

    selected_investor = st.selectbox("Select Investor Portfolio", list(investor_portfolios.keys()))
    tickers_to_track = investor_portfolios[selected_investor]

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader(f"Portfolio Summary")
        portfolio_data = []
        for ticker in tickers_to_track:
            q = fetch_yahoo_quote(ticker)
            if q:
                sum_d = q.get("summaryDetail", {})
                price = q.get("price", {})

                portfolio_data.append({
                    "Ticker": ticker,
                    "Company": price.get("shortName", ticker),
                    "Price": f"${price.get('regularMarketPrice', {}).get('raw', 0):,.2f}",
                    "P/E Ratio": round(sum_d.get("trailingPE", {}).get("raw", 0), 2) if sum_d.get("trailingPE") else "N/A",
                    "Market Cap ($B)": round(price.get("marketCap", {}).get("raw", 0) / 1e9, 2) if price.get("marketCap") else "N/A",
                })

        if portfolio_data:
            st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)

    with col2:
        st.subheader(f"Live RSS News Feed")
        primary_ticker = tickers_to_track[0]
        st.caption(f"Showing headline updates for primary holding: **{primary_ticker}**")
        
        articles = fetch_ticker_rss_news(primary_ticker)
        if articles:
            for item in articles:
                st.markdown(
                    f"""
                    <div class="ui-card" style="padding: 12px; margin-bottom: 10px;">
                        <a href="{item['link']}" target="_blank" style="color: #38bdf8; text-decoration: none; font-weight: 600;">{item['title']}</a>
                        <div style="color: #64748b; font-size: 0.75rem; margin-top: 4px;">{item['published']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("No current news available.")
