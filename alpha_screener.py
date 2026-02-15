import requests
import pandas as pd
import time
from datetime import datetime

# --- YOUR ARSENAL (8 Keys) ---
API_KEYS = [
    'Q0MHC85REM11RRSP', 'NDWP3ECHB89B2HB2', 'P62QZ651UY5YGIIA',
    '6BBXX0RUTLZ7DG25', 'Z1KNWO1G3P2H7P55', 'W1A7XSNWV2SWH2BS',
    '27206HLK4UQQY2GT', 'VTN2KFEW1R7LC0PM'
]

assets = [
    {"symbol": "EUR", "type": "FX", "name": "Euro (EUR/USD)"},
    {"symbol": "GBP", "type": "FX", "name": "British Pound (GBP/USD)"},
    {"symbol": "JPY", "type": "FX", "name": "Japanese Yen (JPY/USD)"}, 
    {"symbol": "CHF", "type": "FX", "name": "Swiss Franc (CHF/USD)"},
    {"symbol": "AUD", "type": "FX", "name": "Aust Dollar (AUD/USD)"},
    {"symbol": "NZD", "type": "FX", "name": "NZ Dollar (NZD/USD)"},
    {"symbol": "BTC", "type": "CRYPTO", "name": "Bitcoin"},
    {"symbol": "GLD", "type": "ETF", "name": "Gold (Proxy)"},
    {"symbol": "SLV", "type": "ETF", "name": "Silver"},
    {"symbol": "CPER", "type": "ETF", "name": "Copper"},
    {"symbol": "USO", "type": "ETF", "name": "Oil"},
    {"symbol": "UUP", "type": "ETF", "name": "Dollar Index"}, 
    {"symbol": "SPY", "type": "ETF", "name": "S&P 500"},
    {"symbol": "DIA", "type": "ETF", "name": "Dow Jones"},
    {"symbol": "QQQ", "type": "ETF", "name": "Nasdaq 100"},
    {"symbol": "EWG", "type": "ETF", "name": "Germany 40"},
    {"symbol": "EWJ", "type": "ETF", "name": "Japan 225"},
    {"symbol": "FXI", "type": "ETF", "name": "China Large-Cap"}
]

def get_data_with_deep_retry(asset, start_key_index):
    # TRY ALL KEYS if necessary. Don't give up after 3.
    for attempt in range(len(API_KEYS)):
        current_key_idx = (start_key_index + attempt) % len(API_KEYS)
        key = API_KEYS[current_key_idx]
        
        # Only print the asset name once
        if attempt == 0:
            print(f"Analyzing {asset['name']}...", end=" ", flush=True)
        
        result, status = fetch_data(asset, key)
        
        if result:
            print(f"DONE. ({result['20D Momentum']:.2f}%)")
            return result
        
        # If we hit a rate limit, we silently try the next key
        if status == "LIMIT_HIT":
            continue 
            
    print("FAILED (Checked all 8 keys - Limits or Errors).")
    return None

def fetch_data(asset, api_key):
    symbol = asset['symbol']
    
    # 1. Endpoint Selection
    if asset['type'] == "CRYPTO":
        url = f'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol}&market=USD&apikey={api_key}'
        data_key = "Time Series (Digital Currency Daily)"
    elif asset['type'] == "FX":
        url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={symbol}&to_symbol=USD&apikey={api_key}'
        data_key = "Time Series FX (Daily)"
    else: 
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}'
        data_key = "Time Series (Daily)"

    try:
        r = requests.get(url)
        data = r.json()

        # 2. Check for Limits
        if "Note" in data or "Information" in data:
            return None, "LIMIT_HIT"
        
        if data_key not in data:
            return None, "DATA_MISSING"

        # 3. Dynamic Key Finding (Universal)
        dates = list(data[data_key].keys())
        latest_row = data[data_key][dates[0]]
        
        # Find ANY column with "close" in the name
        close_key = next((k for k in latest_row.keys() if "close" in k), None)
        if not close_key:
            return None, "KEY_ERROR"

        # 4. Calculation
        price_now = float(data[data_key][dates[0]][close_key])
        price_20d = float(data[data_key][dates[20]][close_key])
        
        mom = ((price_now - price_20d) / price_20d) * 100
        
        return {
            "Asset": asset['name'],
            "Price": round(price_now, 4),
            "20D Momentum": mom
        }, "SUCCESS"

    except Exception:
        return None, "SYSTEM_ERROR"

if __name__ == "__main__":
    print(f"--- DEEP RETRY SCAN: {datetime.now().strftime('%H:%M:%S')} ---")
    results = []
    
    for i, asset in enumerate(assets):
        # Start with a distributed key index
        start_key_index = i % len(API_KEYS)
        
        res = get_data_with_deep_retry(asset, start_key_index)
        if res:
            results.append(res)
        
        # 0.1s delay for speed
        time.sleep(0.1) 

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by="20D Momentum", ascending=False)
        df['20D Momentum'] = df['20D Momentum'].apply(lambda x: f"{x:.2f}%")
        
        filename = f"Deep_Scan_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(filename, index=False)
        
        print("\n--- GLOBAL MOMENTUM RANKING ---")
        print(df.to_string(index=False))
        print(f"\n[SUCCESS] Report saved: {filename}")