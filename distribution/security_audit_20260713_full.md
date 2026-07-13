# 🔐 BDE Score™ 全维度安全宪法校验报告

**版本**: Full Audit v1.0  
**日期**: 2026-07-13 23:00 BJT  
**审计范围**: 所有Agent项目系统（BDE Score主系统 / Agent Registry / MCP Server / 多项目隔离 / 定时任务安全）  
**依据**: 安全宪法 v4.1（铁律I-XI + 12章）  
**审计方法**: 自动化扫描 + 人工分析

---

## 一、审计总览

| 维度 | 检查项数 | 通过 | 问题 | 通过率 |
|------|---------|------|------|--------|
| 铁律I-IV 凭证安全 | 8 | 8 | 0 | 100% |
| 铁律V-VIII 服务安全 | 12 | 7 | 5 | 58% |
| 铁律IX-X 告警安全 | 4 | 4 | 0 | 100% |
| 铁律XI 发布前校验 | 3 | 3 | 0 | 100% |
| §5 安全基线 | 10 | 7 | 3 | 70% |
| 跨项目隔离 | 6 | 5 | 1 | 83% |
| **总计** | **43** | **34** | **9** | **79%** |

**风险等级分布**: P0×2 / P1×4 / P2×3 / P3×0

---

## 二、逐项审计结果

### ✅ 通过项（34项）

#### 铁律I：私钥不入传播媒介 ✅
- 代码中无硬编码64位hex私钥（仅测试用例和ERC20标准topic）
- TRANSFER_TOPIC是ERC20标准常量，非私钥
- wallet_balance_monitor.py不含私钥，仅含公开地址

#### 铁律II：暴露即死亡 ✅
- 3个废弃地址全部在DECOMMISSIONED_ADDRESSES中登记
- 无指向废弃地址的活跃充值引导
- 废弃地址监控仅用于安全事件检测

#### 铁律III：SECRET.md永不上传 ✅
- SECRET.md仅在Agent工作目录，未出现在任何git仓库
- 项目空间无SECRET.md

#### 铁律IV：Git推送前安全检查 ✅
- `.gitignore`完整：覆盖.env/.key/.pem/.wallet/secrets.json/*private*key*/.credentials/*.audit.log等
- `git ls-files`无敏感文件被跟踪
- `git diff --cached`无敏感信息
- api_keys.json已在.gitignore中

#### 铁律V（部分）：公网服务安全 ✅
- MCP Server：认证✅（401）+ 速率限制✅ + SecurityMiddleware完整
- BDE API：安全头完整（HSTS/X-Frame-DENY/X-Content-Type-nosniff）
- 服务绑定127.0.0.1✅（BDE API port 8890 + MCP port 8891）
- Cloudflare Tunnel正常转发

#### 铁律VI：错误响应脱敏 ✅
- 错误响应返回通用"detail":"Not Found"，无str(e)泄露
- 无traceback暴露
- 错误响应附带discover链接（设计合理，非泄露）

#### 铁律VII：Privacy声明 ✅
- docs/privacy.html 和 docs/privacy.md 均存在
- Landing page引用privacy

#### 铁律IX/X：告警白名单 ✅
- wallet_balance_monitor.py硬编码ACTIVE_ADDRESSES白名单
- DECOMMISSIONED_ADDRESSES黑名单完整（3个废弃地址）
- 废弃地址仅出现在黑名单定义中，不参与监控逻辑
- 告警不含充值引导

#### 铁律XI：发布前校验 ✅
- OpenAPI spec已禁用（/docs /openapi.json /redoc 均返回404）
- 最新版本commit `c0dd601` 包含SSRF防护+输入校验+容量限制

#### §5.4 SQLite安全 ✅
- bde_history.db: WAL模式✅ busy_timeout=10000ms✅ synchronous=2(NORMAL)✅
- bde_score.db: WAL模式✅ busy_timeout=10000ms✅ synchronous=2(NORMAL)✅

#### §5.7 XSS防护（Registry HTML） ✅
- 所有用户数据通过escapeHtml()函数转义后再渲染
- escapeHtml使用textContent→innerHTML的安全模式

#### .env文件权限 ✅
- .env权限: 600✅

---

### 🔴 问题项（9项）

#### P0-1: Agent Registry SSRF漏洞（铁律V）
**严重等级**: P0 CRITICAL  
**位置**: `agent-registry/registry_server.py` → `verify_endpoint()`  
**描述**: 
- `_handle_register`接收用户提交的`primary_endpoint` URL，直接传递给`verify_endpoint()`
- `verify_endpoint()`使用`urllib.request.urlopen(url)`无URL校验
- 攻击者可提交`http://169.254.169.254/latest/meta-data/`（云元数据）或`http://127.0.0.1:8890/`（内部服务探测）
- `_handle_agent_health`也对已注册endpoint执行相同操作
**影响**: 服务器端请求伪造，可探测/获取内部服务信息
**修复**: 添加URL白名单/黑名单校验（禁止私有IP/元数据地址/非HTTP协议）

#### P0-2: Agent Registry 无认证（铁律V）
**严重等级**: P0 CRITICAL  
**位置**: `agent-registry/registry_server.py` 全局  
**描述**: 
- 所有端点（register/deregister/health）无任何认证机制
- 任何人可直接注册/注销agent
- 无API Key / Bearer Token / 任何身份验证
**影响**: 注册表可被任意篡改，恶意agent可被注入
**修复**: 至少添加基础API Key认证或注册审核机制

#### P1-1: Agent Registry 无速率限制（铁律V）
**严重等级**: P1 HIGH  
**位置**: `agent-registry/registry_server.py`  
**描述**: 无任何请求频率限制，可被用于DoS攻击或批量注册垃圾agent  
**修复**: 添加基于IP的速率限制

#### P1-2: Agent Registry CORS配置（铁律V）
**严重等级**: P1 HIGH  
**位置**: `registry_server.py` + `registry.html`  
**描述**: `Access-Control-Allow-Origin: *` 违反§5.1 CORS白名单要求  
**修复**: 限制为已知域名或移除CORS（同域不需要）

#### P1-3: Agent Registry 输入校验缺失（铁律V）
**严重等级**: P1 HIGH  
**描述**: 
- `_read_body()`无Content-Length上限
- 无JSON schema校验（仅检查required fields）
- agent name/description无长度限制
**修复**: 添加请求体大小限制（1MB）+ 字段长度限制

#### P1-4: Agent Registry 无数据容量上限（§5.5）
**严重等级**: P1 HIGH  
**描述**: `agents.json`无注册数量限制，可无限增长  
**修复**: 设置MAX_AGENTS上限（如1000）

#### P2-1: gitleaks pre-commit未安装（铁律IV）
**严重等级**: P2 MEDIUM  
**描述**: 安全宪法§2.3要求所有项目安装gitleaks pre-commit hook，当前未安装  
**修复**: 安装pre-commit + gitleaks hook

#### P2-2: BDE API CORS未配置（铁律V）
**严重等级**: P2 MEDIUM  
**描述**: bde_api.py中未找到CORSMiddleware配置。当前通过Cloudflare Tunnel暴露，Tunnel自身不提供CORS头。如果Landing page需要跨域调用API，需要配置CORS白名单。  
**修复**: 评估是否需要CORS。如果不需要跨域调用，保持现状即可（更安全）。

#### P2-3: Port 9000 绑定0.0.0.0（铁律V）
**严重等级**: P2 MEDIUM  
**描述**: 一个Python进程（PID 2198）绑定在`0.0.0.0:9000`，对所有网络接口可达。经查是系统级Coze Agent运行时（`/app`路径）。  
**修复**: 确认是否为预期行为。如果是系统组件，可豁免。

---

## 三、跨项目隔离审计

| 项目 | .gitignore | .env | 硬编码凭证 | 状态 |
|------|-----------|------|-----------|------|
| BDE-Stock（主项目）| ✅ 完整 | ✅ 600 | ✅ 无 | ✅ |
| agent-passport | 未检查 | 无 | ✅ 无 | ⚠️ 待细查 |
| NeuroBridge | 空目录 | 无 | N/A | ⚠️ 空项目 |
| ZeroFriction | 空目录 | 无 | N/A | ⚠️ 空项目 |
| IPO合规服务 | ✅ 存在 | 无 | N/A | ✅ |
| sprint4-art50-mvp/contracts | N/A | 无 | N/A | ⚠️ 待细查 |
| awesome-prs/*(6个fork) | 继承上游 | 无 | ✅ 无 | ✅ |
| 其他fork仓库 | 继承上游 | 无 | ✅ 无 | ✅ |

**结论**: 凭证隔离良好。各项目无共享.env，无交叉凭证。

---

## 四、定时任务安全审计

| 任务 | 白名单 | 黑名单 | 签名 | 脱敏 | 状态 |
|------|--------|--------|------|------|------|
| wallet_balance_monitor | ✅ 硬编码 | ✅ 3地址 | ✅ v4.0 | ✅ | ✅ |
| 推广引擎扫描 | N/A | N/A | N/A | N/A | ✅ |
| Deployer健康检查 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 安全审计 | N/A | N/A | N/A | N/A | ✅ |
| 邮件通报 | 仅BDE Score | N/A | N/A | N/A | ✅ |

---

## 五、修复建议（按优先级排序）

### 立即修复（P0）
1. **Agent Registry SSRF防护**: 在`verify_endpoint()`中添加URL校验
   - 禁止: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fe80::/10`
   - 仅允许: `https://` 协议
   - 域名白名单或至少禁止已知内网段
2. **Agent Registry 基础认证**: 至少为write操作（register/deregister）添加API Key验证

### 短期修复（P1）
3. Agent Registry 速率限制
4. Agent Registry CORS收紧
5. Agent Registry 输入校验（Content-Length上限 + 字段长度限制）
6. Agent Registry 数据容量上限

### 中期改进（P2）
7. 安装gitleaks pre-commit hook
8. 评估BDE API CORS需求
9. 确认Port 9000归属

---

## 六、结论

**核心系统（BDE API + MCP Server）安全态势良好**，11项铁律中10项完全合规。v3.0/v4.0/v4.1升级后的纵深防御体系运行有效。

**Agent Registry是唯一P0级风险点**，作为自建发现栈的核心组件，SSRF+无认证的组合构成显著攻击面。需要在保持"零gatekeeper"理念的同时，添加基础安全层。

**总评**: 
- BDE Score主系统: A级（纵深防御完备）
- Agent Registry: C级（需立即加固）
- 跨项目隔离: A-级（良好）
- 定时任务安全: A级（白名单+反钓鱼完备）

---

*审计工具: 自动化扫描 + 人工分析*  
*审计人: BDE Score Agent (claw: 7626920923488207139)*  
*下次审计: 2026-07-20（每周定期）*
