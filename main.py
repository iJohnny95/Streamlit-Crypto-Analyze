import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from pycoingecko import CoinGeckoAPI
from ta.volatility import BollingerBands
from ta.trend import MACD, SMAIndicator, EMAIndicator, IchimokuIndicator
from ta.volume import VolumeWeightedAveragePrice
import requests
from requests.exceptions import RequestException

# Function to clear cache in newer versions
def clear_cache():
    if "cache" in dir(st):
        st.cache.clear()
    else:
        st.caching.clear_cache()  # For older versions that use st.caching

# Clear Streamlit cache to avoid issues with old data
clear_cache()

# Constants for timeframes
SHORT_TERM = "Short-Term"
MEDIUM_TERM = "Medium-Term"
LONG_TERM = "Long-Term"

# Initialize CoinGeckoAPI
cg = CoinGeckoAPI()

# Define CoinGecko IDs
coingecko_ids = {
    "Bitcoin (BTC)": "bitcoin",
    "Ethereum (ETH)": "ethereum",
    "Solana (SOL)": "solana",
    "Binance Coin (BNB)": "binancecoin",
    "Cardano (ADA)": "cardano",
    "Avalanche (AVAX)": "avalanche-2",
    "Dogecoin (DOGE)": "dogecoin",
    "Shiba Inu (SHIBA)": "shiba-inu",
    "Fetch.ai (FET)": "fetch-ai",
    "Ocean Protocol (OCEAN)": "ocean-protocol",
    "SingularityNET (AGIX)": "singularitynet",
}


@st.cache_data
def get_market_caps():
    try:
        # Fetch market data for all coins
        ids = ",".join(coingecko_ids.values())
        market_data = cg.get_coins_markets(vs_currency="usd", ids=ids)

        # Create a dictionary for fast access
        market_caps = {item["id"]: item["market_cap"] for item in market_data}
        return market_caps
    except RequestException as e:
        st.warning(f"Could not fetch market caps. Error: {e}")
        return {}


def get_market_cap(coin_id):
    market_caps = get_market_caps()
    return market_caps.get(coin_id, None)


# Function to load data
def load_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.index.name in ["Date", "Datetime"]:
            data = data.reset_index()
        return data
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return None


# Function to calculate percentage price change
def calculate_price_change(data):
    if data is not None and len(data) > 1:
        non_zero_price_idx = data["Adj Close"].ne(0).idxmax()
        initial_price = data["Adj Close"].loc[non_zero_price_idx]
        if initial_price != 0:
            return ((data["Adj Close"].iloc[-1] - initial_price) / initial_price) * 100
    return None


def create_dashboard(crypto_mapping, period, interval, coingecko_ids):
    st.subheader("Cryptocurrency Price Change Dashboard")

    # Get filter selection from the sidebar
    sort_by = st.sidebar.selectbox("Sort by", ["Price Change", "Market Cap"])

    changes = []

    for coin, ticker in crypto_mapping.items():
        data = load_data(ticker, period, interval)
        price_change = calculate_price_change(data)

        # Fetch market cap from CoinGecko using scraping
        coin_id = coingecko_ids.get(coin)
        market_cap = get_market_cap(coin_id)

        if price_change is not None:
            changes.append(
                {
                    "coin": coin,
                    "ticker": ticker,
                    "change": price_change,
                    "current_price": (
                        data["Adj Close"].iloc[-1] if len(data) > 0 else None
                    ),
                    "market_cap": market_cap,
                }
            )

    # Sort by user-selected criteria
    if sort_by == "Price Change":
        changes = sorted(changes, key=lambda x: x["change"], reverse=True)
    elif sort_by == "Market Cap":
        changes = sorted(changes, key=lambda x: x["market_cap"] or 0, reverse=True)

    # Display in cards
    card_per_row = 3
    card_style = """
        <style>
            .card {
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
                text-align: center;
                height: 270px;
                transition: background-color 0.3s ease, box-shadow 0.3s ease;
            }
            .card.green {
                background-color: #28a745;
                color: white;
            }
            .card.red {
                background-color: #dc3545;
                color: white;
            }
            .card:hover {
                background-color: #ff851b;
                box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.2);
            }
            .card h3 {
                margin: 10px 0;
            }
            .card p {
                margin: 5px 0;
            }
        </style>
    """

    st.markdown(card_style, unsafe_allow_html=True)

    # Display cards in rows of 3 cards per row
    for index, item in enumerate(changes):
        color_class = "green" if item["change"] > 0 else "red"

        # Handle price display logic
        price_display = (
            f"${item['current_price']:.2f}"
            if item["current_price"] is not None
            else "Price Unavailable"
        )

        # Format the market cap for display
        if item["market_cap"] is not None:
            if item["market_cap"] >= 1_000_000_000_000:
                market_cap_display = f"${item['market_cap'] / 1_000_000_000_000:.2f}T"
            elif item["market_cap"] >= 1_000_000_000:
                market_cap_display = f"${item['market_cap'] / 1_000_000_000:.2f}B"
            elif item["market_cap"] >= 1_000_000:
                market_cap_display = f"${item['market_cap'] / 1_000_000:.2f}M"
            else:
                market_cap_display = f"${item['market_cap']:.2f}"
        else:
            market_cap_display = "Market Cap Unavailable"

        # Create responsive grid layout
        if index % card_per_row == 0:
            cols = st.columns(card_per_row)

        with cols[index % card_per_row]:
            st.markdown(
                f"""
                <div class="card {color_class}">
                    <h3>{item['coin']}</h3>
                    <p style="font-size: 20px; font-weight: bold;">{item['ticker']}</p>
                    <p><b>Price:</b> {price_display}</p>
                    <p><b>Change:</b> <span>{item['change']:.2f}%</span></p>
                    <p><b>Market Cap:</b> <span>{market_cap_display}</span></p>
                </div>
                """,
                unsafe_allow_html=True,
            )


# Function to calculate indicators based on the timeframe
def calculate_indicators(data, timeframe):
    indicators = {}

    if timeframe == SHORT_TERM:
        indicators["RSI"] = RSIIndicator(data["Adj Close"]).rsi()
        bb = BollingerBands(data["Adj Close"])
        indicators["BB_High"] = bb.bollinger_hband()
        indicators["BB_Low"] = bb.bollinger_lband()
        macd = MACD(data["Adj Close"])
        indicators["MACD"] = macd.macd()
        indicators["MACD_Signal"] = macd.macd_signal()
        indicators["EMA_9"] = EMAIndicator(data["Adj Close"], window=9).ema_indicator()

    elif timeframe == MEDIUM_TERM:
        indicators["SMA_50"] = SMAIndicator(
            data["Adj Close"], window=50
        ).sma_indicator()
        indicators["SMA_200"] = SMAIndicator(
            data["Adj Close"], window=200
        ).sma_indicator()

        ichimoku = IchimokuIndicator(
            high=data["High"],
            low=data["Low"],
            window1=9,
            window2=26,
            window3=52,
            fillna=True,
        )
        indicators["Ichimoku_A"] = ichimoku.ichimoku_a()
        indicators["Ichimoku_B"] = ichimoku.ichimoku_b()

    elif timeframe == LONG_TERM:
        if len(data) >= 200:
            indicators["SMA_200"] = SMAIndicator(
                data["Adj Close"], window=200
            ).sma_indicator()
        else:
            st.warning("Not enough data for SMA 200 calculation.")
            indicators["SMA_200"] = pd.Series([None] * len(data), index=data.index)

        vwap_calc = VolumeWeightedAveragePrice(
            high=data["High"],
            low=data["Low"],
            close=data["Adj Close"],
            volume=data["Volume"],
        )
        indicators["VWAP"] = vwap_calc.vwap

    return indicators


# Function to analyze the trend (bullish or bearish)
def analyze_trend(data, indicators, timeframe):
    trend = "Neutral"
    trend_color = "black"
    reason = ""

    if timeframe == SHORT_TERM:
        key_indicator = "EMA_9"
    elif timeframe == MEDIUM_TERM:
        key_indicator = "SMA_50"
    else:
        key_indicator = "SMA_200"

    if (
        len(data) > 0
        and key_indicator in indicators
        and len(indicators[key_indicator]) > 0
    ):
        if data["Adj Close"].iloc[-1] > indicators[key_indicator].iloc[-1]:
            trend = "Bullish"
            trend_color = "green"
            reason = f"The current price is above the {key_indicator.replace('_', '-')}"
        else:
            trend = "Bearish"
            trend_color = "red"
            reason = f"The current price is below the {key_indicator.replace('_', '-')}"
    else:
        reason = "Insufficient data to determine the trend."

    return trend, trend_color, reason


# Function to provide insights based on technical analysis
def provide_insights(data, indicators, timeframe, period):
    insights = []

    trend, trend_color, trend_reason = analyze_trend(data, indicators, timeframe)

    non_zero_price_idx = data["Adj Close"].ne(0).idxmax()
    initial_price = data["Adj Close"].loc[non_zero_price_idx]
    if initial_price != 0:
        price_change = (
            (data["Adj Close"].iloc[-1] - initial_price) / initial_price
        ) * 100
        price_change_color = "green" if price_change > 0 else "red"
    else:
        price_change = None
        price_change_color = "black"

    period_label = {
        "5d": "last 7 days",
        "1mo": "last month",
        "6mo": "last 6 months",
        "1y": "last year",
        "3y": "last 3 years",
        "5y": "last 5 years",
        "10y": "last 10 years",
    }.get(period, f"the selected time period ({period})")

    insights.append(f"**Trend: <span style='color:{trend_color}'>{trend}</span>**")

    if price_change is not None:
        insights.append(
            f"**Price change in the {period_label}: <span style='color:{price_change_color}'>{price_change:.2f}%</span>**"
        )
    else:
        insights.append(
            f"Price change in the {period_label}: Not enough data to calculate."
        )

    insights.append(trend_reason)

    return insights, trend, trend_color


# Function to create the chart
def create_chart(data, indicators, timeframe):
    datetime_column = "Datetime" if "Datetime" in data.columns else "Date"

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data[datetime_column],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Adj Close"],
            name="Candlesticks",
            increasing_line_color="green",
            decreasing_line_color="red",
        )
    )

    if timeframe == SHORT_TERM:
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["EMA_9"],
                mode="lines",
                name="EMA 9",
                line=dict(color="blue"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["BB_High"],
                mode="lines",
                name="BB High",
                line=dict(color="orange"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["BB_Low"],
                mode="lines",
                name="BB Low",
                line=dict(color="orange"),
            )
        )

    elif timeframe == MEDIUM_TERM:
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["SMA_50"],
                mode="lines",
                name="SMA 50",
                line=dict(color="green"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["SMA_200"],
                mode="lines",
                name="SMA 200",
                line=dict(color="red"),
            )
        )
        if "Ichimoku_A" in indicators and "Ichimoku_B" in indicators:
            fig.add_trace(
                go.Scatter(
                    x=data[datetime_column],
                    y=indicators["Ichimoku_A"],
                    mode="lines",
                    name="Ichimoku A",
                    line=dict(color="purple"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=data[datetime_column],
                    y=indicators["Ichimoku_B"],
                    mode="lines",
                    name="Ichimoku B",
                    line=dict(color="pink"),
                )
            )

    elif timeframe == LONG_TERM:
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["VWAP"],
                mode="lines",
                name="VWAP",
                line=dict(color="purple"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data[datetime_column],
                y=indicators["SMA_200"],
                mode="lines",
                name="SMA 200",
                line=dict(color="red"),
            )
        )

    fig.update_layout(
        title=f"{timeframe} Cryptocurrency Price Analysis",
        xaxis_title="Datetime",
        yaxis_title="Price (USD)",
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
        ),
    )

    st.plotly_chart(fig)


# Main App Interface
st.sidebar.title("Cryptocurrency Analysis Dashboard")
st.sidebar.write("Choose the timeframe and analysis settings.")

# Cryptocurrency dictionary
crypto_mapping = {
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD",
    "Solana (SOL)": "SOL-USD",
    "Binance Coin (BNB)": "BNB-USD",
    "Cardano (ADA)": "ADA-USD",
    "Avalanche (AVAX)": "AVAX-USD",
    "Dogecoin (DOGE)": "DOGE-USD",
    "Shiba Inu (SHIBA)": "SHIB-USD",
    "Fetch.ai (FET)": "FET-USD",
    "Ocean Protocol (OCEAN)": "OCEAN-USD",
    "SingularityNET (AGIX)": "AGIX-USD",
}

# Dashboard or Detailed View
view_choice = st.sidebar.selectbox("Select View", ["Dashboard", "Detailed Analysis"])

if view_choice == "Dashboard":
    # Timeframe selection for dashboard
    timeframe = st.sidebar.selectbox(
        "Select Dashboard Timeframe", [SHORT_TERM, MEDIUM_TERM, LONG_TERM]
    )

    if timeframe == SHORT_TERM:
        period = st.sidebar.selectbox("Select Period", ["5d", "1mo"])
        interval = "15m"
    elif timeframe == MEDIUM_TERM:
        period = st.sidebar.selectbox("Select Period", ["6mo", "1y", "3y"])
        interval = "1d"
    else:
        period = st.sidebar.selectbox("Select Period", ["5y", "10y"])
        interval = "1wk"

    create_dashboard(crypto_mapping, period, interval, coingecko_ids)


else:
    selected_coin = st.sidebar.selectbox(
        "Select Cryptocurrency", list(crypto_mapping.keys())
    )
    ticker = crypto_mapping[selected_coin]
    st.write(f"You selected: {selected_coin} with ticker {ticker}")

    timeframe = st.sidebar.selectbox(
        "Select Analysis Timeframe", [SHORT_TERM, MEDIUM_TERM, LONG_TERM]
    )

    if timeframe == SHORT_TERM:
        period = st.sidebar.selectbox("Select Period", ["5d", "1mo"])
        interval = "15m"
    elif timeframe == MEDIUM_TERM:
        period = st.sidebar.selectbox("Select Period", ["6mo", "1y", "3y"])
        interval = "1d"
    else:
        period = st.sidebar.selectbox("Select Period", ["5y", "10y"])
        interval = "1wk"

    with st.spinner("Loading data..."):
        data = load_data(ticker, period=period, interval=interval)

    if data is not None:
        indicators = calculate_indicators(data, timeframe)
        insights, trend, trend_color = provide_insights(
            data, indicators, timeframe, period
        )
        st.subheader(f"{timeframe} Analysis Insights")
        for insight in insights:
            st.markdown(insight, unsafe_allow_html=True)
        create_chart(data, indicators, timeframe)
    else:
        st.error("Failed to load data.")
