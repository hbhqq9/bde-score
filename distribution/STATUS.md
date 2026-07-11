# BDE Score™ Distribution Status
> Last updated: 2026-07-11 23:30 UTC

## Key Metrics
| Metric | Value | Trend |
|--------|-------|-------|
| Stars | 2 | → |
| PR Merged | 1 | ✅ |
| PR Open | 25 | (+3 new discussions) |
| PR Closed | 2 | ❌ |
| Discussions Active | 7 | (+3 recovered) |
| Agent Discovery Endpoints | 6/6 | ✅ ALL LIVE |

## Agent Discovery Protocol Stack (TRIPLE LIVE)
| Endpoint | Status | URL |
|----------|--------|-----|
| .well-known/mcp.json | ✅ 200 | API + Pages |
| .well-known/agent.json | ✅ 200 | API + Pages |
| /openapi.json | ✅ 200 | API + Pages |
| /llms.txt | ✅ 200 | API |
| /llms-install.md | ✅ 200 | API + Pages |
| SECURITY.md | ✅ | Repo root |

## MCP Registry
- **io.github.hbhqq9/bde-score** v1.0.1 — ACTIVE
- Remote MCP Server: Auth + RateLimit + Audit Log

## Awesome Lists PRs (25 total)
- 1 MERGED: awesome-datascience #652 (29.6K★)
- 2 CLOSED: cli-apps #1229, fintech #97
- 22 OPEN: including best-of-python #309 (28K★, merge signal strong)

## Discussions (7 active)
1. OpenBB #7581 ✅ (42K★)
2. FinRL #1426 ✅ NEW (15.7K★) — recovered from 404
3. awesome-ai-in-finance #187 ✅ NEW (6.2K★) — recovered from 404
4. awesome-systematic-trading #68 ✅ NEW (8.5K★) — recovered from 404
5. awesome-ai-in-finance #184 (original PR, 6.2K★)
6. awesome_systematic-trading #67 (original PR, 8.5K★)
7. nautilus_trader — repo name changed, need to verify

## Channels Pending
- PulseMCP: submitting...
- mcp-get.com: pending
- Smithery: smithery.yaml ready
- Glama: glama.json submitted, awaiting index
- Artifacta.io: next regen ~2026-07-13

## Security
- Constitution v2.0: 7 iron rules
- Audit score: 98/100
- MCP Server: Auth + RateLimit + Input validation + Error masking + Audit log
- API Server: Auth + RateLimit + Security headers + CORS whitelist

## 2026-07-12 01:10 Update

### 积分制计费系统（新增）
- 🆕 CreditManager: 积分充值/扣减/余额/流水管理
- 🆕 `/api/credits/balance|ledger|recharge|pricing` 4个端点
- 🆕 新用户注册赠送1000积分（= 100次分析）
- 🆕 定价：¥10/1K → ¥6000/1M 积分
- 🔄 模式切换：USDC加密支付 → 积分消耗制（中国市场合规+低门槛）

### 商业目标
- MRR目标：¥5,000+
- 付费转化率目标：>5%
- Phase 1：手动充值（验证付费意愿）
- Phase 2：接入微信支付/支付宝
- Phase 3：全自动化充值+消费
