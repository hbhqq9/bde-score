# BDE Score™ 公网部署指南

## 方案A：Railway（推荐，最快15分钟）

### 步骤

1. 注册 [Railway](https://railway.app) (GitHub登录)

2. 新建Project → Deploy from GitHub repo
   - 将BDE-Stock目录推送到GitHub仓库
   
3. 配置环境变量：
   ```
   BDE_API_HOST=0.0.0.0
   BDE_API_PORT=8890
   ```

4. Railway会自动检测Dockerfile并部署

5. 分配域名：Settings → Domains → Generate Domain
   - 获得类似 `https://bde-score.up.railway.app` 的公网URL

6. 访问 Dashboard：`https://bde-score.up.railway.app/`

### 注意
- Railway上没有FutuOpenD，会**自动降级到新浪JSONP数据源**
- 新浪数据源免费、无需登录、覆盖全部14只标的
- 如果后续需要Futu数据，需要在Railway服务器上安装FutuOpenD

### 费用
- Hobby Plan: $5/月（含$5免费额度）
- 预估月费：$5-10（轻量API服务）

---

## 方案B：Render（免费方案）

1. 注册 [Render](https://render.com)
2. 新建Web Service → 连接GitHub仓库
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python3 bde_api.py`
5. Free Tier可用（但会休眠，首次访问需等待30秒唤醒）

---

## 方案C：Vercel Serverless（最快，但需改造）

需要把FastAPI改造为Vercel serverless functions。适合纯前端+轻量API。
当前架构更适合Railway/Render这类支持长运行进程的平台。

---

## 部署后验证

```bash
# 健康检查
curl https://your-domain.com/api/health

# 运行分析
curl https://your-domain.com/api/analyze

# 查看Dashboard
open https://your-domain.com/
```

## 下一步：接入支付

部署到公网后，下一步是接入支付系统：
- 国际：Stripe（最快）
- 中国：微信支付/支付宝
- 需要：用户注册系统 + 订阅管理 + 付费墙

这部分预计4小时开发量。
