"""
FutuOpenD 进程管理器
确保FutuOpenD在每日任务执行时处于运行状态
如果未运行则自动启动并等待Ready
"""

import subprocess
import time
import sys
import os
import re

FUTU_OPEND_DIR = os.path.expanduser('~/futu/opend/Futu_OpenD_10.8.6818_Ubuntu18.04/Futu_OpenD_10.8.6818_Ubuntu18.04')
FUTU_OPEND_BIN = os.path.join(FUTU_OPEND_DIR, 'FutuOpenD')
FUTU_RUNTIME_DIR = os.path.expanduser('~/.com.futunn.FutuOpenD')
MAX_WAIT = 30  # 最长等待30秒


def is_running():
    """检查FutuOpenD是否在运行"""
    result = subprocess.run(['pgrep', '-f', 'FutuOpenD'], capture_output=True, text=True)
    return result.returncode == 0


def is_ready():
    """检查FutuOpenD是否Ready（通过检查最新日志）"""
    log_dir = os.path.join(FUTU_RUNTIME_DIR, 'Log')
    if not os.path.exists(log_dir):
        return False
    
    # 找最新的GTW log
    logs = sorted([f for f in os.listdir(log_dir) if f.startswith('GTWLog_')], reverse=True)
    if not logs:
        return False
    
    latest_log = os.path.join(log_dir, logs[0])
    try:
        with open(latest_log, 'r', errors='ignore') as f:
            content = f.read()
            return 'ProgramStatusType_Ready' in content
    except:
        return False


def start():
    """启动FutuOpenD并等待Ready"""
    if is_running():
        if is_ready():
            print("✅ FutuOpenD已运行且Ready")
            return True
        else:
            print("⚠️ FutuOpenD在运行但未Ready，等待...")
            for i in range(MAX_WAIT):
                time.sleep(1)
                if is_ready():
                    print(f"✅ 等待{i+1}秒后Ready")
                    return True
            print("❌ 等待超时，重启...")
            stop()
    
    print("🚀 启动FutuOpenD...")
    os.makedirs(FUTU_RUNTIME_DIR, exist_ok=True)
    
    # 启动进程
    proc = subprocess.Popen(
        [FUTU_OPEND_BIN],
        cwd=FUTU_OPEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"  PID: {proc.pid}")
    
    # 等待Ready
    for i in range(MAX_WAIT):
        time.sleep(1)
        if is_ready():
            print(f"✅ FutuOpenD启动成功，等待{i+1}秒后Ready")
            return True
    
    print("❌ FutuOpenD启动超时")
    return False


def stop():
    """停止FutuOpenD"""
    subprocess.run(['pkill', '-f', 'FutuOpenD'], capture_output=True)
    time.sleep(2)
    print("🛑 FutuOpenD已停止")


def health_check():
    """健康检查"""
    if not is_running():
        return {"status": "DOWN", "message": "进程未运行"}
    
    if not is_ready():
        return {"status": "STARTING", "message": "进程运行中但未Ready"}
    
    # 测试API连接
    try:
        from futu import OpenQuoteContext, RET_OK
        ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = ctx.get_market_snapshot(['US.AAPL'])
        ctx.close()
        if ret == RET_OK:
            price = data.iloc[0]['last_price']
            return {"status": "HEALTHY", "message": f"API正常, AAPL=${price:.2f}"}
        else:
            return {"status": "DEGRADED", "message": f"API返回错误: {data}"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'ensure'
    
    if action == 'ensure':
        # 确保运行（每日任务前调用）
        success = start()
        sys.exit(0 if success else 1)
    elif action == 'status':
        result = health_check()
        print(f"状态: {result['status']} | {result['message']}")
    elif action == 'start':
        start()
    elif action == 'stop':
        stop()
    else:
        print("用法: python3 futu_opend_manager.py [ensure|start|stop|status]")
