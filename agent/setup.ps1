# agent/setup.ps1 —— Windows 一次性安装：Python 环境 + 注册到 Codex + 扫码登录
#
# 用法（在仓库根目录的 PowerShell 里）：
#   powershell -ExecutionPolicy Bypass -File agent\setup.ps1 -OwnerUid 你的B站UID
#
# 做的事：
#   1. 在 ~/.bili-agent 建数据目录和独立的 Python 环境（有 uv 用 uv，没有用 python -m venv）
#   2. 没有画像就放一份模板到 ~/.bili-agent/profile.md
#   3. 用 `codex mcp add` 把 B站 工具注册成名为 bili 的 MCP 服务器（只开白名单里的工具）
#   4. 运行扫码登录（给 agent 用的小号）
param(
  [Parameter(Mandatory = $true)][string]$OwnerUid,
  [string]$DataDir = "$env:USERPROFILE\.bili-agent",
  [switch]$Schedule   # 加上它：顺便注册"每天 12:30 日报 + 每周日 20:00 复盘"两个计划任务
)
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $DataDir '.venv'
$Py = Join-Path $Venv 'Scripts\python.exe'
$Req = Join-Path $Repo 'vendor\bilibili-mcp\requirements.txt'

New-Item -ItemType Directory -Force $DataDir | Out-Null

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
  throw '找不到 codex 命令。请先安装 Codex CLI（npm i -g @openai/codex）并运行 codex login。'
}

Write-Host '== 1/4 准备 Python 环境' -ForegroundColor Cyan
if (-not (Test-Path $Py)) {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv venv $Venv --python 3.12
    uv pip install --python $Py -r $Req
  } else {
    python -m venv $Venv
    & $Py -m pip install -r $Req
  }
} else {
  Write-Host "已存在：$Venv（要重装就先删掉这个目录）"
}

Write-Host '== 2/4 画像' -ForegroundColor Cyan
$ProfileFile = Join-Path $DataDir 'profile.md'
if (-not (Test-Path $ProfileFile)) {
  Copy-Item (Join-Path $Repo 'agent\profile.template.md') $ProfileFile
  Write-Host "已放一份模板到 $ProfileFile —— 记得换成你自己的画像。"
} else {
  Write-Host "已有画像：$ProfileFile（不覆盖）"
}

Write-Host '== 3/4 注册到 Codex（MCP 服务器名：bili）' -ForegroundColor Cyan
try { codex mcp remove bili *> $null } catch { }  # 第一次装时它不存在，报错无所谓
codex mcp add bili `
  --env "BILI_DUTY_HOME=$DataDir" `
  --env "BILI_OWNER_UID=$OwnerUid" `
  --env "BILI_MCP_TOOLS=@tools.allow" `
  -- $Py (Join-Path $Repo 'agent\server.py')

Write-Host '== 4/4 扫码登录（用 agent 的小号扫）' -ForegroundColor Cyan
$env:BILI_DUTY_HOME = $DataDir
& $Py (Join-Path $Repo 'agent\login.py')

if ($Schedule) {
  Write-Host '== 计划任务' -ForegroundColor Cyan
  $ps = (Get-Command powershell).Source
  $daily = New-ScheduledTaskAction -Execute $ps -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Repo\agent\run-daily.ps1`""
  $weekly = New-ScheduledTaskAction -Execute $ps -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Repo\agent\run-weekly.ps1`""
  $set = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
  Register-ScheduledTask -TaskName 'bili-agent-daily' -Action $daily -Trigger (New-ScheduledTaskTrigger -Daily -At 12:30) -Settings $set -Force | Out-Null
  Register-ScheduledTask -TaskName 'bili-agent-weekly' -Action $weekly -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 20:00) -Settings $set -Force | Out-Null
  Write-Host '已注册：bili-agent-daily（每天 12:30）、bili-agent-weekly（每周日 20:00）。电脑要开着；错过的会在开机后补跑一次。'
}

Write-Host ''
Write-Host '装好了。手动试跑一轮：' -ForegroundColor Green
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$Repo\agent\run-daily.ps1`""
Write-Host "日志在 $DataDir\logs，日报在 $DataDir\out。"
if (-not $Schedule) { Write-Host '想每天自动跑：重新运行本脚本并加上 -Schedule。' }
