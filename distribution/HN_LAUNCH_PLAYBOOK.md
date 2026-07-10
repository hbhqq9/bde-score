# 🚀 Hacker News Launch Playbook

## 前置条件
- HN 账号已注册（见 MANUAL_REGISTRATION_GUIDE.md）

## 最佳发布时间
- **美西时间**: 周二-周四 上午 8-10 点（太平洋时间）
- **北京时间**: 周二-周四 晚上 23:00 - 次日 01:00
- **原因**: HN 流量高峰期，新帖曝光最大

## 标题（选一个）

### 推荐标题 1（技术向）
```
Show HN: BDE Score – Open-source EU AI Act Art.50 compliant stock scoring (74 stocks, 3 markets)
```

### 推荐标题 2（合规向）
```
Show HN: I built an open-source transparency scoring system for stocks to comply with EU AI Act Art.50
```

### 推荐标题 3（简洁）
```
Show HN: BDE Score – One score to compare stocks across US, HK, and A-share markets
```

## 正文内容

```
Hi HN,

I built BDE Score™, an open-source stock transparency scoring system that:

- Analyzes 74 stocks across US (25), HK (26), and A-share (23) markets
- Provides a single comparable score (0-100) using 5 explainable factors
- Fully complies with EU AI Act Article 50 transparency requirements
- Supports USDC payment on Base chain for premium API access

Tech stack:
- Python/Flask API with real-time data from FutuOpenD + Sina Finance
- Multi-factor scoring: Momentum, Mean Reversion, Volume, Volatility, Trend
- GitHub Action for automated analysis in your CI/CD
- GEO-optimized with llms.txt, FAQ Schema, robots.txt

Why I built it:
EU AI Act Art.50 requires AI systems providing investment recommendations to 
disclose their methodology. BDE Score™ makes this transparent by design.

Live demo: https://hbhqq9.github.io/bde-score/
GitHub: https://github.com/hbhqq9/bde-score
API: curl "https://atlantic-remains-atomic-floor.trycloudflare.com/api/analyze?market=ALL"

Happy to answer any questions!

*Technical service, not financial advice.*
```

## 发布步骤
1. 登录 https://news.ycombinator.com/submit
2. 粘贴 URL: https://github.com/hbhqq9/bde-score
3. 粘贴标题（选上面的推荐标题）
4. 在正文框粘贴上面的正文
5. 点击 Submit

## 发布后
- 前30分钟：积极回复每条评论（HN社区看重作者互动）
- 前2小时：监控点赞数，>50 就可能上首页
- 同步在 Twitter/Reddit 分享 HN 帖子链接

## 告诉我账号后我会做什么
1. ✅ 立即提交 Show HN 帖子
2. ✅ 在帖子下发布详细技术说明
3. ✅ 监控评论并准备回复
4. ✅ 同步提交 Reddit r/algorithms r/stocks r/technology
