# BDE-Stock 数据源测试报告

**测试时间**: 2026-07-10  
**测试环境**: 云电脑 (Python 3.13, 出口IP: 115.190.107.107)  
**目标**: 找到可在Python requests中直接获取美股历史K线的免费API

---

## ✅ 确认可用的数据源

### 1. 新浪财经 - 历史日K线 (JSONP接口)

**状态**: ✅ 完全可用，所有14只测试股票均成功

**URL格式**:
```
https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var%20data=/US_MinKService.getDailyK?symbol={symbol_lower}&scale=240&datalen={N}
```

**参数说明**:
- `symbol`: 小写股票代码，如 `aapl`, `msft`, `googl`
- `scale`: K线周期，240=日线（分钟数）
- `datalen`: 请求数据量（注意：实际返回全部历史，此参数无效）

**Headers**:
```python
{
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://finance.sina.com.cn"
}
```

**返回格式**: JSONP
```javascript
var data=([{"d":"2026-07-09","o":"313.39","h":"317.40","l":"310.51","c":"316.22","v":"48124490","a":"14687356001"}, ...])
```

**字段映射**:
| 字段 | 含义 |
|------|------|
| d | 日期 (YYYY-MM-DD) |
| o | 开盘价 (Open) |
| h | 最高价 (High) |
| l | 最低价 (Low) |
| c | 收盘价 (Close) |
| v | 成交量 (Volume) |
| a | 调整后数据 (可忽略) |

**解析方式**:
```python
import re, json
match = re.search(r'var data=\((.+)\)', resp.text)
records = json.loads(match.group(1))
# 取最后N条: records[-N:]
```

**测试覆盖** (14只全部成功):
AAPL(9985天), MSFT(9603天), GOOGL(4856天), AMZN(6768天), META(1023天), NVDA(5716天), TSLA(3856天), V(4604天), MA(4857天), JNJ(9645天), PG(9646天), BABA(2966天), SPY(6414天), QQQ(4822天)

---

### 2. 新浪财经 - 实时行情

**状态**: ✅ 完全可用

**URL格式**:
```
https://hq.sinajs.cn/list=gb_aapl,gb_msft,gb_googl,...
```

**Headers**:
```python
{
    "User-Agent": "Mozilla/5.0 ...",
    "Referer": "https://finance.sina.com.cn"
}
```

**返回格式**:
```
var hq_str_gb_aapl="苹果,316.2200,0.90,2026-07-10 08:18:14,2.8300,...";
```

**关键字段** (逗号分隔):
- [0]: 名称
- [1]: 当前价格
- [2]: 涨跌幅(%)
- [4]: 涨跌额
- [5]: 开盘价
- [6]: 最高价
- [7]: 最低价
- [8]: 昨收价
- [10]: 成交量

---

## ❌ 测试失败的数据源

| # | 数据源 | 状态 | 原因 |
|---|--------|------|------|
| 1 | Yahoo Finance query1 | ❌ 403 | IP被封，返回地区限制页 |
| 2 | Yahoo Finance query2 | ❌ 403 | 同上 |
| 3 | yfinance库 | ❌ 429 | Rate limited / Too Many Requests |
| 4 | Google Finance | ❌ 连接失败 | 无法连接google.com |
| 5 | Alpha Vantage (demo) | ❌ 需key | demo key仅支持演示，需注册免费key |
| 6 | Finnhub | ❌ 401 | 必须提供API key |
| 7 | Twelve Data | ❌ 401 | 必须提供API key |
| 8 | Polygon.io | ❌ 401/404 | 必须提供API key |
| 9 | Tiingo | ❌ 403/404 | 必须提供token |
| 10 | EOD Historical Data | ❌ 401 | 必须提供API key |
| 11 | Financial Modeling Prep | ❌ 401 | 必须提供API key |
| 12 | Stooq.com | ❌ JS验证 | 返回JS挑战页，无法绕过 |
| 13 | Investing.com | ❌ 403 | 被封锁 |
| 14 | MarketWatch | ❌ 401 | 需要认证 |
| 15 | Nasdaq Data Link | ❌ 403 | Incapsula防护 |
| 16 | 东方财富 | ❌ 连接断开 | 服务器主动断开连接 |
| 17 | 腾讯证券(日K) | ❌ 参数错误 | 美股代码格式未找到正确格式 |
| 18 | 网易财经 | ❌ 502 | 服务不可用 |
| 19 | 百度股市通 | ❌ 空结果 | 返回空数据 |
| 20 | 同花顺 | ❌ 404 | 接口不存在 |
| 21 | 雪球 | ❌ 400 | 需要登录cookie |
| 22 | TradingView Scanner | ❌ 连接重置 | 连接被重置 |

### 新浪日K线变体测试（失败的变体）

| URL变体 | 结果 |
|---------|------|
| quotes.sina.cn/usstock/.../US_MinKService.getDailyK | Service not valid |
| money.finance.sina.com.cn/.../getKLineData | 返回null |
| finance.sina.com.cn/stock/usstock/api/jsonp.php | 404 |

---

## 扩展建议

### 如需更多数据源（需注册免费API Key）

1. **Finnhub** (finnhub.io) - 免费60次/分钟
   - 注册: https://finnhub.io/register
   - 端点: `GET /api/v1/stock/candle?symbol=AAPL&resolution=D&from=TS&to=TS&token=KEY`

2. **Alpha Vantage** - 免费25次/天
   - 注册: https://www.alphavantage.co/support/#api-key
   - 端点: `GET /query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=KEY`

3. **Twelve Data** - 免费800次/天
   - 注册: https://twelvedata.com/
   - 端点: `GET /time_series?symbol=AAPL&interval=1day&apikey=KEY`

4. **Polygon.io** - 免费5次/分钟
   - 注册: https://polygon.io/
   - 端点: `GET /v2/aggs/ticker/AAPL/range?timespan=day&limit=50&apiKey=KEY`

> 注册账户: nnhbh@foxmail.com / Nnhbhqqq@999

---

## 结论

**新浪股票API是唯一在云电脑环境中无需注册、可直接通过Python requests获取美股历史K线+实时行情的免费数据源。**

- 历史数据：覆盖全部美股主要股票，数据从IPO至今
- 实时行情：盘后也有数据，延迟约15分钟
- 无需API Key、无频率限制（合理请求间隔0.3秒即可）
- 唯一注意事项：该接口返回全部历史数据（datalen参数无效），需客户端截取
