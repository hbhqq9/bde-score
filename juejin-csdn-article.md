# BDE Score：从零构建符合EU AI Act的股票分析API

> 本文将分享如何从零开始构建一个完全符合欧盟AI法案（EU AI Act）合规要求的股票分析API，涵盖多因子评分系统、风险信号检测、以及透明的决策解释机制。

## 背景：为什么需要另一个股票分析工具？

金融AI领域面临一个根本矛盾：**模型越复杂，决策越不透明**。

当用户看到一个"买入"信号时，他们需要知道：
- 这个结论基于哪些数据？
- 模型考虑了哪些风险因素？
- 如果市场条件变化，结论会如何改变？
- 这个AI系统是否合规？

BDE Score（BDE评分）正是为了解决这些问题而生的。它不是一个黑盒预测模型，而是一个**透明、可解释、合规优先**的股票分析API。

## 核心架构设计

### 1. 多因子评分系统

BDE Score采用多因子加权评分模型，而非单一的机器学习预测：

```python
# 核心评分维度
factors = {
    "technical": 0.25,      # 技术指标（RSI、MACD、均线等）
    "fundamental": 0.25,    # 基本面指标（PE、PB、ROE等）
    "sentiment": 0.20,      # 市场情绪（新闻、社交媒体）
    "risk": 0.15,           # 风险信号（波动率、流动性）
    "compliance": 0.15      # 合规指标（监管风险、ESG）
}
```

**为什么不用深度学习？**

金融时序预测的噪声比极高（信噪比约0.05），深度模型容易过拟合历史模式。多因子系统的优势在于：
- **可解释性**：每个因子的贡献清晰可见
- **可调试性**：当某个因子失效时，可以快速定位和调整
- **合规性**：满足EU AI Act对"高风险AI系统"的透明度要求

### 2. EU AI Act合规设计

EU AI Act将金融领域的AI系统归类为"高风险"，要求：

1. **透明度（Transparency）**：用户必须理解AI如何做出决策
2. **可追溯性（Traceability）**：决策过程必须可审计
3. **人工监督（Human Oversight）**：关键决策需人工确认
4. **鲁棒性（Robustness）**：系统必须在异常情况下保持安全

BDE Score的合规实现：

```python
class ComplianceLayer:
    """EU AI Act合规层"""
    
    def explain_decision(self, stock_code: str, score: float):
        """生成决策解释报告"""
        return {
            "score": score,
            "confidence": self.calculate_confidence(score),
            "factor_breakdown": self.get_factor_contributions(stock_code),
            "data_sources": self.list_data_sources(stock_code),
            "limitations": self.get_known_limitations(),
            "risk_warnings": self.get_risk_warnings(stock_code),
            "human_review_required": score > 80 or score < 20
        }
    
    def audit_trail(self, request_id: str):
        """审计追踪日志"""
        return self.db.query_audit_log(request_id)
```

### 3. 富途OpenD集成

数据是金融AI的血液。BDE Score通过富途OpenD获取实时行情数据：

```python
import futu as fut

class FutuDataProvider:
    def get_realtime_quote(self, stock_code: str):
        """获取实时行情"""
        ctx = fut.OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = ctx.get_market_snapshot([stock_code])
        ctx.close()
        return data
    
    def get_kline(self, stock_code: str, ktype=fut.KLType.K_DAY, num=100):
        """获取K线数据"""
        ctx = fut.OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data, _ = ctx.request_history_kline(
            stock_code, ktype=ktype, max_count=num
        )
        ctx.close()
        return data
```

**关键点**：富途OpenD需要在本地运行，通过Cloudflare Tunnel暴露API，确保安全访问。

## 技术栈选型

### 后端框架：FastAPI

选择FastAPI而非Flask/Django的原因：
- **异步支持**：金融数据获取是IO密集型，async/await显著提升性能
- **自动文档**：OpenAPI/Swagger自动生成，降低文档维护成本
- **类型安全**：Pydantic模型验证，减少运行时错误
- **性能**：基于Starlette，性能接近Node.js/Go

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="BDE Score API",
    description="EU AI Act compliant stock analysis API",
    version="1.0.0"
)

class ScoreRequest(BaseModel):
    stock_code: str
    include_explanation: bool = True

class ScoreResponse(BaseModel):
    stock_code: str
    score: float
    confidence: float
    explanation: dict | None
    timestamp: str
```

### 部署：Cloudflare Tunnel

为什么不直接暴露服务器IP？
- **安全性**：隐藏真实IP，防止DDoS攻击
- **零配置TLS**：自动HTTPS证书
- **无需开放端口**：绕过ISP端口封锁

```bash
# Cloudflare Tunnel配置
cloudflared tunnel --url http://localhost:8890
```

## 实际使用案例

### 案例1：港股技术分析

```bash
curl -X POST "https://your-domain.trycloudflare.com/api/score" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "HK.00700",
    "include_explanation": true
  }'
```

响应示例：

```json
{
  "stock_code": "HK.00700",
  "score": 72.5,
  "confidence": 0.83,
  "explanation": {
    "factor_breakdown": {
      "technical": 18.5,
      "fundamental": 15.2,
      "sentiment": 14.8,
      "risk": 12.0,
      "compliance": 12.0
    },
    "risk_warnings": [
      "RSI接近超买区域（68）",
      "近期成交量放大，需关注持续性"
    ],
    "human_review_required": false
  },
  "timestamp": "2026-07-11T11:30:00Z"
}
```

### 案例2：批量筛选高分股票

```python
import requests

stocks = ["HK.00700", "HK.09988", "US.AAPL", "US.MSFT"]
results = []

for stock in stocks:
    resp = requests.post("https://your-domain/api/score", json={
        "stock_code": stock,
        "include_explanation": False
    })
    results.append(resp.json())

# 筛选score > 70的股票
high_scores = [r for r in results if r["score"] > 70]
print(f"Found {len(high_scores)} stocks with score > 70")
```

## 开源与社区

BDE Score完全开源，采用MIT许可证：

- **GitHub仓库**：https://github.com/hbhqq9/bde-score
- **在线文档**：https://hbhqq9.github.io/bde-score/
- **API端点**：通过Cloudflare Tunnel提供公共访问

我们欢迎社区贡献，特别是在以下方向：
- 新的数据源集成（A股、美股期权等）
- 更多的技术指标实现
- EU AI Act合规性增强
- 多语言支持

## 经验总结与踩坑记录

### 1. 金融数据的质量问题

**坑**：免费数据源（如Yahoo Finance）经常缺失或延迟。

**解决**：
- 使用富途OpenD获取实时数据
- 实现数据缓存层，减少API调用
- 添加数据质量检查，标记异常值

### 2. API限速与并发

**坑**：高频调用富途API会触发限速。

**解决**：
- 实现请求队列和重试机制
- 批量获取数据（如一次获取多个股票的快照）
- 使用WebSocket替代REST API获取实时推送

### 3. EU AI Act合规的灰色地带

**坑**：法规对"高风险AI系统"的定义不够明确。

**解决**：
- 采取保守策略：将所有金融AI视为高风险
- 实现完整的审计追踪
- 在score > 80或< 20时强制人工审核
- 提供清晰的免责声明

### 4. Cloudflare Tunnel的稳定性

**坑**：临时域名（*.trycloudflare.com）会定期更换。

**解决**：
- 购买永久域名（约$10/年）
- 使用systemd管理cloudflared进程
- 实现自动重启和故障恢复

## 未来路线图

1. **多市场支持**：扩展到A股、美股期权、加密货币
2. **机器学习增强**：在可解释性框架（如SHAP）下引入ML模型
3. **社区评分**：允许用户分享和讨论评分结果
4. **移动端SDK**：iOS/Android原生客户端
5. **企业版**：私有化部署、定制化合规报告

## 结语

BDE Score不是一个"预测股价"的工具，而是一个**帮助理解市场**的系统。

在金融AI领域，透明度不是可选项，而是必需项。EU AI Act只是开始，未来会有更多法规要求AI系统的可解释性和问责性。

我们选择从一开始就把合规性作为核心设计原则，而不是事后补救。这不仅是对用户的负责，也是对整个行业的负责。

---

**项目地址**：https://github.com/hbhqq9/bde-score  
**在线演示**：https://hbhqq9.github.io/bde-score/  
**作者**：hbhqq9  
**许可证**：MIT

*免责声明：本工具仅供技术研究和教育目的，不构成任何投资建议。投资有风险，入市需谨慎。*
