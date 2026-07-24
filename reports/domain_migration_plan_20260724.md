# BDE Score 永久域名迁移计划
**Created**: 2026-07-24 06:55 UTC  
**Status**: 执行中（dpdns.org域名注册进行中）

## 问题诊断

### 根因：Cloudflare Quick Tunnel URL漂移
- Quick Tunnel每次重启生成随机URL
- 导致MCP Registry/Glama/所有外部链接全部失效
- 已观察到URL每12-24小时变化一次

### 影响链
```
Tunnel URL漂移 → MCP Registry URL失效 → Glama无法连接 → Unhealthy
                                          → punkpeye PR无法merge（需Glama评分）
                                          → 所有外部MCP客户端无法连接
```

### Glama Unhealthy具体原因
1. MCP Registry v1.27.0 指向 `consolidated-survey-gamma-arrival.trycloudflare.com`（已死）
2. Glama最后测试 2026-07-23 09:34 UTC → 连接失败 → 标记Unhealthy
3. x402支付中间件对无body的POST返回402（已确认initialize方法可正常通过）
4. Tool Definition Quality实际为A（4.2/5.0）— 质量很高

### MCP Registry现状
- v1.27.0 (isLatest=true) → URL已死
- v1.27.1 已准备好但token过期未发布
- mcp-publisher Device Flow等待中（code: D678-7482, PID 518595）

## 迁移方案

### Phase 1: 域名注册 ✅ 进行中
- **平台**: dpdns.org (DigitalPlat FreeDomain)
- **目标域名**: `bde-score.dpdns.org`
- **认证**: GitHub OAuth (hbhqq9)
- **优势**: 免费、PSL认证、支持Cloudflare、支持NS/CNAME/MX/TXT

### Phase 2: Cloudflare配置 ⏳ 等待Phase 1
1. 注册/登录Cloudflare账号
2. 添加 `bde-score.dpdns.org` 到Cloudflare
3. 将Cloudflare给的NS地址填回dpdns.org管理面板
4. 等待DNS传播（几分钟到几小时）
5. `cloudflared login` → 获取cert.pem
6. `cloudflared tunnel create bde-score` → 获取TUNNEL_ID
7. 创建配置文件 `~/.cloudflared/config.yml`
8. 设置DNS路由：
   - `api.bde-score.dpdns.org` → CNAME → TUNNEL_ID.cfargotunnel.com
   - `mcp.bde-score.dpdns.org` → CNAME → TUNNEL_ID.cfargotunnel.com
   - `bde-score.dpdns.org` → CNAME → TUNNEL_ID.cfargotunnel.com
9. 启动命名隧道，停掉旧的quick tunnel进程

### Phase 3: 服务切换 ⏳ 等待Phase 2
1. 验证新域名所有端点可达
2. 更新 server.json → v1.28.0 + 新域名URL
3. 更新 .well-known/glama.json（已创建，需在永久域名下可达）
4. 更新 Landing Page 链接
5. 更新所有引用旧URL的文件
6. Git push

### Phase 4: 外部服务更新 ⏳ 等待Phase 3
1. **MCP Registry**: mcp-publisher login + publish v1.28.0（新域名URL）
2. **Glama**: 
   - 确认 `/.well-known/glama.json` 在新域名可达
   - 在Glama页面请求重新测试
   - 验证从Unhealthy→Healthy
3. **punkpeye #10049**: 
   - 更新评论（Glama评分+新URL）
   - 等维护者merge

## 配置文件模板

### ~/.cloudflared/config.yml
```yaml
tunnel: bde-score
credentials-file: /root/.cloudflared/{TUNNEL_ID}.json
ingress:
  - hostname: api.bde-score.dpdns.org
    service: http://localhost:8890
  - hostname: mcp.bde-score.dpdns.org
    service: http://localhost:8891
  - hostname: bde-score.dpdns.org
    service: http://localhost:8888
  - service: http_status:404
```

### server.json (v1.28.0)
```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.hbhqq9/bde-score",
  "description": "7-factor stock scoring MCP server. US/HK/CN, 74 stocks. Free + Premium (USDC/Base). x402 ready.",
  "version": "1.28.0",
  "remotes": [
    {
      "type": "streamable-http",
      "url": "https://mcp.bde-score.dpdns.org/mcp"
    }
  ],
  "repository": {
    "url": "https://github.com/hbhqq9/bde-score",
    "source": "github"
  }
}
```

## 当前运行服务（切换时需保留）
- REST API: PID 431405, 端口 8890
- MCP Server: PID 461842, 端口 8891 (含AcceptFixMiddleware + x402)
- USDC Listener: PID 431423
- Landing Server: PID 303613, 端口 8888 (python3 -m http.server, cwd: web-serve/)
- Cloudflare Quick Tunnels: 4个进程（切换后kill并替换为命名隧道）

## 备份方案
如果dpdns.org注册失败：
1. DuckDNS.org → `bde-score.duckdns.org`（免费，无需OAuth，但只能设A记录）
2. us.kg → dpdns.org的前身
3. is-a.dev → 需GitHub PR，审批周期长
4. freedesktop.org → 非PSL，不推荐

## 风险
- dpdns.org需要每年手动续期（到期前180天内点击续期）
- Cloudflare命名隧道绑定账号，账号丢失=隧道丢失
- 域名被dpdns.org回收（违规使用/忘记续期）
