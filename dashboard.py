import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io
import zipfile
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Momentum", layout="wide")
st.title("📊 Quant Macro Terminal")

# --- GLOBAL CONFIG ---
cot_map = {
    "Gold": "GOLD - COMMODITY EXCHANGE INC.",
    "Silver": "SILVER - COMMODITY EXCHANGE INC.",
    "Crude Oil (WTI)": "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",
    "Euro": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "British Pound": "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
    "Japanese Yen": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "Bitcoin": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
    "S&P 500 (E-Mini)": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "Nasdaq 100": "NASDAQ-100 CONSOLIDATED - CHICAGO MERCANTILE EXCHANGE",
    "10-Year Treasury": "10-YEAR U.S. TREASURY NOTES - CHICAGO BOARD OF TRADE"
}

tab1, tab2 = st.tabs(["🚀 Momentum Scanner", "🐋 COT Data (Statistical Depth)"])

# ==============================================================================
# TAB 1: MOMENTUM SCANNER
# ==============================================================================
with tab1:
    st.markdown("*> Real-time Mechanical Market Analysis*")
    col1, col2 = st.columns([1, 3])
    with col1:
        lookback_days = st.slider("Momentum Lookback (Days)", 10, 60, 20)
    
    assets = [
        {"symbol": "^TNX", "name": "US 10Y Yield", "type": "MACRO"},
        {"symbol": "^FVX", "name": "US 5Y Yield", "type": "MACRO"},
        {"symbol": "^MOVE", "name": "MOVE Index", "type": "MACRO"},
        {"symbol": "RINF", "name": "Inflation ETF", "type": "MACRO"},
        {"symbol": "EURUSD=X", "name": "Euro (EUR)", "type": "FX"},
        {"symbol": "GBPUSD=X", "name": "Pound (GBP)", "type": "FX"},
        {"symbol": "JPY=X", "name": "Yen (JPY)", "type": "FX"},
        {"symbol": "CHF=X", "name": "Swiss Franc", "type": "FX"},
        {"symbol": "BTC-USD", "name": "Bitcoin", "type": "CRYPTO"},
        {"symbol": "GC=F", "name": "Gold", "type": "COMMODITY"},
        {"symbol": "SI=F", "name": "Silver", "type": "COMMODITY"},
        {"symbol": "CL=F", "name": "Crude Oil", "type": "COMMODITY"},
        {"symbol": "^GSPC", "name": "S&P 500", "type": "INDEX"},
        {"symbol": "^IXIC", "name": "Nasdaq 100", "type": "INDEX"},
        {"symbol": "^GDAXI", "name": "DAX (Germany)", "type": "INDEX"},
        {"symbol": "^N225", "name": "Nikkei (Japan)", "type": "INDEX"},
        {"symbol": "000001.SS", "name": "Shanghai (China)", "type": "INDEX"}
    ]

    @st.cache_data(ttl=3600)
    def get_momentum_data(days):
        data_list = []
        for asset in assets:
            try:
                ticker = yf.Ticker(asset['symbol'])
                hist = ticker.history(period="3mo")
                if len(hist) > 25:
                    price_now = hist['Close'].iloc[-1]
                    price_past = hist['Close'].iloc[-days]
                    price_short = hist['Close'].iloc[-5]
                    mom_long = ((price_now - price_past) / price_past) * 100
                    mom_short = ((price_now - price_short) / price_short) * 100
                    state = "ACCELERATING" if abs(mom_long) > abs(mom_short) else "DECELERATING"
                    trend = "BULLISH" if mom_long > 0 else "BEARISH"
                    if asset['type'] == "MACRO" and "Yield" in asset['name'] and price_now > 20:
                        display_price = price_now / 10
                    else: display_price = price_now
                    data_list.append({"Asset": asset['name'], "Symbol": asset['symbol'], "Type": asset['type'], "Price": display_price, "Momentum (%)": round(mom_long, 2), "Trend": trend, "State": state})
            except: pass
        return pd.DataFrame(data_list)

    df = get_momentum_data(lookback_days)
    if st.button('🔄 REFRESH MOMENTUM', type="primary"):
        st.cache_data.clear()
        df = get_momentum_data(lookback_days)

    st.subheader("Asset Ranking")
    if not df.empty:
        sorted_df = df.sort_values(by="Momentum (%)", ascending=False)
        st.dataframe(sorted_df[['Asset', 'Price', 'Momentum (%)', 'Trend', 'State']], use_container_width=True)

        st.markdown("---")
        st.subheader("📈 Deep Dive Analysis")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1: chart_asset_name = st.selectbox("Select Asset to Chart", sorted_df['Asset'].values)
        with c2: timeframe = st.selectbox("Timeframe", ["1 Month", "3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "10 Years"], index=1)
        with c3: ema_length = st.number_input("EMA Length", min_value=5, max_value=200, value=50, step=5)
        
        tf_map = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "3 Years": "3y", "5 Years": "5y", "10 Years": "10y"}
        symbol = sorted_df.loc[sorted_df['Asset'] == chart_asset_name, 'Symbol'].values[0]
        chart_data = yf.Ticker(symbol).history(period=tf_map[timeframe])
        if not chart_data.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name=chart_asset_name))
            ema_line = chart_data['Close'].ewm(span=ema_length, adjust=False).mean()
            fig.add_trace(go.Scatter(x=chart_data.index, y=ema_line, mode='lines', name=f'{ema_length}-Day EMA', line=dict(color='orange', width=2)))
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB 2: COT DATA ENGINE (HISTORICAL BARS + MULTI-GROUP STATS)
# ==============================================================================
with tab2:
    st.markdown("*> Institutional Bias vs. Commercial Hedging vs. Retail Sentiment*")

    @st.cache_data(ttl=86400) 
    def fetch_historical_cot(years_back):
        all_data = []
        current_year = datetime.now().year
        for y in range(current_year - years_back, current_year + 1):
            url = f"https://www.cftc.gov/files/dea/history/deacot{y}.zip"
            try:
                r = requests.get(url, timeout=10)
                z = zipfile.ZipFile(io.BytesIO(r.content))
                df_year = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
                
                def find_col(keywords, excludes=None):
                    for col in df_year.columns:
                        c = str(col).lower().replace("_", " ").strip()
                        if all(k.lower() in c for k in keywords):
                            if excludes and any(e.lower() in c for e in excludes): continue
                            return col
                    return None

                c_map = {
                    'Market': find_col(["market", "name"]),
                    'DateRaw': find_col(["date"]),
                    'NC_Long': find_col(["noncomm", "long"], excludes=["old", "other"]),
                    'NC_Short': find_col(["noncomm", "short"], excludes=["old", "other"]),
                    'C_Long': find_col(["comm", "long"], excludes=["non", "old"]),
                    'C_Short': find_col(["comm", "short"], excludes=["non", "old"]),
                    'NR_Long': find_col(["nonrept", "long"]),
                    'NR_Short': find_col(["nonrept", "short"])
                }
                found = {k: v for k, v in c_map.items() if v is not None}
                if len(found) >= 4:
                    df_temp = df_year[list(found.values())].copy()
                    df_temp.columns = list(found.keys())
                    df_temp['Date'] = pd.to_datetime(df_temp['DateRaw'], format='%y%m%d', errors='coerce')
                    all_data.append(df_temp)
            except: continue
        
        if not all_data: return pd.DataFrame()
        full_df = pd.concat(all_data).sort_values(by='Date').drop_duplicates()
        
        num_cols = ['NC_Long', 'NC_Short', 'C_Long', 'C_Short', 'NR_Long', 'NR_Short']
        for col in num_cols:
            if col in full_df.columns:
                full_df[col] = pd.to_numeric(full_df[col], errors='coerce').fillna(0)
        
        # Explicit calculations for all 3 groups
        full_df['Net_NC'] = full_df.get('NC_Long', 0) - full_df.get('NC_Short', 0) # Smart Money
        full_df['Net_C'] = full_df.get('C_Long', 0) - full_df.get('C_Short', 0)   # Hedgers
        full_df['Net_NR'] = full_df.get('NR_Long', 0) - full_df.get('NR_Short', 0) # Retail
        
        return full_df.dropna(subset=['Date'])

    # --- UI CONTROLS ---
    c_a, c_b, c_c = st.columns([2, 1, 1])
    with c_a: 
        selected_asset = st.selectbox("Select Asset", list(cot_map.keys()), key="cot_sel_final")
    with c_b:
        cot_tf = st.selectbox("Lookback Period", ["3 Months", "6 Months", "1 Year", "3 Years", "5 Years", "10 Years"], index=2)
    with c_c:
        if st.button("🔄 REFRESH COT"):
            st.cache_data.clear()
            cot_data = fetch_historical_cot(10)
        else: cot_data = fetch_historical_cot(10)

    # Participant Filter
    st.markdown("**Show Participants on Chart:**")
    cp_1, cp_2, cp_3 = st.columns(3)
    with cp_1: show_nc = st.checkbox("Smart Money (Non-Comm)", value=True)
    with cp_2: show_c  = st.checkbox("Hedgers (Commercial)", value=True)
    with cp_3: show_nr = st.checkbox("Retail (Non-Reportable)", value=False)

    if not cot_data.empty:
        tf_days = {"3 Months": 90, "6 Months": 180, "1 Year": 365, "3 Years": 1095, "5 Years": 1825, "10 Years": 3650}
        cutoff = datetime.now() - timedelta(days=tf_days[cot_tf])
        asset_key = cot_map[selected_asset].split("-")[0].strip()
        filtered = cot_data[(cot_data['Market'].str.contains(asset_key, case=False)) & (cot_data['Date'] >= cutoff)].copy()
        
        if not filtered.empty:
            # Stats for the primary selected group (Smart Money)
            avg_nc = filtered['Net_NC'].mean()
            std_nc = filtered['Net_NC'].std()
            latest = filtered.iloc[-1]
            
            # --- METRICS BAR (Matches timeframe) ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Smart Money (Latest)", f"{latest['Net_NC']:,.0f}")
            m2.metric("Hedgers (Latest)", f"{latest['Net_C']:,.0f}")
            m3.metric("Retail (Latest)", f"{latest['Net_NR']:,.0f}")
            m4.metric(f"Avg Smart Money ({cot_tf})", f"{avg_nc:,.0f}")
            
            # --- BAR CHART VISUALIZATION ---
            fig_cot = go.Figure()
            
            if show_nc:
                fig_cot.add_trace(go.Bar(x=filtered['Date'], y=filtered['Net_NC'], name='Smart Money', marker_color='#00CC96', opacity=0.7))
            if show_c:
                fig_cot.add_trace(go.Bar(x=filtered['Date'], y=filtered['Net_C'], name='Hedgers', marker_color='#EF553B', opacity=0.7))
            if show_nr:
                fig_cot.add_trace(go.Bar(x=filtered['Date'], y=filtered['Net_NR'], name='Retail', marker_color='#AB63FA', opacity=0.7))
            
            # --- STATISTICAL BANDS (Based on Smart Money) ---
            fig_cot.add_trace(go.Scatter(x=filtered['Date'], y=[avg_nc]*len(filtered), name='Average', line=dict(color='white', dash='dash', width=1.5)))
            
            # 1st Standard Deviation (Cyan - High Visibility)
            fig_cot.add_trace(go.Scatter(x=filtered['Date'], y=[avg_nc + std_nc]*len(filtered), name='+1 Std Dev', line=dict(color='cyan', width=1.5, dash='dot')))
            fig_cot.add_trace(go.Scatter(x=filtered['Date'], y=[avg_nc - std_nc]*len(filtered), name='-1 Std Dev', line=dict(color='cyan', width=1.5, dash='dot'), showlegend=False))
            
            # 2nd Standard Deviation (Red - Danger Zone)
            fig_cot.add_trace(go.Scatter(x=filtered['Date'], y=[avg_nc + 2*std_nc]*len(filtered), name='+2 Std Dev (EXTREME)', line=dict(color='red', width=2.5)))
            fig_cot.add_trace(go.Scatter(x=filtered['Date'], y=[avg_nc - 2*std_nc]*len(filtered), name='-2 Std Dev (EXTREME)', line=dict(color='red', width=2.5), showlegend=False))

            fig_cot.update_layout(title=f"Positioning Comparison: {selected_asset} ({cot_tf})", barmode='group', template="plotly_dark", height=600, hovermode="x unified")
            st.plotly_chart(fig_cot, use_container_width=True)
            
            st.success(f"**Smart Money Z-Score:** Positioning is **{((latest['Net_NC'] - avg_nc) / std_nc):.2f} standard deviations** from the mean.")
        else: st.warning("No data found for this period.")