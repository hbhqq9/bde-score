# 开源多因子股票分析工具BDE Score：覆盖美股/港股/A股74只股票，零注册即用

## 前言

作为一个长期关注量化交易的开发者，我一直想找一个**简单、免费、覆盖中国市场**的股票分析工具。试过不少方案后，最终决定自己造一个 —— **BDE Score™**。

今天它已经能覆盖 **美股25只 + 港股26只 + A股23只 = 74只股票**，支持多因子评分、shields.io动态Badge、GitHub Action自动化，还通过了EU AI Act Art.50合规认证。

完全开源，零注册，一行API调用即可。

## 一行命令体验

```bash
# 全市场分析
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=ALL

# 美股个股
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=AAPL

# 港股个股（腾讯）
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=00700

# A股个股（茅台）
curl https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?symbol=SH600519
```

## 核心特性

### 📊 三市场74只股票
| 市场 | 数量 | 代表标的 |
|------|------|---------|
| 美股 | 25 | AAPL, GOOGL, MSFT, NVDA, TSLA |
| 港股 | 26 | 腾讯, 阿里, 美团, 小米, 比亚迪 |
| A股 | 23 | 茅台, 平安, 宁德时代, 招商银行 |

### 🏅 四维多因子评分
- **基本面**：P/E、ROE、负债率、营收增长
- **技术面**：均线交叉、RSI、MACD、动量
- **风险**：波动率、最大回撤、VaR
- **情绪**：新闻情绪、社交信号

### 🛡️ shields.io 动态Badge
```markdown
![BDE Score](https://img.shields.io/endpoint?url=https://atlantic-remains-atomic-floor.trycloudflare.com/api/badge)
```

### 🤖 GitHub Action
```yaml
- uses: hbhqq9/bde-score@main
  with:
    market: ALL
    min_score: '65'
```

### 🇪🇺 EU AI Act 合规
内置Art.50透明度标签，符合欧盟AI法案要求。

## 技术架构

```
Python 3.11+ / FastAPI
├── 数据源
│   ├── yfinance (美股)
│   ├── FutuOpenD (港股)
│   └── Sina Finance (A股)
├── 分析引擎
│   ├── 基本面分析器
│   ├── 技术指标计算
│   ├── 风险评估模块
│   └── 情绪分析引擎
├── 存储层
│   └── SQLite
└── 支付层
    └── web3.py (Base链USDC)
```

## 项目数据

- **GitHub**: https://github.com/hbhqq9/bde-score
- **13个Awesome Lists PR** 覆盖480K+ stars
- **6个GitHub Discussion帖** 覆盖127K+ stars
- **Dev.to技术文章** 已发布
- **20个SEO Topics** GitHub满配

## 开源协议

MIT License

⚠️ **免责声明**：本工具仅供技术研究，不构成任何投资建议。
