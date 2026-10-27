#!/usr/bin/env bash
# agent/run.sh daily|weekly —— 用 Codex 无人值守地跑一轮（cron 调用它）
set -euo pipefail
MODE="${1:-daily}"
DATA="${BILI_DUTY_HOME:-$HOME/.bili-agent}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DATA/logs"
STAMP="$(date +%F)"
case "$MODE" in
  daily)  PROMPT='使用 bili-daily 技能，跑今天这一轮。' ;;
  weekly) PROMPT='使用 bili-weekly 技能，按"模式一：复盘"做本周复盘。' ;;
  *) echo "用法：run.sh daily|weekly"; exit 1 ;;
esac
codex exec -C "$REPO" -s read-only --skip-git-repo-check \
  -c 'approval_policy="never"' \
  -c 'mcp_servers.bili.startup_timeout_sec=60' \
  -c 'mcp_servers.bili.tool_timeout_sec=180' \
  -o "$DATA/logs/$STAMP-$MODE-final.txt" \
  "$PROMPT" >> "$DATA/logs/$STAMP-$MODE.log" 2>&1
