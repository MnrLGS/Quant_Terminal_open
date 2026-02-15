import yfinance as yf
import pandas as pd
import time
from datetime import datetime

# --- MASTER CONFIGURATION ---
# This list contains every major asset class and economic indicator
assets = [
    # --- 1. ECONOMIC HEALTH INDICATORS (The "Dashboard") ---
    {"symbol": "^TNX", "name": "US 10-Year Yield", "type": "BOND_YIELD"},
    {"symbol": "^FVX", "name": "US 5-Year Yield", "type": "BOND_YIELD"}, # Proxy for short-term rates
    {"symbol": "^MOVE", "name": "MOVE Index (Bond Volatility)", "type": "INDEX"},
    {"symbol": "RINF", "name": "Inflation Expectations (ETF)", "type": "ETF"}, # Market-implied inflation
    
    # --- 2. FOREX (Major Pairs) ---
    {"symbol": "EURUSD=X", "name": "Euro (EUR/USD)", "type": "FX"},
    {"symbol": "GBPUSD=X", "name": "British Pound (GBP/USD)", "type": "FX"},
    {"symbol": "JPY=X", "name": "Japanese Yen (USD/JPY)", "type": "FX"}, 
    {"symbol": "CHF=X", "name": "Swiss Franc (USD/CHF)", "type": "FX"},
    {"symbol": "AUDUSD=X", "name": "Aust Dollar (AUD/USD)", "type": "FX"},
    {"symbol": "NZDUSD=X", "name": "NZ Dollar (NZD/USD)", "type": "FX"},

    # --- 3. CRYPTO ---
    {"symbol": "BTC-USD", "name": "Bitcoin", "type": "CRYPTO"},

    # --- 4. COMMODITIES (Futures & Spot) ---
    {"symbol": "GC=F", "name": "Gold (Futures)", "type": "COMMODITY"},
    {"symbol": "SI=F", "name": "Silver (Futures)", "type": "COMMODITY"},
    {"symbol": "HG=F", "name": "Copper (Futures)", "type": "COMMODITY"},
    {"symbol": "CL=F", "name": "Crude Oil (WTI)", "type": "COMMODITY"},

    # --- 5. US INDICES ---
    {"symbol": "^GSPC", "name": "S&P 500", "type": "INDEX"},
    {"symbol": "^DJI", "name": "Dow Jones", "type": "INDEX"},
    {"symbol": "^IXIC", "name": "Nasdaq 100", "type": "INDEX"},
    
    # --- 6. GLOBAL INDICES ---
    {"symbol": "^GDAXI", "name": "Germany 40 (DAX)", "type": "INDEX"}, 
    {"symbol": "^N225", "name": "Japan 225 (Nikkei)", "type": "INDEX"},
    {"symbol": "000001.SS", "name": "China (Shanghai Composite)", "type": "INDEX"} 
]

def get_market_data(asset):
    symbol = asset['symbol']
    print(f"Analyzing {asset['name']} ({symbol})...", end=" ", flush=True)
    
    try:
        # Fetch 3 months of history to ensure we have enough data for the 20-day lookback
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo") 
        
        # Validation 1: No Data
        if hist.empty:
            print("FAILED (No Data).")
            return None
        
        # Validation 2: Short History
        hist = hist.dropna()
        if len(hist) < 25:
             print("FAILED (Not enough history).")
             return None

        # --- DATA EXTRACTION ---
        price_now = hist['Close'].iloc[-1]
        price_1mo = hist['Close'].iloc[-21] # Approx 20 trading days ago
        price_1wk = hist['Close'].iloc[-6]  # Approx 1 week ago
        
        # --- SPECIAL LOGIC FOR YIELDS ---
        # Yahoo often stores yields as whole numbers (e.g., 42.50 for 4.25%). 
        # We normalize this for the spreadsheet.
        if asset['type'] == "BOND_YIELD":
             if price_now > 20: # Heuristic: If yield > 20%, it's likely scaled by 10
                 raw_price = price_now / 10
                 display_price = f"{raw_price:.2f}%"
             else:
                 raw_price = price_now
                 display_price = f"{raw_price:.2f}%"
        else:
             raw_price = price_now
             display_price = round(price_now, 4)

        # --- MOMENTUM CALCULATION ---
        mom = ((raw_price - price_1mo) / price_1mo) * 100
        mom_short = ((raw_price - price_1wk) / price_1wk) * 100
        
        # --- STATE CLASSIFICATION ---
        # ACCELERATING: The 20-day trend is stronger than the 5-day noise
        # DECELERATING: The recent week is volatile compared to the monthly trend
        state = "ACCELERATING" if abs(mom) > abs(mom_short) else "DECELERATING"
        
        # BULLISH: Price is higher than it was 20 days ago
        trend = "BULLISH" if mom > 0 else "BEARISH"

        print(f"DONE. ({mom:.2f}%)")
        
        return {
            "Asset": asset['name'], 
            "Price": display_price, 
            "20D Momentum": f"{mom:.2f}%", 
            "Trend": trend,
            "State": state,
            "Type": asset['type'],
            "Raw": raw_price # Hidden column for macro calculations
        }

    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    print(f"--- MACRO & MARKET SCANNER: {datetime.now().strftime('%H:%M:%S')} ---")
    results = []
    
    # 1. Fetch Data
    for asset in assets:
        data = get_market_data(asset)
        if data:
            results.append(data)
        # Small delay to be polite to Yahoo's servers
        time.sleep(1) 

    if results:
        df = pd.DataFrame(results)
        
        # --- 2. ECONOMIC HEALTH DASHBOARD (The Prediction Layer) ---
        print("\n" + "="*40)
        print("      MACRO ECONOMIC DASHBOARD      ")
        print("="*40)
        
        # A. YIELD SPREAD CHECK (10Y - 5Y)
        # Note: We use 5Y as a proxy for Short Term because 2Y data is often restricted.
        try:
            yield_10 = df.loc[df['Asset'] == "US 10-Year Yield", 'Raw'].values[0]
            yield_5 = df.loc[df['Asset'] == "US 5-Year Yield", 'Raw'].values[0]
            spread = yield_10 - yield_5
            
            print(f"Yield Curve (10Y - 5Y): {spread:.2f}%", end=" ")
            
            if spread < 0:
                print(" -> [WARNING: INVERTED -> RECESSION SIGNAL]")
            elif spread < 0.15:
                print(" -> [CAUTION: FLATTENING]")
            else:
                print(" -> [NORMAL: POSITIVE GROWTH CURVE]")
        except IndexError:
            print("Yield Curve: Data Missing")

        # B. MOVE INDEX CHECK (Bond Volatility)
        try:
            if "MOVE Index (Bond Volatility)" in df['Asset'].values:
                move = df.loc[df['Asset'] == "MOVE Index (Bond Volatility)", 'Raw'].values[0]
                print(f"MOVE Index (Volatility): {move:.0f}", end="   ")
                
                if move > 120:
                    print(" -> [DANGER: LIQUIDITY CRISIS RISK]")
                elif move > 100:
                    print(" -> [CAUTION: HIGH STRESS]")
                else:
                    print(" -> [STABLE: MARKET IS CALM]")
            else:
                print("MOVE Index: Data Missing")
        except:
            print("MOVE Index: Calculation Error")

        # C. INFLATION CHECK
        try:
            if "Inflation Expectations (ETF)" in df['Asset'].values:
                inf_mom = float(df.loc[df['Asset'] == "Inflation Expectations (ETF)", '20D Momentum'].values[0].strip('%'))
                print(f"\nInflation Trend (RINF): {inf_mom:.2f}%", end=" ")
                if inf_mom > 2.0:
                     print(" -> [WARNING: INFLATION EXPECTATIONS RISING]")
                else:
                     print(" -> [STABLE]")
        except:
            pass

        print("\n" + "="*40)

        # --- 3. SAVE & DISPLAY ---
        # Remove helper columns before saving
        final_df = df.drop(columns=['Raw', 'Type'])
        
        # Sort by Momentum to see the strongest movers first
        # We need to temporarily clean the '%' to sort numerically
        final_df['SortVal'] = final_df['20D Momentum'].astype(str).str.rstrip('%').astype(float)
        final_df = final_df.sort_values(by='SortVal', ascending=False)
        final_df = final_df.drop(columns=['SortVal'])
        
        filename = f"Macro_Scanner_{datetime.now().strftime('%Y%m%d')}.xlsx"
        final_df.to_excel(filename, index=False)
        
        print("\n--- ASSET PERFORMANCE RANKING ---")
        print(final_df.to_string(index=False))
        print(f"\n[SUCCESS] Report saved to Desktop: {filename}")