# agent/run-weekly.ps1 —— 用 Codex 无人值守地做每周复盘（只写建议，不改画像）
param([string]$DataDir = "$env:USERPROFILE\.bili-agent")
$Repo = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'

codex exec `
  -C $Repo `
  -s read-only `
  -c 'approval_policy="never"' `
  -c 'mcp_servers.bili.startup_timeout_sec=60' `
  -c 'mcp_servers.bili.tool_timeout_sec=180' `
  -o (Join-Path $Logs "$Stamp-weekly-final.txt") `
  '使用 bili-weekly 技能，按"模式一：复盘"做本周复盘。' *>> (Join-Path $Logs "$Stamp-weekly.log")
