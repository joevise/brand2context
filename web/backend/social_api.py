"""Social Media API - 独立服务，运行在 Docker 容器外"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
import sqlite3

app = FastAPI(title="Brand2Context Social API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MEDIACRAWLER_PATH = "/opt/MediaCrawler"
VNC_URL = os.environ.get("VNC_URL", "http://67.209.190.54:6080/vnc_lite.html")
VNC_URL_AUTOCONNECT = "http://67.209.190.54:6080/vnc_lite.html?autoconnect=true&resize=scale&reconnect=true"
VALID_PLATFORMS = {"wb", "xhs", "dy"}
_login_process = None


@app.get("/api/social/status")
def get_social_status():
    platforms = {
        "wb": {"name": "微博", "logged_in": True, "login_required": False},
        "xhs": {"name": "小红书", "logged_in": False, "login_required": True},
        "dy": {"name": "抖音", "logged_in": False, "login_required": True},
    }
    
    # 检查小红书：查数据库里有没有 web_session cookie
    platforms["xhs"]["logged_in"] = _check_login_cookie(
        f"{MEDIACRAWLER_PATH}/browser_data/xhs_user_data_dir/Default/Cookies",
        "web_session", "%xiaohongshu%"
    )
    if platforms["xhs"]["logged_in"]:
        platforms["xhs"]["login_required"] = False
    
    # 检查抖音：查数据库里有没有 sessionid cookie
    platforms["dy"]["logged_in"] = _check_login_cookie(
        f"{MEDIACRAWLER_PATH}/browser_data/dy_user_data_dir/Default/Cookies",
        "sessionid", "%douyin%"
    )
    if platforms["dy"]["logged_in"]:
        platforms["dy"]["login_required"] = False

    return {"platforms": platforms, "vnc_url": VNC_URL}


def _check_login_cookie(db_path: str, cookie_name: str, host_pattern: str) -> bool:
    """检查 Chromium cookie 数据库里是否有指定的登录 cookie 且 value 非空"""
    if not os.path.exists(db_path):
        return False
    try:
        db = sqlite3.connect(db_path)
        cursor = db.execute(
            f"SELECT value, encrypted_value FROM cookies WHERE name=? AND host_key LIKE ?",
            (cookie_name, host_pattern)
        )
        row = cursor.fetchone()
        db.close()
        if row is None:
            return False
        value, encrypted_value = row
        # Chromium 加密后 value 为空，encrypted_value 非空
        return bool(value) or (encrypted_value is not None and len(encrypted_value) > 10)
    except Exception:
        return False


@app.post("/api/social/login/{platform}")
def start_social_login(platform: str):
    global _login_process
    
    # 验证平台参数
    if platform not in VALID_PLATFORMS:
        return {"status": "error", "message": f"Invalid platform: {platform}. Must be one of: {VALID_PLATFORMS}"}
    
    # 如果之前的进程已结束，清理掉
    if _login_process is not None:
        if _login_process.poll() is not None:
            _login_process = None
        else:
            # 进程还在跑，先杀掉再重新启动
            _login_process.terminate()
            try:
                _login_process.wait(timeout=5)
            except:
                _login_process.kill()
            _login_process = None

    env = {
        "DISPLAY": os.environ.get("DISPLAY", ":99"),
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/root"),
    }
    cmd = f"cd {MEDIACRAWLER_PATH} && /root/.local/bin/uv run python main.py --platform {platform} --type search --keywords test --headless false --get_comment false"
    _login_process = subprocess.Popen(cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"status": "login_started", "vnc_url": VNC_URL_AUTOCONNECT}


@app.post("/api/social/login/{platform}/cancel")
def cancel_social_login(platform: str):
    global _login_process
    if _login_process is not None:
        _login_process.terminate()
        _login_process = None
    return {"status": "cancelled"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "brand2context-social-api"}


# --- Social Crawl API（供 Docker 容器内的 brand2context 调用） ---

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
