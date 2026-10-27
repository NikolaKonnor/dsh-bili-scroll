#!/usr/bin/env python3
"""
agent/inspect_videos.py —— 把几条视频的"体检数据"导出成一个文件（只读，不影响推荐）

用法（Windows）：
  & "$env:USERPROFILE\\.bili-agent\\.venv\\Scripts\\python.exe" agent\\inspect_videos.py            # 最近一期日报推过的那几条
  & "$env:USERPROFILE\\.bili-agent\\.venv\\Scripts\\python.exe" agent\\inspect_videos.py BV1xx BV1yy  # 指定 BV 号

每条导出：
  · 视频：标题、发布时间和距今天数、时长、标签、简介、播放/点赞/投币/收藏/评论/弹幕/分享、互动率
  · UP 主：昵称、UID、粉丝数、签名、投稿总数、近 30 天投稿数、最近 15 条投稿（日期 / 播放 / 标题）、标题模板重复度
  · 字幕（带时间点，最长约 6000 字）和热评前 8 条
结果写到 ~/.bili-agent/inspect/<时间>.md，最后打印路径 —— 把这个文件发出来就行。
"""
import asyncio
import datetime as dt
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.pop("BILI_MCP_TOOLS", None)
_HOME = Path(os.environ.get("BILI_DUTY_HOME") or (Path.home() / ".bili-agent")).expanduser()
os.environ["BILI_DUTY_HOME"] = str(_HOME)
os.environ.setdefault("BILI_CREDENTIAL_FILE", str(_HOME / "bili_credential.json"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "bilibili-mcp"))
import mcp_server as base  # noqa: E402

SUB_LIMIT = 6000
NOW = dt.datetime.now()


def fmt_ts(ts) -> str:
    return dt.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M") if ts else "?"


def days_ago(ts) -> str:
    return f"{(NOW - dt.datetime.fromtimestamp(int(ts))).total_seconds() / 86400:.1f}" if ts else "?"


def rate(a, b) -> str:
    return f"{a / b:.2%}" if b else "-"


def template_key(title: str) -> str:
    """标题去掉数字和英文后的"骨架"，用来看是不是同一个模板批量出的"""
    t = str(title or "")
    for sep in ("｜", "|", "丨"):
        if sep in t:
            t = t.rsplit(sep, 1)[1]
            break
    return "".join(ch for ch in t if not (ch.isascii() and ch.isalnum())).strip()


def latest_index_bvids() -> list:
    out = _HOME / "out"
    found = sorted(out.glob("*.index.json")) if out.exists() else []
    if not found:
        return []
    data = json.loads(found[-1].read_text(encoding="utf-8"))
    print("没给 BV 号，用最近一期日报：", found[-1].name)
    return [it["bvid"] for it in data.get("items", []) if it.get("bvid")]


async def inspect(bv: str, cred) -> str:
    L = [f"## {bv}", ""]
    v = base.video.Video(bvid=bv, credential=cred)
    info = await v.get_info()
    st = info.get("stat", {}) or {}
    own = info.get("owner", {}) or {}
    view = int(st.get("view") or 0)
    L += [
        f"- 标题：{info.get('title', '')}",
        f"- 链接：https://www.bilibili.com/video/{bv}",
        f"- 发布：{fmt_ts(info.get('pubdate'))}（距今 {days_ago(info.get('pubdate'))} 天）",
        f"- 时长：{int(info.get('duration') or 0) // 60} 分 {int(info.get('duration') or 0) % 60} 秒 · 分P：{len(info.get('pages') or [])}",
        f"- 数据：播放 {view} · 点赞 {st.get('like', 0)} · 投币 {st.get('coin', 0)} · 收藏 {st.get('favorite', 0)}"
        f" · 评论 {st.get('reply', 0)} · 弹幕 {st.get('danmaku', 0)} · 分享 {st.get('share', 0)}",
        f"- 互动率：赞 {rate(int(st.get('like') or 0), view)} · 币 {rate(int(st.get('coin') or 0), view)}"
        f" · 藏 {rate(int(st.get('favorite') or 0), view)}",
    ]
    try:
        tags = await v.get_tags()
        L.append("- 标签：" + "、".join(t.get("tag_name", "") for t in tags if t.get("tag_name")))
    except Exception as e:  # noqa: BLE001
        L.append(f"- 标签：读取失败（{type(e).__name__}）")
    desc = str(info.get("desc") or "").strip().replace("\n", " / ")
    L += [f"- 简介：{desc[:500]}", ""]

    mid = own.get("mid")
    L.append(f"### UP 主：{own.get('name', '')}（UID {mid}）")
    if mid:
        u = base.user.User(uid=int(mid), credential=cred)
        try:
            rel = await u.get_relation_info()
            L.append(f"- 粉丝：{rel.get('follower', '?')}")
        except Exception as e:  # noqa: BLE001
            L.append(f"- 粉丝：读取失败（{type(e).__name__}）")
        try:
            ui = await u.get_user_info()
            L.append(f"- 签名：{str(ui.get('sign') or '').strip()[:120]}")
        except Exception as e:  # noqa: BLE001
            L.append(f"- 签名：读取失败（{type(e).__name__}）")
        try:
            res = await u.get_videos(pn=1, ps=30, order=base.user.VideoOrder.PUBDATE)
            vl = (res.get("list") or {}).get("vlist") or []
            total = (res.get("page") or {}).get("count", "?")
            cutoff = (NOW - dt.timedelta(days=30)).timestamp()
            n30 = sum(1 for x in vl if int(x.get("created") or 0) >= cutoff)
            more = "（可能更多，只取了最近 30 条）" if n30 == len(vl) == 30 else ""
            keys = Counter(k for k in (template_key(x.get("title")) for x in vl[:15]) if k)
            top = keys.most_common(1)
            L += [
                f"- 投稿总数：{total} · 近 30 天投稿：{n30}{more}",
                f"- 最近 15 条里同一标题骨架出现最多的：{top[0][1]} 次「{top[0][0]}」" if top else "- 标题骨架：没有明显重复",
                "- 最近 15 条投稿：",
            ]
            for x in vl[:15]:
                L.append(f"  - {fmt_ts(x.get('created'))[:10]} · 播放 {x.get('play', '?')} · {x.get('length', '')} · {x.get('title', '')}")
        except Exception as e:  # noqa: BLE001
            L.append(f"- 投稿列表：读取失败（{type(e).__name__}: {str(e)[:80]}）")
    L.append("")

    L.append("### 字幕（带时间点）")
    try:
        sub = json.loads(await base.bili_subtitle(bv, timestamps=True))
        text = sub.get("text") or sub.get("message") or json.dumps(sub, ensure_ascii=False)
        cut = "" if len(text) <= SUB_LIMIT else f"\n……（共 {len(text)} 字，只截前 {SUB_LIMIT} 字）"
        L += ["```", text[:SUB_LIMIT] + cut, "```"]
    except Exception as e:  # noqa: BLE001
        L.append(f"读取失败（{type(e).__name__}: {str(e)[:120]}）")
    L.append("")

    L.append("### 热评前 8 条")
    try:
        cm = json.loads(await base.bili_comments(bv, 8))
        items = cm.get("comments") if isinstance(cm, dict) else cm
        for c in (items or [])[:8]:
            if isinstance(c, dict):
                L.append(f"- （赞 {c.get('likes', c.get('like', '?'))}）{str(c.get('content') or c.get('message') or '')[:150]}")
        if isinstance(cm, dict) and cm.get("error"):
            L.append(f"- 读取出错：{cm.get('error')}")
    except Exception as e:  # noqa: BLE001
        L.append(f"读取失败（{type(e).__name__}）")
    L.append("")
    return "\n".join(L)


async def main() -> int:
    bvs = [a for a in sys.argv[1:] if a.startswith("BV")] or latest_index_bvids()
    if not bvs:
        print("没有 BV 号：请在命令后面写上 BV 号，或者先跑出一期日报。")
        return 1
    cred = base.get_cred()
    parts = [f"# 视频体检 {NOW:%Y-%m-%d %H:%M}", ""]
    for bv in bvs:
        print("正在读：", bv)
        try:
            parts.append(await inspect(bv, cred))
        except Exception as e:  # noqa: BLE001
            parts.append(f"## {bv}\n\n读取失败：{type(e).__name__}: {e}\n")
    out = _HOME / "inspect" / f"{NOW:%Y-%m-%d_%H%M}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts), encoding="utf-8")
    print("已导出：", out)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
