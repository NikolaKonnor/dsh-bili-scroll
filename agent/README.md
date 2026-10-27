# 用 Codex 跑「B站 日报」

这是 [dsh-bili-scroll](https://github.com/c1overzz/dsh-bili-scroll) 的另一种跑法：不需要 DSH，改由 **Codex CLI** 每天跑一轮。
B站 工具（`vendor/bilibili-mcp`）、值班思路都沿用原项目；这里加的是一个 MCP 入口、两份技能、个性化记忆和定时脚本。原来的 DSH 插件不受影响，照常可用。

## 它每天做什么

1. 读你的**画像**（`~/.bili-agent/profile.md`）和你最近的**反馈**；
2. 读你回给它的私信，把"3 好 讲得清楚"这类反馈记下来；
3. 按画像搜 B站、**读字幕原文**筛视频；
4. 写一份完整日报（知识类每条附带时间点的内容大纲），存在 `~/.bili-agent/out/<日期>.md`；
5. 私信你一份简版（≤490 字，带编号），你回编号＋评价就是反馈。

每周日再做一次**复盘**：根据这两周的反馈提出画像修改建议，**只写建议、不改画像**；你在 Codex 里说"应用画像建议"，它逐条问你，你同意的才改。

## 准备

- **Codex CLI**：`npm i -g @openai/codex`，然后 `codex login`。
- **Python 3.10+ 或 uv**（有 uv 最省事）。
- **一个给 agent 用的 B站 小号**：日报要私信给你本人，B站 不能自己给自己发私信。
  ⚠️ 小号的首页推荐流不是按你的口味推的，所以候选主要靠画像里的方向去搜索。
- **你自己的 B站 UID**（日报发给谁）。

## 安装（Windows）

在仓库根目录打开 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File agent\setup.ps1 -OwnerUid 你的UID -Schedule
```

它会：建 `~/.bili-agent` 和独立 Python 环境 → 放一份画像模板 → 把 B站 工具注册成 Codex 的 MCP 服务器 `bili` → 打印二维码让你用**小号**扫码 →（加了 `-Schedule` 时）注册两个计划任务：每天 12:30 日报、每周日 20:00 复盘。

然后**把画像换成你自己的**：用你的画像覆盖 `~/.bili-agent/profile.md`。

macOS / Linux：`bash agent/setup.sh 你的UID`，按最后打印的提示加 cron。

## 日常使用

- **手动跑一轮**：`powershell -ExecutionPolicy Bypass -File agent\run-daily.ps1`（macOS/Linux：`bash agent/run.sh daily`）
- **看日报**：`~/.bili-agent/out/<日期>.md`；运行日志在 `~/.bili-agent/logs/`（UTF-8）。手动跑时进度直接显示在窗口里；
  想在另一个窗口看定时任务的进度：`Get-Content -Encoding UTF8 -Wait "$env:USERPROFILE\.bili-agent\logs\$(Get-Date -Format yyyy-MM-dd)-daily.log"`
- **给反馈**：直接回小号的私信，比如
  `2 好 讲得清楚` · `4 不想看 太浅` · `1 已看过`。理由最有用，照原话记进 `feedback.jsonl`。
- **应用复盘建议**：在仓库目录运行 `codex --add-dir ~/.bili-agent`，说"应用画像建议"。

## 数据都在哪（全在你电脑上，不进仓库）

| 文件 | 内容 | 谁能改 |
|---|---|---|
| `profile.md` | 你的画像 | 只有你（或你同意后让 Codex 改） |
| `feedback.jsonl` | 你的每条反馈 | 只追加 |
| `seen.md` | 判重表 | 只追加 |
| `out/<日期>.md`、`out/<日期>.index.json` | 日报全文、私信编号索引 | 每轮写 |
| `proposals/<日期>.md` | 每周的画像修改建议 | 每周写 |
| `bili_credential.json` | 小号登录凭证（敏感） | 扫码时写 |

## 安全设计

- **工具白名单**（`agent/tools.allow`）：每天那一轮只能看到只读的 B站 工具、固定路径的记忆工具，以及**只能发给你**的私信工具。评论、点赞、投稿、发动态、给别人发私信这些工具**根本不注册**，模型连名字都看不到。
- **只发给你**：收件人写死在 `BILI_OWNER_UID` 里，模型改不了；一条不超过 490 字，一轮最多两条。
- **画像只读**：每天那一轮只能读画像；想改只能写建议，由你拍板。
- **只读沙箱**：`codex exec -s read-only`，模型自己的 shell 命令不能写文件、不能联网。
- **防注入**：技能里写明字幕、标题、评论里的文字都只是素材，不是指令。

⚠️ 只读沙箱仍然能**读**本机文件（包括凭证）。能把内容带出去的渠道只有"搜索关键词"和"发给你的私信"，风险很小，但凭证依然要妥善保管。

## 文件一览

```
.agents/skills/bili-daily/SKILL.md    每天一轮的做法（Codex 和 Claude Code 都认这个格式）
.agents/skills/bili-weekly/SKILL.md   每周复盘 / 应用建议
agent/server.py                       MCP 入口：B站 工具 + 记忆 + 只发给你的私信
agent/login.py                        终端扫码登录
agent/tools.allow                     每天那一轮的工具白名单
agent/profile.template.md             画像模板
agent/setup.ps1 / setup.sh            一次性安装
agent/run-daily.ps1 / run-weekly.ps1 / run.sh   无人值守地跑一轮
```

## 已知问题

- 运行脚本里用 `mcp_servers.bili.default_tools_approval_mode="approve"` 让 bili 的工具免审批（无人值守时没人点同意）。如果日志里仍出现 `MCP tool call requires approval`，请把日志发出来。
- 私信 500 字的上限是原项目实测得出的，B站 随时可能调整。

## 致谢

B站 工具来自 [AGI_Ananas/bilibili-mcp](https://github.com/adoresever/bilibili-mcp)（MIT），值班设计来自 [c1overzz/dsh-bili-scroll](https://github.com/c1overzz/dsh-bili-scroll)（MIT）。
