# BDE Score™ PC端全量穿透测试报告
日期：2026-07-15

## 测试结果汇总
| # | URL | 状态码 | 结果 | 问题 |
|---|-----|--------|------|------|
| 1 | / | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 2 | /pricing | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 3 | /dashboard | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 4 | /credit-payment | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 5 | /payment | 500 | FAIL | 页面加载失败，无法进行后续检查 || 6 | /compliance-check | 400 | FAIL | 缺少必填参数url，无法正常完成合规检查 || 7 | /widget | 503 | FAIL | 页面显示Temporarily unavailable，无法正常展示Widget || 8 | /registry | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 9 | /terms | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 10 | /privacy | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 11 | /compliance | 200 | PASS | 页面正常渲染，未发现JS错误、broken links及敏感信息泄露 || 12 | /api/health | 200 | PASS | 页面正常返回JSON响应，状态为healthy，未发现敏感信息泄露 || 13 | /api/credits/pricing | 200 | PASS | 页面正常返回JSON响应，包含积分定价信息，未发现敏感信息泄露 || 14 | /llms.txt | 200 | PASS | 页面正常返回AI发现协议内容，未发现敏感信息泄露 || 15 | /.well-known/mcp.json | 200 | PASS | 页面正常返回MCP发现JSON响应，未发现敏感信息泄露 || 16 | /.well-known/agent.json | 200 | PASS | 页面正常返回Agent发现JSON响应，未发现敏感信息泄露 || 17 | /robots.txt | 502 | FAIL | 页面返回Bad gateway错误，无法正常访问 || 18 | /api/badge | 200 | PASS | 页面正常返回Badge SVG相关JSON响应，未发现敏感信息泄露 || 19 | /qr-image | 200 | PASS | 页面正常返回QR码图片，未发现敏感信息泄露 || 20 | /api/v1/registry/agents | 200 | PASS | 页面正常返回Registry Agent列表JSON响应，未发现敏感信息泄露 || 21 | /pay/info | 200 | PASS | 页面正常返回x402支付信息JSON响应，未发现敏感信息泄露 || 22 | /pay/free | 200 | PASS | 页面正常返回免费额度状态JSON响应，未发现敏感信息泄露 |
## 发现的问题
1.  /payment页面加载失败，返回500错误
2.  /compliance-check页面缺少必填参数url，返回400错误
3.  /widget页面显示Temporarily unavailable，返回503错误
4.  /robots.txt页面返回502 Bad gateway错误

## 修复建议
1.  检查/payment页面的服务器配置和相关接口，排查加载失败原因
2.  访问/compliance-check页面时补充必填的url参数
3.  修复/widget页面的服务不可用问题
4.  排查/robots.txt页面的502错误原因，检查服务器和Cloudflare配置