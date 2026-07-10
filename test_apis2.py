"""
第二轮测试 - 更多变体URL和方式
"""
import requests
import json
import time
import re

headers_ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# ============================================================
# 1. 新浪 - 尝试不同历史K线URL变体
# ============================================================
print("=" * 60)
print("新浪日K线 - 各种URL变体")
urls_sina = [
    # 变体1: us_minK
    "https://quotes.sina.cn/usstock/api/jsonp.php/data/US_MinKService.getMinK?symbol=aapl&type=240",
    # 变体2: 直接json
    "https://quotes.sina.cn/usstock/api/jsonp.php/var%20_aapl=/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50",
    # 变体3: finance.sina.com.cn直接路径
    "https://finance.sina.com.cn/stock/usstock/section/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50",
    # 变体4: vip.stock.finance
    "https://vip.stock.finance.sina.com.cn/corp/go.php/vMS_MarketHistory/stockid/AAPL.phtml?year=2025&jession=123",
    # 变体5: 新浪港股接口格式
    "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50",
    # 变体6: 新浪美股历史数据新接口
    "https://finance.sina.com.cn/stock/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50",
]

for i, url in enumerate(urls_sina):
    try:
        h = {**headers_ua, "Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=h, timeout=10)
        preview = resp.text[:200].replace('\n', ' ')
        print(f"  [{i+1}] Status={resp.status_code}, Len={len(resp.text)}")
        print(f"       {preview}")
    except Exception as e:
        print(f"  [{i+1}] Error: {str(e)[:100]}")
    time.sleep(0.5)

# ============================================================
# 2. 腾讯 - 尝试不同格式
# ============================================================
print("\n" + "=" * 60)
print("腾讯证券 - 不同参数格式")
urls_tencent = [
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=usAAPL.day,2025-04-01,2025-07-09,50,qfq",
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=us.aapl.day,2025-04-01,2025-07-09,50,qfq",
    "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=aapl.day,2025-04-01,2025-07-09,50,qfq",
    "https://web.ifzq.gtimg.cn/appstock/app/kline/kline?param=usAAPL.day,,,50,qfq",
    "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param=usAAPL.day,2025-04-01,2025-07-09,50,qfq",
    "https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=usAAPL",
]

for i, url in enumerate(urls_tencent):
    try:
        resp = requests.get(url, headers=headers_ua, timeout=10)
        preview = resp.text[:300].replace('\n', ' ')
        print(f"  [{i+1}] Status={resp.status_code}, Len={len(resp.text)}")
        print(f"       {preview}")
    except Exception as e:
        print(f"  [{i+1}] Error: {str(e)[:100]}")
    time.sleep(0.5)

# ============================================================
# 3. 百度股市通
# ============================================================
print("\n" + "=" * 60)
print("百度股市通")
urls_baidu = [
    "https://gushitong.baidu.com/opendata?resource_id=5352&query=AAPL&code=AAPL&market=us&group=quotation_kline_ab&finClientType=pc",
    "https://finance.pae.baidu.com/selfselect/openapi?srcid=5353&code=AAPL&market=us&ktype=day&start_time=2025-04-01&end_time=2025-07-09&count=50",
]
for i, url in enumerate(urls_baidu):
    try:
        resp = requests.get(url, headers=headers_ua, timeout=10)
        preview = resp.text[:400].replace('\n', ' ')
        print(f"  [{i+1}] Status={resp.status_code}, Len={len(resp.text)}")
        print(f"       {preview}")
    except Exception as e:
        print(f"  [{i+1}] Error: {str(e)[:100]}")
    time.sleep(0.5)

# ============================================================
# 4. Tiingo - 正确的endpoint
# ============================================================
print("\n" + "=" * 60)
print("Tiingo - 不同endpoint")
urls_tiingo = [
    ("https://api.tiingo.com/tiingo/daily/AAPL/prices?startDate=2025-04-01&endDate=2025-07-09", {"Content-Type": "application/json"}),
    ("https://api.tiingo.com/iex/?tickers=AAPL&startDate=2025-04-01&endDate=2025-07-09&resampleFreq=daily", {"Content-Type": "application/json"}),
]
for i, (url, h) in enumerate(urls_tiingo):
    try:
        resp = requests.get(url, headers=h, timeout=10)
        preview = resp.text[:300].replace('\n', ' ')
        print(f"  [{i+1}] Status={resp.status_code}, Len={len(resp.text)}")
        print(f"       {preview}")
    except Exception as e:
        print(f"  [{i+1}] Error: {str(e)[:100]}")
    time.sleep(0.5)

# ============================================================
# 5. Polygon.io v3
# ============================================================
print("\n" + "=" * 60)
print("Polygon.io - v3 endpoint")
try:
    url = "https://api.polygon.io/v3/reference/tickers/AAPL"
    resp = requests.get(url, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 6. Financial Modeling Prep (FMP) - 有免费tier
# ============================================================
print("\n" + "=" * 60)
print("Financial Modeling Prep")
try:
    url = "https://financialmodelingprep.com/api/v3/historical-price-full/AAPL?timeseries=50"
    resp = requests.get(url, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:300]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 7. TradingView 扫描器API
# ============================================================
print("\n" + "=" * 60)
print("TradingView Scanner API")
try:
    url = "https://scanner.tradingview.comamerica/scan"
    payload = {
        "symbols": {"tickers": ["NASDAQ:AAPL"]},
        "columns": ["close", "open", "high", "low", "volume", "change"]
    }
    resp = requests.post(url, json=payload, headers={**headers_ua, "Content-Type": "application/json"}, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:300]}")
except Exception as e:
    print(f"  Error: {str(e)[:200]}")

# ============================================================
# 8. Alpha Vantage - 尝试直接获取免费key
# ============================================================
print("\n" + "=" * 60)
print("尝试直接获取Alpha Vantage key")
try:
    # 有些API可以通过表单提交直接获取key
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "AAPL",
        "outputsize": "5",
        "apikey": "demo"
    }
    resp = requests.get(url, params=params, timeout=10)
    d = resp.json()
    print(f"  Response keys: {list(d.keys())}")
    print(f"  {json.dumps(d, indent=2)[:500]}")
except Exception as e:
    print(f"  Error: {e}")

# ============================================================
# 9. 尝试 Nasdaq Data Link (Quandl)
# ============================================================
print("\n" + "=" * 60)
print("Nasdaq Data Link")
try:
    url = "https://data.nasdaq.com/api/v3/datasets/WIKI/AAPL.json?rows=5&column_index=4"
    resp = requests.get(url, headers=headers_ua, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:300]}")
except Exception as e:
    print(f"  Error: {str(e)[:200]}")

# ============================================================
# 10. 尝试通过 fetch from different Chinese data sources
# ============================================================
print("\n" + "=" * 60)
print("同花顺 10jqka")
try:
    url = "https://stockpage.10jqka.com.cn/HQ_v4.html#hscode=us&AAPL"
    resp = requests.get("http://d.10jqka.com.cn/v6/line/us_AAPL/01/last.js", headers=headers_ua, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:300]}")
except Exception as e:
    print(f"  Error: {str(e)[:200]}")

print("\n" + "=" * 60)
print("雪球 xueqiu")
try:
    # 先获取cookie
    s = requests.Session()
    s.get("https://xueqiu.com/", headers=headers_ua, timeout=10)
    # 然后用cookie请求数据
    url = "https://stock.xueqiu.com/v5/stock/chart/kline.json?symbol=AAPL&begin=1720000000000&period=day&type=before&count=-50"
    resp = s.get(url, headers={**headers_ua, "Referer": "https://xueqiu.com/"}, timeout=10)
    print(f"  Status={resp.status_code}, Len={len(resp.text)}")
    print(f"  {resp.text[:500]}")
except Exception as e:
    print(f"  Error: {str(e)[:200]}")

