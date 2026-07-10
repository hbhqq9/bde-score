"""
系统性测试各免费股票历史数据API
"""
import requests
import json
import time
import re
from datetime import datetime, timedelta

results = {}

def test_api(name, func):
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    try:
        success, detail = func()
        results[name] = {"success": success, "detail": detail}
        status = "✅ 成功" if success else "❌ 失败"
        print(f"结果: {status} -> {detail[:200]}")
    except Exception as e:
        results[name] = {"success": False, "detail": str(e)[:200]}
        print(f"结果: ❌ 异常 -> {str(e)[:200]}")
    time.sleep(1)

# ============================================================
# 1. 新浪财经 - 日K线 (JSONP格式)
# ============================================================
def test_sina_daily():
    url = "https://quotes.sina.cn/usstock/api/jsonp.php/data/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", "Referer": "https://finance.sina.com.cn"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    
    if resp.status_code == 200:
        # Parse JSONP
        match = re.search(r'\((.+)\)', resp.text)
        if match:
            data = json.loads(match.group(1))
            if data and len(data) > 0:
                print(f"  Records: {len(data)}")
                print(f"  Sample: {data[0]}")
                return True, f"成功！{len(data)}条记录, 字段: {list(data[0].keys())}"
    return False, f"Status={resp.status_code}, len={len(resp.text)}"

test_api("新浪日K线(JSONP)", test_sina_daily)

# ============================================================
# 2. 新浪财经 - money.finance 接口
# ============================================================
def test_sina_money():
    url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=gb_aapl&scale=240&ma=no&datalen=50"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", "Referer": "https://finance.sina.com.cn"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    
    if resp.status_code == 200 and resp.text.strip():
        try:
            data = json.loads(resp.text)
            if data and len(data) > 0:
                print(f"  Records: {len(data)}")
                print(f"  Sample: {data[0]}")
                return True, f"成功！{len(data)}条记录, 字段: {list(data[0].keys())}"
        except:
            return False, f"JSON解析失败, text[:200]={resp.text[:200]}"
    return False, f"Status={resp.status_code}"

test_api("新浪money.finance接口", test_sina_money)

# ============================================================
# 3. Yahoo Finance 非官方 - query1
# ============================================================
def test_yahoo_q1():
    end = int(time.time())
    start = end - 86400 * 60
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/AAPL?period1={start}&period2={end}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    if resp.status_code == 200:
        try:
            d = resp.json()
            ts = d.get('chart', {}).get('result', [{}])[0].get('timestamp', [])
            if ts:
                return True, f"成功！{len(ts)}条时间戳"
        except: pass
    return False, f"Status={resp.status_code}"

test_api("Yahoo Finance query1", test_yahoo_q1)

# ============================================================
# 4. Yahoo Finance 非官方 - query2
# ============================================================
def test_yahoo_q2():
    end = int(time.time())
    start = end - 86400 * 60
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/AAPL?period1={start}&period2={end}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    if resp.status_code == 200:
        try:
            d = resp.json()
            ts = d.get('chart', {}).get('result', [{}])[0].get('timestamp', [])
            if ts:
                return True, f"成功！{len(ts)}条时间戳"
        except: pass
    return False, f"Status={resp.status_code}"

test_api("Yahoo Finance query2", test_yahoo_q2)

# ============================================================
# 5. Yahoo Finance v7 endpoint
# ============================================================
def test_yahoo_v7():
    url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL,MSFT"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    return resp.status_code == 200, f"Status={resp.status_code}"

test_api("Yahoo Finance v7 quote", test_yahoo_v7)

# ============================================================
# 6. Stooq.com CSV
# ============================================================
def test_stooq():
    url = "https://stooq.com/q/d/l/?s=aapl.us&d1=20250401&d2=20250709&i=d"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200 and "Date" in resp.text and "Close" in resp.text:
        lines = resp.text.strip().split("\n")
        return True, f"成功！{len(lines)}行, Header: {lines[0]}"
    return False, f"Status={resp.status_code}, len={len(resp.text)}"

test_api("Stooq.com CSV", test_stooq)

# ============================================================
# 7. Alpha Vantage (无key测试)
# ============================================================
def test_alphavantage_nokey():
    url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=demo"
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200:
        d = resp.json()
        if "Time Series (Daily)" in d:
            n = len(d["Time Series (Daily)"])
            return True, f"demo key成功！{n}天数据"
        elif "Note" in d:
            return False, f"频率限制: {d['Note'][:100]}"
        elif "Information" in d:
            return False, f"提示: {d['Information'][:100]}"
    return False, f"Status={resp.status_code}"

test_api("Alpha Vantage (demo key)", test_alphavantage_nokey)

# ============================================================
# 8. Finnhub (无key测试)
# ============================================================
def test_finnhub_nokey():
    end = int(time.time())
    start = end - 86400 * 60
    url = f"https://finnhub.io/api/v1/stock/candle?symbol=AAPL&resolution=D&from={start}&to={end}"
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    return False, f"Status={resp.status_code}, likely need key"

test_api("Finnhub (无key)", test_finnhub_nokey)

# ============================================================
# 9. Twelve Data (无key测试)
# ============================================================
def test_twelve_nokey():
    url = "https://api.twelvedata.com/time_series?symbol=AAPL&interval=1day&outputsize=5"
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200:
        d = resp.json()
        if "data" in d:
            return True, f"成功！无需key"
        elif "message" in d:
            return False, f"需key: {d['message'][:100]}"
    return False, f"Status={resp.status_code}"

test_api("Twelve Data (无key)", test_twelve_nokey)

# ============================================================
# 10. Polygon.io (无key测试)
# ============================================================
def test_polygon_nokey():
    url = "https://api.polygon.io/v2/aggs/ticker/AAPL/range?timespan=day&limit=5"
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    return False, f"Status={resp.status_code}"

test_api("Polygon.io (无key)", test_polygon_nokey)

# ============================================================
# 11. Tiingo (无key测试)
# ============================================================
def test_tiingo_nokey():
    url = "https://api.tiingo.com/tiingo/utilities/format?type=json&startDate=2025-04-28&endDate=2025-07-09&symbols=AAPL&resampleFreq=daily"
    headers = {"Content-Type": "application/json"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    return False, f"Status={resp.status_code}"

test_api("Tiingo (无key)", test_tiingo_nokey)

# ============================================================
# 12. EODHD (无key测试)
# ============================================================
def test_eodhd():
    url = "https://eodhistoricaldata.com/api/eod/AAPL.US?api=demo&from=2025-04-01&to=2025-07-09&fmt=json"
    resp = requests.get(url, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:300]}")
    return False, f"Status={resp.status_code}"

test_api("EOD Historical Data (demo)", test_eodhd)

# ============================================================
# 13. investing.com
# ============================================================
def test_investing():
    url = "https://www.investing.com/instruments/morehistory/175?date=2025-06-10"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "X-Requested-With": "XMLHttpRequest"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    return False, f"Status={resp.status_code}"

test_api("Investing.com", test_investing)

# ============================================================
# 14. MarketWatch
# ============================================================
def test_marketwatch():
    url = "https://www.marketwatch.com/investing/stock/aapl/downloadcsv?startDate=04/01/2025&endDate=07/09/2025"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15, allow_redirects=False)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text) if resp.text else 0}")
    return False, f"Status={resp.status_code}"

test_api("MarketWatch", test_marketwatch)

# ============================================================
# 15. 腾讯证券API
# ============================================================
def test_tencent():
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=usaapl.day,2025-04-01,2025-07-09,50,qfq"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200:
        try:
            d = resp.json()
            print(f"  Keys: {list(d.keys())}")
            data = d.get('data', {})
            if data:
                return True, f"成功！Keys: {list(data.keys())}"
        except: pass
    return False, f"Status={resp.status_code}"

test_api("腾讯证券API", test_tencent)

# ============================================================
# 16. 网易财经API
# ============================================================
def test_netease():
    url = "https://quotes.money.163.com/service/chddata.html?code=0AAPL&start=20250401&end=20250709&fields=TCLOSE;HIGH;LOW;TOPEN;LCLOSE;CHG;PCHG;TURNOVER;VOTURNOVER;VATURNOVER"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    return False, f"Status={resp.status_code}"

test_api("网易财经", test_netease)

# ============================================================
# 17. 东方财富
# ============================================================
def test_eastmoney():
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=105.AAPL&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&beg=20250401&end=20250709"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200:
        try:
            d = resp.json()
            klines = d.get('data', {}).get('klines', [])
            if klines:
                return True, f"成功！{len(klines)}条K线, 示例: {klines[0]}"
        except: pass
    return False, f"Status={resp.status_code}"

test_api("东方财富API", test_eastmoney)

# ============================================================
# 18. yfinance库
# ============================================================
def test_yfinance():
    try:
        import yfinance as yf
        ticker = yf.Ticker("AAPL")
        df = ticker.history(period="1mo")
        if len(df) > 0:
            print(f"  Records: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Last row: {df.iloc[-1].to_dict()}")
            return True, f"成功！{len(df)}条, 字段: {list(df.columns)}"
    except Exception as e:
        print(f"  Error: {e}")
        return False, str(e)[:200]
    return False, "no data"

test_api("yfinance库", test_yfinance)

# ============================================================
# 19. Google Finance (via requests)
# ============================================================
def test_google():
    url = "https://www.google.com/finance/quote/AAPL:NASDAQ"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    return False, f"Status={resp.status_code}, scraping needed"

test_api("Google Finance", test_google)

# ============================================================
# 20. 新浪实时行情（确认）
# ============================================================
def test_sina_realtime():
    url = "https://hq.sinajs.cn/list=gb_aapl,gb_msft"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"  Status: {resp.status_code}, Length: {len(resp.text)}")
    print(f"  Preview: {resp.text[:500]}")
    if resp.status_code == 200 and "hq_str" in resp.text:
        return True, f"实时行情可用！"
    return False, f"Status={resp.status_code}"

test_api("新浪实时行情(确认)", test_sina_realtime)

# ============================================================
# 汇总
# ============================================================
print("\n\n" + "="*80)
print("汇总报告")
print("="*80)
for name, r in results.items():
    status = "✅" if r["success"] else "❌"
    print(f"  {status} {name}: {r['detail'][:120]}")

# Save full results
with open("/app/data/所有对话/主对话/BDE-Stock/api_test_results.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
