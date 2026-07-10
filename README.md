# BDE-Stock

美股自动化交易系统 - Interactive Brokers 架构

## 投资哲学

基于**段永平价值投资框架**，核心约束：
- 绝对不做空
- 绝对不加杠杆
- 只做多，现金买入

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                  BDE-Stock 系统                   │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ factor_engine │  │stock_screener│              │
│  │  (5因子引擎)  │  │  (选股器)     │              │
│  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                      │
│  ┌──────┴──────────────────┴───────┐              │
│  │         risk_manager             │              │
│  │         (风控管理器)              │              │
│  └──────────────┬──────────────────┘              │
│                 │                                  │
│  ┌──────────────┴──────────────────┐              │
│  │        paper_trader             │              │
│  │      (模拟交易引擎)              │              │
│  └──────────────┬──────────────────┘              │
│                 │                                  │
│  ┌──────────────┴──────────────────┐              │
│  │    broker_adapter (ABC)          │              │
│  │    统一券商接口层                 │              │
│  ├──────────────┬──────────────────┤              │
│  │              │                  │              │
│  │  ┌───────────┴──┐  ┌──────────┴────┐         │
│  │  │ ibkr_adapter │  │alpaca_adapter │         │
│  │  │  (主用 IBKR) │  │ (备用 Alpaca) │         │
│  │  └──────┬───────┘  └──────┬────────┘         │
│  └─────────┼─────────────────┼──────────────────┘              │
└────────────┼─────────────────┼──────────────────┘
             │                 │
    ┌────────┴───────┐  ┌─────┴──────────┐
    │  IB Gateway    │  │  Alpaca API    │
    │  (TWS/Socket)  │  │  (REST/WebSocket)│
    │  Port: 7497    │  │  Paper: 停用    │
    └────────────────┘  └────────────────┘
```

## 券商架构

### Broker Adapter 模式

系统通过 `BrokerAdapter` 抽象基类支持多券商：

| 券商 | 适配器 | 状态 | 说明 |
|------|--------|------|------|
| Interactive Brokers | `ibkr_adapter.py` | ✅ 主用 | 通过 ib_insync + IB Gateway Socket 连接 |
| Alpaca | `alpaca_adapter.py` | ⏸️ 备用 | 账户已停用，代码保留 |

### 切换券商

```bash
# 使用 IBKR (默认)
export BDE_BROKER=ibkr
python paper_trader.py

# 使用 Alpaca
export BDE_BROKER=alpaca
python paper_trader.py
```

## IBKR 连接配置

### 连接方式

通过 IB Gateway 或 TWS 的 Socket 端口连接：

| 环境 | 主机 | 端口 |
|------|------|------|
| Paper Trading | 127.0.0.1 | 7497 |
| Live Trading | 127.0.0.1 | 7496 |

### 环境变量

```bash
export IB_HOST=127.0.0.1          # IB Gateway 地址
export IB_PORT=7497               # 端口 (7497=paper, 7496=live)
export IB_CLIENT_ID=1             # Client ID
export IB_USERNAME=your_user      # IB 账户用户名
export IB_PASSWORD=your_pass      # IB 账户密码
```

### 部署 IB Gateway

```bash
# 设置账户信息
export IB_USERNAME='your_username'
export IB_PASSWORD='your_password'

# 一键安装部署
bash deploy_ib_gateway.sh
```

## 文件结构

```
BDE-Stock/
├── config.py              # 配置文件（含券商选择逻辑）
├── broker_adapter.py      # 抽象基类 - 统一券商接口
├── ibkr_adapter.py        # IBKR 适配器（主用）
├── alpaca_adapter.py      # Alpaca 适配器（备用）
├── factor_engine.py       # 5因子引擎（不变）
├── stock_screener.py      # 选股器（不变）
├── risk_manager.py        # 风控管理器（不变）
├── feishu_push.py         # 飞书推送（不变）
├── paper_trader.py        # 模拟交易引擎（通过 adapter 调用）
├── test_connection.py     # 连接测试工具
├── deploy_ib_gateway.sh   # IB Gateway 安装部署脚本
└── README.md              # 本文档
```

## 五因子模型

| 因子 | 权重 | 说明 |
|------|------|------|
| 动量因子 | 30% | 14日涨幅，捕捉趋势延续 |
| 均值回归 | 20% | RSI超卖信号，捕捉反弹机会 |
| 成交量因子 | 20% | 资金流入信号 |
| 波动率因子 | 15% | 低波动率优先 |
| 趋势因子 | 15% | 均线趋势判断 |

## 快速开始

### 1. 安装依赖

```bash
pip install ib_insync
```

### 2. 离线测试

```bash
python test_connection.py --offline
```

### 3. 安装 IB Gateway

```bash
bash deploy_ib_gateway.sh
```

### 4. 启动 IB Gateway

```bash
bash ~/ibc/start_ib_gateway.sh
```

### 5. 测试连接

```bash
python test_connection.py --ibkr
```

## 飞书推送

系统通过飞书机器人推送交易信号和风控告警。

配置:
- base_token: `EMGtbCVY0auttWsnorTcjqbZnSf`

---

*段永平: "买股票就是买公司，买公司就是买其未来现金流的折现值。"*
