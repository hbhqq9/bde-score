# 🛡️ BDE Score™ 安全重塑方案
## 以《安全宪法》为蓝本的全栈安全加固

**版本**: 1.0  
**日期**: 2026-07-11  
**依据**: 安全审计报告（同日发布）  
**设计原则**: 防火墙式关爱 — 保护不依赖人的状态，让安全成为不可逆的结构  

---

## 加固清单：按优先级排序

### 🔴 P0 — 立即修复（MCP Server安全空白）

MCP Server是全栈最大缺口。它公网可达、零认证、零限制，直接绕过付费门控。

---

#### 加固1: MCP Server 认证层

**目标**: 每个MCP请求必须携带有效凭证  
**方案**: 三层认证（由松到紧，渐进部署）

```
Layer 1 — API Key Bearer Token（推荐立即部署）
  MCP Client → Header: Authorization: Bearer bde_xxxx
  MCP Server → 调用 KeyManager.verify() 验证
  无效key → 返回 JSON-RPC error code -32001

Layer 2 — 匿名降级模式（保持零账号可达性）
  无key请求 → 降级为free tier（3次/天/IP）
  仍然可用，但受限

Layer 3 — 可选的Premium通道
  持有premium/institutional key → 无限调用
```

**实现要点**:
```python
# mcp_http_server.py 新增
import hashlib
from datetime import datetime

# IP追踪（匿名降级用）
_anonymous_usage = {}  # {ip: {"date": "YYYY-MM-DD", "count": 0}}

async def authenticate_request(request) -> dict:
    """从MCP请求中提取并验证API Key"""
    # MCP协议通过HTTP header传递认证
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # 调用API的验证端点
        result = await call_bde_api("/api/keys/verify", {"key": token})
        if not result.get("error") and result.get("valid"):
            return {"authenticated": True, "tier": result.get("tier", "free")}
    
    # 匿名模式：检查免费配额
    client_ip = request.headers.get("X-Forwarded-For", "unknown")
    today = datetime.now().strftime("%Y-%m-%d")
    
    if client_ip not in _anonymous_usage:
        _anonymous_usage[client_ip] = {"date": today, "count": 0}
    
    usage = _anonymous_usage[client_ip]
    if usage["date"] != today:
        usage["date"] = today
        usage["count"] = 0
    
    if usage["count"] >= 3:
        return {"authenticated": False, "error": "Free quota exceeded (3/day). Provide API key."}
    
    usage["count"] += 1
    return {"authenticated": False, "tier": "anonymous", "remaining": 3 - usage["count"]}
```

---

#### 加固2: MCP Server 速率限制

**目标**: 防止资源耗尽攻击  
**方案**: 与API Server共享rate limiting逻辑

```python
# 每个API key的速率限制
_key_rate = {}  # {key_hash: [timestamps]}

# 匿名IP的速率限制（更严格）
_anon_rate = {}  # {ip: [timestamps]}

KEY_RATE_LIMIT = 30      # 认证用户: 30次/分钟
ANON_RATE_LIMIT = 5       # 匿名用户: 5次/分钟
WINDOW_SECONDS = 60

def check_rate_limit(identifier: str, is_authenticated: bool) -> bool:
    """返回True=允许, False=限流"""
    now = time.time()
    store = _key_rate if is_authenticated else _anon_rate
    limit = KEY_RATE_LIMIT if is_authenticated else ANON_RATE_LIMIT
    
    store[identifier] = [t for t in store.get(identifier, []) if now - t < WINDOW_SECONDS]
    if len(store[identifier]) >= limit:
        return False
    store[identifier].append(now)
    return True
```

---

#### 加固3: MCP Server 输入校验

**目标**: 白名单校验所有输入参数  
**方案**: 与API Server共享VALID_MARKETS等常量

```python
# 硬编码白名单（不依赖API Server的常量）
VALID_MARKETS = {"US", "HK", "CN", "ALL"}
VALID_SYMBOL_PATTERN = re.compile(r'^[A-Za-z0-9._\-]{1,20}$')

def validate_market(market: str) -> str:
    """校验market参数，返回规范化值或抛异常"""
    m = market.upper().strip()
    if m not in VALID_MARKETS:
        raise ValueError(f"Invalid market. Must be one of: {', '.join(sorted(VALID_MARKETS))}")
    return m

def validate_symbol(symbol: str) -> str:
    """校验symbol参数，拒绝注入"""
    s = symbol.upper().strip()
    if not VALID_SYMBOL_PATTERN.match(s):
        raise ValueError(f"Invalid symbol format: {s[:20]}")
    return s
```

---

#### 加固4: MCP Server 错误信息脱敏

**目标**: 不泄露内部架构信息  
**方案**: 统一错误响应格式

```python
# 替换所有 str(e) 的直接返回
class SafeError(Exception):
    """安全错误：用户可见的错误消息"""
    pass

async def call_bde_api_safe(endpoint: str, params: dict = None) -> dict:
    """安全版API调用：脱敏错误信息"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if params:
                resp = await client.get(f"{BDE_API_BASE}{endpoint}", params=params)
            else:
                resp = await client.get(f"{BDE_API_BASE}{endpoint}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            # HTTP错误：返回状态码和通用描述
            return {"error": f"Service temporarily unavailable (HTTP {e.response.status_code})"}
        except httpx.TimeoutException:
            return {"error": "Request timed out. Please try again."}
        except Exception:
            # 其他错误：只返回通用消息，内部信息记录到日志
            logging.error(f"Internal error calling {endpoint}: {traceback.format_exc()}")
            return {"error": "An internal error occurred. Please try again later."}
```

---

#### 加固5: MCP Server 审计日志

**目标**: 每次工具调用留痕，支持事后溯源  
**方案**: 结构化JSON日志

```python
import logging
import uuid

# 配置审计日志
audit_logger = logging.getLogger("bde_audit")
handler = logging.FileHandler("mcp_audit.log")
handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(handler)
audit_logger.setLevel(logging.INFO)

def audit_log(tool_name: str, client_ip: str, authenticated: bool, 
              tier: str, params: dict, success: bool, duration_ms: float):
    """记录每次工具调用"""
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "request_id": str(uuid.uuid4())[:8],
        "tool": tool_name,
        "ip": client_ip,
        "auth": authenticated,
        "tier": tier,
        "params": {k: v for k, v in params.items() if k != "api_key"},
        "success": success,
        "duration_ms": round(duration_ms, 1),
    }
    audit_logger.info(json.dumps(entry))
```

---

### 🟠 P1 — 72小时内修复

---

#### 加固6: API Key验证端点

**目标**: 为MCP Server认证提供后端支持  
**方案**: 新增 `/api/keys/verify` 端点

```python
@app.get("/api/keys/verify")
async def verify_key(key: str = Query(..., description="API Key to verify")):
    """验证API Key是否有效（供MCP Server内部调用）"""
    # 仅允许本地调用
    # 返回: {valid: bool, tier: str, email: str|null}
    entry = key_manager._find_by_key(key)
    if entry and entry.get("active", True):
        return {"valid": True, "tier": entry.get("tier", "free"), "email": entry.get("email")}
    return {"valid": False}
```

---

#### 加固7: MCP文件权限收紧

**目标**: 消除777权限风险  
**方案**: `chmod 644` 所有MCP Python文件

```bash
chmod 644 mcp/*.py
chmod 755 mcp/
```

---

#### 加固8: Pre-commit Hook 安装

**目标**: 防止凭证意外提交  
**方案**: 安装gitleaks pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

---

#### 加固9: Privacy Policy 修正

**目标**: 消除Privacy Policy与实际实现的矛盾  
**修改**: 
```
原文: "No IP addresses, user agents, or session data collected"
改为: "IP addresses are read transiently for rate limiting purposes only. 
       They are never persisted, stored, or shared with third parties."
```

---

### 🟡 P2 — 一周内完成

---

#### 加固10: 请求追踪（X-Request-ID）

**目标**: 每个请求有唯一标识，贯穿API和MCP  
**方案**:
```python
# API Server middleware 生成 request_id
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

#### 加固11: 硬编码钱包地址 → 环境变量强制

**目标**: 消除代码中的硬编码地址  
**方案**:
```python
# 删除硬编码fallback，强制从环境变量读取
WALLET_ADDRESS = os.environ.get('BDE_WALLET_ADDRESS')
if not WALLET_ADDRESS:
    raise RuntimeError("BDE_WALLET_ADDRESS environment variable not set")
```

---

#### 加固12: 正式废弃清单

**目标**: 记录所有已废弃的凭证和地址  
**文件**: `docs/decommissioned.md`

```markdown
# Decommissioned Credentials & Addresses

| 类型 | 标识 | 废弃日期 | 原因 |
|------|------|----------|------|
| 收款钱包 | 0x87d6C8F71d89d7E1f17EcAB138EDfaAc19d9D2fE | 2026-07-10 | 安全审计：公开git history中的地址不宜继续使用 |
```

---

#### 加固13: Registry Token 自动轮转

**目标**: 防止Registry token过期导致发布中断  
**方案**: keepalive.sh中加入token刷新逻辑

---

## 架构图：加固后的请求流

```
┌──────────────────────────────────────────────────────────────┐
│                     Cloudflare Tunnel                         │
│              (TLS终结 + DDoS防护 + WAF可选)                    │
└──────────────┬──────────────────────────┬────────────────────┘
               │                          │
        ┌──────▼──────┐           ┌───────▼───────┐
        │  MCP :8891  │           │   API :8890   │
        │  新增安全层: │           │  已有安全层:   │
        │  ┌─────────┐│           │  ┌───────────┐│
        │  │Auth     ││           │  │Rate Limit ││
        │  │Layer    ││           │  │10/min/IP  ││
        │  ├─────────┤│           │  ├───────────┤│
        │  │Rate     ││           │  │API Key    ││
        │  │Limit    ││           │  │bcrypt     ││
        │  │30/min   ││           │  ├───────────┤│
        │  ├─────────┤│           │  │Input      ││
        │  │Input    ││           │  │Whitelist  ││
        │  │Validate ││           │  ├───────────┤│
        │  ├─────────┤│           │  │Security   ││
        │  │Audit    ││           │  │Headers    ││
        │  │Log      ││           │  │CORS/HSTS  ││
        │  ├─────────┤│           │  └───────────┘│
        │  │SafeError││           │               │
        │  │Sanitize ││           │               │
        │  └─────────┘│           │               │
        └──────┬──────┘           └───────┬───────┘
               │                          │
               └──────────┬───────────────┘
                          │
                   ┌──────▼──────┐
                   │  127.0.0.1  │
                   │  内部通信    │
                   │  无外部暴露  │
                   └─────────────┘
```

---

## 执行计划

| 阶段 | 内容 | 时间 |
|------|------|------|
| Phase 1 | 加固1-5（MCP Server安全层） | 立即 |
| Phase 2 | 加固6-9（API补充+权限+Hook+Policy） | 72h内 |
| Phase 3 | 加固10-13（追踪+去硬编码+轮转） | 1周内 |
| Phase 4 | 安全审计复查 | 2周后 |

---

## 宪法传承：子Agent安全约束

所有 `sessions_spawn` 涉及BDE代码修改时，task中必须包含：

```
安全约束（不可跳过）:
1. 永远不在代码中硬编码私钥/密钥/密码
2. 所有新增端点必须有认证+速率限制+输入校验
3. 错误响应不得泄露内部路径/堆栈
4. 每次工具调用必须有审计日志
5. 新文件权限不高于644（代码）或600（凭证）
6. 修改后执行 git diff --cached | grep 安全检查
```

---

*安全不是目的地，是方向。反熵需设计，保护不依赖人的状态。*
