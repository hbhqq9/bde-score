#!/usr/bin/env python3
"""
BDE Score™ DNA 完整性校验脚本
==============================
独立运行，验证所有核心文件的 SHA-256 指纹是否与 SYSTEM_DNA_FULL.md 一致。

用法:
  python3 scripts/dna_verify.py                  # 校验全部
  python3 scripts/dna_verify.py --json            # JSON输出
  python3 scripts/dna_verify.py --file bde_api.py # 校验单个文件

返回码:
  0 = 全部通过
  1 = 部分文件不匹配
  2 = DNA文件缺失或解析失败
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

# 定位 BDE-Stock 根目录
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent  # BDE-Stock/

DNA_FILE = REPO_ROOT / "SYSTEM_DNA_FULL.md"

# 从 SYSTEM_DNA_FULL.md 解析 SHA-256 条目
def parse_dna_hashes():
    """从DNA文件中提取 SHA256(filename) = hash 条目"""
    if not DNA_FILE.exists():
        print(f"❌ DNA文件不存在: {DNA_FILE}", file=sys.stderr)
        sys.exit(2)
    
    content = DNA_FILE.read_text(encoding='utf-8')
    pattern = r'SHA256\(([^)]+)\)\s*=\s*([a-f0-9]{64})'
    matches = re.findall(pattern, content)
    
    hashes = {}
    for filepath, hashval in matches:
        # 跳过DNA文件自身的引用（自引用哈希会有偏移）
        if 'SYSTEM_DNA_FULL' in filepath:
            continue
        hashes[filepath.strip()] = hashval.strip()
    
    return hashes


def compute_sha256(filepath):
    """计算文件的 SHA-256"""
    full_path = REPO_ROOT / filepath
    if not full_path.exists():
        return None
    h = hashlib.sha256()
    with open(full_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_all(json_output=False, target_file=None):
    """校验所有或指定文件"""
    hashes = parse_dna_hashes()
    
    if not hashes:
        print("❌ DNA文件中未找到SHA-256条目", file=sys.stderr)
        sys.exit(2)
    
    results = []
    all_pass = True
    
    files_to_check = hashes.items()
    if target_file:
        files_to_check = [(k, v) for k, v in hashes.items() if target_file in k]
        if not files_to_check:
            print(f"❌ DNA中未找到匹配 '{target_file}' 的条目", file=sys.stderr)
            sys.exit(2)
    
    for filepath, expected_hash in files_to_check:
        actual_hash = compute_sha256(filepath)
        
        if actual_hash is None:
            status = "MISSING"
            all_pass = False
        elif actual_hash == expected_hash:
            status = "PASS"
        else:
            status = "TAMPERED"
            all_pass = False
        
        results.append({
            "file": filepath,
            "expected": expected_hash,
            "actual": actual_hash or "FILE_NOT_FOUND",
            "status": status,
        })
    
    if json_output:
        output = {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "dna_file": str(DNA_FILE),
            "total_files": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASS"),
            "failed": sum(1 for r in results if r["status"] != "PASS"),
            "all_pass": all_pass,
            "results": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n🧬 BDE Score™ DNA 完整性校验")
        print(f"   DNA文件: {DNA_FILE}")
        print(f"   校验时间: {__import__('datetime').datetime.now().isoformat()}")
        print(f"   {'─' * 60}")
        
        for r in results:
            icon = "✅" if r["status"] == "PASS" else "❌"
            print(f"   {icon} {r['file']:50s} [{r['status']}]")
            if r["status"] == "TAMPERED":
                print(f"      期望: {r['expected'][:16]}...")
                print(f"      实际: {r['actual'][:16]}...")
        
        print(f"   {'─' * 60}")
        passed = sum(1 for r in results if r["status"] == "PASS")
        total = len(results)
        
        if all_pass:
            print(f"   ✅ 全部通过 ({passed}/{total})")
        else:
            failed = total - passed
            print(f"   ❌ {failed} 个文件不通过 ({passed}/{total} 通过)")
            # 输出安全告警
            tampered = [r for r in results if r["status"] == "TAMPERED"]
            if tampered:
                print(f"\n   🚨 安全告警: 以下文件可能被篡改:")
                for r in tampered:
                    print(f"      → {r['file']}")
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    json_mode = "--json" in sys.argv
    target = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            target = sys.argv[idx + 1]
    
    exit_code = verify_all(json_output=json_mode, target_file=target)
    sys.exit(exit_code)
