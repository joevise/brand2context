"""Social Media API - 独立服务，运行在 Docker 容器外"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
import signal

app = FastAPI(title="Brand2Context Social API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

MEDIACRAWLER_PATH = "/opt/MediaCrawler"
VNC_URL = os.environ.get("VNC_URL", "http://67.209.190.54:6080/vnc.html")
VNC_URL_AUTOCONNECT = "http://67.209.190.54:6080/vnc.html?autoconnect=true&resize=scale"
_login_process = None


@app.get("/api/social/status")
def get_social_status():
    platforms = {
        "wb": {"name": "微博", "logged_in": True, "login_required": False},
        "xhs": {"name": "小红书", "logged_in": False, "login_required": True},
        "dy": {"name": "抖音", "logged_in": False, "login_required": True},
    }
    xhs_cookie_path = (
        f"{MEDIACRAWLER_PATH}/browser_data/xhs_user_data_dir/Default/Cookies"
    )
    dy_cookie_path = (
        f"{MEDIACRAWLER_PATH}/browser_data/dy_user_data_dir/Default/Cookies"
    )

    if os.path.exists(xhs_cookie_path) and os.path.getsize(xhs_cookie_path) > 10240:
        platforms["xhs"]["logged_in"] = True
        platforms["xhs"]["login_required"] = False
    if os.path.exists(dy_cookie_path) and os.path.getsize(dy_cookie_path) > 10240:
        platforms["dy"]["logged_in"] = True
        platforms["dy"]["login_required"] = False

    return {"platforms": platforms, "vnc_url": VNC_URL}


@app.post("/api/social/login/{platform}")
def start_social_login(platform: str):
    global _login_process
    if _login_process is not None:
        return {"status": "already_running", "vnc_url": VNC_URL_AUTOCONNECT}

    env = {
        "DISPLAY": os.environ.get("DISPLAY", ":99"),
        "PATH": os.environ.get("PATH", ""),
    }
    cmd = f"cd {MEDIACRAWLER_PATH} && /root/.local/bin/uv run python main.py --platform {platform} --type search --keywords test --headless false --get_comment false"
    _login_process = subprocess.Popen(cmd, shell=True, env=env)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8006)
