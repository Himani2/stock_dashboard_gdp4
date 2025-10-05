import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from sqlalchemy import create_engine
# Import the autorefresh component
#from streamlit_autorefresh import st_autorefresh 

# ------------------------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------------------------

st.set_page_config(page_title="Indian Stock Monitor", page_icon="📈", layout="wide")
# # 1️⃣ Database connection
db_user = "postgres"
db_password = "oX7IDNsZF1OrTOzS75Ek"
db_host = "database-1.cs9ycq6ishdm.us-east-1.rds.amazonaws.com"
db_port = "5432"  # default PostgreSQL port
db_name = "capstone_project"


DB_URI = f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
DATA_PATH = "data"
os.makedirs(DATA_PATH, exist_ok=True)
CACHE_TTL = "4h"

st.title("📊 Indian Stock Intelligence Dashboard")
st.caption("Live + Cached data | Auto-fallback | Weekend-aware")
# ------------------------------------------------------------------------------
# CONFIGURATION
# # ------------------------------------------------------------------------------
# # NOTE: CACHE_TTL still controls how long Streamlit caches the result of load_or_fetch
# CACHE_TTL = 3600 # 1 hour TTL for cache
# REFRESH_INTERVAL_MS = 5 * 60 * 1000 # 5 minutes for auto-refresh
# LATEST_DF_KEY = 'latest_stocks_df' # Session state key for the previous latest data

# # The DATA_PATH is no longer used for fallback/caching but kept for structure
# DATA_PATH = "data"
# os.makedirs(DATA_PATH, exist_ok=True)

# st.title("📊 Indian Stock Intelligence Dashboard")
# st.caption("Live Alerts + Database Data | Auto-refresh | Weekend-aware")

# # --- NEW: Auto-refresh component ---
# st_autorefresh(interval=REFRESH_INTERVAL_MS, key="data_refresh_timer")

# ------------------------------------------------------------------------------
# UTILITY: Database Loader (Simplified - NO FALLBACK)
# ------------------------------------------------------------------------------

@st.cache_data(ttl=CACHE_TTL)
def load_or_fetch(table_name: str):
    cache_file = f"{DATA_PATH}/{table_name}.csv"
    df = None
    try:
        engine = create_engine(DB_URI)
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        st.success(f"✅ Loaded {table_name} from Database")
    except Exception as e:
        st.warning(f"⚠️ Database load failed for {table_name}: {e}")
    # if df is None or df.empty:
    #     df = fallback_data(table_name)
    #     st.info(f"ℹ️ Using fallback data for {table_name}")
    if table_name == 'stocks' and df is not None and not df.empty:
        return df
    elif df is not None and not df.empty:
        df.to_csv(cache_file, index=False)
        return df
    if os.path.exists(cache_file):
        st.info(f"📁 Using cached {table_name}.csv")
        return pd.read_csv(cache_file)
    st.error(f"❌ No data for {table_name}")
    return pd.DataFrame()

# ------------------------------------------------------------------------------
# LOAD ALL TABLES
# ------------------------------------------------------------------------------

stocks_df = load_or_fetch("stocks")
news_df = load_or_fetch("news_sentiment")
pred_df = load_or_fetch("buy_sell_predictions")

# ------------------------------------------------------------------------------
# ALERT BELL LOGIC: Check for Top 5 Changes since last refresh
# ------------------------------------------------------------------------------

# # 1. Get the latest price data (Current Run)
# current_latest_df = stocks_df.groupby("symbol").last().reset_index()
# current_latest_df = current_latest_df.set_index("symbol")[["close"]]
# current_latest_df.columns = ['current_close']

# # 2. Retrieve previous latest price data (Previous Run)
# if LATEST_DF_KEY not in st.session_state:
#     # First run: Initialize session state
#     st.session_state[LATEST_DF_KEY] = current_latest_df.copy().rename(columns={'current_close': 'previous_close'})
#     st.toast("Initialization complete. Real-time alerts will start after the next auto-refresh.", icon="🔔", duration="long")

# previous_latest_df = st.session_state[LATEST_DF_KEY].copy()
# previous_latest_df.columns = ['previous_close']

# # 3. Calculate Change%
# merged_df = current_latest_df.join(previous_latest_df, how='inner')
# if 'previous_close' in merged_df.columns and not merged_df.empty:
#     merged_df['Change% (5m)'] = (
#         (merged_df['current_close'] - merged_df['previous_close']) / merged_df['previous_close']
#     ) * 100
    
#     # 4. Filter for top 5 changes (absolute value)
#     alert_df = merged_df.sort_values(by='Change% (5m)', key=abs, ascending=False).head(5)

#     # 5. Generate Toast Notifications for the Top 5
#     for symbol, row in alert_df.iterrows():
#         change_pct = row['Change% (5m)']
        
#         # Only alert if the change is meaningful (e.g., more than 0.1% in 5 mins)
#         if abs(change_pct) >= 0.1: 
#             emoji = "🚀" if change_pct > 0 else "📉"
#             st.toast(
#                 f"{emoji} **{symbol}** Alert: **{change_pct:.2f}%** change in last 5 min.", 
#                 icon="🔔",
#                 duration="long"
#             )
        
#     # 6. Update session state with current data for the next run
#     st.session_state[LATEST_DF_KEY] = current_latest_df.rename(columns={'current_close': 'previous_close'})

# ------------------------------------------------------------------------------
# MARKET TIME LOGIC: show Friday data on weekends
# ------------------------------------------------------------------------------

today = datetime.now().date()
weekday = today.weekday()  # 0=Mon ... 6=Sun
if weekday >= 5:  # Sat/Sun
    last_friday = today - timedelta(days=weekday - 4)
    st.warning(f"Market closed 🛑 Showing data from Friday ({last_friday})")
    stocks_df["timestamp"] = pd.to_datetime(stocks_df["timestamp"])
    stocks_df = stocks_df[stocks_df["timestamp"] <= pd.Timestamp(last_friday)]

# ------------------------------------------------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------------------------------------------------

st.sidebar.header("⚙️ Controls")
all_symbols = sorted(stocks_df["symbol"].unique())
selected_symbols = st.sidebar.multiselect("Select Stocks for Chart", all_symbols, default=all_symbols[:3])
refresh = st.sidebar.button("🔄 Manual Refresh Data")

if refresh:
    # Clear Streamlit cache to force a fresh DB query
    st.cache_data.clear()
    st.rerun()

threshold = st.sidebar.slider("Daily Alert Threshold (%)", 1, 10, 3)

# ------------------------------------------------------------------------------
# PRICE CHARTS
# ------------------------------------------------------------------------------

st.subheader("📈 Price Trend")
if not stocks_df.empty:
    fig = px.line(stocks_df[stocks_df["symbol"].isin(selected_symbols)],
                  x="timestamp", y="close", color="symbol",
                  title="Stock Closing Prices")
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# TOP GAINERS / LOSERS (Daily)
# ------------------------------------------------------------------------------

latest_df = stocks_df.groupby("symbol").last().reset_index()
# Assuming 'open' price is available for daily change calculation
latest_df["Change%"] = ((latest_df["close"] - latest_df["open"]) / latest_df["open"]) * 100

def format_change(val):
    """Formats the Change% with appropriate icon and color."""
    if val > 0:
        return f"$\bigtriangleup$ **{val:.2f}%**"
    elif val < 0:
        return f"$\bigtriangledown$ **{val:.2f}%**"
    else:
        return f"⚪ **{val:.2f}%**"

latest_df["Change"] = latest_df["Change%"].apply(format_change)

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🟢 Top Gainers (Daily)")
    gainers = latest_df.sort_values("Change%", ascending=False).head(5)
    st.markdown(gainers[["symbol", "Change"]].to_markdown(index=False))
with col2:
    st.markdown("### 🔴 Top Losers (Daily)")
    losers = latest_df.sort_values("Change%").head(5)
    st.markdown(losers[["symbol", "Change"]].to_markdown(index=False))

# ------------------------------------------------------------------------------
# BUY / SELL PREDICTIONS
# ------------------------------------------------------------------------------

st.subheader("💹 Model Recommendations")
st.dataframe(pred_df[["symbol", "buy_pred", "sell_pred", "action"]], use_container_width=True)

# ------------------------------------------------------------------------------
# NEWS SECTION
# ------------------------------------------------------------------------------

st.subheader("📰 Latest News & Sentiment")
if not news_df.empty:
    for _, row in news_df.iterrows():
        sentiment = row.get("sentiment", "neutral").lower()
        color = "🟢" if sentiment == "bullish" or sentiment == "positive" else "🔴" if sentiment == "bearish" or sentiment == "negative" else "⚪"
        news_title = row.get('title', row.get('headline', 'No Title'))
        # Using row.get('symbol', 'N/A') for safety
        st.markdown(f"{color} **{row.get('symbol', 'N/A')}** — {news_title} ({sentiment})")

# ------------------------------------------------------------------------------
# DAILY ALERT POP-UPS (for threshold moves)
# ------------------------------------------------------------------------------

for _, row in latest_df.iterrows():
    if abs(row["Change%"]) >= threshold:
        emoji = "📈" if row["Change%"] > 0 else "📉"
        # This toast is for the daily threshold move, distinct from the 5-min alert
        st.toast(f"{emoji} {row['symbol']} crossed the {threshold}% daily threshold ({row['Change%']:.2f}% change)!", icon="⚡")

# ------------------------------------------------------------------------------
# CHATBOT (basic rule-based)
# ------------------------------------------------------------------------------

st.subheader("💬 Stock Chatbot")
query = st.text_input("Ask about any stock:", key="chatbot_input")
if query:
    query_symbol = query.upper().strip()
    if query_symbol in all_symbols:
        rec = pred_df[pred_df["symbol"] == query_symbol]
        if not rec.empty:
            rec_row = rec.iloc[0]
            buy_pred = rec_row.get("buy_pred", 0) 
            sell_pred = rec_row.get("sell_pred", 0)
            action = rec_row.get("action", "Hold")
            st.success(f"{query_symbol}: Model suggests **{action}** (with buy confidence {buy_pred*100:.1f}% and sell confidence {sell_pred*100:.1f}%)")
        else:
            st.info(f"No prediction available for {query_symbol}.")
    else:
        st.info("Please type a valid stock symbol (e.g. TCS, INFY).")