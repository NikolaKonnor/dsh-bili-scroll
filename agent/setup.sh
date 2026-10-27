#!/usr/bin/env bash
# agent/setup.sh —— macOS / Linux 一次性安装（Windows 用 setup.ps1）
# 用法：bash agent/setup.sh <你的B站UID>
set -euo pipefail
OWNER_UID="${1:?用法：bash agent/setup.sh <你的B站UID>}"
DATA="${BILI_DUTY_HOME:-$HOME/.bili-agent}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$DATA/.venv"
PY="$VENV/bin/python"
REQ="$REPO/vendor/bilibili-mcp/requirements.txt"
mkdir -p "$DATA"

command -v codex >/dev/null || { echo "找不到 codex：先 npm i -g @openai/codex 并 codex login"; exit 1; }

echo "== 1/4 Python 环境"
if [ ! -x "$PY" ]; then
  if command -v uv >/dev/null; then uv venv "$VENV" --python 3.12 && uv pip install --python "$PY" -r "$REQ"
  else python3 -m venv "$VENV" && "$PY" -m pip install -r "$REQ"; fi
fi

echo "== 2/4 画像"
[ -f "$DATA/profile.md" ] || { cp "$REPO/agent/profile.template.md" "$DATA/profile.md"; echo "已放模板到 $DATA/profile.md，记得换成你的画像"; }

echo "== 3/4 注册到 Codex（bili）"
codex mcp remove bili >/dev/null 2>&1 || true
codex mcp add bili \
  --env "BILI_DUTY_HOME=$DATA" \
  --env "BILI_OWNER_UID=$OWNER_UID" \
  --env "BILI_MCP_TOOLS=$(tr -d '\n' < "$REPO/agent/tools.allow")" \
  -- "$PY" "$REPO/agent/server.py"

echo "== 4/4 扫码登录（agent 的小号）"
BILI_DUTY_HOME="$DATA" "$PY" "$REPO/agent/login.py"

cat <<EOF

装好了。手动试跑：  bash "$REPO/agent/run.sh" daily
每天 12:30 自动跑（crontab -e 加一行）：
  30 12 * * * bash "$REPO/agent/run.sh" daily
每周日 20:00 复盘：
  0 20 * * 0 bash "$REPO/agent/run.sh" weekly
EOF
