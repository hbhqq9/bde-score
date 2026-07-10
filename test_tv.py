"""快速测试 TradingView scanner API"""
import requests, json

# TradingView Scanner API - 正确URL
try:
    url = "https://scanner.tradingview.com/america/scan"
    payload = {
        "symbols": {"tickers": ["NASDAQ:AAPL", "NASDAQ:MSFT"]},
        "columns": ["close", "open", "high", "low", "volume", "change"]
    }
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    print(f"TV Scanner: Status={resp.status_code}, Len={len(resp.text)}")
    if resp.status_code == 200:
        d = resp.json()
        print(f"Keys: {list(d.keys())}")
        if 'data' in d:
            for item in d['data'][:2]:
                print(f"  {item.get('s', '')}: {item.get('d', [])}")
except Exception as e:
    print(f"TV Error: {e}")
