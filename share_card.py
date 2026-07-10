#!/usr/bin/env python3
"""
BDE Score™ Share Card Generator
================================
零账号病毒式分发机制 — 生成精美的股票分数分享卡片（PNG）
用户截图/分享 → 自带品牌+URL → 每一次分享都是获客

用法:
  python3 share_card.py AAPL         # 生成单只股票卡片
  python3 share_card.py --top 5 US   # 生成Top 5排行卡片
"""

import sys
import os
import json
import urllib.request
from datetime import datetime

# API endpoint
API_BASE = "http://127.0.0.1:8890"

def fetch_snapshot(market="US"):
    """获取最新快照"""
    url = f"{API_BASE}/api/snapshot?market={market}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BDE-ShareCard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"API Error: {e}")
        return None

def generate_svg_card(results, title="BDE Score™", subtitle=""):
    """生成SVG卡片（无需PIL/matplotlib，纯文本渲染）"""
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    card_width = 540
    card_height = 80 + len(results) * 72 + 100
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="{card_width}" height="{card_height}" rx="16" fill="url(#bg)"/>
  
  <!-- Header -->
  <text x="24" y="36" font-family="system-ui,sans-serif" font-size="20" font-weight="700" fill="#f1f5f9">📊 {title}</text>
  <text x="24" y="56" font-family="system-ui,sans-serif" font-size="12" fill="#64748b">{subtitle} · {now}</text>
  
  <!-- Accent line -->
  <rect x="24" y="66" width="80" height="3" rx="1.5" fill="url(#accent)"/>
'''
    
    y = 88
    for i, r in enumerate(results):
        symbol = r.get('symbol', '???')
        score = r.get('composite_score', r.get('bde_score', 0))
        score_int = round(score) if score else 0
        
        if score_int >= 70:
            color = "#22c55e"
            signal = "BULLISH"
        elif score_int >= 40:
            color = "#eab308"
            signal = "NEUTRAL"
        else:
            color = "#ef4444"
            signal = "BEARISH"
        
        # Score bar width (max 200px)
        bar_width = max(10, min(200, score_int * 2))
        
        svg += f'''
  <!-- {symbol} -->
  <g transform="translate(0, {y + i * 72})">
    <text x="24" y="24" font-family="system-ui,sans-serif" font-size="16" font-weight="600" fill="#e2e8f0">{symbol}</text>
    <text x="24" y="44" font-family="system-ui,sans-serif" font-size="11" fill="#64748b">{r.get('market', 'US')}</text>
    
    <!-- Score -->
    <text x="{card_width - 24}" y="24" font-family="system-ui,monospace" font-size="28" font-weight="700" fill="{color}" text-anchor="end">{score_int}</text>
    <text x="{card_width - 24}" y="44" font-family="system-ui,sans-serif" font-size="10" fill="{color}" text-anchor="end" letter-spacing="1">{signal}</text>
    
    <!-- Score bar -->
    <rect x="120" y="32" width="200" height="6" rx="3" fill="rgba(255,255,255,0.06)"/>
    <rect x="120" y="32" width="{bar_width}" height="6" rx="3" fill="{color}"/>
  </g>
'''
    
    # Footer
    footer_y = 80 + len(results) * 72
    svg += f'''
  <!-- Footer -->
  <line x1="24" y1="{footer_y}" x2="{card_width - 24}" y2="{footer_y}" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
  <text x="{card_width // 2}" y="{footer_y + 28}" font-family="system-ui,sans-serif" font-size="11" fill="#475569" text-anchor="middle">BDE Score™ · AI-Powered Multi-Market Analysis</text>
  <text x="{card_width // 2}" y="{footer_y + 48}" font-family="system-ui,sans-serif" font-size="10" fill="#3b82f6" text-anchor="middle">rebel-north-intermediate-roof.trycloudflare.com</text>
  <text x="{card_width // 2}" y="{footer_y + 68}" font-family="system-ui,sans-serif" font-size="9" fill="#374151" text-anchor="middle">⚠️ Technical analysis only. Not financial advice.</text>
</svg>'''
    
    return svg

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 share_card.py <SYMBOL> | --top N [MARKET]")
        print("Example: python3 share_card.py AAPL")
        print("Example: python3 share_card.py --top 5 US")
        sys.exit(1)
    
    if sys.argv[1] == "--top":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        market = sys.argv[3] if len(sys.argv) > 3 else "US"
        
        data = fetch_snapshot(market)
        if not data:
            print("Failed to fetch data")
            sys.exit(1)
        
        results = data.get('results', [])
        # Sort by score descending
        results.sort(key=lambda x: x.get('composite_score', x.get('bde_score', 0)), reverse=True)
        top_n = results[:n]
        
        svg = generate_svg_card(
            top_n,
            title=f"BDE Score™ Top {n} — {market}",
            subtitle=f"Highest scoring stocks in {market} market"
        )
        
        output_file = f"bde_top{n}_{market.lower()}_{datetime.now().strftime('%Y%m%d')}.svg"
        with open(output_file, 'w') as f:
            f.write(svg)
        
        print(f"✅ Generated: {output_file}")
        print(f"   Top {n} {market} stocks by BDE Score:")
        for r in top_n:
            print(f"   {r.get('symbol'):8s} → {round(r.get('composite_score', r.get('bde_score', 0))):3d}")
    else:
        symbol = sys.argv[1].upper()
        data = fetch_snapshot("ALL")
        if not data:
            print("Failed to fetch data")
            sys.exit(1)
        
        results = data.get('results', [])
        match = [r for r in results if r.get('symbol') == symbol]
        
        if not match:
            print(f"Symbol {symbol} not found")
            sys.exit(1)
        
        svg = generate_svg_card(
            match,
            title=f"BDE Score™ — {symbol}",
            subtitle=f"Single stock analysis"
        )
        
        output_file = f"bde_{symbol.lower()}_{datetime.now().strftime('%Y%m%d')}.svg"
        with open(output_file, 'w') as f:
            f.write(svg)
        
        print(f"✅ Generated: {output_file}")
        r = match[0]
        print(f"   {symbol} → BDE Score: {round(r.get('composite_score', r.get('bde_score', 0)))}")

if __name__ == "__main__":
    main()
