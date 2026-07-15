# BDE Score — Official MCP Registry Publish Announcement

## 🎉 Published to Official MCP Registry

**BDE Score is now discoverable by all MCP clients!**

- **Registry ID**: `io.github.hbhqq9/bde-score`
- **Version**: 1.0.3
- **Schema**: 2025-12-11 (latest)
- **Status**: Active
- **Published**: 2026-07-14

### What This Means
Any MCP-compatible AI client (Claude Desktop, Cursor, Codex, Windsurf, etc.) can now automatically discover and connect to BDE Score without manual configuration.

### How to Use
MCP clients will find BDE Score through the official registry. No API keys required for basic usage.

### Tools Available
- `get_bde_score` - Composite BDE analysis (0-100)
- `get_stock_analysis` - Detailed stock analysis
- `get_multi_market_comparison` - Cross-market comparison
- `get_stock_screener` - Stock screening
- `get_sector_analysis` - Sector rankings
- `get_esg_analysis` - ESG analysis

### EU AI Act Art.50 Compliance
All responses include three-layer AI system identification:
- L1: HTTP Response Headers (`X-BDE-AI-System`)
- L2: JSON Tool Response Embedding
- L3: Content Fingerprint (sha256)

### Links
- Repository: https://github.com/hbhqq9/bde-score
- Live Demo: https://hbhqq9.github.io/bde-score/
- Art.50 Checker: https://hbhqq9.github.io/bde-score/art50-checker.html
- GitHub Discussion: https://github.com/hbhqq9/bde-score/discussions/3
