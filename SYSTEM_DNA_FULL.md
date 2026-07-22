# BDE Score™ 全栈系统DNA — 不可变核心基因

> **本文件是 BDE Score™ 全栈系统的DNA蓝图。任何与本文档矛盾的代码变更均视为非法。**
>
> 创建时间: 2026-07-21 | 版本: v2.0 | DNA锚定日期: 2026-07-21
>
> 取代 v1.0（BDE-Stock 单模块DNA），升级为全栈系统级DNA

---

## A. 系统身份（不可变）

```
名称: BDE Score™
定位: AI-Powered Multi-Market Stock Analysis
协议: AGPL-3.0 + 商业双许可
作者: hbhqq9
仓库: https://github.com/hbhqq9/bde-score
Landing: https://hbhqq9.github.io/bde-score/
合规标记: EU AI Act Art.50 compliant
```

---

## B. 系统架构全景（不可变拓扑）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BDE Score™ 全栈架构                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────── 发现层 (Discovery Layer) ──────────────────────────┐  │
│  │  .well-known/mcp.json    → MCP协议发现                                 │  │
│  │  .well-known/agent.json  → A2A协议发现                                 │  │
│  │  .well-known/ai-plugin.json → ChatGPT Plugin发现                       │  │
│  │  .well-known/glama.json  → Glama MCP发现                               │  │
│  │  Agent Registry (port 8892) → Agent原生注册/发现                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                           │
│  ┌─────────────────── 协议层 (Protocol Layer) ───────────────────────────┐  │
│  │  MCP Server (port 8891)        → Streamable HTTP MCP协议               │  │
│  │  REST API (port 8890)          → FastAPI RESTful接口                    │  │
│  │  Agent Registry (port 8892)    → Agent注册/发现/心跳                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                           │
│  ┌─────────────────── 分析层 (Analysis Layer) ───────────────────────────┐  │
│  │  FactorEngine (基础5因子)                                              │  │
│  │  ├── momentum (30%) + mean_reversion (20%) + volume (20%)             │  │
│  │  ├── volatility (15%) + trend (15%)                                   │  │
│  │  Phase1 (7因子扩展)                                                    │  │
│  │  ├── 因果层: VIX(15%) + Volume Profile(20%)                            │  │
│  │  └── 技术层: momentum(19.5%) + mean_rev(13%) + vol(13%) + volat(9.75%)│  │
│  │           + trend(9.75%)                                               │  │
│  │  Phase2 (动态权重)                                                     │  │
│  │  └── VIX四档动态权重引擎 (因果层30%-50% / 技术层70%-50%)               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                           │
│  ┌─────────────────── 数据层 (Data Layer) ───────────────────────────────┐  │
│  │  主数据源: 新浪JSONP API (K线) + yfinance (VIX)                        │  │
│  │  备选数据源: FutuOpenD (富途网关)                                       │  │
│  │  存储: SQLite (bde_history.db) + JSON (每日快照)                        │  │
│  │  缓存: 内存LRU, TTL=900s                                               │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                           │
│  ┌─────────────────── 生产层 (Production Layer) ─────────────────────────┐  │
│  │  bde_production_daily.py → 每日执行入口（含DNA校验）                     │  │
│  │  paper_trading_engine.py → 模拟盘交易 ($1M初始)                         │  │
│  │  signal_notifier.py      → 飞书推送（lark-cli）                         │  │
│  │  model_monitor.py        → 模型监控（胜率/回撤/告警）                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                           │
│  ┌─────────────────── 基础设施层 (Infrastructure) ───────────────────────┐  │
│  │  Cloudflare Tunnel (API + MCP)  → 公网暴露                             │  │
│  │  bore.pub Tunnel (Registry)     → 公网暴露                             │  │
│  │  GitHub Pages                   → Landing Page + .well-known           │  │
│  │  heal-discovery-urls.sh         → 自愈脚本（Tunnel漂移自动修复）         │  │
│  │  AGL Receipt Schema v2.0        → 链上治理凭证                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## C. 核心服务端口与协议（不可变）

| 服务 | 端口 | 协议 | 认证 | 文件 |
|------|------|------|------|------|
| REST API | 8890 | HTTP/REST | 可选API Key | `bde_api.py` |
| MCP Server | 8891 | Streamable HTTP MCP | X-API-Key Header | `mcp/mcp_http_server.py` |
| Agent Registry | 8892 | HTTP/REST | 可选API Key | `agent-registry/registry_server.py` |

**安全约束（铁律）：**
- API 仅监听 127.0.0.1，通过 Cloudflare Tunnel 暴露公网
- MCP 必须验证 X-API-Key（10 req/min 限流/IP）
- Registry 必须做 SSRF 防护（禁止内网IP注册）
- 所有服务必须输出安全头（X-Content-Type-Options, X-Frame-Options 等）

---

## D. 七因子模型（不可变核心）

### D.1 静态基准权重

| 因子 | 权重 | 层级 | 计算逻辑 |
|------|------|------|----------|
| VIX恐慌指数 | 15% | 因果层 | 情绪极值检测，VIX fallback=20 |
| Volume Profile | 20% | 因果层 | 50bin筹码分布，HVN/LVN/POC |
| 动量 momentum | 19.5% | 技术层 | 14日涨幅+多周期加权 |
| 均值回归 mean_reversion | 13% | 技术层 | RSI超卖/超买信号 |
| 成交量 volume | 13% | 技术层 | 资金流入/成交量突变 |
| 波动率 volatility | 9.75% | 技术层 | ATR/低波动优先 |
| 趋势 trend | 9.75% | 技术层 | EMA10/50均线对齐 |

**因果层合计: 35% | 技术层合计: 65%**

### D.2 VIX四档动态权重

| VIX区间 | 市场状态 | 因果层 | 技术层 |
|---------|----------|--------|--------|
| < 15 | 过度乐观 | 40% | 60% |
| 15-25 | 正常区间 | 30% | 70% |
| 25-35 | 恐慌升温 | 45% | 55% |
| ≥ 35 | 极度恐慌 | 50% | 50% |

### D.3 信号生成规则

```
Score > 68 且 trend ≥ 45  →  BUY
Score < 32 或 trend ≤ 15  →  SELL
其他                       →  HOLD
```

**因果层否决权：**
- VIX ≥ 85 + HOLD/SELL + trend ≥ 40 → 升级BUY（逆向做多）
- VIX ≤ 35 + BUY + VP < 40 → 降级HOLD（乐观陷阱）
- VP ≤ 30 + BUY → 降级HOLD（压力位抑制）
- VP ≥ 75 + HOLD + trend ≥ 50 → 升级BUY（支撑+趋势）
- VIX ≥ 35 + 因果层 < 30 → BUY降级HOLD（一票否决）

---

## E. 段永平框架约束（铁律，不可变）

```python
DUAN_RULES = {
    'no_short_selling': True,     # 绝对不做空
    'no_leverage': True,          # 绝对不加杠杆
    'long_only': True,            # 只做多，现金买入
    'cash_purchase_only': True,   # 必须全额现金支付
}
```

**任何代码变更若修改以上四条规则中的任何一条，DNA校验必须拒绝执行。**

---

## F. 标的池（不可变）

### F.1 生产系统标的（14只，BDE-Stock）

```
AAPL, MSFT, GOOGL, AMZN, META, NVDA,   # 科技龙头
V, MA,                                   # 金融支付
JNJ, PG,                                 # 防御消费
TSLA, BABA,                              # 高波动
SPY, QQQ,                                # 指数ETF
```

### F.2 API服务标的（30+只，全市场覆盖）

```
科技龙头: AAPL, GOOGL, MSFT, AMZN, META, NVDA, TSLA
消费: PLNT, COST, ORCL, NKE, GM, LULU
中概: BABA, TSM, BIDU
巴菲特/金融: BRK.B, BAC, JPM, AXP, V, KO, WMT, PG, DIS
中概ETF: MCHI, KWEB, CQQQ
指数ETF: SPY, QQQ, IWM, DIA
```

---

## G. 自愈机制（不可变架构）

### G.1 Tunnel漂移自愈 v3.3

```
触发条件: 推广引擎每4h扫描发现URL不匹配
自愈流程:
  1. 从日志文件自动发现当前Tunnel URL（grep trycloudflare.com）
  2. 验证URL可达性（curl health endpoint）
  3. 更新 .well-known/mcp.json + agent.json
  4. 更新 README.md + ACCESS_URLS.md + STATUS.md
  5. git commit + push
回退策略: bore.pub静态端口作为Registry fallback
```

### G.2 已知漂移记录

| 时间 | 组件 | 旧URL | 新URL |
|------|------|-------|-------|
| 7/21 00:38 | API | animal-munich-topics-tasks | provides-part-lamb-leaves |
| 7/21 00:38 | MCP | (同步漂移) | muscle-prison-explore-recorded |
| 7/21 08:39 | Pages CDN | expert-won-helmet-chris | 已修复 (commit 8e4bf66) |

---

## H. AGL治理层（不可变）

### H.1 Receipt Schema v2.0

```
文件: agl/receipt_schema_v2.py
功能: drift-aware governance receipts
特性:
  - BDE_DISCLOSURE_TEMPLATE: 免责声明模板
  - BDE_IDENTITY_TEMPLATE: 身份披露模板
  - PolicyVersion + ValidityWindow: 时间窗口校验
  - create_bde_receipt(): 生成带漂移检测的治理凭证
```

### H.2 EU AI Act Art.50 合规标记

```
合规层级:
  - Art.50(5) chatbot disclosure → ✅ 已实现（SOUL.md + API响应头）
  - Art.50(2) 机器可读水印 → N/A（不做图片/音频/视频合成）
  - Art.50(4) 深度伪造标注 → N/A（不发布deepfake）

标记位置:
  - mcp.json: metadata.compliance = ["EU AI Act Art.50"]
  - agent.json: metadata.compliance = ["EU AI Act Art.50"]
  - API响应: X-EU-AI-Act-Compliance header
```

---

## I. 数据源配置（不可变）

| 数据 | 主数据源 | 备用数据源 | Fallback |
|------|---------|-----------|----------|
| VIX | yfinance (`^VIX`) | 新浪JSONP API | 固定值20 |
| K线(120日) | 新浪JSONP API | FutuOpenD | 无数据→退出 |
| K线字段 | open/high/low/close/volume | 同左 | - |
| 交易参数 | 模拟盘$1M, 等权分配, 5%现金保留 | - | - |

---

## J. SHA-256 文件指纹链

> **每次代码变更必须更新本节。校验失败 → 拒绝执行。**
>
> 校验锚点: `bde_production_daily.py` 内嵌 `DNA_HASH_EXPECTED` = 本文件 SHA-256

```
# === 核心服务层 ===
SHA256(bde_api.py)                                = 48e7e0c7e6952f9c4122b9a5988cfc5e237e2eb9138647a6b42f9369fc67daa6
SHA256(factor_engine.py)                          = 83a82fbf3aeb1f7df59e1d67c45750ab9f1218d316ac27b0df446dd4c99af8bd
SHA256(config.py)                                 = 3d5bb57906dd658adb9d87b6317cacd913a8ca967c0bf15726ae3703ef8e59ec

# === MCP + Registry ===
SHA256(mcp/mcp_http_server.py)                    = 523626b8abd6bfe78dd82ce6a588918e2442b006b1ab0a5597d18a001d8ea642
SHA256(agent-registry/registry_server.py)          = dd5d5764725a63c9500e4b32a8645e4d0eef85fb1b43d79a1cc35552127287cd

# === 自愈与运维 ===
SHA256(scripts/heal-discovery-urls.sh)            = 891c91c837881822378d89db0d2567636f85bce29df1715f987fe50ca6f50b0b
SHA256(scripts/dna_verify.py)                     = 403b4bba0256c0e1f5e41bc50d8f469ba74e222e0b3f6a3fce200899d4d20bb8

# === 生产系统 ===
SHA256(production/signal_notifier.py)             = 8b143678baff5eb195c25d7e7213709e2aae0a6af9a08097ac6cab5cb205f732
SHA256(production/paper_trading_engine.py)        = 921dab24e0121d3d3aedfb171db62d87579a1a1d89cf28a8bf3ceec8f7af0eb0
SHA256(production/model_monitor.py)               = a3a90bbc2e536df447bc72dbf135437e87357de255ca4ef449c2255aedbe0223

# === 因子引擎 ===
SHA256(phase1_vix_vp/factor_engine_phase1.py)    = 2322c06ccaa92e1d147d0a7bae8641310910188dc18a2bfd15ef3589e8612a02
SHA256(phase2_backtest/factor_engine_phase2.py)  = b4204e111a29b07145c776ede2673554df6c7d94583dc16e1a2b325a6d47122b
SHA256(phase2_backtest/dynamic_weight_engine.py) = 6ca4a970f0ca865eb8411015cb8529e3d35ef399898e3cde26371aa98800cef5
SHA256(phase2_backtest/backtest_engine.py)       = 3055f579f663db5942582aa48958d0bfe7eb8a1d04d71fa01c9ca96a683734a0

# === AGL治理层 ===
SHA256(agl/receipt_schema_v2.py)                 = b7a6ca4926eeeb79231b7077a7d1a3d8fc75868034684942e263a80adaece6f4
SHA256(agl/receipt_store.py)                     = 17a5b4b9971c9756f2e3ddbcf1f25d930e1954e722b500d3be08652e4f5f3ca4

# === 发现层 ===
SHA256(docs/.well-known/mcp.json)                = a8c2cf717e951d2fcac80a83a7af171795ecc7f3a41b68411b1777e0320447fc
SHA256(docs/.well-known/agent.json)              = 23ca45c82b3fec9fc0233044297e7a093460fc8c0373d438aa33feae242fa930

# === DNA文档自身 ===
SHA256(SYSTEM_DNA_FULL.md)                       = 9a63ccad5971fa56b36de036486d3f68b1df96969b63f29b45497b40cd4903f0
```

**手动校验命令：**
```bash
cd BDE-Stock && sha256sum bde_api.py factor_engine.py config.py \
  mcp/mcp_http_server.py agent-registry/registry_server.py \
  scripts/heal-discovery-urls.sh \
  production/*.py phase1_vix_vp/*.py phase2_backtest/*.py \
  agl/*.py docs/.well-known/*.json
```

---

## K. 性能基线

### K.1 回测指标（90个交易日，2026-07-20）

| 指标 | 5因子基准(v0) | 7因子(Phase3) | 提升 |
|------|--------------|--------------|------|
| BUY胜率(5日) | 7.1% | **41.5%** | **+34.3pp** |
| BUY胜率(10日) | 7.1% | **42.5%** | +35.3pp |
| BUY胜率(20日) | 0.0% | **32.5%** | +32.5pp |
| 平均BUY信号数 | 0.3只/天 | **39只/天** | 覆盖率↑ |
| 夏普比率 | 0.06 | 0.06 | 持平 |
| 最大回撤 | 19.1% | 19.1% | 持平 |

### K.2 服务可用性目标

| 指标 | 目标 | 当前状态 |
|------|------|----------|
| API响应时间 | < 3s (缓存命中 < 0.5s) | ✅ |
| Tunnel自愈时间 | < 10min | ✅ (v3.3) |
| 每日生产执行 | 21:30 UTC 准时 | ✅ |
| DNA校验通过率 | 100% | ✅ |

---

## L. 免责声明（不可变）

> ⚠️ **免责声明：** 本系统仅供学习和研究目的。所有信号仅为量化模型输出，不构成任何投资建议。
> 股市有风险，投资需谨慎。过往回测表现不代表未来收益。使用者需自行承担投资决策的全部责任。

---

## M. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-07-21 | 初始DNA镌刻：BDE-Stock 7因子架构固化 |
| v2.0 | 2026-07-21 | 升级为全栈系统DNA：覆盖API+MCP+Registry+自愈+AGL+发现层 |

