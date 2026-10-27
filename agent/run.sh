#!/usr/bin/env bash
# agent/run.sh daily|weekly —— 用 Codex 无人值守地跑一轮（cron 调用它）
# daily 分两段：初筛（便宜模型，写短名单）→ 精选（读短名单，体检、读字幕、写日报）。
# 换模型：PREFILTER_MODEL=… MODEL=… bash agent/run.sh daily；只跑精选：SKIP_PREFILTER=1
set -uo pipefail
MODE="${1:-daily}"
DATA="${BILI_DUTY_HOME:-$HOME/.bili-agent}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$DATA/logs"
STAMP="$(date +%F)"
PREFILTER_MODEL="${PREFILTER_MODEL:-gpt-6.1-terra}"
PREFILTER_EFFORT="${PREFILTER_EFFORT:-medium}"
MODEL="${MODEL:-gpt-6.1-sol}"
EFFORT="${EFFORT:-medium}"

stage() {  # stage 名字 模型 推理强度 提示词 [额外参数…]
  local name="$1" model="$2" effort="$3" prompt="$4"; shift 4
  echo "===== $name: $model / $effort · $(date +%T) =====" >> "$DATA/logs/$STAMP-$MODE.log"
  codex exec -C "$REPO" -s read-only --skip-git-repo-check \
    -m "$model" -c "model_reasoning_effort=$effort" \
    -c 'approval_policy="never"' \
    -c 'mcp_servers.bili.default_tools_approval_mode="approve"' \
    -c 'mcp_servers.bili.startup_timeout_sec=60' \
    -c 'mcp_servers.bili.tool_timeout_sec=300' \
    "$@" \
    -o "$DATA/logs/$STAMP-$name-final.txt" \
    "$prompt" >> "$DATA/logs/$STAMP-$MODE.log" 2>&1
}

case "$MODE" in
  daily)
    if [ -z "${SKIP_PREFILTER:-}" ]; then
      stage prefilter "$PREFILTER_MODEL" "$PREFILTER_EFFORT" '使用 bili-prefilter 技能，做今天的初筛。' \
        -c 'mcp_servers.bili.env.BILI_MCP_TOOLS=@tools.prefilter.allow' \
        || echo "初筛没跑成功，精选会自己搜候选。" >> "$DATA/logs/$STAMP-$MODE.log"
    fi
    stage daily "$MODEL" "$EFFORT" '使用 bili-daily 技能，跑今天这一轮。'
    ;;
  weekly)
    stage weekly "$MODEL" "$EFFORT" '使用 bili-weekly 技能，按"模式一：复盘"做本周复盘。'
    ;;
  *) echo "用法：run.sh daily|weekly"; exit 1 ;;
esac
