#!/usr/bin/env python3
"""
agent/doctor.py —— 不经过 Codex，直接测一遍 B站 工具通不通

用法：  ~/.bili-agent/.venv/Scripts/python.exe agent/doctor.py   （macOS/Linux：.venv/bin/python）
会依次检查：凭证文件 → 登录是否有效 → 搜索 → 字幕 → 私信收件人设置
"""
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.pop("BILI_MCP_TOOLS", None)
_HOME = Path(os.environ.get("BILI_DUTY_HOME") or (Path.home() / ".bili-agent")).expanduser()
os.environ["BILI_DUTY_HOME"] = str(_HOME)
os.environ.setdefault("BILI_CREDENTIAL_FILE", str(_HOME / "bili_credential.json"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "bilibili-mcp"))
import mcp_server as base  # noqa: E402


def show(title, text):
    try:
        text = json.dumps(json.loads(text), ensure_ascii=False)
    except (ValueError, TypeError):
        pass
    print(f"[{title}] {str(text)[:300]}")


async def main():
    f = base.CRED_FILE
    print("数据目录：", _HOME)
    print("凭证文件：", f, "存在" if f.exists() else "【不存在 —— 先运行 agent/login.py 扫码】")
    if f.exists():
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            print("凭证里的 UID：", d.get("dedeuserid") or "【空】", "| buvid3：", "有" if d.get("buvid3") else "【空】")
        except ValueError as e:
            print("凭证文件读不了：", e)
    show("登录检查", await base.bili_check_credential())
    try:
        r = await base.bili_search("资产定价", 3, "pubdate")
        show("搜索", r)
        bv = None
        try:
            items = json.loads(r)
            items = items.get("results") or items.get("videos") or items if isinstance(items, dict) else items
            bv = next((x.get("bvid") for x in items if isinstance(x, dict) and x.get("bvid")), None)
        except (ValueError, TypeError, AttributeError):
            pass
    except Exception as e:  # noqa: BLE001
        print("[搜索] 失败：", type(e).__name__, e)
        bv = None
    bv = bv or "BV1GJ411x7h7"
    try:
        show(f"字幕 {bv}", await base.bili_subtitle(bv, timestamps=True))
    except Exception as e:  # noqa: BLE001
        print(f"[字幕 {bv}] 失败：", type(e).__name__, e)
    print("私信收件人 BILI_OWNER_UID：", os.environ.get("BILI_OWNER_UID") or "（这里没设；Codex 跑的时候由 codex mcp add 的配置提供）")


if __name__ == "__main__":
    asyncio.run(main())
