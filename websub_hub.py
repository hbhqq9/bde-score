"""
BDE Score WebSub Hub — 零人工介入推送发现渠道
W3C WebSub (PubSubHubbub) 协议实现
P2 优先级：让 AI Agent 订阅 BDE Score 变更推送

端点:
  POST /hub/subscribe  — Agent 订阅主题
  POST /hub/unsubscribe — Agent 取消订阅
  POST /hub/publish    — 发布者推送更新（内部API）
  GET  /hub/health     — 健康检查
"""

import json
import time
import hmac
import hashlib
import logging
import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict

import aiohttp
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s [WebSub] %(message)s')
logger = logging.getLogger(__name__)

# --- 配置 ---
HOST = "127.0.0.1"
PORT = 8893
MAX_SUBSCRIBERS_PER_TOPIC = 100
MAX_TOPICS = 50
MAX_BODY_SIZE = 64 * 1024  # 64KB
SUBSCRIPTION_TTL = 86400 * 7  # 7天过期
HUB_SECRET = None  # 可选，用于 HMAC 签名推送

# 已知主题
VALID_TOPICS = {
    "bde:score:update",      # 评分变更
    "bde:stock:new",         # 新股票分析
    "bde:compliance:update", # 合规状态变更
    "bde:system:status",     # 系统状态变更
    "bde:registry:new_agent",# 新Agent注册
}

@dataclass
class Subscription:
    callback_url: str
    topic: str
    created_at: float
    expires_at: float
    lease_seconds: int = SUBSCRIPTION_TTL
    last_delivery: Optional[float] = None
    delivery_count: int = 0
    failure_count: int = 0

# --- 存储 ---
subscriptions: Dict[str, Dict[str, Subscription]] = defaultdict(dict)
# subscriptions[topic][callback_url] = Subscription

total_deliveries = 0
total_failures = 0
start_time = time.time()

# --- SSRF 防护 ---
def is_safe_url(url: str) -> bool:
    """防止订阅回调到内部网络"""
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('https', 'http'):
            return False
        hostname = parsed.hostname or ""
        # 禁止私有IP
        for prefix in ('127.', '10.', '172.16.', '192.168.', '169.254.', '0.', 'localhost', '::1'):
            if hostname.startswith(prefix) or hostname == prefix.rstrip('.'):
                return False
        return True
    except Exception:
        return False

# --- 认证 ---
API_KEY = None
def load_api_key():
    """复用BDE API的认证"""
    global API_KEY
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("BDE_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip()
                return
    # fallback
    API_KEY = "bde-websub-" + hashlib.sha256(b"bde-websub-hub").hexdigest()[:16]

def check_auth(request: web.Request) -> bool:
    """publish端点需要认证"""
    if request.path == "/hub/publish":
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return hmac.compare_digest(auth[7:], API_KEY or "")
        return False
    return True  # subscribe/unsubscribe 公开（有限速率）

# --- 速率限制 ---
rate_limit_tracker: Dict[str, list] = defaultdict(list)
def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    now = time.time()
    rate_limit_tracker[ip] = [t for t in rate_limit_tracker[ip] if now - t < window]
    if len(rate_limit_tracker[ip]) >= limit:
        return False
    rate_limit_tracker[ip].append(now)
    return True

# --- 路由 ---
async def handle_subscribe(request: web.Request):
    """处理订阅请求"""
    ip = request.remote or "unknown"
    if not check_rate_limit(f"{ip}:sub", limit=5, window=60):
        return web.json_response({"error": "rate_limit"}, status=429)
    
    try:
        if request.content_type == "application/json":
            data = await request.json()
        else:
            data = await request.post()
            data = dict(data)
    except Exception:
        return web.json_response({"error": "invalid_body"}, status=400)
    
    topic = data.get("hub.topic") or data.get("topic", "")
    callback = data.get("hub.callback") or data.get("callback", "")
    mode = data.get("hub.mode") or data.get("mode", "subscribe")
    lease = int(data.get("hub.lease_seconds") or SUBSCRIPTION_TTL)
    
    if mode != "subscribe":
        return web.json_response({"error": "unsupported_mode"}, status=400)
    if topic not in VALID_TOPICS:
        return web.json_response({"error": "unknown_topic", "valid_topics": list(VALID_TOPICS)}, status=400)
    if not callback or not is_safe_url(callback):
        return web.json_response({"error": "invalid_callback"}, status=400)
    
    # 检查主题容量
    if len(subscriptions[topic]) >= MAX_SUBSCRIBERS_PER_TOPIC:
        return web.json_response({"error": "topic_full"}, status=503)
    
    now = time.time()
    subscriptions[topic][callback] = Subscription(
        callback_url=callback,
        topic=topic,
        created_at=now,
        expires_at=now + lease,
        lease_seconds=lease,
    )
    
    logger.info(f"订阅成功: topic={topic}, callback={callback[:80]}")
    return web.json_response({
        "status": "accepted",
        "topic": topic,
        "lease_seconds": lease,
    }, status=202)

async def handle_unsubscribe(request: web.Request):
    """处理取消订阅"""
    ip = request.remote or "unknown"
    if not check_rate_limit(f"{ip}:sub", limit=5, window=60):
        return web.json_response({"error": "rate_limit"}, status=429)
    
    try:
        data = await request.json()
    except Exception:
        data = dict(await request.post())
    
    topic = data.get("hub.topic") or data.get("topic", "")
    callback = data.get("hub.callback") or data.get("callback", "")
    
    if topic in subscriptions and callback in subscriptions[topic]:
        del subscriptions[topic][callback]
        logger.info(f"取消订阅: topic={topic}, callback={callback[:80]}")
    
    return web.json_response({"status": "removed"}, status=202)

async def handle_publish(request: web.Request):
    """内部API：发布更新并推送给所有订阅者"""
    if not check_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid_json"}, status=400)
    
    topic = data.get("topic", "")
    content = data.get("content", {})
    
    if topic not in VALID_TOPICS:
        return web.json_response({"error": "unknown_topic"}, status=400)
    
    # 清理过期订阅
    now = time.time()
    expired = [cb for cb, sub in subscriptions[topic].items() if sub.expires_at < now]
    for cb in expired:
        del subscriptions[topic][cb]
    
    subs = list(subscriptions[topic].values())
    if not subs:
        return web.json_response({"status": "published", "delivered": 0})
    
    # 并行推送到所有订阅者
    global total_deliveries, total_failures
    delivered = 0
    headers = {
        "Content-Type": "application/json",
        "X-WebSub-Topic": topic,
        "X-WebSub-Hub": request.host,
    }
    if HUB_SECRET:
        signature = hmac.new(HUB_SECRET.encode(), json.dumps(content).encode(), hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={signature}"
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for sub in subs:
            tasks.append(deliver_to_subscriber(session, sub, topic, content, headers))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, bool) and r:
                delivered += 1
    
    total_deliveries += delivered
    logger.info(f"发布: topic={topic}, delivered={delivered}/{len(subs)}")
    
    return web.json_response({
        "status": "published",
        "delivered": delivered,
        "total_subscribers": len(subs),
    })

async def deliver_to_subscriber(session, sub: Subscription, topic: str, content: dict, headers: dict) -> bool:
    """推送到单个订阅者"""
    global total_failures
    try:
        async with session.post(
            sub.callback_url,
            json={"topic": topic, "content": content, "timestamp": time.time()},
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status < 300:
                sub.delivery_count += 1
                sub.last_delivery = time.time()
                return True
            else:
                sub.failure_count += 1
                total_failures += 1
                # 连续5次失败自动移除
                if sub.failure_count >= 5:
                    del subscriptions[sub.topic][sub.callback_url]
                    logger.warning(f"移除失败订阅: {sub.callback_url[:80]}")
                return False
    except Exception as e:
        sub.failure_count += 1
        total_failures += 1
        if sub.failure_count >= 5:
            del subscriptions[sub.topic][sub.callback_url]
        return False

async def handle_health(request: web.Request):
    """健康检查 + 统计"""
    total_subs = sum(len(v) for v in subscriptions.values())
    return web.json_response({
        "status": "healthy",
        "protocol": "W3C WebSub (PubSubHubbub)",
        "uptime_seconds": int(time.time() - start_time),
        "topics": {topic: len(subs) for topic, subs in subscriptions.items()},
        "total_subscriptions": total_subs,
        "total_deliveries": total_deliveries,
        "total_failures": total_failures,
    })

async def handle_discovery(request: web.Request):
    """WebSub 发现端点 - 返回 hub 信息"""
    return web.json_response({
        "hub_url": f"https://{request.host}/hub/subscribe",
        "topics": list(VALID_TOPICS),
        "protocol": "W3C WebSub",
        "spec": "https://www.w3.org/TR/websub/",
    })

# --- 安全头 ---
@web.middleware
async def security_headers(request: web.Request, handler):
    resp = await handler(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Cache-Control"] = "no-store"
    return resp

# --- 启动 ---
load_api_key()
app = web.Application(middlewares=[security_headers], client_max_size=MAX_BODY_SIZE)
app.router.add_post("/hub/subscribe", handle_subscribe)
app.router.add_post("/hub/unsubscribe", handle_unsubscribe)
app.router.add_post("/hub/publish", handle_publish)
app.router.add_get("/hub/health", handle_health)
app.router.add_get("/hub/discovery", handle_discovery)

if __name__ == "__main__":
    logger.info(f"WebSub Hub starting on {HOST}:{PORT}")
    logger.info(f"API Key loaded: {API_KEY[:8]}..." if API_KEY else "No API Key")
    web.run_app(app, host=HOST, port=PORT, access_log=None)
