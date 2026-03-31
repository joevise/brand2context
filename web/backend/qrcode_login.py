#!/usr/bin/env python3
"""QR Code Login Script - 使用 Playwright 获取社交媒体登录二维码"""

import asyncio
import base64
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

PLATFORM_CONFIG = {
    "wb": {
        "name": "微博",
        "url": "https://weibo.com",
        "qrcode_selector": "//img[@class='w-full h-full']",
        "qrcode_type": "img",
        "login_button": None,
        "login_check": "cookie",
        "login_cookie_name": "SUB",
    },
    "xhs": {
        "name": "小红书",
        "url": "https://www.xiaohongshu.com",
        "qrcode_selector": "xpath=//img[@class='qrcode-img']",
        "qrcode_type": "img",
        "login_button": "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button",
        "login_check": "cookie",
        "login_cookie_name": "web_session",
    },
    "dy": {
        "name": "抖音",
        "url": "https://www.douyin.com",
        "qrcode_selector": "//canvas",
        "qrcode_type": "canvas",
        "login_button": "//p[text() = '登录']",
        "login_check": "cookie",
        "login_cookie_name": "sessionid",
    },
}


async def get_qrcode_base64(page, config):
    """从页面获取二维码图片的 base64 编码"""
    qrcode_type = config["qrcode_type"]
    selector = config["qrcode_selector"]

    if qrcode_type == "img":
        locator = page.locator(selector)
        await locator.wait_for(timeout=30000)
        img_src = await locator.get_attribute("src")
        if img_src:
            if img_src.startswith("data:image"):
                return img_src
            elif img_src.startswith("http"):
                async with page.context.request.get(img_src) as resp:
                    if resp.ok:
                        content = await resp.body()
                        return f"data:image/png;base64,{base64.b64encode(content).decode()}"
    elif qrcode_type == "canvas":
        locator = page.locator(selector)
        await locator.wait_for(timeout=30000)
        # 直接对 canvas 元素截图
        screenshot_bytes = await locator.screenshot(type="png")
        if screenshot_bytes:
            return f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode()}"

    return None


async def check_login_success(context, config):
    """检查登录是否成功"""
    cookie_name = config["login_cookie_name"]
    cookies = await context.cookies()
    for cookie in cookies:
        if cookie["name"] == cookie_name and cookie["value"]:
            return True
    return False


async def main(platform: str):
    if platform not in PLATFORM_CONFIG:
        print(
            json.dumps({"status": "error", "message": f"Invalid platform: {platform}"})
        )
        sys.stdout.flush()
        return

    config = PLATFORM_CONFIG[platform]
    user_data_dir = f"/opt/MediaCrawler/browser_data/{platform}_user_data_dir"
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # 必须非 headless，否则被反爬检测
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto(config["url"], wait_until="networkidle", timeout=60000)
        print(json.dumps({"status": "page_loaded", "title": await page.title()}), flush=True)

        if config["login_button"]:
            try:
                login_btn = page.locator(config["login_button"])
                await login_btn.click(timeout=10000)
                await page.wait_for_timeout(3000)
                print(json.dumps({"status": "login_button_clicked"}), flush=True)
            except Exception as e:
                print(json.dumps({"status": "login_button_failed", "error": str(e)[:200]}), flush=True)

        qrcode_b64 = await get_qrcode_base64(page, config)
        if qrcode_b64:
            print(json.dumps({"status": "qrcode_ready", "qrcode": qrcode_b64}))
        else:
            # 尝试整个页面截图作为 fallback
            page_screenshot = await page.screenshot(type="png")
            fallback_b64 = f"data:image/png;base64,{base64.b64encode(page_screenshot).decode()}"
            print(json.dumps({"status": "qrcode_ready", "qrcode": fallback_b64, "fallback": True}))
        sys.stdout.flush()

        while True:
            line = sys.stdin.readline().strip()
            if not line:
                break
            if line == "check":
                logged_in = await check_login_success(context, config)
                print(json.dumps({"logged_in": logged_in}))
                sys.stdout.flush()
                if logged_in:
                    await context.close()
                    return
            elif line == "close":
                await context.close()
                return


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Platform argument required"}))
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
