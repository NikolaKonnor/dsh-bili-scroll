# agent/run-daily.ps1 —— 用 Codex 无人值守地跑一轮日报（任务计划程序调用它）
param([string]$DataDir = "$env:USERPROFILE\.bili-agent")
$Repo = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'

# -s read-only：模型自己的 shell 命令只能读、不能写、不能联网；写东西只能通过 bili 的固定路径工具
# approval_policy=never：没人在电脑前，不弹审批（需要审批的操作直接失败，不会卡住）
codex exec `
  -C $Repo `
  -s read-only `
  --skip-git-repo-check `
  -c 'approval_policy="never"' `
  -c 'mcp_servers.bili.startup_timeout_sec=60' `
  -c 'mcp_servers.bili.tool_timeout_sec=180' `
  -o (Join-Path $Logs "$Stamp-daily-final.txt") `
  '使用 bili-daily 技能，跑今天这一轮。' *>> (Join-Path $Logs "$Stamp-daily.log")
