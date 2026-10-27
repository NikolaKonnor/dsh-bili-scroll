# agent/run-daily.ps1 —— 用 Codex 无人值守地跑一轮日报（任务计划程序调用它）
param([string]$DataDir = "$env:USERPROFILE\.bili-agent")
$Repo = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'
# Codex 输出的是 UTF-8；Windows PowerShell 默认按 GBK 解码，日志会乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Log = Join-Path $Logs "$Stamp-daily.log"

# -s read-only：模型自己的 shell 命令只能读、不能写、不能联网；写东西只能通过 bili 的固定路径工具
# approval_policy=never：没人在电脑前，不弹审批（需要审批的操作直接失败，不会卡住）
# default_tools_approval_mode=approve：bili 里的工具都已经过白名单筛选，调用时不再逐个审批
codex exec `
  -C $Repo `
  -s read-only `
  --skip-git-repo-check `
  -c 'approval_policy="never"' `
  -c 'mcp_servers.bili.default_tools_approval_mode="approve"' `
  -c 'mcp_servers.bili.startup_timeout_sec=60' `
  -c 'mcp_servers.bili.tool_timeout_sec=180' `
  -o (Join-Path $Logs "$Stamp-daily-final.txt") `
  '使用 bili-daily 技能，跑今天这一轮。' 2>&1 | ForEach-Object {
  # 同时显示在窗口里、并以 UTF-8 追加到日志（Windows PowerShell 自带的 >> 会写成 UTF-16，和旧内容混在一起就乱码）
  $line = "$_"
  Write-Host $line
  Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}
