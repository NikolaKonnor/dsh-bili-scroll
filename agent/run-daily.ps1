# agent/run-daily.ps1 —— 用 Codex 无人值守地跑一轮日报（任务计划程序调用它）
#
# 分两段跑：
#   1. 初筛（便宜的模型）：按画像拉几百条候选，挑 60–80 条写进短名单
#   2. 精选（强一点的模型）：读短名单，体检、读字幕、写日报、发私信
# 初筛失败也不要紧：精选那一段发现没有短名单，会按老办法自己搜。
#
# 换模型：  run-daily.ps1 -PrefilterModel gpt-6.1-terra -Model gpt-6.1-sol
# 只跑精选：run-daily.ps1 -SkipPrefilter
param(
  [string]$DataDir = "$env:USERPROFILE\.bili-agent",
  [string]$PrefilterModel = 'gpt-6.1-terra',
  [string]$PrefilterEffort = 'medium',
  [string]$Model = 'gpt-6.1-sol',
  [string]$Effort = 'medium',
  [switch]$SkipPrefilter
)
$Repo = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$Stamp = Get-Date -Format 'yyyy-MM-dd'
# Codex 输出的是 UTF-8；Windows PowerShell 默认按 GBK 解码，日志会乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$Log = Join-Path $Logs "$Stamp-daily.log"

function Write-Log([string]$line) {
  Write-Host $line
  Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}

# -s read-only：模型自己的 shell 命令只能读、不能写、不能联网；写东西只能通过 bili 的固定路径工具
# approval_policy=never：没人在电脑前，不弹审批（需要审批的操作直接失败，不会卡住）
# default_tools_approval_mode=approve：bili 里的工具都已经过白名单筛选，调用时不再逐个审批
# 下面 -c 里的字符串值不加引号：Codex 把解析不了的值当字符串，这样也避开了 PowerShell 吃掉引号的问题
function Invoke-Stage([string]$Name, [string]$UseModel, [string]$UseEffort, [string]$Prompt, [string[]]$Extra) {
  Write-Log "===== $Name：$UseModel / $UseEffort · $(Get-Date -Format 'HH:mm:ss') ====="
  $codexArgs = @(
    'exec', '-C', $Repo, '-s', 'read-only', '--skip-git-repo-check',
    '-m', $UseModel,
    '-c', "model_reasoning_effort=$UseEffort",
    '-c', 'approval_policy="never"',
    '-c', 'mcp_servers.bili.default_tools_approval_mode="approve"',
    '-c', 'mcp_servers.bili.startup_timeout_sec=60',
    '-c', 'mcp_servers.bili.tool_timeout_sec=300'
  ) + $Extra + @('-o', (Join-Path $Logs "$Stamp-$Name-final.txt"), $Prompt)
  & codex @codexArgs 2>&1 | ForEach-Object {
    # 原生命令写到 stderr 的行会变成 ErrorRecord；空行直接打印会显示成 "System.Management.Automation.RemoteException"
    $line = if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { "$_" }
    Write-Log $line
  }
  return $LASTEXITCODE
}

$Hint = '（读 SKILL.md 等文本文件时请加 -Encoding UTF8，否则会乱码。）'

if (-not $SkipPrefilter) {
  # 初筛只开它要用的几个工具（白名单换成 tools.prefilter.allow）
  $code = Invoke-Stage 'prefilter' $PrefilterModel $PrefilterEffort "使用 bili-prefilter 技能，做今天的初筛。$Hint" `
    @('-c', 'mcp_servers.bili.env.BILI_MCP_TOOLS=@tools.prefilter.allow')
  if ($code -ne 0) { Write-Log "初筛没跑成功（退出码 $code），精选会自己搜候选。" }
}

$code = Invoke-Stage 'daily' $Model $Effort "使用 bili-daily 技能，跑今天这一轮。$Hint" @()
Write-Log "===== 结束 · $(Get-Date -Format 'HH:mm:ss')（退出码 $code） ====="
