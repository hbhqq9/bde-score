# BDE Score™ 全链路穿透校验报告
**日期**: 2026-07-10 10:28
**校验人**: Agent（自主执行）

---

## 校验结论：✅ 全链路畅通，1项已修复

| Layer | 环节 | 状态 | 备注 |
|-------|------|------|------|
| L1 | FutuOpenD进程 | ✅ | PID运行中，端口11111可达 |
| L1 | BDE API服务 | ✅ | PID运行中，端口8890正常 |
| L1 | Bore隧道 | ✅ | 公网bore.pub:18502可达 |
| L1 | Cron守护 | ✅ | 每5分钟keepalive |
| L2 | Futu数据获取 | ✅ | 直连正常，市场状态OVERNIGHT |
| L2 | 美股(25只) | ✅ | FutuOpenD数据源，全量获取 |
| L2 | 港股(26只) | ✅ | FutuOpenD数据源，全量获取 |
| L2 | A股(23只) | ✅ 已修复 | 原9只→修复后23只全量（批量限速15只/秒） |
| L2 | 新浪备用通道 | ✅ | Futu限频时自动降级 |
| L3 | Dashboard HTML | ✅ | 15132 bytes，8个Tab，14处Chart组件 |
| L3 | API端点(/) | ✅ | HTTP 200 |
| L3 | API端点(/api/health) | ✅ | HTTP 200 |
| L3 | API端点(/api/snapshot) | ✅ | HTTP 200 |
| L3 | API端点(/api/market-status) | ✅ | HTTP 200 |
| L3 | API端点(/docs) | ✅ | HTTP 200 |
| L4 | SQLite历史存储 | ✅ | 310条记录，147456 bytes |
| L5 | 定时任务 | ✅ | UID: 1ef053b4, 周一至周五08:00 |
| L5 | 每日脚本 | ✅ | bde_unified_daily.py存在 |
| L6 | 飞书团队群 | ✅ | 已创建，简报已发送 |
| L6 | 独立钱包 | ✅ | Base链USDC收款地址已生成 |
| L7 | 白皮书 | ✅ | 480行/33KB |
| L7 | LinkedIn文案 | ✅ | 3版本就绪 |

---

## 发现并修复的问题

### 问题1：A股数据缺口（已修复）
- **现象**：23只A股仅9只成功分析
- **根因**：Futu API频率限制（60次/30秒），连续请求触发限流
- **修复**：在fetch_via_futu中添加批量限速（每15只暂停1秒）
- **验证**：修复后23只全量成功

### 问题2：bore隧道非永久（待处理）
- **现象**：bore.pub URL在进程重启后变化
- **影响**：Dashboard URL不稳定
- **方案**：需迁移到Railway/Fly.io正式部署（需用户手动完成GitHub OAuth）

### 问题3：cloudflared 429（不可修复，已绕过）
- **现象**：Cloudflare quick tunnel返回429限速
- **原因**：短时间内多次尝试触发IP级限流
- **处理**：已改用bore隧道替代

---

## 钱包决策说明

**决策**：为BDE-Stock创建独立钱包，不复用NeuroBridge AGL项目钱包

**理由**：
1. **会计清晰**：两个项目商业模式不同（SaaS vs AI协议），收入来源不同
2. **法律隔离**：合规咨询业务需要独立的财务记录
3. **审计友好**：未来如有融资/审计需求，独立钱包更清晰
4. **成本极低**：Base链Gas费接近零，多一个EOA无成本

**钱包信息**：
- 地址: 0x87d6C8F71d89d7E1f17EcAB138EDfaAc19d9D2fE
- 链: Base Mainnet (8453)
- 用途: USDC收款（SaaS订阅 + 合规咨询费）

---

## 下一步行动

| 优先级 | 任务 | 负责 | 截止 |
|--------|------|------|------|
| P0 | Railway正式部署（需用户OAuth） | 用户 | 本周 |
| P0 | LinkedIn Post 1&2发布 | Agent | 下周二 |
| P1 | 下周一08:00定时任务首次验证 | Agent-Alpha | 07-13 |
| P1 | 白皮书PDF排版 | Agent-Content | 07-15 |
| P2 | 标的池扩展到100+ | Agent-Alpha | 07-20 |
| P2 | 支付系统接入（Stripe/微信） | Agent | 部署后 |
