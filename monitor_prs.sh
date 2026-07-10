#!/bin/bash
# BDE Score Awesome Lists PR Monitor
# Checks status of all 10 submitted PRs

declare -A PRS
PRS=(
  ["awesome-python"]="vinta/awesome-python:3247"
  ["awesome-ml"]="josephmisiti/awesome-machine-learning:1379"
  ["awesome-ds"]="academic/awesome-datascience:652"
  ["awesome-quant"]="wilsonfreitas/awesome-quant:466"
  ["awesome-sys-trade"]="paperswithbacktest/awesome-systematic-trading:66"
  ["awesome-ai-fin"]="georgezouq/awesome-ai-in-finance:184"
  ["awesome-sys-trade2"]="wangzhe3224/awesome-systematic-trading:126"
  ["awesome-quant-ml"]="grananqvist/Awesome-Quant-Machine-Learning-Trading:33"
  ["awesome-deep-trade"]="cbailes/awesome-deep-trading:19"
  ["awesome-stock"]="shi-rudo/awesome-stock-trading:53"
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
