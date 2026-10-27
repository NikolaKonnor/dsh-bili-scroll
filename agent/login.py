#!/usr/bin/env python3
"""
agent/login.py —— 在终端里扫码登录 B站（agent 用的那个号）

用法：  python agent/login.py
  · 终端里会打印一个二维码，同时存一张 PNG（终端显示不清就打开图片扫）
  · 用手机 B站 扫码，确认时选「记住我 / 长期」
  · 凭证保存在 BILI_CREDENTIAL_FILE（默认 ~/.bili-agent/bili_credential.json），只在你本机
⚠️ 建议给 agent 用一个**单独的小号**：日报要私信给你本人，B站 不能自己给自己发私信。
"""
import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.pop("BILI_MCP_TOOLS", None)  # 登录脚本需要登录工具，这里不走白名单
_HOME = Path(os.environ.get("BILI_DUTY_HOME") or (Path.home() / ".bili-agent")).expanduser()
_HOME.mkdir(parents=True, exist_ok=True)
os.environ["BILI_DUTY_HOME"] = str(_HOME)
os.environ.setdefault("BILI_CREDENTIAL_FILE", str(_HOME / "bili_credential.json"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "bilibili-mcp"))

import mcp_server as base  # noqa: E402


async def main() -> int:
    if "--force" in sys.argv and base.CRED_FILE.exists():
        base.CRED_FILE.unlink()
    r = json.loads(await base.bili_login())
    if r.get("status") == "already_logged_in":
        print("已经登录过了（要换号就加 --force 重新扫）：", base.CRED_FILE)
        return 0
    print(r.get("qrcode_terminal", ""))
    print("二维码图片：", r.get("qrcode_file"))
    print("请用 B站 App 扫码，确认时选「记住我 / 长期」（180 秒内有效）……")
    for _ in range(90):
        await asyncio.sleep(2)
        s = json.loads(await base.bili_login_check())
        st = s.get("status")
        if st == "done":
            print("登录成功，凭证已保存：", base.CRED_FILE)
            return 0
        if st == "timeout":
            print("二维码过期了，请重新运行。")
            return 1
    print("等太久了，请重新运行。")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
