#!/usr/bin/env python3
"""
agent/login.py —— 在终端里扫码登录 B站（agent 用的那个号）

用法：  python agent/login.py          已登录且有效就不重复扫
        python agent/login.py --force  强制重新扫码

为什么不用 bilibili-api 自带的扫码登录：17.x 里它把"除了未扫码/待确认/过期之外的任何返回"都当成登录成功，
而且只从跳转链接里取 SESSDATA；B站 现在把 Cookie 放在响应头里，于是会"登录成功"却存下一份空凭证。
这里直接调网页端扫码接口：只有 code == 0 才算成功，Cookie 从响应头和跳转链接两处取，存之前再验一次。

⚠️ 建议给 agent 用一个**单独的小号**：日报要私信给你本人，B站 不能自己给自己发私信。
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import aiohttp

HOME = Path(os.environ.get("BILI_DUTY_HOME") or (Path.home() / ".bili-agent")).expanduser()
HOME.mkdir(parents=True, exist_ok=True)
CRED = Path(os.environ.get("BILI_CREDENTIAL_FILE") or (HOME / "bili_credential.json")).expanduser()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Referer": "https://www.bilibili.com/", "Origin": "https://www.bilibili.com"}
GEN = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
NAV = "https://api.bilibili.com/x/web-interface/nav"
SPI = "https://api.bilibili.com/x/frontend/finger/spi"


def cookie_header(c: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in (
        ("SESSDATA", c.get("sessdata")), ("bili_jct", c.get("bili_jct")),
        ("DedeUserID", c.get("dedeuserid")), ("buvid3", c.get("buvid3"))) if v)


async def whoami(s: aiohttp.ClientSession, c: dict):
    """用 nav 接口验一下凭证：返回 (是否登录, uid, 昵称)"""
    async with s.get(NAV, headers={**HEADERS, "Cookie": cookie_header(c)}) as r:
        j = await r.json(content_type=None)
    d = (j or {}).get("data") or {}
    return bool(d.get("isLogin")), str(d.get("mid") or ""), str(d.get("uname") or "")


def show_qr(url: str) -> Path:
    import qrcode
    png = HOME / "qrcode_login.png"
    qrcode.make(url).save(png)
    q = qrcode.QRCode(border=1)
    q.add_data(url)
    q.make(fit=True)
    try:
        q.print_ascii(invert=True)
    except UnicodeEncodeError:
        print("（这个终端显示不了二维码字符，请打开下面的图片扫码）")
    return png


async def main() -> int:
    async with aiohttp.ClientSession() as s:
        if CRED.exists() and "--force" not in sys.argv:
            try:
                old = json.loads(CRED.read_text(encoding="utf-8"))
                ok, uid, name = await whoami(s, old)
                if ok:
                    print(f"已经登录：{name}（UID {uid}）。要换号就加 --force。")
                    return 0
            except Exception:  # noqa: BLE001
                pass
            print("现有凭证无效，重新扫码。")

        async with s.get(GEN, headers=HEADERS) as r:
            j = await r.json(content_type=None)
        if (j or {}).get("code") != 0:
            print("生成二维码失败：", j)
            return 1
        url, key = j["data"]["url"], j["data"]["qrcode_key"]
        png = show_qr(url)
        print("二维码图片：", png)
        print("请用 B站 App（agent 的小号）扫码，并在手机上点确认登录。180 秒内有效……")

        deadline = time.time() + 180
        while time.time() < deadline:
            await asyncio.sleep(2)
            async with s.get(POLL, params={"qrcode_key": key}, headers=HEADERS) as r:
                j = await r.json(content_type=None)
                set_cookies = {k: m.value for k, m in r.cookies.items()}
            d = (j or {}).get("data") or {}
            code = d.get("code")
            if code == 86101:      # 还没扫
                continue
            if code == 86090:      # 扫了，等手机上确认
                print("已扫码，请在手机上确认……")
                continue
            if code == 86038:
                print("二维码过期了，请重新运行。")
                return 1
            if code != 0:
                print("登录没有成功：", d.get("message") or j)
                return 1

            # 成功：Cookie 先看响应头，再看跳转链接里的参数
            q = dict(parse_qsl(urlparse(d.get("url") or "").query))
            jar = {m.key: m.value for m in s.cookie_jar}
            pick = lambda name: set_cookies.get(name) or jar.get(name) or q.get(name) or ""  # noqa: E731
            cred = {
                "sessdata": pick("SESSDATA"),
                "bili_jct": pick("bili_jct"),
                "dedeuserid": pick("DedeUserID"),
                "buvid3": jar.get("buvid3", ""),
                "ac_time_value": d.get("refresh_token") or "",
            }
            if not cred["buvid3"]:
                try:
                    async with s.get(SPI, headers=HEADERS) as r2:
                        cred["buvid3"] = ((await r2.json(content_type=None)) or {}).get("data", {}).get("b_3", "")
                except Exception:  # noqa: BLE001
                    pass
            if not cred["sessdata"]:
                print("B站 说登录成功了，但没拿到 SESSDATA。请把这行发给开发者：",
                      {"set_cookie": list(set_cookies), "url_params": list(q)})
                return 1
            ok, uid, name = await whoami(s, cred)
            if not ok:
                print("拿到了凭证，但验证没通过（nav 接口说没登录）。请重试一次。")
                return 1
            cred["dedeuserid"] = cred["dedeuserid"] or uid
            tmp = CRED.with_name(CRED.name + ".tmp")
            tmp.write_text(json.dumps(cred, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, CRED)
            try:
                png.unlink()
            except OSError:
                pass
            print(f"登录成功：{name}（UID {uid}），凭证已保存：{CRED}")
            return 0
        print("等太久了，二维码已失效，请重新运行。")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
