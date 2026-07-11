# BDE Score™ 安全审计报告

**审计范围:** `bde_api.py` (2503行) + 5个HTML模板  
**审计日期:** 2026年  
**审计人:** 自动化安全审计Agent  
**严重等级:** P0(远程可利用/立即修复) > P1(高危) > P2(中危) > P3(低危/加固建议)

---

## 审计总览

| 严重等级 | 数量 | 关键发现 |
|---------|------|---------|
| **P0** | 4 | 积分无限充值、SVG注入、iframe劫持、CDN无SRI |
| **P1** | 5 | tx_hash伪造、API Key存localStorage、管理端点IP绕过、缺少CSP、请求体无限制 |
| **P2** | 6 | 速率限制绕过、速率限制不全覆盖、SQLite并发锁、信息泄露、CORS白名单硬编码、OpenAPI暴露 |
| **P3** | 5 | 服务器版本暴露、钱包地址硬编码、无HSTS preload实际注册、日志泄露、依赖更新 |

---

## 🔴 P0 — 可远程利用，立即修复

### P0-1: 积分无限充值漏洞（支付绕过 — 可白嫖无限积分）

**位置:** `bde_api.py` `POST /api/credits/recharge` (约第1330行)

**漏洞:** 该端点允许任何持有API Key的用户**无限制地给自己充值任意数量的积分**，完全不需要支付验证！

```python
@app.post("/api/credits/recharge")
async def credits_recharge(
    request: Request,
    amount: int = Query(1000, description="充值积分数", ge=1),  # 无上限！
    auth: dict = Depends(optional_api_key)
):
    if not auth['authenticated'] or not auth.get('key_prefix'):
        raise HTTPException(status_code=401, ...)
    # 🔓 无任何支付验证！直接充值！
    credit_manager.recharge(auth['key_prefix'], amount, description=f"手动充值 {amount} 积分")
```

**攻击场景:**
```bash
# 任何有效API Key持有者可以无限充值
curl -X POST "https://target/api/credits/recharge?amount=999999999" \
     -H "X-API-Key: bde_xxxxx"
# 结果: 获得无限积分，绕过所有付费限制
```

**修复:**
```python
@app.post("/api/credits/recharge")
async def credits_recharge(
    request: Request,
    amount: int = Query(..., description="充值积分数", ge=1, le=1000000),  # 加上限
    auth: dict = Depends(optional_api_key)
):
    # 🔒 移除公开端点或要求管理员认证
    client_ip = request.client.host if request.client else "unknown"
    if client_ip not in ('127.0.0.1', '::1'):
        raise HTTPException(status_code=403, detail="Recharge requires admin access.")
    
    # 或者完全移除此端点，改用支付回调自动充值
    ...
```

---

### P0-2: SVG注入攻击（Stored XSS via `/share/`）

**位置:** `bde_api.py` `GET /share/{symbols}` → `_generate_share_svg()` (约第1050行)

**漏洞:** 虽然有正则校验 `^[A-Za-z0-9.,\-]+$`，但`title`变量中由用户输入构造的部分被直接拼接进SVG的`<text>`元素中，且SVG中未对特殊字符做XML转义。

```python
def _generate_share_svg(results, title):
    # title 来自 user input → symbols.upper()
    svg = f'''...
<text ...>📊 {title}</text>   # 🔓 未XML转义
...'''
    for i, r in enumerate(results):
        sym = r.get('symbol', '?')  # 来自数据库，但原始输入可绕过
        svg += f'''<text ...>{sym}</text>'''  # 🔓 symbol未转义
```

**攻击场景:** 虽然symbol有正则限制，但如果缓存数据中的symbol被污染（如通过恶意数据源），或未来放宽校验，`<`和`>`可注入SVG元素。此外SVG作为`image/svg+xml`返回，某些浏览器环境下可执行JavaScript。

**修复:**
```python
import html

def _generate_share_svg(results, title):
    safe_title = html.escape(title, quote=True)
    for i, r in enumerate(results):
        sym = html.escape(r.get('symbol', '?'))
        signal = html.escape(r.get('signal', ''))
        # ... 使用 safe_title, sym 代替原始值
```

---

### P0-3: Widget/Embed iframe可被恶网站劫持（Clickjacking + API Key窃取）

**位置:** `bde_api.py` SecurityHeadersMiddleware + `/widget` 端点

**漏洞:** Widget允许任意网站iframe嵌入（`X-Frame-Options: ALLOWALL` + `frame-ancestors *`），如果用户在widget中有任何交互功能（如API Key输入），恶意网站可通过CSS覆盖层实现点击劫持。

```python
if request.url.path in ('/widget', '/embed/snippet'):
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
```

**攻击场景:**
1. 恶意网站 `evil.com` 嵌入 `<iframe src="https://bde.app/widget">`
2. 通过透明覆盖层诱导用户点击
3. 如果widget未来添加API Key输入功能，可直接窃取

**修复:**
```python
# 使用CSP frame-ancestors限制允许的域名，而非 *
ALLOWED_EMBED_ORIGINS = [
    "https://hbhqq9.github.io",
    # 添加已知的嵌入方
]
# 在middleware中动态生成
csp_frames = " ".join(ALLOWED_EMBED_ORIGINS)
response.headers["Content-Security-Policy"] = f"frame-ancestors {csp_frames}"
```

---

### P0-4: 外部CDN加载无SRI完整性校验

**位置:** 
- `dashboard.html` line 8: `<script src="https://cdn.tailwindcss.com"></script>`
- `dashboard.html` line 9: `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>`
- `landing.html` line 8: `<script src="https://cdn.tailwindcss.com"></script>`
- `credit-payment.html`: 动态加载 `qrcode-generator`
- `payment.html`: 动态加载 `qrcode-generator`
- `pricing.html`: `<script src="https://cdn.tailwindcss.com"></script>`

**漏洞:** 所有外部CDN脚本均无`integrity`属性（SRI）。如果CDN被攻破或中间人攻击，恶意脚本可替换为窃取API Key、注入挖矿代码等。

**攻击场景:**
1. CDN `cdn.jsdelivr.net` 被攻破或DNS劫持
2. 恶意脚本替换 `chart.js`
3. 所有访问dashboard的用户被植入恶意代码
4. localStorage中的API Key被窃取

**修复:**
```html
<!-- 使用SRI hash -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
        integrity="sha384-_ACTUAL_HASH_HERE"
        crossorigin="anonymous"></script>

<!-- tailwindcss CDN 不支持SRI，建议自托管或使用固定版本的CDN -->
<script src="https://cdn.tailwindcss.com/3.4.1"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

> **注意:** `cdn.tailwindcss.com` 是一个动态脚本，会实时更新，无法使用SRI。建议替换为固定版本的 `tailwindcss` 或使用编译后的CSS。

---

## 🟠 P1 — 高危

### P1-1: USDC支付tx_hash可伪造/重放

**位置:** `bde_api.py` `POST /api/payment/verify` (约第1440行)

**漏洞:** tx_hash验证依赖`usdc_listener_instance.listener.verify_transaction()`，该方法需调用链上RPC验证。但如果`usdc_listener_instance`为None（支付系统未启动时），该端点直接返回错误但仍可被滥用。更严重的是：

1. **无tx_hash去重**: 同一个有效tx_hash可被多次提交
2. **金额校验不明确**: `verify_transaction`可能不检查金额是否匹配所选tier
3. **前端仅检查 `0x` + 长度 >= 60**: 无服务端格式严格校验

**攻击场景:**
```bash
# 1. 发送最小金额USDC（如$1）到钱包
# 2. 提交tx_hash，声称是$90 Standard套餐
# 3. 如果verify_transaction不严格校验金额，获得超额积分
```

**修复:**
```python
@app.post("/api/payment/verify")
async def verify_payment(request: Request):
    body = await request.json()
    tx_hash = body.get("tx_hash", "").strip()
    
    # 🔒 严格格式校验
    if not re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash):
        return {"error": "Invalid tx_hash format"}
    
    # 🔒 去重检查
    if usdc_activator_instance.get_payment_status(tx_hash=tx_hash):
        return {"error": "Transaction already processed"}
    
    # 🔒 链上验证（必须包含金额校验）
    verify_result = usdc_listener_instance.listener.verify_transaction(tx_hash)
    if verify_result.get('valid'):
        # 🔒 校验金额与声称的tier匹配
        expected_amount = TIERS_DATA.get(body.get('tier', 'starter'), {}).get('price', 0)
        actual_amount = verify_result.get('amount', 0)
        if abs(actual_amount - expected_amount) > 0.01:  # 允许微小浮点误差
            return {"error": f"Amount mismatch: expected {expected_amount}, got {actual_amount}"}
        ...
```

---

### P1-2: API Key存储在localStorage（XSS可直接窃取）

**位置:** `dashboard.html` JavaScript

```javascript
let boundApiKey = localStorage.getItem('bde_api_key') || null;
// ...
localStorage.setItem('bde_api_key', key);
```

**漏洞:** 如果发生任何XSS攻击（包括上述CDN被攻破场景），`localStorage`中的API Key可被直接读取并发送到攻击者服务器。

**修复建议:**
- 短期: 使用`sessionStorage`替代（关闭浏览器即清除）
- 长期: API Key仅通过后端HttpOnly Cookie传递，或使用短期token机制
- 添加CSP头限制脚本来源

---

### P1-3: 管理端点IP校验可通过Cloudflare绕过

**位置:** `bde_api.py` `/api/keys/generate`, `/api/keys/list`, `/api/keys/revoke`

```python
client_ip = request.client.host if request.client else "unknown"
if client_ip not in ('127.0.0.1', '::1'):
    raise HTTPException(status_code=403, detail="Forbidden. Internal use only.")
```

**漏洞:** 由于系统通过Cloudflare Tunnel暴露到公网，`request.client.host`实际上可能是Cloudflare代理的IP（如`127.0.0.1`）。如果Cloudflare Tunnel配置不当，外部请求可能被识别为来自`127.0.0.1`，从而绕过IP限制。

**修复:**
```python
# 🔒 使用专用管理员密钥或Bearer Token
ADMIN_TOKEN = os.environ.get('BDE_ADMIN_TOKEN')

async def require_admin(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or not ADMIN_TOKEN:
        raise HTTPException(status_code=403)
    if not secrets.compare_digest(auth_header[7:], ADMIN_TOKEN):
        raise HTTPException(status_code=403)
    return True

@app.post("/api/keys/generate")
async def generate_key(admin: bool = Depends(require_admin), ...):
```

---

### P1-4: 缺少Content-Security-Policy（全局CSP）

**位置:** `bde_api.py` SecurityHeadersMiddleware

**漏洞:** 仅在widget/embed路径设置了CSP（且为宽松的`frame-ancestors *`），其他HTML页面完全没有CSP头。

**修复:**
```python
# 在SecurityHeadersMiddleware中为所有HTML页面添加CSP
if response.headers.get('content-type', '').startswith('text/html'):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
```

---

### P1-5: 请求体无大小限制

**位置:** `bde_api.py` — 所有POST端点

**漏洞:** FastAPI默认无请求体大小限制。攻击者可发送超大JSON请求体消耗服务器内存。

**修复:**
```python
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 1_048_576:  # 1MB
            return JSONResponse(status_code=413, content={"error": "Request too large"})
        return await call_next(request)

app.add_middleware(BodySizeLimitMiddleware)
```

---

## 🟡 P2 — 中危

### P2-1: 速率限制可被绕过

**位置:** `bde_api.py` RateLimiter类

```python
client_ip = request.client.host if request.client else "unknown"
if not rate_limiter.is_allowed(client_ip):
```

**问题:**
1. **IP绕过**: 通过Cloudflare Tunnel，所有请求的`client.host`可能都是`127.0.0.1`，导致所有用户共享同一个速率限制桶，或Cloudflare的`X-Forwarded-For`被伪造
2. **内存泄漏**: `self.requests`字典永不清理历史数据，长时间运行会内存泄漏
3. **不覆盖所有端点**: `/api/history`、`/api/stock/unlock`、`/api/credits/*`等端点未加速率限制

**修复:**
```python
# 使用Cloudflare提供的真实IP
def get_real_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# 添加定期清理
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        ...
        self._last_cleanup = time.time()
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # 每10分钟清理一次过期数据
        if now - self._last_cleanup > 600:
            stale_keys = [k for k, v in self.requests.items() if not v]
            for k in stale_keys:
                del self.requests[k]
            self._last_cleanup = now
        ...
```

---

### P2-2: SQLite并发写入问题

**位置:** `bde_api.py` — 多处SQLite操作

**问题:**
1. `KeyManager._save()` 和 `CreditManager` 使用 `sqlite3.connect()` 无并发控制
2. 多个用户同时请求时可能出现 `database is locked` 错误
3. `api_keys.json` 文件的读写操作无文件锁

**修复:**
```python
# SQLite: 使用WAL模式 + 超时
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

# api_keys.json: 使用文件锁
import fcntl

def _save_with_lock(self):
    with open(self.keys_file + '.lock', 'w') as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(list(self.keys.values()), f, indent=2)
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
```

---

### P2-3: 错误响应泄露内部信息

**位置:** `bde_api.py` `credit_payment_page` 和 `payment_page`

```python
except Exception as e:
    return HTMLResponse(content=f"<h1>Credit payment page load failed</h1><p>{str(e)}</p>", status_code=500)
```

**漏洞:** 异常消息可能包含文件路径、数据库路径、环境变量等敏感信息。

**修复:**
```python
except Exception as e:
    logger.exception("Payment page error")
    return HTMLResponse(content="<h1>Service temporarily unavailable</h1>", status_code=500)
```

---

### P2-4: OpenAPI规范文件暴露完整API结构

**位置:** `bde_api.py` line 155

```python
openapi_url="/openapi.json",  # 🔓 Agent发现需要，端点本身受Auth保护
```

**问题:** 虽然注释说明是有意暴露，但`/openapi.json`暴露了完整的端点结构、参数类型、默认值，攻击者可据此精确构造攻击请求。

**修复:** 至少对管理端点（keys/generate, keys/list, keys/revoke, credits/recharge）在OpenAPI中隐藏：
```python
@app.post("/api/keys/generate", include_in_schema=False)
```

---

### P2-5: CORS白名单硬编码了临时URL

**位置:** `bde_api.py` SecurityHeadersMiddleware

```python
allowed_origins = {
    "https://hbhqq9.github.io",
    "https://atlantic-remains-atomic-floor.trycloudflare.com",  # 🔓 临时Tunnel URL!
    "http://localhost:8890",
    "http://127.0.0.1:8890",
}
```

**问题:** `trycloudflare.com` 临时URL会被回收并可被他人注册。如果该域名被重新分配给恶意用户，可以从该域名发起跨域请求。

**修复:** 使用环境变量管理CORS白名单，移除临时URL。

---

### P2-6: `/api/history` 端点缺少认证和速率限制

**位置:** `bde_api.py` `GET /api/history`

```python
@app.get("/api/history")
async def api_history(
    symbol: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365)
):
    # 🔓 无认证、无速率限制
```

**问题:** 任何人都可以无限制地查询历史数据，可被用来做数据爬取或DoS。

---

## 🔵 P3 — 低危/加固建议

### P3-1: 服务器版本信息暴露

**位置:** `bde_api.py` FastAPI配置

```python
app = FastAPI(
    title="BDE Score™ - AI Quantitative Analysis",
    version="1.0.0-mvp",
    ...
)
```

**建议:** 移除或混淆版本信息，禁用Server头。

```python
# 添加中间件移除Server头
class ServerHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.pop("server", None)
        return response
```

---

### P3-2: 钱包地址硬编码在源码中

**位置:** `bde_api.py` 多处

```python
wallet = os.environ.get('BDE_WALLET_ADDRESS', '0x349Eea0E2f4d3594797851758325Da3eb49D4343')
```

**问题:** 默认值硬编码了真实钱包地址。虽然通过环境变量覆盖是好的实践，但默认值暴露了生产地址。

---

### P3-3: `api_keys.json` 文件包含敏感元数据

**位置:** `KeyManager` 类

虽然key已使用bcrypt哈希，但`api_keys.json`中仍包含`key_prefix`、`email`、`created_at`、`last_used`等信息。该文件如被泄露，攻击者可获取所有用户的使用模式。

---

### P3-4: waitlist.json写入无速率限制外的保护

**位置:** `bde_api.py` `POST /api/waitlist`

```python
waitlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'waitlist.json')
```

**问题:** 虽然有速率限制和邮箱校验，但waitlist可无限增长（无上限检查），且文件写入无锁保护。

---

### P3-5: `lang` 参数未校验

**位置:** 多个模板端点

```python
@app.get("/credit-payment")
async def credit_payment_page(request: Request, tier: str = 'starter', lang: str = 'zh'):
```

**问题:** `lang`参数未做白名单校验（只接受zh/en/ja），虽然不会直接导致注入（因为是用于查字典），但应该加上校验：

```python
if lang not in ('zh', 'en', 'ja'):
    lang = 'zh'
```

---

## 📊 SQL注入检查总结

✅ **所有SQLite查询均使用参数化查询 (`?` 占位符)**，未发现f-string拼接SQL的情况。SQL注入风险：**低**。

关键SQL语句均使用 `(symbol, cutoff)` 等参数元组传递，`cursor.execute()` 的格式化安全。

---

## 📊 XSS检查总结

| 位置 | 风险 | 说明 |
|------|------|------|
| dashboard.html `renderTable()` | ⚠️ 中 | `r.symbol`通过`innerHTML`渲染，数据来自服务端API，但如果数据源被污染可触发XSS |
| dashboard.html `loadMarketStatus()` | ⚠️ 低 | 使用`innerHTML`渲染市场状态，数据来自内部API |
| credit-payment.html `setLang()` | ⚠️ 低 | `el.innerHTML = val`当值包含`<`时，但翻译字典是硬编码的 |
| landing.html | ✅ 安全 | 使用`textContent`而非`innerHTML` |

---

## 🔧 修复优先级排序

| 优先级 | 编号 | 漏洞 | 预计工时 |
|--------|------|------|---------|
| **1** | P0-1 | 积分无限充值 | 30分钟 |
| **2** | P0-4 | CDN无SRI | 1小时 |
| **3** | P1-3 | 管理端点IP绕过 | 1小时 |
| **4** | P1-4 | 缺少全局CSP | 1小时 |
| **5** | P1-1 | tx_hash伪造 | 2小时 |
| **6** | P1-5 | 请求体无限制 | 30分钟 |
| **7** | P0-2 | SVG注入 | 30分钟 |
| **8** | P0-3 | iframe劫持 | 1小时 |
| **9** | P1-2 | localStorage存Key | 2小时 |
| **10** | P2-1 | 速率限制绕过 | 2小时 |
| **11** | P2-2 | SQLite并发 | 1小时 |
| **12** | P2-3 | 错误信息泄露 | 30分钟 |
| **13** | P2-4 | OpenAPI暴露 | 15分钟 |
| **14** | P2-5 | CORS临时URL | 15分钟 |
| **15** | P2-6 | history无认证 | 30分钟 |
| **16** | P3-* | 低危加固 | 2小时 |

---

## 🏗️ 架构级建议

1. **引入API网关层**: 在FastAPI前面加一层Nginx/Caddy，统一处理速率限制、请求大小限制、安全头
2. **实施最小权限原则**: `/api/credits/recharge`应删除或限制为内部调用
3. **密钥管理**: 使用Vault或环境变量管理所有密钥，禁止硬编码默认值
4. **监控与告警**: 添加异常充值、异常请求模式的监控
5. **安全审计日志**: 所有支付和管理操作记录到独立审计日志
6. **定期依赖审计**: 使用 `pip-audit` 和 `npm audit` 检查已知CVE

---

*报告结束 — 建议立即修复P0级漏洞，P1级在24小时内完成，P2级在1周内完成。*
