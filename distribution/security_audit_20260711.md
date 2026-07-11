# 🔐 BDE Score™ 安全审计报告
## 基于《安全宪法》的全面穿透审查

**审计日期**: 2026-07-11 20:55 UTC+8  
**审计范围**: BDE Score全栈 — API Server / MCP Server / Cloudflare Tunnel / Git仓库 / 支付系统  
**审计依据**: 《安全宪法》v1.0（铁律I-IV + 6章30条）  

---

## 总览：安全评分卡

| 维度 | 评级 | 核心问题 |
|------|------|----------|
| 铁律合规 | ⚠️ 部分 | 钱包地址永久写入git history（39处） |
| 网络边界 | ✅ 良好 | API+MCP均绑定127.0.0.1，Cloudflare Tunnel为唯一入口 |
| 认证授权 | ❌ 严重缺失 | MCP Server零认证，任何人可无限调用 |
| 速率控制 | ⚠️ 分裂 | API有（10/min），MCP无（0限制） |
| 输入校验 | ⚠️ 分裂 | API有白名单，MCP无校验 |
| 审计追踪 | ❌ 缺失 | 全栈无结构化日志，无请求追踪 |
| 凭证管理 | ✅ 良好 | API Key bcrypt哈希存储，无.env泄露 |
| 隐私合规 | ⚠️ 需修正 | Privacy Policy声明"不收集IP"，但rate limiter实际读取IP |
| 资金安全 | ✅ 良好 | 只读监听，无私钥存储，旧钱包已废弃 |
| 错误处理 | ⚠️ 有风险 | MCP Server原始异常信息泄露内部架构 |

**综合评分: 45/100 — 基础防线在，但MCP Server是敞开的后门**

---

## 第一章：铁律逐条审查

### 铁律 I：私钥永远不进入可传播媒介 — ✅ 合规

```
✅ 无.py/.js文件中发现硬编码私钥
✅ 无.git目录中发现私钥文件
✅ .gitignore包含: .env, *.key, *.pem, .wallet, *secret*, *private*key*
✅ api_keys.json已在.gitignore中
✅ USDC Listener明确标注"只读监听，不需要私钥"
```

**⚠️ 但需注意**: 两个钱包接收地址（0x87d6...旧, 0x349E...新）出现在git history中39处。这些是**公开接收地址**（类似银行IBAN），不是私钥，不构成铁律I违反。但旧钱包已正确标记为DECOMMISSIONED并废弃。

### 铁律 II：暴露即死亡 — ⚠️ 部分合规

```
✅ 旧钱包 0x87d6C8... 已废弃，代码中已全部替换为新钱包
✅ 代码中无"0x87d6C8..."的活跃引用
⚠️ 旧钱包地址永久存在于git history中（无法删除，除非rewrite history）
⚠️ 新钱包 0x349Eea... 也已在git history中公开
```

**判定**: 接收地址公开 ≠ 私钥暴露。接收地址本身就是设计为公开的（用户需要知道往哪里付款）。铁律II不触发。但建议在文档中明确标注旧钱包已废弃。

### 铁律 III：SECRET.md永远不上传项目空间 — ✅ 合规

```
✅ SECRET.md仅在Agent工作目录 (/app/data/所有对话/主对话/SECRET.md)
✅ 项目空间 (Project ID: 7658139600313139471) 中无敏感文件
✅ .gh/hosts.yml权限600, .mcp_publisher_token权限600
```

### 铁律 IV：Git推送前的安全检查 — ⚠️ 未制度化

```
✅ .gitignore覆盖全面
⚠️ 无pre-commit hook安装（宪法2.3推荐但未执行）
⚠️ 无gitleaks配置
✅ 本次审计未发现实际泄露
```

---

## 第二章：MCP Server — 🔴 严重安全缺陷

这是本次审计发现的**最严重问题**。MCP Server作为公网可达的服务端点，几乎没有任何安全控制。

### 2.1 零认证 — 🔴 CRITICAL

```python
# mcp_http_server.py 中无任何auth/token/api_key检查
# 任何人知道Cloudflare Tunnel URL即可调用全部6个工具
# 对比：API Server有rate_limiter + KeyManager + 输入白名单
```

**风险**: MCP Server直接调用本地API（`http://127.0.0.1:8890`），完全绕过API的付费门控。任何MCP客户端（Claude Desktop、Cursor等）连接后，等于获得了无限免费API访问。

**宪法映射**: 违反第一章（凭证生命周期）— 服务暴露无凭证保护；违反第三章（资金安全）— 绕过付费机制。

### 2.2 零速率限制 — 🔴 CRITICAL

```python
# MCP Server无任何rate limiting
# API Server有: RateLimiter(max_requests=10, window_seconds=60)
# MCP Server: 无
```

**风险**: 单IP可无限调用`get_multi_market_comparison`（每次触发3次API调用），形成资源耗尽攻击。

### 2.3 零输入校验 — 🟠 HIGH

```python
# MCP Server的market参数仅做.upper()，无白名单校验
async def get_bde_score(market: str = "ALL") -> str:
    result = await call_bde_api("/api/snapshot", {"market": market.upper()})
    # market可以是任何字符串，直接传递给API

# symbol参数无任何校验
async def get_stock_analysis(symbol: str, market: str = "US") -> str:
    result = await call_bde_api("/api/analyze", {"symbol": symbol.upper(), ...})
    # symbol可以是任意字符串
```

**对比**: API Server有 `VALID_MARKETS` 白名单 + 详细校验。

### 2.4 错误信息泄露 — 🟠 HIGH

```python
async def call_bde_api(endpoint, params=None):
    except Exception as e:
        return {"error": str(e)}  # 原始异常信息直接返回
```

**实测**: 传入`symbol="INVALID;;;DROP TABLE"`时，MCP Server返回完整25支股票数据（API忽略了无效输入），但如果有其他错误，`str(e)`可能泄露内部路径、数据库结构、堆栈信息。

### 2.5 零审计日志 — 🟠 HIGH

```python
# MCP Server唯一一条日志：
print("Starting BDE Score MCP Server (streamable-http) on port 8891...")
# 无工具调用记录、无IP记录、无错误记录
```

**宪法映射**: 违反第四章（应急响应）— 无法事后溯源。

### 2.6 DNS Rebinding Protection已禁用 — 🟡 MEDIUM

```python
security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=False  # 必须禁用，否则Cloudflare Tunnel无法工作
)
```

**判定**: 这是Cloudflare Tunnel架构的固有约束，非设计缺陷。但应在文档中明确说明。

---

## 第三章：API Server — ✅ 基础防线健全

### 3.1 认证体系 — ✅ 良好

```
✅ RateLimiter: 10 requests/IP/minute
✅ KeyManager: bcrypt(cost=12) 哈希存储，明文key仅生成时返回一次
✅ Free quota: 3次/天/IP
✅ /api/keys/generate: 仅允许127.0.0.1调用（403 for external）
✅ /api/analyze: 输入白名单(VALID_MARKETS) + 并发锁 + 冷却期
```

### 3.2 安全响应头 — ✅ 全面

```
✅ X-Content-Type-Options: nosniff
✅ X-XSS-Protection: 1; mode=block
✅ Referrer-Policy: strict-origin-when-cross-origin
✅ Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
✅ X-Frame-Options: DENY（除widget/embed外）
✅ Cache-Control: no-store, no-cache
```

### 3.3 CORS白名单 — ✅ 合理

```python
allowed_origins = {
    "https://hbhqq9.github.io",           # GitHub Pages
    "https://atlantic-remains-atomic-floor.trycloudflare.com",  # API Tunnel
    "http://localhost:8890",
    "http://127.0.0.1:8890",
}
# /widget和/embed允许任意来源（零账号分发机制，设计如此）
```

### 3.4 需修正项 — ⚠️

```
⚠️ Privacy Policy声明"No IP addresses collected"，但RateLimiter和FreeQuota实际读取IP
   → 需修正Privacy Policy或修改实现
⚠️ /api/analyze返回完整数据，含内部discover字段（neurobridge/ipo_compliance链接）
   → 非安全问题，但暴露了项目关联信息
```

---

## 第四章：网络边界与暴露面

### 4.1 端口暴露检查

```
✅ 127.0.0.1:8890 — BDE API（仅本地）
✅ 127.0.0.1:8891 — MCP Server（仅本地）
✅ 127.0.0.1:20241/20242/20243 — Cloudflare Tunnel内部
✅ 127.0.0.1:5900 — Xvnc（VNC，仅本地）
✅ 127.0.0.1:22222 — FutuOpenD（仅本地）
✅ 127.0.0.1:11111 — FutuOpenD（仅本地）
⚠️ 0.0.0.0:9000 — Coze平台服务（非BDE代码，平台管控）
⚠️ 0.0.0.0:22 — SSH（容器标准，平台管控）
```

**判定**: BDE自身服务的网络隔离做得好。所有业务端口绑定127.0.0.1，仅通过Cloudflare Tunnel暴露。

### 4.2 Cloudflare Tunnel安全

```
✅ Tunnel URL → localhost:8890/8891（仅本地端口）
✅ TLS由Cloudflare终结（HTTPS端到端）
⚠️ Tunnel URL临时性：每次重启URL变化
   → server.json中的URL会在Tunnel重启后失效
   → 可能被利用进行URL接管（概率极低）
```

---

## 第五章：凭证与密钥管理

### 5.1 API Key管理 — ✅ 良好

```
✅ bcrypt哈希存储（cost=12）
✅ 自动迁移旧版明文格式
✅ key_prefix前8位快速识别
✅ tier分级（free/premium/institutional）
✅ revoke机制（按prefix撤销）
```

### 5.2 文件权限

```
✅ .gh/hosts.yml → 600 (rw-------)
✅ .mcp_publisher_token → 600 (rw-------)
✅ .ssh/deploy_key → 未找到文件（可能路径不同）
⚠️ mcp/目录下所有文件 → 777 (rwxrwxrwx) — 权限过宽
```

### 5.3 环境变量

```
⚠️ 多个API Key在环境变量中（GEMINI_API_KEY, OPENAI_API_KEY等）
   → 这是Coze平台注入的，非BDE代码问题
   → 但BDE进程可读取这些变量
✅ BDE_WALLET_ADDRESS可通过环境变量覆盖（有硬编码fallback）
```

---

## 第六章：隐私合规一致性

### 6.1 Privacy Policy与实际实现的矛盾

```
Privacy Policy声称:
  ❌ "No IP addresses, user agents, or session data collected"
  
实际实现:
  ✅ RateLimiter读取client_ip（用于限流，非持久存储）
  ✅ KeyManager._free_usage按IP追踪每日配额
  ✅ SecurityHeadersMiddleware读取Origin header（用于CORS判断）
```

**建议**: 修改Privacy Policy措辞为"IP addresses are read for rate limiting purposes but not persisted or stored"。

---

## 第七章：缺失的安全机制（宪法要求但未实现）

| 宪法要求 | 当前状态 | 差距 |
|----------|----------|------|
| Pre-commit安全检查 (§2.3) | ❌ 未安装 | 无gitleaks hook |
| 审计日志 (§4.1) | ❌ 无 | MCP/API均无结构化审计日志 |
| 请求追踪 (§4.1) | ❌ 无 | 无X-Request-ID |
| 凭证轮转 (§1.3) | ❌ 无 | Registry token/API Key无自动轮转 |
| 应急响应 (§4) | ❌ 无 | 无安全事件响应流程文档 |
| 安全审计自检 (§5.2) | ⚠️ 本次是首次 | 应定期执行 |
| 废弃清单 (§1.4) | ⚠️ 非正式 | 旧钱包废弃但未记录到正式清单 |

---

## 风险等级汇总

| # | 风险项 | 等级 | 铁律映射 |
|---|--------|------|----------|
| 1 | MCP Server零认证 | 🔴 CRITICAL | §1 凭证管理 |
| 2 | MCP Server零速率限制 | 🔴 CRITICAL | §3 资金安全（绕过付费） |
| 3 | MCP Server零输入校验 | 🟠 HIGH | §2 代码安全 |
| 4 | MCP Server错误信息泄露 | 🟠 HIGH | §2 公开仓库零信任 |
| 5 | MCP Server零审计日志 | 🟠 HIGH | §4 应急响应 |
| 6 | MCP文件权限777 | 🟠 HIGH | §2 代码安全 |
| 7 | Privacy Policy与实现不一致 | 🟡 MEDIUM | 合规 |
| 8 | 无pre-commit hook | 🟡 MEDIUM | §2.3 |
| 9 | 无请求追踪机制 | 🟡 MEDIUM | §4.1 |
| 10 | 硬编码钱包地址fallback | 🟡 MEDIUM | §1.1 生成规范 |
| 11 | 无凭证自动轮转 | 🟢 LOW | §1.3 |
| 12 | 无正式废弃清单 | 🟢 LOW | §1.4 |

---

*本报告基于2026-07-11 20:55 UTC+8的代码快照。所有发现均经过实际代码验证。*
*审计方法论: 静态代码分析 + 运行时探测 + 宪法条款逐项对照。*
