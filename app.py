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
                data = yf.download(ticker, period="1mo", interval="1h")
                if data.empty or len(data) < 2:
                    raise ValueError("Not enough data")

                data = data.copy()
                data["Close"] = pd.to_numeric(data["Close"], errors="coerce")

                # Only calculate EMA/RSI if enough data
                if len(data["Close"].dropna()) >= 20:
                    data["EMA_20"] = EMAIndicator(data["Close"], window=20, fillna=True).ema_indicator()
                    data["EMA_50"] = EMAIndicator(data["Close"], window=50, fillna=True).ema_indicator()
                    data["RSI"] = RSIIndicator(data["Close"], window=14, fillna=True).rsi()
                else:
                    data["EMA_20"] = data["Close"]
                    data["EMA_50"] = data["Close"]
                    data["RSI"] = 0

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
                support = data["Low"].tail(10).min()
                resistance = data["High"].tail(10).max()

                # Smart Money (Z-score)
                try:
                    vol = pd.to_numeric(data["Volume"], errors="coerce").dropna()
                    if len(vol) > 1:
                        smart_money = round(zscore(vol)[-1], 2)
                    else:
                        smart_money = 0
                except:
                    smart_money = 0

                results.append({
                    "Ticker": ticker,
                    "Price": round(last_close,2),
                    "Trend": trend,
                    "Confidence (%)": confidence,
                    "Support": round(support,2),
                    "Resistance": round(resistance,2),
                    "Smart Money (Z)": smart_money,
                    "RSI": round(rsi,1),
                    "data": data  # store for chart
                })

                if data_for_plot is None:
                    data_for_plot = data

            except Exception as e:
                st.error(f"Error fetching or processing data for {ticker}: {e}")

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df.drop(columns="data"), use_container_width=True)

            # Chart first valid ticker
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
