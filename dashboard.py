import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Quant Macro Terminal", layout="wide")

st.title("📊 Quant Macro Terminal")
st.markdown("*> Real-time Mechanical Market Analysis*")

# --- SIDEBAR: ASSET CONFIGURATION ---
st.sidebar.header("Configuration")
lookback_days = st.sidebar.slider("Lookback Period (Days)", min_value=10, max_value=60, value=20)

assets = [
    # MACRO
    {"symbol": "^TNX", "name": "US 10Y Yield", "type": "MACRO"},
    {"symbol": "^FVX", "name": "US 5Y Yield", "type": "MACRO"},
    {"symbol": "^MOVE", "name": "MOVE Index", "type": "MACRO"},
    {"symbol": "RINF", "name": "Inflation ETF", "type": "MACRO"},
    # FOREX
    {"symbol": "EURUSD=X", "name": "Euro (EUR)", "type": "FX"},
    {"symbol": "GBPUSD=X", "name": "Pound (GBP)", "type": "FX"},
    {"symbol": "JPY=X", "name": "Yen (JPY)", "type": "FX"},
    {"symbol": "CHF=X", "name": "Swiss Franc", "type": "FX"},
    # CRYPTO
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "CRYPTO"},
    # COMMODITIES
    {"symbol": "GC=F", "name": "Gold", "type": "COMMODITY"},
    {"symbol": "SI=F", "name": "Silver", "type": "COMMODITY"},
    {"symbol": "CL=F", "name": "Crude Oil", "type": "COMMODITY"},
    # INDICES
    {"symbol": "^GSPC", "name": "S&P 500", "type": "INDEX"},
    {"symbol": "^IXIC", "name": "Nasdaq 100", "type": "INDEX"},
    {"symbol": "^GDAXI", "name": "DAX (Germany)", "type": "INDEX"},
    {"symbol": "^N225", "name": "Nikkei (Japan)", "type": "INDEX"},
    {"symbol": "000001.SS", "name": "Shanghai (China)", "type": "INDEX"}
]

# --- DATA FETCHING FUNCTION ---
@st.cache_data(ttl=3600) 
def get_data():
    data_list = []
    progress_bar = st.progress(0)
    
    for i, asset in enumerate(assets):
        try:
            ticker = yf.Ticker(asset['symbol'])
            hist = ticker.history(period="3mo")
            
            if len(hist) > 25:
                # Prices
                price_now = hist['Close'].iloc[-1]
                price_past = hist['Close'].iloc[-lookback_days]
                price_short = hist['Close'].iloc[-5]

                # Calculations
                mom_long = ((price_now - price_past) / price_past) * 100
                mom_short = ((price_now - price_short) / price_short) * 100
                
                # Logic
                state = "ACCELERATING" if abs(mom_long) > abs(mom_short) else "DECELERATING"
                trend = "BULLISH" if mom_long > 0 else "BEARISH"

                # Normalized Price for Yields
                if asset['type'] == "MACRO" and "Yield" in asset['name'] and price_now > 20:
                    display_price = price_now / 10
                else:
                    display_price = price_now

                data_list.append({
                    "Asset": asset['name'],
                    "Symbol": asset['symbol'],
                    "Type": asset['type'],
                    "Price": display_price,
                    "Momentum (%)": round(mom_long, 2),
                    "Trend": trend,
                    "State": state,
                    "History": hist['Close'] 
                })
        except Exception as e:
            pass 
        
        progress_bar.progress((i + 1) / len(assets))

    progress_bar.empty()
    return pd.DataFrame(data_list)

# --- THE "MANUAL UPDATE" BUTTON ---
if st.button('🔄 REFRESH MARKET DATA', type="primary"):
    st.cache_data.clear() 
    df = get_data()
else:
    df = get_data() 

# --- DASHBOARD SECTION 1: MACRO HEALTH ---
st.subheader("🏥 Economic Health Dashboard")

try:
    yield_10 = df.loc[df['Symbol'] == "^TNX", 'Price'].values[0]
    yield_5 = df.loc[df['Symbol'] == "^FVX", 'Price'].values[0]
    spread = yield_10 - yield_5
    
    move_index = df.loc[df['Symbol'] == "^MOVE", 'Price'].values[0]
    inflation_mom = df.loc[df['Symbol'] == "RINF", 'Momentum (%)'].values[0]
except:
    spread, move_index, inflation_mom = 0, 0, 0

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Yield Curve (10Y - 5Y)", value=f"{spread:.2f}%", 
              delta="Inverted! (Recession Signal)" if spread < 0 else "Normal Curve",
              delta_color="normal" if spread > 0 else "inverse")

with col2:
    st.metric(label="MOVE Index (Volatility)", value=f"{move_index:.0f}", 
              delta="Panic Mode" if move_index > 120 else "Stable",
              delta_color="inverse") 

with col3:
    st.metric(label="Inflation Trend (RINF)", value=f"{inflation_mom:.2f}%", 
              delta="Rising Expectations" if inflation_mom > 2 else "Stable")

st.markdown("---")

# --- DASHBOARD SECTION 2: ASSET RANKING ---
st.subheader("🚀 Asset Momentum Ranking")

asset_filter = st.multiselect("Filter by Type", options=df['Type'].unique(), default=df['Type'].unique())
filtered_df = df[df['Type'].isin(asset_filter)]
sorted_df = filtered_df.sort_values(by="Momentum (%)", ascending=False)

def highlight_trend(val):
    color = '#d4f7dc' if val > 0 else '#f7d4d4' 
    return f'background-color: {color}; color: black'

st.dataframe(
    sorted_df[['Asset', 'Price', 'Momentum (%)', 'Trend', 'State']].style.applymap(highlight_trend, subset=['Momentum (%)']),
    use_container_width=True,
    height=400
)

# --- DASHBOARD SECTION 3: DEEP DIVE CHART ---
st.markdown("---")
st.subheader("📈 Deep Dive Analysis")

selected_asset_name = st.selectbox("Select Asset to Visualize", sorted_df['Asset'].values)

if selected_asset_name:
    row = df[df['Asset'] == selected_asset_name].iloc[0]
    history = row['History']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=history.index, y=history.values, mode='lines', name=selected_asset_name, line=dict(color='#00CC96', width=2)))
    
    ma_20 = history.rolling(window=20).mean()
    fig.add_trace(go.Scatter(x=history.index, y=ma_20.values, mode='lines', name='20-Day Avg', line=dict(color='#EF553B', width=1, dash='dash')))

    fig.update_layout(title=f"{selected_asset_name} - 3 Month Trend", xaxis_title="Date", yaxis_title="Price", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)