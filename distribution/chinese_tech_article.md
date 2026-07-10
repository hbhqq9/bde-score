# 我花了一个月做了个AI股票评分系统，还顺便搞定了欧盟AI法案合规

> BDE Score™：覆盖美股、港股、A股73只股票的透明多因子评分系统，开源、合规、可嵌入。

## 背景

2026年8月2日，欧盟AI法案第50条将正式生效。所有与用户交互的AI系统必须提供**透明、可解释的输出**。

目前78%的AI系统运营者尚未采取合规措施。与此同时，亚洲市场的散户投资者几乎没有获取系统化、透明股票分析工具的机会。市面上的"AI股票预测器"大多是包装精美但完全不透明的黑箱。

我决定同时解决这两个问题。

## BDE Score是什么

一个量化股票评分系统，从5个独立维度评估股票：

| 因子 | 衡量内容 |
|------|---------|
| 动量 | 价格趋势强度和方向持续性 |
| 均值回归 | 价格偏离统计均值的程度 |
| 成交量 | 聪明资金流向检测 |
| 波动率 | 风险调整后的收益特征 |
| 趋势 | 多周期均线排列 |

每只股票获得0-100的综合评分：
- **看多** (>70)：多因子发出强烈上涨信号
- **中性** (40-70)：信号混合，方向不明
- **看空** (<40)：信号疲弱或负面

## 覆盖范围

- **美股** 25只：AAPL、MSFT、GOOG、NVDA、TSLA等
- **港股** 26只：腾讯、阿里、比亚迪、小米、京东等
- **A股** 23只：茅台、五粮液、宁德时代、平安、招行等

**一个可比较的分数，三个市场。**

## 技术栈

- **数据**：富途OpenD（主力）+ 新浪财经（备用），双通道自动故障转移
- **API**：FastAPI + Uvicorn
- **安全**：bcrypt密钥哈希、CORS白名单、HSTS、输入验证
- **基础设施**：Cloudflare Tunnel（HTTPS + DDoS防护）
- **支付**：Base链USDC（加密原生，无银行依赖）

## 为什么合规是竞争优势

大多数创业公司把监管当负担。我从架构设计第一天就内建了合规：
- 每次评分都有完整审计追踪
- API响应包含方法论披露
- 合规元数据已内嵌评分管线

当8月2日Art.50执行时，BDE Score已经准备好了。

## 立即试用

```bash
# 查看苹果评分
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/quote/AAPL"

# 查看腾讯评分
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/quote/00700"

# 查看茅台评分
curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/quote/600519"
```

- GitHub: https://github.com/hbhqq9/bde-score (MIT开源)
- 在线体验: https://hbhqq9.github.io/bde-score/

---

*免责声明：BDE Score™是技术分析工具，非投资建议。所有投资决策应独立做出。*
