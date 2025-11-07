import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from scipy.stats import zscore

st.set_page_config(page_title="Stock Options Scanner", layout="wide")
st.title("📊 Daily Stock Options Scanner")

tickers_input = st.text_input("Enter stock tickers separated by commas:", "AAPL, MSFT, NVDA, TSLA, AMZN")
run_scan = st.button("Run Scan")

# ----------------------------
# Safe helpers
# ----------------------------
def safe_indicator(series, indicator_class, window=14):
    """Calculate indicator safely; return Series of NaNs if fails"""
    try:
        series = pd.to_numeric(series, errors='coerce').dropna()
        if len(series) < window:
            return pd.Series([float('nan')]*len(series))
        if indicator_class == EMAIndicator:
            return EMAIndicator(series, window=window, fillna=True).ema_indicator()
        elif indicator_class == RSIIndicator:
            return RSIIndicator(series, window=window, fillna=True).rsi()
    except:
        return pd.Series([float('nan')]*len(series))

def safe_zscore(series):
    """Calculate z-score safely; return last value or 0 if fails"""
    try:
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:,0]
        series = pd.to_numeric(series, errors='coerce').dropna()
        if len(series) < 2:
            return 0
        return round(zscore(series)[-1],2)
    except:
        return 0

# ----------------------------
# Main Scan
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
                # Download data
                data = yf.download(ticker, period="1mo", interval="1h")
                if data.empty or len(data) < 2:
                    raise ValueError("Not enough data")

                # Flatten multi-index columns if present
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = [col[1] for col in data.columns]

                data = data.copy()
                data["Close"] = pd.to_numeric(data["Close"], errors='coerce')

                # Safe EMA/RSI
                data["EMA_20"] = safe_indicator(data["Close"], EMAIndicator, window=20)
                data["EMA_50"] = safe_indicator(data["Close"], EMAIndicator, window=50)
                data["RSI"] = safe_indicator(data["Close"], RSIIndicator, window=14)

                last_close = data["Close"].iloc[-1]
                ema20 = data["EMA_20"].iloc[-1] if not pd.isna(data["EMA_20"].iloc[-1]) else last_close
                ema50 = data["EMA_50"].iloc[-1] if not pd.isna(data["EMA_50"].iloc[-1]) else last_close
                rsi = data["RSI"].iloc[-1] if not pd.isna(data["RSI"].iloc[-1]) else 0

                # Trend
                if ema20 > ema50:
                    trend = "Bullish"
                elif ema20 < ema50:
                    trend = "Bearish"
                else:
                    trend = "Neutral"

                # Confidence
                distance = abs(ema20 - ema50) / last_close * 100 if last_close != 0 else 0
                confidence = min(100, round(distance*2,2))

                # Support & Resistance
                support = data["Low"].tail(10).min() if "Low" in data.columns else 0
                resistance = data["High"].tail(10).max() if "High" in data.columns else 0

                # Smart Money
                smart_money = safe_zscore(data["Volume"]) if "Volume" in data.columns else 0

                results.append({
                    "Ticker": ticker,
                    "Price": round(last_close,2),
                    "Trend": trend,
                    "Confidence (%)": confidence,
                    "Support": round(support,2),
                    "Resistance": round(resistance,2),
                    "Smart Money (Z)": smart_money,
                    "RSI": round(rsi,1),
                    "data": data
                })

                if data_for_plot is None:
                    data_for_plot = data

            except Exception as e:
                st.error(f"Error fetching or processing data for {ticker}: {e}")

        # Display results table
        if results:
            df = pd.DataFrame(results)
            st.dataframe(df.drop(columns="data"), use_container_width=True)

            # Plot chart for first valid ticker
            if data_for_plot is not None:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=data_for_plot.index,
                    open=data_for_plot["Open"],
                    high=data_for_plot["High"],
                    low=data_for_plot["Low"],
                    close=data_for_plot["Close"],
                    name="Price"
                ))
                if "EMA_20" in data_for_plot.columns:
                    fig.add_trace(go.Scatter(x=data_for_plot.index, y=data_for_plot["EMA_20"], line=dict(color="orange", width=1), name="EMA 20"))
                if "EMA_50" in data_for_plot.columns:
                    fig.add_trace(go.Scatter(x=data_for_plot.index, y=data_for_plot["EMA_50"], line=dict(color="blue", width=1), name="EMA 50"))
                st.plotly_chart(fig, use_container_width=True)
