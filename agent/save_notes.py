#!/usr/bin/env python3
"""
agent/save_notes.py —— 手动把某一期日报里学习位视频的字幕存下来（平时日报会自动存，这个用来补存）

用法（Windows）：
  & "$env:USERPROFILE\\.bili-agent\\.venv\\Scripts\\python.exe" agent\\save_notes.py              # 今天这期
  & "$env:USERPROFILE\\.bili-agent\\.venv\\Scripts\\python.exe" agent\\save_notes.py 2026-10-27   # 指定日期
  加 --force：已经存过的也重新存一遍

存到 ~/.bili-agent/notes/<年-月>/ 下，每条视频一个 markdown：日报里的介绍 + 带时间点的字幕。
"""
import asyncio
import datetime as dt
import json
import os
import sys
from pathlib import Path

os.environ.pop("BILI_MCP_TOOLS", None)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import server  # noqa: E402


async def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    date = args[0] if args else dt.date.today().isoformat()
    idx = server.HOME / "out" / f"{date}.index.json"
    if not idx.exists():
        print(f"没有这一期的索引：{idx}")
        return 1
    items = json.loads(idx.read_text(encoding="utf-8")).get("items", [])
    saved = await server.save_learning_notes(items, date, force="--force" in sys.argv)
    if saved:
        print("已存：")
        for p in saved:
            print("  ", p)
    else:
        print("没有新存的（这一期没有学习位视频，或者已经存过了；要重存加 --force）")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
