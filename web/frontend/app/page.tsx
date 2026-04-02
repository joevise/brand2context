"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { searchBrands, getCategories, getStatsOverview, createBrand, Brand } from "@/lib/api";
import { Search, Plus, X, Loader2, ChevronRight, Database, Zap, Globe } from "lucide-react";

function hashColor(str: string): string {
  const colors = [
    "bg-red-500", "bg-orange-500", "bg-amber-500", "bg-yellow-500",
    "bg-lime-500", "bg-green-500", "bg-emerald-500", "bg-teal-500",
    "bg-cyan-500", "bg-sky-500", "bg-blue-500", "bg-indigo-500",
    "bg-violet-500", "bg-purple-500", "bg-fuchsia-500", "bg-pink-500",
  ];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function BrandLogo({ brand, size = 64 }: { brand: Brand; size?: number }) {
  if (brand.logo_url) {
    return (
      <img
        src={brand.logo_url}
        alt={brand.name || ""}
        className="rounded-lg object-contain"
        style={{ width: size, height: size }}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = "none";
          (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
        }}
      />
    );
  }
  const initial = (brand.name?.charAt(0) || brand.url.charAt(0)).toUpperCase();
  return (
    <div
      className={`${hashColor(brand.name || brand.url)} rounded-lg flex items-center justify-center text-white font-bold`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
    >
      {initial}
    </div>
  );
}

function AddBrandModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: (id: string) => void }) {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const brand = await createBrand(url.trim());
      onSuccess(brand.id);
      onClose();
      setUrl("");
    } catch {
      setError("创建失败，请检查网络连接");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-[var(--card)] rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">添加品牌</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--muted)] transition">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">品牌官网 URL</label>
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted-foreground)]" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full pl-10 pr-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
              />
            </div>
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">品类（可选）</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="科技、消费品、汽车..."
              className="w-full px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--background)] focus:outline-none focus:ring-2 focus:ring-primary-600"
            />
          </div>
          {error && <p className="text-red-500 text-sm mb-4">{error}</p>}
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="w-full py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            创建品牌知识库
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Brand[]>([]);
  const [searching, setSearching] = useState(false);
  const [categories, setCategories] = useState<{ name: string; count: number }[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);
  const [stats, setStats] = useState({ total_brands: 0, total_categories: 0, total_api_calls: 0 });
  const [addModalOpen, setAddModalOpen] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    getCategories().then((res) => setCategories(res.categories)).catch(() => {});
    getStatsOverview().then((res) => setStats(res)).catch(() => {});
  }, []);

  useEffect(() => {
    if (debouncedQuery && !selectedCategory) {
      setSearching(true);
      searchBrands(debouncedQuery, undefined, 1, 8)
        .then((res) => setSearchResults(res.brands))
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false));
    } else {
      setSearchResults([]);
    }
  }, [debouncedQuery, selectedCategory]);

  const loadBrands = useCallback(async (reset = false) => {
    const newPage = reset ? 1 : page;
    if (reset) setPage(1);
    setSearching(true);
    try {
      const res = await searchBrands(debouncedQuery, selectedCategory || undefined, newPage, 20);
      if (reset) {
        setBrands(res.brands);
      } else {
        setBrands((prev) => [...prev, ...res.brands]);
      }
      setTotal(res.total);
    } catch {}
    setSearching(false);
  }, [debouncedQuery, selectedCategory, page]);

  useEffect(() => {
    if (!searchQuery || selectedCategory) {
      loadBrands(true);
    }
  }, [debouncedQuery, selectedCategory]);

  const loadMore = () => {
    setPage((p) => p + 1);
    setLoadingMore(true);
  };

  useEffect(() => {
    if (page > 1) {
      loadBrands(false).then(() => setLoadingMore(false));
    }
  }, [page]);

  const handleAddSuccess = (id: string) => {
    router.push(`/brands/${id}`);
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-50 via-white to-blue-50 dark:from-primary-950/20 dark:via-[var(--background)] dark:to-blue-950/20" />
        <div className="relative max-w-4xl mx-auto px-4 pt-16 pb-12 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm font-medium mb-6">
            <Zap className="w-4 h-4" /> AI 品牌知识库门户
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">
            Brand2Context
            <br />
            <span className="gradient-text">AI 品牌知识库</span>
          </h1>
          <p className="text-lg text-[var(--muted-foreground)] max-w-xl mx-auto mb-8">
            数千个品牌的实时知识，AI Agent 可直接调用
          </p>

          {/* Search Box */}
          <div className="max-w-2xl mx-auto relative">
            <div className="relative">
              <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-[var(--muted-foreground)]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索品牌..."
                className="w-full pl-14 pr-6 py-4 rounded-2xl border border-[var(--border)] bg-[var(--card)] text-lg focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent shadow-lg"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-5 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-[var(--muted)]"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Search Results Dropdown */}
            {searchQuery && debouncedQuery && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-[var(--card)] rounded-2xl border border-[var(--border)] shadow-xl overflow-hidden z-10">
                {searching ? (
                  <div className="p-8 text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-600 mx-auto" />
                  </div>
                ) : searchResults.length > 0 ? (
                  <div className="max-h-96 overflow-y-auto">
                    {searchResults.map((brand) => (
                      <Link
                        key={brand.id}
                        href={`/brands/${brand.id}`}
                        className="flex items-center gap-4 p-4 hover:bg-[var(--muted)] transition"
                        onClick={() => setSearchQuery("")}
                      >
                        <BrandLogo brand={brand} size={48} />
                        <div className="flex-1 text-left">
                          <div className="font-medium">{brand.name || "Unnamed"}</div>
                          <div className="text-sm text-[var(--muted-foreground)] truncate">{brand.url}</div>
                        </div>
                        {brand.category && (
                          <span className="px-2 py-1 rounded-full bg-[var(--muted)] text-xs">
                            {brand.category}
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-[var(--muted-foreground)]">
                    未找到匹配的品牌
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Category Filter Bar */}
      <section className="border-y border-[var(--border)] bg-[var(--card)]">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-2 py-4 overflow-x-auto scrollbar-hide">
            <button
              onClick={() => setSelectedCategory(null)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                selectedCategory === null
                  ? "bg-primary-600 text-white"
                  : "bg-[var(--muted)] hover:bg-[var(--muted-foreground)]/20"
              }`}
            >
              全部
            </button>
            {categories.map((cat) => (
              <button
                key={cat.name}
                onClick={() => setSelectedCategory(cat.name)}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                  selectedCategory === cat.name
                    ? "bg-primary-600 text-white"
                    : "bg-[var(--muted)] hover:bg-[var(--muted-foreground)]/20"
                }`}
              >
                {cat.name} ({cat.count})
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Brand Wall */}
      <section className="max-w-7xl mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold">
            {selectedCategory ? `${selectedCategory} 品牌` : "全部品牌"}
          </h2>
          <span className="text-[var(--muted-foreground)]">共 {total} 个品牌</span>
        </div>

        {brands.length === 0 && !searching ? (
          <div className="text-center py-20">
            <Globe className="w-16 h-16 mx-auto mb-4 text-[var(--muted-foreground)] opacity-50" />
            <p className="text-lg text-[var(--muted-foreground)] mb-6">还没有品牌，成为第一个添加的人！</p>
            <button
              onClick={() => setAddModalOpen(true)}
              className="px-6 py-3 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold transition inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" /> 添加品牌
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {brands.map((brand) => (
                <Link
                  key={brand.id}
                  href={`/brands/${brand.id}`}
                  className="group rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 hover:shadow-lg hover:border-primary-200 dark:hover:border-primary-800 transition-all duration-200"
                >
                  <div className="flex flex-col items-center text-center">
                    <div className="mb-3 transition-transform group-hover:scale-105">
                      <BrandLogo brand={brand} size={72} />
                    </div>
                    <h3 className="font-semibold text-sm truncate w-full mb-1">
                      {brand.name || "Unnamed"}
                    </h3>
                    {brand.category && (
                      <span className="px-2 py-0.5 rounded-full bg-[var(--muted)] text-xs text-[var(--muted-foreground)]">
                        {brand.category}
                      </span>
                    )}
                    {brand.description && (
                      <p className="mt-2 text-xs text-[var(--muted-foreground)] line-clamp-2">
                        {brand.description}
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>

            {brands.length < total && (
              <div className="mt-12 text-center">
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="px-8 py-3 rounded-xl border border-[var(--border)] hover:bg-[var(--muted)] transition inline-flex items-center gap-2 disabled:opacity-50"
                >
                  {loadingMore ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <>
                      加载更多 <ChevronRight className="w-5 h-5" />
                    </>
                  )}
                </button>
              </div>
            )}
          </>
        )}
      </section>

      {/* Stats Section */}
      <section className="border-t border-[var(--border)] bg-[var(--muted)]/30">
        <div className="max-w-7xl mx-auto px-4 py-16">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">{stats.total_brands}</div>
              <div className="text-[var(--muted-foreground)]">已收录品牌</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">{stats.total_categories}</div>
              <div className="text-[var(--muted-foreground)]">覆盖品类</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary-600 mb-2">{stats.total_api_calls}</div>
              <div className="text-[var(--muted-foreground)]">API 调用次数</div>
            </div>
          </div>
          <div className="mt-12 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm">
              <Database className="w-4 h-4" />
              接入 MCP 协议，AI Agent 可直接调用
            </div>
          </div>
        </div>
      </section>

      {/* Floating Add Button */}
      <button
        onClick={() => setAddModalOpen(true)}
        className="fixed bottom-8 right-8 w-14 h-14 rounded-full bg-primary-600 hover:bg-primary-700 text-white shadow-lg hover:shadow-xl transition-all flex items-center justify-center z-40"
        aria-label="添加品牌"
      >
        <Plus className="w-6 h-6" />
      </button>

      {/* Add Brand Modal */}
      <AddBrandModal open={addModalOpen} onClose={() => setAddModalOpen(false)} onSuccess={handleAddSuccess} />
    </div>
  );
}