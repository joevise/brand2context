"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  getAdminDashboard,
  getAdminSeeds,
  createSeed,
  aiGenerateSeeds,
  searchAddSeed,
  startBatch,
  getBatchStatus,
  pauseBatch,
  resumeBatch,
  retryFailedBatch,
  getRefreshStatus,
  refreshOutdated,
  getAdminSettings,
  updateAdminSettings,
  AdminDashboard,
  Seed,
  BatchStatus,
  AdminSettings,
  getMe,
  AuthUser,
} from "@/lib/api";
import {
  LayoutDashboard,
  Database,
  Download,
  RefreshCw,
  Plus,
  Search,
  Play,
  Pause,
  RotateCcw,
  Loader2,
  X,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  Sparkles,
  Settings,
  BarChart3,
  Shield,
} from "lucide-react";

const STATUS_COLORS = {
  new: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  done: "bg-green-500/20 text-green-400 border-green-500/30",
  outdated: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  processing: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
};

const STATUS_ICONS = {
  new: <Clock className="w-3 h-3" />,
  done: <CheckCircle className="w-3 h-3" />,
  outdated: <RefreshCw className="w-3 h-3" />,
  processing: <Loader2 className="w-3 h-3 animate-spin" />,
  error: <XCircle className="w-3 h-3" />,
};

function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[var(--card)] rounded-xl p-6 w-full max-w-md shadow-2xl border border-[var(--border)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-[var(--muted)]">
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function AIGenerateModal({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [category, setCategory] = useState("");
  const [count, setCount] = useState(10);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!category.trim()) return;
    setLoading(true);
    try {
      await aiGenerateSeeds({ category: category.trim(), count });
      onSuccess();
      onClose();
      setCategory("");
      setCount(10);
    } catch {} finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="AI 生成品牌">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">品类名称</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="例如：电动汽车"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">生成数量</label>
          <input
            type="number"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            min={1}
            max={100}
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !category.trim()}
          className="w-full py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          <Sparkles className="w-4 h-4" />
          生成品牌
        </button>
      </form>
    </Modal>
  );
}

function SearchAddModal({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [brandName, setBrandName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) return;
    setLoading(true);
    try {
      await searchAddSeed({ brand_name: brandName.trim() });
      onSuccess();
      onClose();
      setBrandName("");
    } catch {} finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="搜索添加品牌">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">品牌名称</label>
          <input
            type="text"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="输入品牌名称进行搜索"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !brandName.trim()}
          className="w-full py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          <Search className="w-4 h-4" />
          搜索并添加
        </button>
      </form>
    </Modal>
  );
}

function ManualAddModal({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    setLoading(true);
    try {
      await createSeed({ name: name.trim(), url: url.trim(), category: category.trim() });
      onSuccess();
      onClose();
      setName("");
      setUrl("");
      setCategory("");
    } catch {} finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="手动添加种子">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">品牌名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="品牌名称"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">官网 URL</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">品类</label>
          <input
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="品类名称"
            className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !name.trim() || !url.trim()}
          className="w-full py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          <Plus className="w-4 h-4" />
          添加
        </button>
      </form>
    </Modal>
  );
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<"seeds" | "batch" | "refresh">("seeds");
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [seeds, setSeeds] = useState<Seed[]>([]);
  const [seedsTotal, setSeedsTotal] = useState(0);
  const [seedsCategories, setSeedsCategories] = useState<{ name: string; count: number }[]>([]);
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [refreshStatus, setRefreshStatus] = useState<{ total_brands: number; up_to_date: number; outdated: number; outdated_brands: { id: string; name: string; url: string; last_refreshed: string | null; days_since: number }[]; refresh_cycle_days: number } | null>(null);
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiGenerateOpen, setAiGenerateOpen] = useState(false);
  const [searchAddOpen, setSearchAddOpen] = useState(false);
  const [manualAddOpen, setManualAddOpen] = useState(false);
  const [batchFilter, setBatchFilter] = useState<"new" | "outdated" | "all">("all");
  const [batchSize, setBatchSize] = useState(10);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await getAdminDashboard();
      setDashboard(data);
      const cats = ["all", ...data.brands_by_category.map((c) => c.name)];
      setCategories(cats);
    } catch {}
  }, []);

  const fetchSeeds = useCallback(async () => {
    try {
      const cat = selectedCategory === "all" ? undefined : selectedCategory;
      const data = await getAdminSeeds(cat);
      setSeeds(data.seeds);
      setSeedsTotal(data.total);
      setSeedsCategories(data.categories);
    } catch {}
  }, [selectedCategory]);

  const fetchBatchStatus = useCallback(async () => {
    try {
      const data = await getBatchStatus();
      setBatchStatus(data);
    } catch {}
  }, []);

  const fetchRefreshStatus = useCallback(async () => {
    try {
      const data = await getRefreshStatus();
      setRefreshStatus(data);
    } catch {}
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await getAdminSettings();
      setSettings(data);
    } catch {}
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const u = await getMe();
        setUser(u);
        if (!u.is_admin) {
          setAuthChecked(true);
          setLoading(false);
          return;
        }
        setAuthChecked(true);
        setLoading(true);
        await Promise.all([fetchDashboard(), fetchSeeds(), fetchSettings()]);
        setLoading(false);
      } catch {
        setUser(null);
        setAuthChecked(true);
        setLoading(false);
      }
    };
    checkAuth();
  }, [fetchDashboard, fetchSeeds, fetchSettings]);

  useEffect(() => {
    if (activeTab === "batch") {
      fetchBatchStatus();
      pollingRef.current = setInterval(fetchBatchStatus, 5000);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [activeTab, fetchBatchStatus]);

  useEffect(() => {
    if (activeTab === "refresh") {
      fetchRefreshStatus();
    }
  }, [activeTab, fetchRefreshStatus]);

  useEffect(() => {
    if (!loading && authChecked) {
      fetchSeeds();
    }
  }, [selectedCategory, loading, authChecked, fetchSeeds]);

  const handleStartBatch = async () => {
    try {
      await startBatch({
        category: batchFilter === "all" ? undefined : batchFilter === "new" ? undefined : batchFilter,
        batch_size: batchSize,
        filter: batchFilter,
      });
      fetchBatchStatus();
    } catch {}
  };

  const handlePauseBatch = async () => {
    try {
      await pauseBatch();
      fetchBatchStatus();
    } catch {}
  };

  const handleResumeBatch = async () => {
    try {
      await resumeBatch();
      fetchBatchStatus();
    } catch {}
  };

  const handleRetryFailed = async () => {
    try {
      await retryFailedBatch();
      fetchBatchStatus();
    } catch {}
  };

  const handleRefreshOutdated = async () => {
    try {
      await refreshOutdated({ batch_size: batchSize });
      fetchRefreshStatus();
      fetchDashboard();
    } catch {}
  };

  const handleSettingsUpdate = async () => {
    if (!settings) return;
    try {
      await updateAdminSettings(settings);
    } catch {}
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-950 to-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (authChecked && !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-950 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">请先登录</h2>
          <p className="text-gray-400 mb-6">需要登录后才能访问管理后台</p>
          <Link
            href="/login"
            className="px-6 py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold transition inline-flex items-center gap-2"
          >
            前往登录
          </Link>
        </div>
      </div>
    );
  }

  if (authChecked && user && !user.is_admin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-950 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">无管理员权限</h2>
          <p className="text-gray-400 mb-6">您的账号没有访问管理后台的权限</p>
          <Link
            href="/"
            className="px-6 py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold transition inline-flex items-center gap-2"
          >
            返回首页
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-950 to-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 to-gray-900 text-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary-600/20">
              <Settings className="w-6 h-6 text-primary-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">管理后台</h1>
              <p className="text-sm text-gray-400">Brand2Context 系统管理</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-blue-400" />
              <div>
                <div className="text-2xl font-bold">{dashboard?.total_brands ?? 0}</div>
                <div className="text-xs text-gray-400">总品牌数</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-5 h-5 text-purple-400" />
              <div>
                <div className="text-2xl font-bold">{dashboard?.brands_by_category?.length ?? 0}</div>
                <div className="text-xs text-gray-400">品类数</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 text-orange-400" />
              <div>
                <div className="text-2xl font-bold">{dashboard?.outdated_count ?? 0}</div>
                <div className="text-xs text-gray-400">待更新数</div>
              </div>
            </div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-3">
              <LayoutDashboard className="w-5 h-5 text-green-400" />
              <div>
                <div className="text-2xl font-bold">{dashboard?.total_api_calls ?? 0}</div>
                <div className="text-xs text-gray-400">API调用总数</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-8">
          <div className="col-span-2 bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-4">品类分布</h3>
            <div className="space-y-2">
              {dashboard?.brands_by_category.map((cat) => {
                const total = dashboard.brands_by_category.reduce((a, b) => a + b.count, 0);
                const pct = total > 0 ? (cat.count / total) * 100 : 0;
                return (
                  <div key={cat.name} className="flex items-center gap-3">
                    <div className="w-24 text-sm truncate">{cat.name}</div>
                    <div className="flex-1 h-4 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-600 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="w-12 text-sm text-right text-gray-400">{cat.count}</div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-400">最近失败 ({dashboard?.brands_by_status?.error ?? 0})</h3>
              {(dashboard?.brands_by_status?.error ?? 0) > 0 && (
                <button
                  onClick={async () => {
                    try {
                      const { retryDBErrors } = await import("@/lib/api");
                      const result = await retryDBErrors(10);
                      alert(`已启动重试 ${result.count} 个失败品牌`);
                      fetchDashboard();
                      fetchBatchStatus();
                    } catch {}
                  }}
                  className="px-3 py-1 rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 text-xs font-medium hover:bg-red-600/30 transition flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" /> 重试全部失败
                </button>
              )}
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {dashboard?.failed_brands.length === 0 && (
                <div className="text-sm text-gray-500 text-center py-4">暂无失败记录</div>
              )}
              {dashboard?.failed_brands.map((f, i) => (
                <div key={i} className="p-2 rounded bg-red-950/30 border border-red-900/30">
                  <div className="text-sm font-medium truncate">{f.name || "(unnamed)"}</div>
                  <div className="text-xs text-red-400 truncate">{f.error_message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-gray-900/50 rounded-xl border border-gray-800">
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => setActiveTab("seeds")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "seeds"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Database className="w-4 h-4 inline mr-2" />
              种子库管理
            </button>
            <button
              onClick={() => setActiveTab("batch")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "batch"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Download className="w-4 h-4 inline mr-2" />
              批量爬取
            </button>
            <button
              onClick={() => setActiveTab("refresh")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "refresh"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <RefreshCw className="w-4 h-4 inline mr-2" />
              更新调度
            </button>
          </div>

          <div className="p-6">
            {activeTab === "seeds" && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex gap-2 overflow-x-auto">
                    {categories.map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setSelectedCategory(cat)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                          selectedCategory === cat
                            ? "bg-primary-600 text-white"
                            : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                        }`}
                      >
                        {cat === "all" ? "全部" : cat}
                      </button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setAiGenerateOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-600/30 text-xs font-medium hover:bg-purple-600/30 transition flex items-center gap-1"
                    >
                      <Sparkles className="w-3 h-3" />
                      AI 生成
                    </button>
                    <button
                      onClick={() => setSearchAddOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-600/30 text-xs font-medium hover:bg-blue-600/30 transition flex items-center gap-1"
                    >
                      <Search className="w-3 h-3" />
                      搜索添加
                    </button>
                    <button
                      onClick={() => setManualAddOpen(true)}
                      className="px-3 py-1.5 rounded-lg bg-green-600/20 text-green-400 border border-green-600/30 text-xs font-medium hover:bg-green-600/30 transition flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      手动添加
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-800">
                        <th className="pb-3 font-medium">名称</th>
                        <th className="pb-3 font-medium">官网</th>
                        <th className="pb-3 font-medium">品类</th>
                        <th className="pb-3 font-medium">状态</th>
                        <th className="pb-3 font-medium">品牌ID</th>
                        <th className="pb-3 font-medium">上次刷新</th>
                      </tr>
                    </thead>
                    <tbody>
                      {seeds.map((seed, i) => (
                        <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-3 font-medium">{seed.name}</td>
                          <td className="py-3 text-gray-400 truncate max-w-[200px]">{seed.url}</td>
                          <td className="py-3 text-gray-400">{seed.category}</td>
                          <td className="py-3">
                            <span
                              className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs border ${
                                STATUS_COLORS[seed.status]
                              }`}
                            >
                              {STATUS_ICONS[seed.status]}
                              {seed.status}
                            </span>
                          </td>
                          <td className="py-3 text-gray-400 text-xs truncate max-w-[100px]">
                            {seed.brand_id || "-"}
                          </td>
                          <td className="py-3 text-gray-400 text-xs">
                            {seed.last_refreshed ? new Date(seed.last_refreshed).toLocaleDateString() : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {seeds.length === 0 && (
                    <div className="text-center py-8 text-gray-500">暂无种子数据</div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "batch" && (
              <div>
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">品类筛选</label>
                    <select
                      value={batchFilter}
                      onChange={(e) => setBatchFilter(e.target.value as "new" | "outdated" | "all")}
                      className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    >
                      <option value="all">全部</option>
                      <option value="new">新品牌</option>
                      <option value="outdated">过期</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">每批数量</label>
                    <input
                      type="number"
                      value={batchSize}
                      onChange={(e) => setBatchSize(Number(e.target.value))}
                      min={1}
                      max={100}
                      className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    />
                  </div>
                  <div className="col-span-2 flex items-end gap-2">
                    <button
                      onClick={handleStartBatch}
                      className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium text-sm transition flex items-center gap-2"
                    >
                      <Play className="w-4 h-4" />
                      开始爬取
                    </button>
                    <button
                      onClick={handlePauseBatch}
                      className="px-4 py-2 rounded-lg bg-yellow-600/20 text-yellow-400 border border-yellow-600/30 font-medium text-sm hover:bg-yellow-600/30 transition flex items-center gap-2"
                    >
                      <Pause className="w-4 h-4" />
                      暂停
                    </button>
                    <button
                      onClick={handleResumeBatch}
                      className="px-4 py-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-600/30 font-medium text-sm hover:bg-blue-600/30 transition flex items-center gap-2"
                    >
                      <Play className="w-4 h-4" />
                      继续
                    </button>
                    <button
                      onClick={handleRetryFailed}
                      className="px-4 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 font-medium text-sm hover:bg-red-600/30 transition flex items-center gap-2"
                    >
                      <RotateCcw className="w-4 h-4" />
                      重试失败
                    </button>
                  </div>
                </div>

                <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium">实时状态</h4>
                    <div className="text-xs text-gray-500">每5秒自动刷新</div>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="text-center p-3 rounded bg-gray-900/50">
                      <div className="text-2xl font-bold text-green-400">{batchStatus?.completed ?? 0}</div>
                      <div className="text-xs text-gray-400">完成</div>
                    </div>
                    <div className="text-center p-3 rounded bg-gray-900/50">
                      <div className="text-2xl font-bold text-blue-400">{batchStatus?.processing ?? 0}</div>
                      <div className="text-xs text-gray-400">进行中</div>
                    </div>
                    <div className="text-center p-3 rounded bg-gray-900/50">
                      <div className="text-2xl font-bold text-gray-400">{batchStatus?.queued ?? 0}</div>
                      <div className="text-xs text-gray-400">排队</div>
                    </div>
                    <div className="text-center p-3 rounded bg-gray-900/50">
                      <div className="text-2xl font-bold text-red-400">{batchStatus?.failed ?? 0}</div>
                      <div className="text-xs text-gray-400">失败</div>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-400 mb-2">
                      <span>进度</span>
                      <span>
                        {(batchStatus?.completed ?? 0)} / {(batchStatus?.total ?? 0)}
                      </span>
                    </div>
                    <div className="h-3 bg-gray-900 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-600 rounded-full transition-all"
                        style={{
                          width: `${
                            batchStatus?.total
                              ? ((batchStatus.completed + batchStatus.processing) / batchStatus.total) * 100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {batchStatus?.running_items.map((brand) => (
                      <div
                        key={brand.brand_id}
                        className="flex items-center justify-between p-2 rounded bg-gray-900/50"
                      >
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                          <span className="text-sm">{brand.name}</span>
                        </div>
                        <div className="text-xs text-gray-500">进行中</div>
                      </div>
                    ))}
                    {batchStatus?.completed_items.map((brand) => (
                      <div
                        key={brand.brand_id}
                        className="flex items-center justify-between p-2 rounded bg-gray-900/50"
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-400" />
                          <span className="text-sm">{brand.name}</span>
                        </div>
                        <div className="text-xs text-gray-500">完成</div>
                      </div>
                    ))}
                    {batchStatus?.failed_items.map((brand) => (
                      <div
                        key={brand.brand_id}
                        className="flex items-center justify-between p-2 rounded bg-gray-900/50"
                      >
                        <div className="flex items-center gap-2">
                          <XCircle className="w-4 h-4 text-red-400" />
                          <span className="text-sm">{brand.name}</span>
                        </div>
                        <div className="text-xs text-gray-500">失败</div>
                      </div>
                    ))}
                    {(!batchStatus || (batchStatus.running_items.length === 0 && batchStatus.completed_items.length === 0 && batchStatus.failed_items.length === 0)) && (
                      <div className="text-center py-4 text-gray-500 text-sm">暂无正在进行的任务</div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === "refresh" && (
              <div>
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">更新周期（天）</label>
                    <input
                      type="number"
                      value={settings?.refresh_cycle_days ?? 30}
                      onChange={(e) =>
                        setSettings((prev) =>
                          prev ? { ...prev, refresh_cycle_days: Number(e.target.value) } : null
                        )
                      }
                      min={1}
                      className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">最大并发数</label>
                    <input
                      type="number"
                      value={settings?.max_concurrent ?? 5}
                      onChange={(e) =>
                        setSettings((prev) =>
                          prev ? { ...prev, max_concurrent: Number(e.target.value) } : null
                        )
                      }
                      min={1}
                      className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    />
                  </div>
                </div>
                <button
                  onClick={handleSettingsUpdate}
                  className="mb-6 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm transition"
                >
                  保存设置
                </button>

                <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium">待更新品牌 ({refreshStatus?.outdated ?? 0})</h4>
                    <button
                      onClick={handleRefreshOutdated}
                      className="px-3 py-1.5 rounded-lg bg-orange-600/20 text-orange-400 border border-orange-600/30 text-xs font-medium hover:bg-orange-600/30 transition flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" />
                      立即更新所有过期
                    </button>
                  </div>

                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {refreshStatus?.outdated_brands.map((brand) => (
                      <div
                        key={brand.id}
                        className="flex items-center justify-between p-3 rounded bg-gray-900/50"
                      >
                        <div>
                          <div className="text-sm font-medium">{brand.name}</div>
                          <div className="text-xs text-gray-500 truncate max-w-[300px]">{brand.url}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-orange-400">{brand.days_since} 天</div>
                          <div className="text-xs text-gray-500">未更新</div>
                        </div>
                      </div>
                    ))}
                    {(!refreshStatus || refreshStatus.outdated_brands.length === 0) && (
                      <div className="text-center py-8 text-gray-500 text-sm">所有品牌均为最新</div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <AIGenerateModal
        open={aiGenerateOpen}
        onClose={() => setAiGenerateOpen(false)}
        onSuccess={() => {
          fetchSeeds();
          fetchDashboard();
        }}
      />
      <SearchAddModal
        open={searchAddOpen}
        onClose={() => setSearchAddOpen(false)}
        onSuccess={() => {
          fetchSeeds();
          fetchDashboard();
        }}
      />
      <ManualAddModal
        open={manualAddOpen}
        onClose={() => setManualAddOpen(false)}
        onSuccess={() => {
          fetchSeeds();
          fetchDashboard();
        }}
      />
    </div>
  );
}