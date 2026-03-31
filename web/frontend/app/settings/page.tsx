"use client";
import { useEffect, useState } from "react";
import { Settings, CheckCircle, XCircle, MinusCircle, Loader2 } from "lucide-react";

type Platform = "weibo" | "xiaohongshu" | "douyin";
type Status = "connected" | "disconnected" | "not_required";

interface SocialStatus {
  weibo: Status;
  xiaohongshu: Status;
  douyin: Status;
}

interface LoginModalProps {
  platform: Platform;
  onClose: () => void;
  onComplete: () => void;
}

const platformConfig = {
  weibo: { name: "微博", description: "获取微博账号发布的品牌内容" },
  xiaohongshu: { name: "小红书", description: "获取小红书笔记和用户互动数据" },
  douyin: { name: "抖音", description: "获取抖音视频内容和粉丝数据" },
};

const statusConfig = {
  connected: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/30", label: "已连接" },
  disconnected: { icon: XCircle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/30", label: "未连接" },
  not_required: { icon: MinusCircle, color: "text-gray-500", bg: "bg-gray-100 dark:bg-gray-900/30", label: "无需登录" },
};

const SOCIAL_API_URL = "http://67.209.190.54:8006";
const platformToApi: Record<Platform, string> = { weibo: "wb", xiaohongshu: "xhs", douyin: "dy" };

function LoginModal({ platform, onClose, onComplete }: LoginModalProps) {
  const [qrcodeUrl, setQrcodeUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginSuccess, setLoginSuccess] = useState(false);

  useEffect(() => {
    const openLogin = async () => {
      try {
        const res = await fetch(`${SOCIAL_API_URL}/api/social/login/${platformToApi[platform]}`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to get login URL");
        const data = await res.json();
        if (data.status === "qrcode_ready") {
          setQrcodeUrl(data.qrcode);
        } else {
          setError(data.message || "Failed to get QR code");
        }
      } catch (err) {
        setError("无法打开登录窗口");
      } finally {
        setLoading(false);
      }
    };
    openLogin();
  }, [platform]);

  useEffect(() => {
    if (!qrcodeUrl) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${SOCIAL_API_URL}/api/social/login/${platformToApi[platform]}/check`);
        if (res.ok) {
          const data = await res.json();
          if (data.logged_in) {
            setLoginSuccess(true);
            clearInterval(interval);
            setTimeout(() => {
              onComplete();
            }, 3000);
          }
        }
      } catch {}
    }, 3000);

    return () => clearInterval(interval);
  }, [qrcodeUrl, platform, onComplete]);

  const handleCancel = async () => {
    try {
      await fetch(`${SOCIAL_API_URL}/api/social/login/${platformToApi[platform]}/cancel`, { method: "POST" });
    } catch {}
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={handleCancel} />
      <div className="relative bg-[var(--card)] rounded-xl shadow-2xl w-[400px] max-w-[95vw]">
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
          <h2 className="text-lg font-semibold">登录 {platformConfig[platform].name}</h2>
          <button
            onClick={handleCancel}
            className="px-4 py-2 rounded-lg bg-[var(--muted)] hover:bg-[var(--muted-foreground)]/20 font-medium transition"
          >
            关闭
          </button>
        </div>
        <div className="p-6 flex flex-col items-center">
          {loading && (
            <div className="flex items-center justify-center h-[300px]">
              <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
            </div>
          )}
          {error && (
            <div className="flex items-center justify-center h-[300px] text-red-500">
              {error}
            </div>
          )}
          {loginSuccess && (
            <div className="flex flex-col items-center justify-center h-[300px] text-green-500">
              <CheckCircle className="w-16 h-16 mb-4" />
              <p className="text-lg font-medium">登录成功</p>
            </div>
          )}
          {qrcodeUrl && !loading && !loginSuccess && (
            <>
              <p className="text-sm text-[var(--muted-foreground)] mb-4">请使用手机扫描二维码登录</p>
              <div className="bg-white p-4 rounded-lg">
                <img
                  src={qrcodeUrl}
                  alt="QR Code"
                  className="w-[300px] h-[300px] object-contain"
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [status, setStatus] = useState<SocialStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loginPlatform, setLoginPlatform] = useState<Platform | null>(null);

  const loadStatus = async () => {
    try {
      const res = await fetch(`${SOCIAL_API_URL}/api/social/status`);
      if (res.ok) {
        const data = await res.json();
        const platformMap: Record<string, Platform> = { wb: "weibo", xhs: "xiaohongshu", dy: "douyin" };
        const mapped: SocialStatus = { weibo: "disconnected", xiaohongshu: "disconnected", douyin: "disconnected" };
        for (const [key, info] of Object.entries(data.platforms || {})) {
          const p = platformMap[key];
          if (!p) continue;
          const i = info as any;
          if (!i.login_required) mapped[p] = i.logged_in ? "connected" : "not_required";
          else mapped[p] = i.logged_in ? "connected" : "disconnected";
        }
        setStatus(mapped);
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => { loadStatus(); }, []);

  const handleLogin = (platform: Platform) => {
    setLoginPlatform(platform);
  };

  const handleModalClose = () => {
    setLoginPlatform(null);
    loadStatus();
  };

  if (loading) {
    return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <div className="flex items-center gap-3 mb-8">
        <Settings className="w-8 h-8 text-primary-600" />
        <h1 className="text-3xl font-bold">社交媒体数据源</h1>
      </div>

      <div className="grid sm:grid-cols-1 gap-4">
        {(Object.keys(platformConfig) as Platform[]).map((platform) => {
          const config = platformConfig[platform];
          const s = statusConfig[status?.[platform] || "disconnected"];
          const Icon = s.icon;
          const isConnected = status?.[platform] === "connected";

          return (
            <div
              key={platform}
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 hover:shadow-lg transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-lg mb-1">{config.name}</h3>
                  <p className="text-sm text-[var(--muted-foreground)]">{config.description}</p>
                </div>
                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${s.bg} ${s.color}`}>
                  <Icon className="w-4 h-4" />
                  {s.label}
                </span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleLogin(platform)}
                  disabled={status?.[platform] === "not_required"}
                  className={`px-4 py-2 rounded-lg font-medium transition ${
                    isConnected
                      ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 cursor-default"
                      : status?.[platform] === "not_required"
                      ? "bg-gray-100 dark:bg-gray-900/30 text-gray-500 cursor-default"
                      : "bg-primary-600 hover:bg-primary-700 text-white"
                  }`}
                >
                  {isConnected ? "已连接" : status?.[platform] === "not_required" ? "无需登录" : "登录"}
                </button>
                {isConnected && (
                  <button
                    onClick={async () => {
                      await fetch(`${SOCIAL_API_URL}/api/social/logout/${platformToApi[platform]}`, { method: "POST" });
                      loadStatus();
                    }}
                    className="px-3 py-2 rounded-lg text-sm bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition"
                  >
                    重新登录
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {loginPlatform && (
        <LoginModal platform={loginPlatform} onClose={handleModalClose} onComplete={handleModalClose} />
      )}
    </div>
  );
}
