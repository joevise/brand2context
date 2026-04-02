"use client";
import Link from "next/link";
import { useTheme } from "./theme-provider";
import { Sun, Moon, Zap, Search, Plus, ExternalLink, Settings } from "lucide-react";
import { useState } from "react";

export function Navbar() {
  const { theme, toggle } = useTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl">
          <Zap className="w-6 h-6 text-primary-600" />
          <span className="gradient-text">Brand2Context</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm font-medium hover:text-primary-600 transition">
            首页
          </Link>
          <Link href="/brands" className="text-sm font-medium hover:text-primary-600 transition">
            品牌库
          </Link>
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium hover:text-primary-600 transition flex items-center gap-1"
          >
            API文档
            <ExternalLink className="w-3 h-3" />
          </a>
          <Link
            href="/brands"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium transition"
          >
            <Plus className="w-4 h-4" />
            添加品牌
          </Link>
          <button
            onClick={() => setSearchOpen(!searchOpen)}
            className="p-2 rounded-lg hover:bg-[var(--muted)] transition"
            aria-label="Search"
          >
            <Search className="w-5 h-5" />
          </button>
          <Link
            href="/admin"
            className="p-2 rounded-lg hover:bg-[var(--muted)] transition text-[var(--muted-foreground)]"
            title="管理后台"
          >
            <Settings className="w-5 h-5" />
          </Link>
          <button
            onClick={toggle}
            className="p-2 rounded-lg hover:bg-[var(--muted)] transition"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </div>
      {searchOpen && (
        <div className="absolute top-16 left-0 right-0 border-b border-[var(--border)] bg-[var(--background)] p-4">
          <div className="max-w-2xl mx-auto">
            <form action="/brands" method="GET">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  name="q"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索品牌..."
                  className="w-full pl-12 pr-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-primary-600"
                />
              </div>
            </form>
          </div>
        </div>
      )}
    </nav>
  );
}