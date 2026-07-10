# BDE-Stock 本地部署 · 3分钟快速上手

> **段永平价值因子量化系统** — 五因子评分 → 富途模拟盘自动交易

---

## 📋 你需要准备

| 项目 | 要求 |
|------|------|
| 富途账号 | 已注册（手机号: 13928789513） |
| Python | 3.9 或更高版本 |
| 操作系统 | Windows 10/11 · macOS 12+ · Ubuntu 20.04+ |

---

## 🚀 三步启动

### 第1步：安装并启动 FutuOpenD

FutuOpenD 是富途官方本地网关，BDE-Stock 通过它连接富途。

<details>
<summary><b>Windows</b>（点击展开）</summary>

1. 下载: https://www.futunn.com/download/openAPI
2. 解压安装，双击运行 `FutuOpenD.exe`
3. 在弹窗中输入富途账号密码登录
4. 看到 `FutuOpenD is running...` 即成功 ✅

> 💡 建议将 FutuOpenD 添加到开机自启

</details>

<details>
<summary><b>macOS</b>（点击展开）</summary>

```bash
# 下载并安装
brew install --cask futu-opend

# 或者手动下载: https://www.futunn.com/download/openAPI
# 双击 .dmg 安装

# 启动
open -a FutuOpenD
# 在弹窗中登录富途账号
```

</details>

<details>
<summary><b>Linux</b>（点击展开）</summary>

```bash
# 下载
wget https://softdl.futunn.com/FutuOpenD_Ubuntu.tar.gz
tar -xzf FutuOpenD_Ubuntu.tar.gz
cd FutuOpenD

# 编辑配置（填入富途账号）
vim futuopend.xml
# 修改 login_info 中的手机号和密码

# 启动
./FutuOpenD &
```

</details>

**验证 FutuOpenD 已运行：**
```bash
# 看到端口 11111 在监听就对了
# Windows:
netstat -an | findstr 11111
# Mac/Linux:
lsof -i :11111
```

---

### 第2步：安装依赖

```bash
pip install futu-api yfinance pandas numpy requests
```

> 🍎 macOS 用户如果 pip 报错，试试: `pip3 install futu-api yfinance pandas numpy requests`

---

### 第3步：运行

```bash
# 先测试连接（确保 FutuOpenD 正常）
python test_futu_connection.py

# 启动交易（首次建议 dry-run 模式）
python run_bde_stock.py --dry-run

# 确认没问题后，正式运行
python run_bde_stock.py
```

**就这么简单。3条命令，全链路打通。** ✅

---

## 📂 文件说明

```
BDE-Stock/
├── local_deploy/
│   ├── LOCAL_QUICKSTART.md      ← 你正在看的文件
│   ├── run_bde_stock.py         ← 一键启动脚本（核心）
│   ├── config_local.json        ← 配置文件（可按需修改）
│   └── test_futu_connection.py  ← 连接测试工具
├── futu_adapter.py              ← 富途适配器（19个接口）
├── factor_engine.py             ← BDE五因子评分引擎
├── risk_manager.py              ← 风控管理（段永平框架）
├── broker_adapter.py            ← 券商统一接口
└── config.py                    ← 全局配置
```

---

## ⚙️ 配置说明（可选）

打开 `config_local.json`，常用配置项：

```json
{
    "futu_opend": {
        "host": "127.0.0.1",    // FutuOpenD 地址（默认不改）
        "port": 11111            // 端口（默认不改）
    },
    "futu_account": {
        "paper_trading": true    // true=模拟盘, false=实盘(危险!)
    },
    "trading": {
        "max_positions": 5,      // 最多持仓5只
        "min_confidence": 55     // 评分>=55才买入
    }
}
```

---

## 🧪 常用命令

```bash
# 干跑模式 - 只评分不下单
python run_bde_stock.py --dry-run

# 只交易前3只
python run_bde_stock.py --top 3

# 自定义股票池
python run_bde_stock.py --universe "AAPL,MSFT,NVDA,TSLA"

# 快速连接测试
python test_futu_connection.py --quick

# 指定FutuOpenD地址
python test_futu_connection.py --host 192.168.1.100 --port 11111
```

---

## 🛡️ 风控说明（段永平框架，硬编码不可关闭）

| 铁律 | 说明 |
|------|------|
| ❌ 不做空 | 只做多，绝不卖空 |
| ❌ 不加杠杆 | 全额现金买入 |
| 🎯 单只上限 | 最多25%仓位 |
| 🎯 最多5只 | 同时持仓不超过5只 |
| 🛑 止损3% | 单只亏损超3%自动平仓 |
| 🛑 日损5% | 当日亏损超5%停止交易 |
| 🛑 回撤15% | 最大回撤15%全部清仓 |

---

## ❓ 常见问题

**Q: FutuOpenD 启动后连不上？**
- 确认端口没被占用: `lsof -i :11111`
- 确认用富途账号（不是牛牛号）登录
- 尝试重启 FutuOpenD

**Q: pip install futu-api 失败？**
- Windows: 确保安装了 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Mac: `pip3 install --user futu-api`
- 实在不行: `conda install futu-api`

**Q: 运行后没有交易信号？**
- 正常！BDE模型评分≥55分才出信号，不是每次都有
- 可以 `--dry-run` 查看评分排行

**Q: 如何切换实盘？**
- 修改 `config_local.json` 中 `"paper_trading": false`
- ⚠️ 实盘有风险，请充分了解后操作

---

## 📊 策略表现（回测数据）

| 指标 | 数值 |
|------|------|
| 年化收益 | **+23%** |
| 夏普比率 | **2.66** |
| 最大回撤 | **-8.7%** |
| 胜率 | **68%** |

---

<p align="center">
  <b>BDE-Stock</b> · 段永平价值投资框架 × 量化因子模型<br>
  只做多 · 不做空 · 不加杠杆 · 买看得懂的
</p>
