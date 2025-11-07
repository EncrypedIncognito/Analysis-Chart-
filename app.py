import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from scipy.stats import zscore

# -------------------------------
# App Title
# -------------------------------
st.set_page_config(page_title="Stock Options Scanner", layout="wide")
st.title("📊 Daily Stock Options Scanner")

# -------------------------------
# User Input
# -------------------------------
tickers = st.text_input("Enter stock tickers separated by commas:", "AAPL, MSFT, NVDA, TSLA, AMZN")
tickers = [t.strip().upper() for t in tickers.split(",") if t.strip()]

st.write("This tool analyzes price trend, support/resistance, RSI, and smart money flow to score direction and confidence.")

# -------------------------------
# Fetch Stock Data
# -------------------------------
def get_stock_data(ticker):
    data = yf.download(ticker, period="1mo", interval="1h")
    if data.empty:
        return None
    data["EMA_20"] = EMAIndicator(data["Close"], window=20).ema_indicator()
    data["EMA_50"] = EMAIndicator(data["Close"], window=50).ema_indicator()
    data["RSI"] = RSIIndicator(data["Close"], window=14).rsi()
    return data

# -------------------------------
# Analyze Stock
# -------------------------------
def analyze_stock(data):
    if data is None or len(data) < 2:
        return "No Data", 0, 0, 0, 0
    
    last_close = data["Close"].iloc[-1]
    ema20 = data["EMA_20"].iloc[-1]
    ema50 = data["EMA_50"].iloc[-1]
    rsi = data["RSI"].iloc[-1]

    # Trend
    if ema20 > ema50:
        trend = "Bullish"
    elif ema20 < ema50:
        trend = "Bearish"
    else:
        trend = "Neutral"
    
    # Confidence
    distance = abs(ema20 - ema50) / last_close * 100
    confidence = min(100, round(distance * 2, 2))

    # Support & Resistance
    recent_lows = data["Low"].tail(10).min()
    recent_highs = data["High"].tail(10).max()

    # Smart money (Z-score of volume)
    data["Volume_Z"] = zscore(data["Volume"])
    smart_money = round(data["Volume_Z"].iloc[-1], 2)

    return trend, confidence, last_close, recent_lows, recent_highs, smart_money, rsi

# -------------------------------
# Display Results
# -------------------------------
results = []
for ticker in tickers:
    data = get_stock_data(ticker)
    trend, confidence, price, support, resistance, smart_money, rsi = analyze_stock(data)
    results.append({
        "Ticker": ticker,
        "Price": round(price, 2),
        "Trend": trend,
        "Confidence (%)": confidence,
        "Support": round(support, 2),
        "Resistance": round(resistance, 2),
        "Smart Money (Z)": smart_money,
        "RSI": round(rsi, 1)
    })

df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

# -------------------------------
# Plot Chart for first ticker
# -------------------------------
if len(tickers) > 0:
    first_ticker = tickers[0]
    data = get_stock_data(first_ticker)
    if data is not None:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data["Open"], high=data["High"],
            low=data["Low"], close=data["Close"],
            name="Price"
        ))
        fig.add_trace(go.Scatter(x=data.index, y=data["EMA_20"], line=dict(color="orange", width=1), name="EMA 20"))
        fig.add_trace(go.Scatter(x=data.index, y=data["EMA_50"], line=dict(color="blue", width=1), name="EMA 50"))
        st.plotly_chart(fig, use_container_width=True)
