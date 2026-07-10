"""深入测试新浪可用的历史K线接口"""
import requests
import json
import re

headers_ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# ============================================================
# 测试发现可用的URL - 详细分析
# ============================================================
url = "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol=aapl&scale=240&datalen=50"
headers = {**headers_ua, "Referer": "https://finance.sina.com.cn"}

print("测试新浪可用历史K线接口")
print(f"URL: {url}")
resp = requests.get(url, headers=headers, timeout=20)
print(f"Status: {resp.status_code}, Length: {len(resp.text)}")

# 解析
text = resp.text
# 去掉 JSONP wrapper: var data=(...)
match = re.search(r'var data=\((.+)\)', text)
if match:
    data = json.loads(match.group(1))
    print(f"\n总记录数: {len(data)}")
    print(f"字段: {list(data[0].keys())}")
    print(f"\n最早3条:")
    for r in data[:3]:
        print(f"  {r}")
    print(f"\n最新5条:")
    for r in data[-5:]:
        print(f"  {r}")
    
    # 验证数据完整性
    sample = data[-1]
    print(f"\n字段含义推测:")
    print(f"  d={sample.get('d')} -> 日期")
    print(f"  o={sample.get('o')} -> 开盘价")
    print(f"  h={sample.get('h')} -> 最高价")
    print(f"  l={sample.get('l')} -> 最低价")
    print(f"  c={sample.get('c')} -> 收盘价")
    print(f"  v={sample.get('v')} -> 成交量")
    print(f"  a={sample.get('a')} -> 调整后收盘价?")
    
    # 只取最后50条
    recent_50 = data[-50:]
    print(f"\n最近50条范围: {recent_50[0]['d']} ~ {recent_50[-1]['d']}")
else:
    print("JSONP解析失败")
    print(f"Response[:500]: {text[:500]}")

# ============================================================
# 测试多只股票
# ============================================================
print("\n" + "=" * 60)
print("测试多只股票获取")
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'V', 'MA', 'JNJ', 'PG', 'BABA', 'SPY', 'QQQ']

for sym in symbols:
    try:
        url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol={sym.lower()}&scale=240&datalen=50"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            match = re.search(r'var data=\((.+)\)', resp.text)
            if match:
                data = json.loads(match.group(1))
                recent = data[-50:] if len(data) >= 50 else data
                print(f"  ✅ {sym}: 总{len(data)}条, 最近={recent[-1]['d']}, 最新收盘={recent[-1]['c']}")
            else:
                print(f"  ❌ {sym}: JSONP解析失败, len={len(resp.text)}")
        else:
            print(f"  ❌ {sym}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  ❌ {sym}: {str(e)[:80]}")

# ============================================================
# 也测试另一个新浪变体
# ============================================================
print("\n" + "=" * 60)
print("测试新浪 variant 5 的不同scale/datalen")
for params in ["scale=240&datalen=120", "scale=240&datalen=200", "scale=60&datalen=50"]:
    url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol=aapl&{params}"
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 200:
        match = re.search(r'var data=\((.+)\)', resp.text)
        if match:
            data = json.loads(match.group(1))
            print(f"  {params}: {len(data)}条, {data[0]['d']} ~ {data[-1]['d']}")

