import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from scipy.stats import zscore
import base64

# ----------------------------
# PAGE CONFIG & THEME
# ----------------------------
st.set_page_config(page_title="Incognitos Analysis Chart", layout="wide")

# ---- Load and set background image ----
def add_bg_from_local(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    bg_style = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
        opacity: 0.92;
    }}
    </style>
    """
    st.markdown(bg_style, unsafe_allow_html=True)

# Replace with your actual file name if different (same folder as app.py)
add_bg_from_local("profile_image.png")

# ---- Custom CSS styling ----
st.markdown("""
<style>
body {
    color: white;
    background-color: black;
}
h1, h2, h3 {
    color: white;
}
.stTextInput>div>div>input {
    background-color: #111111;
    color: white;
    border: 1px solid #333333;
}
.stButton>button {
    background-color: #222222;
    color: white;
    border: 1px solid #555555;
    transition: 0.3s;
}
.stButton>button:hover {
    background-color: #333333;
}
.dataframe {
    color: white !important;
    background-color: #111111 !important;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# HEADER
# ----------------------------
st.title("📊 Incognitos Analysis Chart")

tickers_input = st.text_input(
    "Enter stock tickers separated by commas:",
    "AAPL, MSFT, NVDA, TSLA, AMZN"
)
run_scan = st.button("Run Scan")

# ----------------------------
# SAFE HELPERS
# ----------------------------
def safe_indicator(series, indicator_class, window=14):
    try:
        series = pd.to_numeric(series, errors='coerce').dropna()
        if len(series) < window:
            return pd.Series([float('nan')]*len(series))
        if indicator_class == EMAIndicator:
            return EMAIndicator(series, window=window, fillna=True).ema_indicator()
        elif indicator_class == RSIIndicator:
            return RSIIndicator(series, window=window, fillna=True).rsi()
    except Exception:
        return pd.Series([float('nan')]*len(series))

def safe_zscore(series):
    try:
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        series = pd.to_numeric(series, errors='coerce').dropna()
        if len(series) < 2:
            return 0
        return round(zscore(series)[-1], 2)
    except Exception:
        return 0

# ----------------------------
# MAIN SCAN LOGIC
# ----------------------------
if run_scan:
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    if not tickers:
        st.warning("Please enter at least one ticker.")
    else:
        st.write("Fetching data and analyzing stocks...")
        results = []
        data_for_plot = None

        for ticker in tickers:
            try:
                ticker_obj = yf.Ticker(ticker)
                data = ticker_obj.history(period="1mo", interval="1d")

                if data.empty or len(data) < 2:
                    raise ValueError("Not enough data")

                # Flatten multi-index columns if any
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [col[1] for col in data.columns]

                if "Close" not in data.columns:
                    st.error(f"No Close data for {ticker}. Skipping.")
                    continue

                data["Close"] = pd.to_numeric(data["Close"], errors="coerce")

                data["EMA_20"] = safe_indicator(data["Close"], EMAIndicator, window=20)
                data["EMA_50"] = safe_indicator(data["Close"], EMAIndicator, window=50)
                data["RSI"] = safe_indicator(data["Close"], RSIIndicator, window=14)

                last_close = data["Close"].iloc[-1]
                ema20 = data["EMA_20"].iloc[-1]
                ema50 = data["EMA_50"].iloc[-1]
                rsi = data["RSI"].iloc[-1]

                if ema20 > ema50:
                    trend = "Bullish"
                elif ema20 < ema50:
                    trend = "Bearish"
                else:
                    trend = "Neutral"

                distance = abs(ema20 - ema50) / last_close * 100 if last_close != 0 else 0
                confidence = min(100, round(distance * 2, 2))

                support = data["Low"].tail(10).min() if "Low" in data.columns else 0
                resistance = data["High"].tail(10).max() if "High" in data.columns else 0
                smart_money = safe_zscore(data["Volume"]) if "Volume" in data.columns else 0

                results.append({
                    "Ticker": ticker,
                    "Price": round(last_close, 2),
                    "Trend": trend,
                    "Confidence (%)": confidence,
                    "Support": round(support, 2),
                    "Resistance": round(resistance, 2),
                    "Smart Money (Z)": smart_money,
                    "RSI": round(rsi, 1)
                })

                if data_for_plot is None:
                    data_for_plot = data

            except Exception as e:
                st.error(f"Error fetching or processing {ticker}: {e}")

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)

            if data_for_plot is not None:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=data_for_plot.index,
                    open=data_for_plot["Open"],
                    high=data_for_plot["High"],
                    low=data_for_plot["Low"],
                    close=data_for_plot["Close"],
                    name="Price",
                    increasing_line_color='white',
                    decreasing_line_color='gray'
                ))
                if "EMA_20" in data_for_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=data_for_plot.index,
                        y=data_for_plot["EMA_20"],
                        line=dict(color="orange", width=1.2),
                        name="EMA 20"
                    ))
                if "EMA_50" in data_for_plot.columns:
                    fig.add_trace(go.Scatter(
                        x=data_for_plot.index,
                        y=data_for_plot["EMA_50"],
                        line=dict(color="blue", width=1.2),
                        name="EMA 50"
                    ))

                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig, use_container_width=True)
