"""
BDE Score™ Auth Manager — 轻量级用户认证系统
=============================================
SQLite + httpOnly cookie session
安全: SHA256+salt密码哈希, httpOnly+SameSite cookie, 速率限制
"""
import os
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

USERS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

# In-memory session store: token -> {user_id, email, created_at, expires_at}
_sessions: Dict[str, dict] = {}
SESSION_TTL_HOURS = 72  # 3天

def _get_db():
    conn = sqlite3.connect(USERS_DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_auth_db():
    """初始化用户数据库"""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            tier TEXT DEFAULT 'free',
            credits_total INTEGER DEFAULT 1000,
            credits_used INTEGER DEFAULT 0,
            compliance_checks INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            eval_type TEXT NOT NULL,
            target TEXT,
            result_summary TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS sessions_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            ip TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()
    print(f"[Auth] DB initialized at {USERS_DB_PATH}")

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()

def register_user(email: str, password: str) -> dict:
    """注册用户，返回 {success, user_id, message}"""
    email = email.strip().lower()
    if not email or not password:
        return {"success": False, "message": "Email and password required"}
    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters"}
    if '@' not in email:
        return {"success": False, "message": "Invalid email format"}

    conn = _get_db()
    try:
        # Check if email already exists
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return {"success": False, "message": "Email already registered"}

        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)

        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, salt) VALUES (?, ?, ?)",
            (email, pw_hash, salt)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"success": True, "user_id": user_id, "message": "Registration successful"}
    except Exception as e:
        return {"success": False, "message": f"Registration failed: {str(e)}"}
    finally:
        conn.close()

def login_user(email: str, password: str) -> dict:
    """登录验证，返回 {success, user_id, email, message}"""
    email = email.strip().lower()
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, salt, tier, credits_total, credits_used, compliance_checks, is_active FROM users WHERE email=?",
            (email,)
        ).fetchone()
        if not row:
            return {"success": False, "message": "Invalid email or password"}

        user_id, db_email, pw_hash, salt, tier, credits_total, credits_used, compliance_checks, is_active = row
        if not is_active:
            return {"success": False, "message": "Account is deactivated"}

        if _hash_password(password, salt) != pw_hash:
            return {"success": False, "message": "Invalid email or password"}

        return {
            "success": True,
            "user_id": user_id,
            "email": db_email,
            "tier": tier,
            "credits_total": credits_total,
            "credits_used": credits_used,
            "compliance_checks": compliance_checks,
        }
    finally:
        conn.close()

def create_session(user_id: int, email: str, ip: str = "", user_agent: str = "") -> str:
    """创建session，返回token"""
    token = secrets.token_hex(32)
    _sessions[token] = {
        "user_id": user_id,
        "email": email,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS),
    }
    # Audit log
    conn = _get_db()
    try:
        conn.execute(
            "INSERT INTO sessions_audit (user_id, action, ip, user_agent) VALUES (?, 'login', ?, ?)",
            (user_id, ip, user_agent[:200])
        )
        conn.commit()
    finally:
        conn.close()
    return token

def validate_session(token: str) -> Optional[dict]:
    """验证session token，返回用户信息或None"""
    if not token:
        return None
    session = _sessions.get(token)
    if not session:
        return None
    if datetime.utcnow() > session["expires_at"]:
        del _sessions[token]
        return None
    return {"user_id": session["user_id"], "email": session["email"]}

def destroy_session(token: str):
    """销毁session"""
    if token in _sessions:
        user_id = _sessions[token]["user_id"]
        del _sessions[token]
        conn = _get_db()
        try:
            conn.execute(
                "INSERT INTO sessions_audit (user_id, action) VALUES (?, 'logout')",
                (user_id,)
            )
            conn.commit()
        finally:
            conn.close()

def get_user_info(user_id: int) -> Optional[dict]:
    """获取用户信息"""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT id, email, tier, credits_total, credits_used, compliance_checks, created_at FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "email": row[1], "tier": row[2],
            "credits_total": row[3], "credits_used": row[4],
            "compliance_checks": row[5], "created_at": row[6],
            "credits_remaining": row[3] - row[4],
        }
    finally:
        conn.close()

def record_evaluation(user_id: int, eval_type: str, target: str = "", result_summary: str = ""):
    """记录一次评估"""
    conn = _get_db()
    try:
        conn.execute(
            "INSERT INTO evaluations (user_id, eval_type, target, result_summary) VALUES (?, ?, ?, ?)",
            (user_id, eval_type, target, result_summary[:500])
        )
        if eval_type == "compliance":
            conn.execute("UPDATE users SET compliance_checks = compliance_checks + 1 WHERE id=?", (user_id,))
        elif eval_type == "analyze":
            conn.execute("UPDATE users SET credits_used = credits_used + 1 WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def check_eval_limit(user_id: int, eval_type: str) -> dict:
    """检查用户是否还有评估额度"""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT tier, credits_total, credits_used, compliance_checks FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return {"allowed": False, "reason": "User not found"}

        tier, credits_total, credits_used, compliance_checks = row

        if eval_type == "compliance":
            # Free: 3 compliance checks total for free tier
            limit = 3 if tier == "free" else 999999
            if compliance_checks >= limit:
                return {"allowed": False, "reason": f"Compliance check limit reached ({limit})",
                        "used": compliance_checks, "limit": limit}
            return {"allowed": True, "used": compliance_checks, "limit": limit, "remaining": limit - compliance_checks}

        elif eval_type == "analyze":
            remaining = credits_total - credits_used
            if remaining <= 0:
                return {"allowed": False, "reason": "No credits remaining",
                        "used": credits_used, "total": credits_total}
            return {"allowed": True, "used": credits_used, "total": credits_total, "remaining": remaining}

        return {"allowed": True}
    finally:
        conn.close()

# Initialize on import
init_auth_db()
