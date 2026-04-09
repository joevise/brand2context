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
  launchIndustry,
  getIndustryStats,
  retryIndustry,
  refreshIndustry,
  refreshAllIndustry,
  IndustryStats,
  getAdminBrands,
  updateBrand,
  adminDeleteBrand,
  batchDeleteBrands,
  batchRefreshBrands,
  refreshBrand,
  cancelBrandTask,
  cancelAllTasks,
  resetStuckTasks,
  Brand,
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
  Rocket,
  Building2,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  CheckSquare,
  Activity,
  Square,
  Ban,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const STATUS_COLORS = {
  new: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  done: "bg-green-500/20 text-green-400 border-green-500/30",
  outdated: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  processing: "bg-blue-500/20 text-blue-400 border-blue-500/30 animate-pulse",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  pending: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

const STATUS_ICONS = {
  new: <Clock className="w-3 h-3" />,
  done: <CheckCircle className="w-3 h-3" />,
  outdated: <RefreshCw className="w-3 h-3" />,
  processing: <Loader2 className="w-3 h-3 animate-spin" />,
  error: <XCircle className="w-3 h-3" />,
  pending: <Clock className="w-3 h-3" />,
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

// ============================================================
// Task Monitor Panel
// ============================================================

const STEP_ORDER = ["pending", "crawling", "searching", "structuring", "done"];
const STEP_LABELS: Record<string, string> = {
  pending: "等待中",
  crawling: "爬取网页",
  searching: "搜索扩展",
  structuring: "LLM 结构化",
  done: "完成",
  error: "出错",
  unknown: "未知",
};

function formatElapsed(startedAt?: string): string {
  if (!startedAt) return "-";
  const start = new Date(startedAt).getTime();
  const now = Date.now();
  const sec = Math.floor((now - start) / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  if (min < 60) return `${min}m ${remSec}s`;
  const hr = Math.floor(min / 60);
  return `${hr}h ${min % 60}m`;
}

function StepProgress({ step }: { step: string }) {
  const activeIdx = STEP_ORDER.indexOf(step);
  return (
    <div className="flex items-center gap-1">
      {STEP_ORDER.slice(1, -1).map((s, i) => {
        const idx = i + 1; // offset because we skip "pending"
        const isActive = step === s;
        const isDone = activeIdx > idx;
        return (
          <div key={s} className="flex items-center gap-1">
            <div
              className={`w-2 h-2 rounded-full transition-all ${
                isActive
                  ? "bg-blue-400 animate-pulse ring-2 ring-blue-400/30"
                  : isDone
                  ? "bg-green-400"
                  : "bg-gray-600"
              }`}
              title={STEP_LABELS[s]}
            />
            {i < 2 && (
              <div className={`w-4 h-0.5 ${isDone ? "bg-green-400/50" : "bg-gray-700"}`} />
            )}
          </div>
        );
      })}
      <span className={`ml-2 text-xs ${step === "error" ? "text-red-400" : "text-gray-400"}`}>
        {STEP_LABELS[step] || step}
      </span>
    </div>
  );
}

function TaskMonitorPanel({
  batchStatus,
  onPause,
  onResume,
  onCancelBrand,
  onCancelAll,
  onRetryFailed,
  onRefreshBrand,
  onResetStuck,
}: {
  batchStatus: BatchStatus | null;
  onPause: () => void;
  onResume: () => void;
  onCancelBrand: (brandId: string) => void;
  onCancelAll: () => void;
  onRetryFailed: () => void;
  onRefreshBrand: (brandId: string) => void;
  onResetStuck: () => void;
}) {
  const [expandedFailed, setExpandedFailed] = useState<Set<string>>(new Set());
  const [showCompleted, setShowCompleted] = useState(false);

  if (!batchStatus) {
    return (
      <div className="text-center py-16 text-gray-500">
        <Activity className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg font-medium mb-1">暂无任务</p>
        <p className="text-sm">在「行业管理」或「批量爬取」中启动任务后，这里会显示实时进度</p>
      </div>
    );
  }

  const total = batchStatus.total || 0;
  const completed = batchStatus.completed || 0;
  const failed = batchStatus.failed || 0;
  const cancelled = batchStatus.cancelled || 0;
  const processing = batchStatus.processing || 0;
  const queued = batchStatus.queued || 0;
  const progressPct = total > 0 ? Math.round(((completed + failed + cancelled) / total) * 100) : 0;
  const isActive = processing > 0 || queued > 0;
  const isDone = total > 0 && processing === 0 && queued === 0;

  const toggleFailed = (id: string) => {
    setExpandedFailed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-1">运行中</div>
          <div className="text-2xl font-bold text-blue-400">{processing}</div>
        </div>
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-1">排队中</div>
          <div className="text-2xl font-bold text-yellow-400">{queued}</div>
        </div>
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-1">已完成</div>
          <div className="text-2xl font-bold text-green-400">{completed}</div>
        </div>
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-1">失败</div>
          <div className="text-2xl font-bold text-red-400">{failed}</div>
        </div>
        <div className="bg-gray-800/60 rounded-xl p-4 border border-gray-700">
          <div className="text-xs text-gray-400 mb-1">总计</div>
          <div className="text-2xl font-bold text-gray-200">{total}</div>
        </div>
      </div>

      {/* Progress Bar + Controls */}
      <div className="bg-gray-800/40 rounded-xl p-4 border border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">
              {isDone ? "✅ 批次完成" : isActive ? "⏳ 进行中" : total === 0 ? "等待任务" : "已暂停"}
            </span>
            {batchStatus.task_id && (
              <span className="text-xs text-gray-500 font-mono">#{batchStatus.task_id}</span>
            )}
            {batchStatus.paused && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                已暂停
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isActive && !batchStatus.paused && (
              <button
                onClick={onPause}
                className="px-3 py-1.5 rounded-lg bg-yellow-600/20 text-yellow-400 border border-yellow-600/30 text-xs font-medium hover:bg-yellow-600/30 transition flex items-center gap-1"
              >
                <Pause className="w-3 h-3" /> 暂停
              </button>
            )}
            {batchStatus.paused && (
              <button
                onClick={onResume}
                className="px-3 py-1.5 rounded-lg bg-green-600/20 text-green-400 border border-green-600/30 text-xs font-medium hover:bg-green-600/30 transition flex items-center gap-1"
              >
                <Play className="w-3 h-3" /> 继续
              </button>
            )}
            {queued > 0 && (
              <button
                onClick={onCancelAll}
                className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 text-xs font-medium hover:bg-red-600/30 transition flex items-center gap-1"
              >
                <Ban className="w-3 h-3" /> 取消排队 ({queued})
              </button>
            )}
            {failed > 0 && (
              <button
                onClick={onRetryFailed}
                className="px-3 py-1.5 rounded-lg bg-orange-600/20 text-orange-400 border border-orange-600/30 text-xs font-medium hover:bg-orange-600/30 transition flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> 重试失败 ({failed})
              </button>
            )}
            <button
              onClick={onResetStuck}
              className="px-3 py-1.5 rounded-lg bg-gray-600/20 text-gray-400 border border-gray-600/30 text-xs font-medium hover:bg-gray-600/30 transition flex items-center gap-1"
              title="重置所有卡住的任务（processing/pending → error），清空队列"
            >
              <Ban className="w-3 h-3" /> 重置卡住
            </button>
          </div>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-500 ${
              isDone ? "bg-green-500" : "bg-blue-500"
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <div className="text-xs text-gray-500 mt-1 text-right">
          {completed + failed + cancelled} / {total} ({progressPct}%)
        </div>
      </div>

      {/* Running Tasks */}
      {batchStatus.running_items.length > 0 && (
        <div className="bg-gray-800/40 rounded-xl border border-gray-700 overflow-hidden">
          <div className="px-4 py-3 bg-blue-500/10 border-b border-gray-700 flex items-center gap-2">
            <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
            <span className="text-sm font-medium text-blue-400">正在运行 ({processing})</span>
          </div>
          <div className="divide-y divide-gray-700/50">
            {batchStatus.running_items.map((item) => (
              <div key={item.brand_id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-700/20 transition">
                <div className="flex-1 min-w-0 mr-4">
                  <div className="text-sm font-medium truncate">{item.name || "—"}</div>
                  <div className="text-xs text-gray-500 truncate">{item.url}</div>
                </div>
                <div className="flex items-center gap-4">
                  <StepProgress step={item.progress_step || "pending"} />
                  <span className="text-xs text-gray-500 font-mono w-16 text-right">
                    {formatElapsed(item.started_at)}
                  </span>
                  <button
                    onClick={() => onCancelBrand(item.brand_id)}
                    className="p-1 rounded hover:bg-red-500/20 text-gray-500 hover:text-red-400 transition"
                    title="取消此任务"
                  >
                    <Square className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Failed Tasks */}
      {batchStatus.failed_items.length > 0 && (
        <div className="bg-gray-800/40 rounded-xl border border-red-900/30 overflow-hidden">
          <div className="px-4 py-3 bg-red-500/10 border-b border-gray-700 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-400" />
            <span className="text-sm font-medium text-red-400">失败 ({failed})</span>
          </div>
          <div className="divide-y divide-gray-700/50">
            {batchStatus.failed_items.map((item, idx) => {
              const key = item.brand_id || `f-${idx}`;
              const isExpanded = expandedFailed.has(key);
              return (
                <div key={key}>
                  <div
                    className="px-4 py-3 flex items-center justify-between hover:bg-gray-700/20 transition cursor-pointer"
                    onClick={() => toggleFailed(key)}
                  >
                    <div className="flex-1 min-w-0 mr-4">
                      <div className="text-sm font-medium truncate">{item.name || "—"}</div>
                      <div className="text-xs text-gray-500 truncate">{item.url}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.brand_id && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onRefreshBrand(item.brand_id); }}
                          className="px-2 py-1 rounded text-xs bg-orange-600/20 text-orange-400 hover:bg-orange-600/30 transition"
                        >
                          重试
                        </button>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-500" />
                      )}
                    </div>
                  </div>
                  {isExpanded && item.error && (
                    <div className="px-4 pb-3">
                      <div className="p-3 rounded bg-red-950/30 border border-red-900/20 text-xs text-red-300 font-mono whitespace-pre-wrap break-all">
                        {item.error}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed Tasks (collapsible) */}
      {batchStatus.completed_items.length > 0 && (
        <div className="bg-gray-800/40 rounded-xl border border-gray-700 overflow-hidden">
          <div
            className="px-4 py-3 bg-green-500/10 border-b border-gray-700 flex items-center justify-between cursor-pointer hover:bg-green-500/15 transition"
            onClick={() => setShowCompleted(!showCompleted)}
          >
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm font-medium text-green-400">已完成 ({completed})</span>
            </div>
            {showCompleted ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </div>
          {showCompleted && (
            <div className="divide-y divide-gray-700/50 max-h-60 overflow-y-auto">
              {batchStatus.completed_items.slice().reverse().map((item, idx) => (
                <div key={item.brand_id || `c-${idx}`} className="px-4 py-2 flex items-center justify-between">
                  <div className="flex-1 min-w-0 mr-4">
                    <div className="text-sm truncate">{item.name || "—"}</div>
                    <div className="text-xs text-gray-500 truncate">{item.url}</div>
                  </div>
                  <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================

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
  const [activeTab, setActiveTab] = useState<"seeds" | "batch" | "refresh" | "industry" | "brands" | "tasks">("seeds");
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
  const [batchCategory, setBatchCategory] = useState<string>("all");
  const [batchSize, setBatchSize] = useState(10);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [industryStats, setIndustryStats] = useState<IndustryStats[]>([]);
  const [launchLoading, setLaunchLoading] = useState(false);
  const [launchIndustryName, setLaunchIndustryName] = useState("");
  const [launchCount, setLaunchCount] = useState(30);
  const [adminBrands, setAdminBrands] = useState<Brand[]>([]);
  const [adminBrandsTotal, setAdminBrandsTotal] = useState(0);
  const [adminBrandsPage, setAdminBrandsPage] = useState(1);
  const [adminBrandsCategory, setAdminBrandsCategory] = useState("all");
  const [adminBrandsStatus, setAdminBrandsStatus] = useState("all");
  const [adminBrandsSearch, setAdminBrandsSearch] = useState("");
  const [selectedBrandIds, setSelectedBrandIds] = useState<Set<string>>(new Set());
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const brandsPollingRef = useRef<NodeJS.Timeout | null>(null);

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

  const fetchIndustryStats = useCallback(async () => {
    try {
      const data = await getIndustryStats();
      setIndustryStats(data.industries);
    } catch {}
  }, []);

  const fetchAdminBrands = useCallback(async () => {
    try {
      const params: any = { page: adminBrandsPage, per_page: 20 };
      if (adminBrandsCategory !== "all") params.category = adminBrandsCategory;
      if (adminBrandsStatus !== "all") params.status = adminBrandsStatus;
      if (adminBrandsSearch) params.q = adminBrandsSearch;
      const data = await getAdminBrands(params);
      setAdminBrands(data.brands);
      setAdminBrandsTotal(data.total);
    } catch {}
  }, [adminBrandsPage, adminBrandsCategory, adminBrandsStatus, adminBrandsSearch]);

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
        await Promise.all([fetchDashboard(), fetchSeeds(), fetchSettings(), fetchIndustryStats()]);
        setLoading(false);
      } catch {
        setUser(null);
        setAuthChecked(true);
        setLoading(false);
      }
    };
    checkAuth();
  }, [fetchDashboard, fetchSeeds, fetchSettings, fetchIndustryStats]);

  useEffect(() => {
    if (activeTab === "batch") {
      fetchBatchStatus();
      pollingRef.current = setInterval(fetchBatchStatus, 5000);
    } else if (activeTab === "tasks") {
      fetchBatchStatus();
      const interval = batchStatus?.processing ? 3000 : 10000;
      pollingRef.current = setInterval(fetchBatchStatus, interval);
    } else if (activeTab === "industry") {
      fetchIndustryStats();
      pollingRef.current = setInterval(fetchIndustryStats, 10000);
    } else if (activeTab === "brands") {
      fetchAdminBrands();
      brandsPollingRef.current = setInterval(fetchAdminBrands, 10000);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (brandsPollingRef.current) clearInterval(brandsPollingRef.current);
    };
  }, [activeTab, fetchBatchStatus, fetchIndustryStats, fetchAdminBrands]);

  useEffect(() => {
    if (activeTab === "refresh") {
      fetchRefreshStatus();
    }
  }, [activeTab, fetchRefreshStatus]);

  useEffect(() => {
    if (activeTab === "industry") {
      fetchIndustryStats();
    }
  }, [activeTab, fetchIndustryStats]);

  useEffect(() => {
    if (!loading && authChecked) {
      fetchSeeds();
    }
  }, [selectedCategory, loading, authChecked, fetchSeeds]);

  useEffect(() => {
    if (activeTab === "brands" && authChecked) {
      fetchAdminBrands();
    }
  }, [activeTab, authChecked, fetchAdminBrands]);

  const handleStartBatch = async () => {
    try {
      await startBatch({
        category: batchCategory === "all" ? undefined : batchCategory,
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

  const handleLaunchIndustry = async () => {
    if (!launchIndustryName.trim()) return;
    setLaunchLoading(true);
    try {
      const result = await launchIndustry({
        industry: launchIndustryName.trim(),
        count: launchCount,
      });
      alert(`已导入 ${result.brands_added} 个品牌并开始抓取 ${result.brands_started} 个`);
      setLaunchIndustryName("");
      fetchIndustryStats();
      fetchDashboard();
      fetchSeeds();
    } catch {
      alert("启动失败");
    } finally {
      setLaunchLoading(false);
    }
  };

  const handleRetryIndustry = async (industry: string) => {
    try {
      const result = await retryIndustry(industry);
      alert(result.message);
      fetchIndustryStats();
    } catch {
      alert("重试失败");
    }
  };

  const handleRefreshIndustryFn = async (industry: string) => {
    try {
      const result = await refreshIndustry(industry);
      alert(result.message);
      fetchIndustryStats();
    } catch {
      alert("刷新失败");
    }
  };

  const handleRefreshAllIndustry = async (industry: string) => {
    try {
      const result = await refreshAllIndustry(industry);
      alert(result.message);
      fetchIndustryStats();
    } catch {
      alert("刷新全部失败");
    }
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

        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-400">行业概览</h3>
            <button
              onClick={() => setActiveTab("industry")}
              className="text-xs text-primary-400 hover:text-primary-300 transition"
            >
              查看全部
            </button>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {industryStats.slice(0, 10).map((industry) => (
              <button
                key={industry.name}
                onClick={() => {
                  setAdminBrandsCategory(industry.name);
                  setActiveTab("brands");
                }}
                className="flex-shrink-0 rounded-xl border border-gray-700 bg-gray-800/50 p-3 min-w-[140px] hover:bg-gray-800/80 transition"
              >
                <div className="text-sm font-medium mb-2 truncate">{industry.name}</div>
                <div className="text-lg font-bold text-green-400">{Math.round(industry.completion_rate * 100)}%</div>
                <div className="text-xs text-gray-500">完成率</div>
              </button>
            ))}
            {industryStats.length === 0 && (
              <div className="text-sm text-gray-500 py-4">暂无行业数据</div>
            )}
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
              onClick={() => setActiveTab("industry")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "industry"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Building2 className="w-4 h-4 inline mr-2" />
              行业管理
            </button>
            <button
              onClick={() => setActiveTab("brands")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "brands"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Database className="w-4 h-4 inline mr-2" />
              品牌管理
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
            <button
              onClick={() => setActiveTab("tasks")}
              className={`px-6 py-3 text-sm font-medium transition ${
                activeTab === "tasks"
                  ? "text-primary-400 border-b-2 border-primary-400 bg-primary-950/20"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              <Activity className="w-4 h-4 inline mr-2" />
              任务监控
              {batchStatus && batchStatus.processing > 0 && (
                <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-400 animate-pulse">
                  {batchStatus.processing}
                </span>
              )}
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

            {activeTab === "industry" && (
              <div>
                <div className="mb-6 p-4 rounded-xl border border-gray-700 bg-gray-800/50">
                  <h3 className="text-sm font-medium text-gray-300 mb-4">一键导入并抓取</h3>
                  <div className="flex gap-3 items-end">
                    <div className="flex-1">
                      <label className="block text-xs text-gray-400 mb-2">行业名称</label>
                      <input
                        type="text"
                        value={launchIndustryName}
                        onChange={(e) => setLaunchIndustryName(e.target.value)}
                        placeholder="如：新能源汽车、美妆护肤..."
                        className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                      />
                    </div>
                    <div className="w-32">
                      <label className="block text-xs text-gray-400 mb-2">品牌数量</label>
                      <input
                        type="number"
                        value={launchCount}
                        onChange={(e) => setLaunchCount(Number(e.target.value))}
                        min={10}
                        max={100}
                        className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                      />
                    </div>
                    <button
                      onClick={handleLaunchIndustry}
                      disabled={launchLoading || !launchIndustryName.trim()}
                      className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium text-sm transition disabled:opacity-50 flex items-center gap-2"
                    >
                      {launchLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                      <Rocket className="w-4 h-4" />
                      一键导入并抓取
                    </button>
                  </div>
                </div>

                {industryStats.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <Building2 className="w-12 h-12 mx-auto mb-4 text-gray-600" />
                    <p>还没有行业数据，在上方输入行业名称开始</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {industryStats.map((industry) => {
                      const donePct = industry.completion_rate * 100;
                      return (
                        <div key={industry.name} className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-base font-semibold">{industry.name}</h3>
                            <span className="text-xs text-gray-400">{donePct.toFixed(0)}%</span>
                          </div>

                          <div className="h-3 bg-gray-900 rounded-full overflow-hidden mb-3">
                            <div
                              className="h-full bg-green-500 rounded-full transition-all"
                              style={{ width: `${donePct}%` }}
                            />
                          </div>

                          <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                            <span>完成 {industry.done} / 总 {industry.total}</span>
                            <div className="flex gap-2">
                              {industry.processing > 0 && (
                                <span className="text-blue-400">处理中 {industry.processing}</span>
                              )}
                              {industry.error > 0 && (
                                <span className="text-red-400">失败 {industry.error}</span>
                              )}
                            </div>
                          </div>

                          <div className="flex gap-2 mb-2">
                            {industry.error > 0 && (
                              <button
                                onClick={() => handleRetryIndustry(industry.name)}
                                className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 text-xs font-medium hover:bg-red-600/30 transition flex items-center gap-1"
                              >
                                <RotateCcw className="w-3 h-3" />
                                重试失败
                              </button>
                            )}
                            <button
                              onClick={() => handleRefreshIndustryFn(industry.name)}
                              className="px-3 py-1.5 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-600/30 text-xs font-medium hover:bg-blue-600/30 transition flex items-center gap-1"
                            >
                              <RefreshCw className="w-3 h-3" />
                              刷新过期
                            </button>
                            <button
                              onClick={async () => {
                                setBatchCategory(industry.name);
                                setActiveTab("batch");
                              }}
                              className="px-3 py-1.5 rounded-lg bg-green-600/20 text-green-400 border border-green-600/30 text-xs font-medium hover:bg-green-600/30 transition flex items-center gap-1"
                            >
                              <Play className="w-3 h-3" />
                              继续抓取
                            </button>
                            {industry.done > 0 && (
                              <button
                                onClick={() => handleRefreshAllIndustry(industry.name)}
                                className="px-3 py-1.5 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-600/30 text-xs font-medium hover:bg-purple-600/30 transition flex items-center gap-1"
                              >
                                <RefreshCw className="w-3 h-3" />
                                刷新全部
                              </button>
                            )}
                          </div>

                          {industry.last_updated && (
                            <div className="text-xs text-gray-500">
                              最后更新: {new Date(industry.last_updated).toLocaleString()}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {activeTab === "brands" && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={adminBrandsSearch}
                      onChange={(e) => {
                        setAdminBrandsSearch(e.target.value);
                        setAdminBrandsPage(1);
                      }}
                      placeholder="搜索品牌名称..."
                      className="w-full pl-10 pr-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    />
                  </div>
                  <select
                    value={adminBrandsCategory}
                    onChange={(e) => {
                      setAdminBrandsCategory(e.target.value);
                      setAdminBrandsPage(1);
                    }}
                    className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  >
                    <option value="all">全品类</option>
                    {seedsCategories.map((cat) => (
                      <option key={cat.name} value={cat.name}>{cat.name}</option>
                    ))}
                  </select>
                  <select
                    value={adminBrandsStatus}
                    onChange={(e) => {
                      setAdminBrandsStatus(e.target.value);
                      setAdminBrandsPage(1);
                    }}
                    className="px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                  >
                    <option value="all">全部状态</option>
                    <option value="done">已完成</option>
                    <option value="processing">处理中</option>
                    <option value="pending">等待中</option>
                    <option value="error">失败</option>
                  </select>
                  <button
                    onClick={() => fetchAdminBrands()}
                    className="px-3 py-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-600/30 text-sm font-medium hover:bg-blue-600/30 transition flex items-center gap-1"
                  >
                    <RefreshCw className="w-4 h-4" />
                    刷新
                  </button>
                </div>

                <div className="rounded-xl border border-gray-700 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-700 bg-gray-800/50">
                        <th className="px-4 py-3 font-medium w-10">
                          <input
                            type="checkbox"
                            checked={adminBrands.length > 0 && selectedBrandIds.size === adminBrands.length}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedBrandIds(new Set(adminBrands.map(b => b.id)));
                              } else {
                                setSelectedBrandIds(new Set());
                              }
                            }}
                            className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-600"
                          />
                        </th>
                        <th className="px-4 py-3 font-medium">Logo+名称</th>
                        <th className="px-4 py-3 font-medium">URL</th>
                        <th className="px-4 py-3 font-medium">品类</th>
                        <th className="px-4 py-3 font-medium">状态</th>
                        <th className="px-4 py-3 font-medium">更新时间</th>
                        <th className="px-4 py-3 font-medium w-32">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {adminBrands.map((brand) => (
                        <tr key={brand.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedBrandIds.has(brand.id)}
                              onChange={(e) => {
                                const newSet = new Set(selectedBrandIds);
                                if (e.target.checked) {
                                  newSet.add(brand.id);
                                } else {
                                  newSet.delete(brand.id);
                                }
                                setSelectedBrandIds(newSet);
                              }}
                              className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-600"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              {brand.logo_url ? (
                                <img src={brand.logo_url} alt="" className="w-8 h-8 rounded-lg object-contain bg-white" />
                              ) : (
                                <div className="w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center text-xs">
                                  {(brand.name || brand.url).charAt(0).toUpperCase()}
                                </div>
                              )}
                              <span className="font-medium">{brand.name || "(unnamed)"}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-gray-400 truncate max-w-[200px]">{brand.url}</td>
                          <td className="px-4 py-3 text-gray-400">{brand.category || "-"}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs border ${STATUS_COLORS[brand.status]}`}>
                              {STATUS_ICONS[brand.status]}
                              {brand.status === "done" ? "已完成" : brand.status === "processing" ? "处理中" : brand.status === "error" ? "失败" : "等待中"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-400 text-xs">
                            {brand.updated_at ? new Date(brand.updated_at).toLocaleDateString() : "-"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => setEditingBrand(brand)}
                                className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-primary-400 transition"
                                title="编辑"
                              >
                                <Pencil className="w-4 h-4" />
                              </button>
                              <button
                                onClick={async () => {
                                  if (!window.confirm(`确定要刷新 "${brand.name || brand.url}" 吗？`)) return;
                                  try {
                                    await refreshBrand(brand.id);
                                    fetchAdminBrands();
                                  } catch {}
                                }}
                                className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-blue-400 transition"
                                title="刷新"
                              >
                                <RotateCcw className="w-4 h-4" />
                              </button>
                              <button
                                onClick={async () => {
                                  if (!window.confirm(`确定要删除 "${brand.name || brand.url}" 吗？`)) return;
                                  try {
                                    await adminDeleteBrand(brand.id);
                                    fetchAdminBrands();
                                  } catch {}
                                }}
                                className="p-1.5 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-red-400 transition"
                                title="删除"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {adminBrands.length === 0 && (
                    <div className="text-center py-12 text-gray-500">暂无品牌数据</div>
                  )}
                </div>

                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-400">
                    共 {adminBrandsTotal} 个品牌，第 {adminBrandsPage} / {Math.ceil(adminBrandsTotal / 20) || 1} 页
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setAdminBrandsPage(Math.max(1, adminBrandsPage - 1))}
                      disabled={adminBrandsPage <= 1}
                      className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:bg-gray-700 disabled:opacity-50 transition flex items-center gap-1"
                    >
                      <ChevronLeft className="w-4 h-4" />
                      上一页
                    </button>
                    <button
                      onClick={() => setAdminBrandsPage(adminBrandsPage + 1)}
                      disabled={adminBrandsPage >= Math.ceil(adminBrandsTotal / 20)}
                      className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:bg-gray-700 disabled:opacity-50 transition flex items-center gap-1"
                    >
                      下一页
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {selectedBrandIds.size > 0 && (
                  <div className="fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-700 p-4 z-40">
                    <div className="max-w-7xl mx-auto flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckSquare className="w-5 h-5 text-primary-400" />
                        <span className="text-sm">已选 <span className="text-primary-400 font-medium">{selectedBrandIds.size}</span> 个</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={async () => {
                            if (!window.confirm(`确定要删除选中的 ${selectedBrandIds.size} 个品牌吗？`)) return;
                            try {
                              await batchDeleteBrands(Array.from(selectedBrandIds));
                              setSelectedBrandIds(new Set());
                              fetchAdminBrands();
                            } catch {}
                          }}
                          className="px-4 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-600/30 text-sm font-medium hover:bg-red-600/30 transition flex items-center gap-2"
                        >
                          <Trash2 className="w-4 h-4" />
                          批量删除
                        </button>
                        <button
                          onClick={async () => {
                            if (!window.confirm(`确定要刷新选中的 ${selectedBrandIds.size} 个品牌吗？`)) return;
                            try {
                              await batchRefreshBrands(Array.from(selectedBrandIds));
                              setSelectedBrandIds(new Set());
                              fetchAdminBrands();
                            } catch {}
                          }}
                          className="px-4 py-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-600/30 text-sm font-medium hover:bg-blue-600/30 transition flex items-center gap-2"
                        >
                          <RotateCcw className="w-4 h-4" />
                          批量刷新
                        </button>
                        <button
                          onClick={() => setSelectedBrandIds(new Set())}
                          className="px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm hover:bg-gray-700 transition"
                        >
                          取消选择
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "batch" && (
              <div>
                <div className="grid grid-cols-5 gap-4 mb-6">
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">行业</label>
                    <select
                      value={batchCategory}
                      onChange={(e) => setBatchCategory(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary-600"
                    >
                      <option value="all">全部</option>
                      {seedsCategories.map((cat) => (
                        <option key={cat.name} value={cat.name}>{cat.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">状态</label>
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

            {activeTab === "tasks" && (
              <TaskMonitorPanel
                batchStatus={batchStatus}
                onPause={async () => { await pauseBatch(); fetchBatchStatus(); }}
                onResume={async () => { await resumeBatch(); fetchBatchStatus(); }}
                onCancelBrand={async (brandId) => { await cancelBrandTask(brandId); fetchBatchStatus(); }}
                onCancelAll={async () => { await cancelAllTasks(); fetchBatchStatus(); }}
                onRetryFailed={async () => { await retryFailedBatch(); fetchBatchStatus(); }}
                onRefreshBrand={async (brandId) => { await refreshBrand(brandId); fetchBatchStatus(); }}
                onResetStuck={async () => { await resetStuckTasks(); fetchBatchStatus(); }}
              />
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
      {editingBrand && (
        <EditBrandModal
          brand={editingBrand}
          onClose={() => setEditingBrand(null)}
          onSuccess={() => {
            setEditingBrand(null);
            fetchAdminBrands();
          }}
        />
      )}
    </div>
  );
}

function EditBrandModal({
  brand,
  onClose,
  onSuccess,
}: {
  brand: Brand;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [name, setName] = useState(brand.name || "");
  const [category, setCategory] = useState(brand.category || "");
  const [url] = useState(brand.url || "");
  const [description, setDescription] = useState(brand.description || "");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await updateBrand(brand.id, {
        name: name.trim() || undefined,
        category: category.trim() || undefined,
        description: description.trim() || undefined,
      });
      onSuccess();
    } catch {} finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-[var(--card)] rounded-xl p-6 w-full max-w-md shadow-2xl border border-[var(--border)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">编辑品牌</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-[var(--muted)]">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">品类</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">URL</label>
            <input
              type="text"
              value={url}
              disabled
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-gray-800 text-gray-500 cursor-not-allowed"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600 resize-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            保存
          </button>
        </form>
      </div>
    </div>
  );
}