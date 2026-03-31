"""Social Media API - 独立服务，使用 Playwright 获取二维码登录"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
import sqlite3
import json
import time
import signal

app = FastAPI(title="Brand2Context Social API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MEDIACRAWLER_PATH = "/opt/MediaCrawler"
VALID_PLATFORMS = {"wb", "xhs", "dy"}

_qrcode_process = {}
_qrcode_start_time = {}


@app.get("/api/social/status")
def get_social_status():
    platforms = {
        "wb": {"name": "微博", "logged_in": True, "login_required": False},
        "xhs": {"name": "小红书", "logged_in": False, "login_required": True},
        "dy": {"name": "抖音", "logged_in": False, "login_required": True},
    }

    platforms["xhs"]["logged_in"] = _check_login_cookie(
        f"{MEDIACRAWLER_PATH}/browser_data/xhs_user_data_dir/Default/Cookies",
        "web_session",
        "%xiaohongshu%",
    )
    if platforms["xhs"]["logged_in"]:
        platforms["xhs"]["login_required"] = False

    platforms["dy"]["logged_in"] = _check_login_cookie(
        f"{MEDIACRAWLER_PATH}/browser_data/dy_user_data_dir/Default/Cookies",
        "sessionid",
        "%douyin%",
    )
    if platforms["dy"]["logged_in"]:
        platforms["dy"]["login_required"] = False

    return {"platforms": platforms}


def _check_login_cookie(db_path: str, cookie_name: str, host_pattern: str) -> bool:
    if not os.path.exists(db_path):
        return False
    try:
        db = sqlite3.connect(db_path)
        cursor = db.execute(
            f"SELECT value, encrypted_value FROM cookies WHERE name=? AND host_key LIKE ?",
            (cookie_name, host_pattern),
        )
        row = cursor.fetchone()
        db.close()
        if row is None:
            return False
        value, encrypted_value = row
        return bool(value) or (
            encrypted_value is not None and len(encrypted_value) > 10
        )
    except Exception:
        return False


def _kill_existing_browser_processes(platform: str):
    """确保没有旧的 Playwright 进程残留"""
    try:
        subprocess.run(
            ["pkill", "-f", f"qrcode_login.py {platform}"], capture_output=True
        )
        time.sleep(0.5)
    except Exception:
        pass


@app.post("/api/social/login/{platform}")
def start_social_login(platform: str):
    global _qrcode_process, _qrcode_start_time

    if platform not in VALID_PLATFORMS:
        return {
            "status": "error",
            "message": f"Invalid platform: {platform}. Must be one of: {VALID_PLATFORMS}",
        }

    _kill_existing_browser_processes(platform)

    if platform in _qrcode_process and _qrcode_process[platform].poll() is None:
        _qrcode_process[platform].terminate()
        try:
            _qrcode_process[platform].wait(timeout=5)
        except:
            _qrcode_process[platform].kill()

    script_path = os.path.join(os.path.dirname(__file__), "qrcode_login.py")
    # 使用 MediaCrawler 的 venv（里面有 playwright）
    python_path = os.path.join(MEDIACRAWLER_PATH, ".venv", "bin", "python3")
    if not os.path.exists(python_path):
        python_path = "python3"  # fallback
    _qrcode_process[platform] = subprocess.Popen(
        [python_path, script_path, platform],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _qrcode_start_time[platform] = time.time()

    try:
        line = _qrcode_process[platform].stdout.readline()
        if line:
            result = json.loads(line)
            return result
        return {"status": "error", "message": "Failed to start QR code login"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/social/login/{platform}/check")
def check_social_login(platform: str):
    global _qrcode_process, _qrcode_start_time

    if platform not in VALID_PLATFORMS:
        return {"status": "error", "message": f"Invalid platform: {platform}"}

    if (
        platform in _qrcode_start_time
        and time.time() - _qrcode_start_time[platform] > 120
    ):
        if platform in _qrcode_process and _qrcode_process[platform].poll() is None:
            _qrcode_process[platform].terminate()
            _qrcode_process[platform].kill()
        return {"logged_in": False, "status": "timeout"}

    if platform not in _qrcode_process or _qrcode_process[platform].poll() is not None:
        return {"logged_in": False, "status": "process_not_running"}

    try:
        _qrcode_process[platform].stdin.write("check\n")
        _qrcode_process[platform].stdin.flush()
        line = _qrcode_process[platform].stdout.readline()
        if line:
            result = json.loads(line)
            if result.get("logged_in"):
                _qrcode_process[platform].stdin.write("close\n")
                _qrcode_process[platform].stdin.flush()
                _qrcode_process[platform] = None
                _qrcode_start_time.pop(platform, None)
            return result
        return {"logged_in": False}
    except Exception:
        return {"logged_in": False, "status": "error"}


@app.post("/api/social/login/{platform}/cancel")
def cancel_social_login(platform: str):
    global _qrcode_process, _qrcode_start_time

    if platform in _qrcode_process and _qrcode_process[platform].poll() is None:
        try:
            _qrcode_process[platform].stdin.write("close\n")
            _qrcode_process[platform].stdin.flush()
            _qrcode_process[platform].terminate()
            _qrcode_process[platform].wait(timeout=5)
        except:
            _qrcode_process[platform].kill()
    _qrcode_process.pop(platform, None)
    _qrcode_start_time.pop(platform, None)
    return {"status": "cancelled"}


@app.post("/api/social/logout/{platform}")
def logout_platform(platform: str):
    """清除平台登录态，重置为未登录"""
    if platform not in VALID_PLATFORMS:
        return {"status": "error", "message": f"Invalid platform: {platform}"}
    
    # 先取消正在进行的登录
    cancel_social_login(platform)
    
    # 删除 cookie 数据库
    import shutil
    user_data_dir = f"{MEDIACRAWLER_PATH}/browser_data/{platform}_user_data_dir"
    if os.path.exists(user_data_dir):
        shutil.rmtree(user_data_dir, ignore_errors=True)
    
    return {"status": "logged_out"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "brand2context-social-api"}


@app.post("/api/social/crawl/{brand_name}")
def crawl_social(brand_name: str):
    """抓取社交媒体数据，返回统一格式结果"""
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

    from brand2context.social_crawler import crawl_social_media

    results = crawl_social_media(brand_name)
    return {"results": results, "count": len(results)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
