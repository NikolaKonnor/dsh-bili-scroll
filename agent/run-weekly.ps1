# agent/run-weekly.ps1 —— 用 Codex 无人值守地做每周复盘（只写建议，不改画像）
param([string]$DataDir = "$env:USERPROFILE\.bili-agent")
$Repo = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'
# Codex 输出的是 UTF-8；Windows PowerShell 默认按 GBK 解码，日志会乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Log = Join-Path $Logs "$Stamp-weekly.log"

codex exec `
  -C $Repo `
  -s read-only `
  --skip-git-repo-check `
  -c 'approval_policy="never"' `
  -c 'mcp_servers.bili.default_tools_approval_mode="approve"' `
  -c 'mcp_servers.bili.startup_timeout_sec=60' `
  -c 'mcp_servers.bili.tool_timeout_sec=180' `
  -o (Join-Path $Logs "$Stamp-weekly-final.txt") `
  '使用 bili-weekly 技能，按"模式一：复盘"做本周复盘。' 2>&1 | ForEach-Object {
  # 同时显示在窗口里、并以 UTF-8 追加到日志（Windows PowerShell 自带的 >> 会写成 UTF-16，和旧内容混在一起就乱码）
  $line = "$_"
  Write-Host $line
  Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}
