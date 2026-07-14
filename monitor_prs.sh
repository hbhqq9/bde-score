#!/bin/bash
# BDE Score Awesome Lists PR Monitor v2
# Updated: 2026-07-14 - reflects current PR state after resubmissions

declare -A PRS
PRS=(
  ["awesome-python"]="vinta/awesome-python:3247"
  ["awesome-ml"]="josephmisiti/awesome-machine-learning:1379"
  ["awesome-ds"]="academic/awesome-datascience:652"
  ["awesome-quant"]="wilsonfreitas/awesome-quant:474"
  ["awesome-sys-trade"]="wangzhe3224/awesome-systematic-trading:128"
  ["awesome-ai-agents"]="e2b-dev/awesome-ai-agents:1234"
  ["awesome-claude-skills"]="ComposioHQ/awesome-claude-skills:1304"
  ["awesome-mcp-servers"]="punkpeye/awesome-mcp-servers:9947"
  ["awesome-mcp-zh"]="yzfly/Awesome-MCP-ZH:384"
  ["awesome-quant-ai"]="leoncuhk/awesome-quant-ai:41"
  ["awesome-finance-skills"]="RKiding/Awesome-finance-skills:22"
  ["awesome-finance-mcp"]="BlockRunAI/awesome-finance-mcp:29"
)

echo "=== BDE Score PR Status Report ==="
echo "Date: $(date '+%Y-%m-%d %H:%M')"
echo ""

merged=0; open=0; closed=0

for name in "${!PRS[@]}"; do
  IFS=':' read -r repo pr <<< "${PRS[$name]}"
  result=$(gh pr view "$pr" --repo "$repo" --json state,reviews,comments 2>/dev/null)
  state=$(echo "$result" | jq -r '.state // "unknown"')
  comments=$(echo "$result" | jq '.comments | length' 2>/dev/null || echo "0")
  reviews=$(echo "$result" | jq '.reviews | length' 2>/dev/null || echo "0")
  
  case $state in
    OPEN) ((open++)); emoji="🟢" ;;
    MERGED) ((merged++)); emoji="✅" ;;
    CLOSED) ((closed++)); emoji="🔴" ;;
    *) emoji="❓" ;;
  esac
  
  echo "$emoji $name: $state (comments: $comments, reviews: $reviews)"
done

echo ""
echo "Summary: $open open | $merged merged | $closed closed"
