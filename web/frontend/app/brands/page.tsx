"use client";
import { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { searchBrands, deleteBrand, Brand, getCategories } from "@/lib/api";
import { Globe, Trash2, Clock, CheckCircle, AlertCircle, Loader2, Plus, Search, X, ChevronRight } from "lucide-react";

const statusConfig = {
  pending: { icon: Clock, color: "text-yellow-500", bg: "bg-yellow-100 dark:bg-yellow-900/30", label: "等待中" },
  processing: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/30", label: "生成中" },
  done: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/30", label: "已完成" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/30", label: "失败" },
};

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

export default function BrandsPage() {
  return (
    <Suspense fallback={
      <div className="max-w-7xl mx-auto px-4 py-10">
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      </div>
    }>
      <BrandsPageContent />
    </Suspense>
  );
}

function BrandsPageContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  
  const [brands, setBrands] = useState<Brand[]>([]);
  const [categories, setCategories] = useState<{ name: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    getCategories().then((res) => setCategories(res.categories)).catch(() => {});
  }, []);

  const loadBrands = useCallback(async (reset = false) => {
    const newPage = reset ? 1 : page;
    if (reset) setPage(1);
    setLoading(true);
    try {
      const res = await searchBrands(debouncedQuery, selectedCategory || undefined, newPage, 20);
      if (reset) {
        setBrands(res.brands);
      } else {
        setBrands((prev) => [...prev, ...res.brands]);
      }
      setTotal(res.total);
    } catch {}
    setLoading(false);
  }, [debouncedQuery, selectedCategory, page]);

  useEffect(() => {
    loadBrands(true);
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

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此品牌？")) return;
    await deleteBrand(id);
    loadBrands(true);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">品牌知识库</h1>
        <Link
          href="/"
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition"
        >
          <Plus className="w-4 h-4" /> 新建品牌
        </Link>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted-foreground)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索品牌..."
            className="w-full pl-12 pr-10 py-3 rounded-xl border border-[var(--border)] bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-primary-600"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-[var(--muted)]"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
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

      {/* Results count */}
      <div className="flex items-center justify-between mb-6">
        <span className="text-[var(--muted-foreground)]">
          共 {total} 个品牌
        </span>
      </div>

      {loading && brands.length === 0 ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      ) : brands.length === 0 ? (
        <div className="text-center py-20 text-[var(--muted-foreground)]">
          <Globe className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">未找到匹配的品牌</p>
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {brands.map((brand) => {
              const s = statusConfig[brand.status] || statusConfig.pending;
              const Icon = s.icon;
              return (
                <div
                  key={brand.id}
                  className="group relative rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:shadow-lg transition overflow-hidden"
                >
                  <Link href={`/brands/${brand.id}`} className="block p-5">
                    <div className="flex items-center gap-4 mb-3">
                      <BrandLogo brand={brand} size={56} />
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-lg truncate">
                          {brand.name || "生成中..."}
                        </h3>
                        {brand.category && (
                          <span className="px-2 py-0.5 rounded-full bg-[var(--muted)] text-xs">
                            {brand.category}
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-[var(--muted-foreground)] truncate mb-3">
                      {brand.url}
                    </p>
                    {brand.description && (
                      <p className="text-xs text-[var(--muted-foreground)] line-clamp-2 mb-3">
                        {brand.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.bg} ${s.color}`}
                      >
                        <Icon
                          className={`w-3 h-3 ${brand.status === "processing" ? "animate-spin" : ""}`}
                        />
                        {s.label}
                      </span>
                      <span className="text-xs text-[var(--muted-foreground)]">
                        {new Date(brand.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </Link>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(brand.id);
                    }}
                    className="absolute top-4 right-4 p-2 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition"
                    aria-label="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              );
            })}
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
    </div>
  );
}