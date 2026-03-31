"use client";
import Link from "next/link";
import { useTheme } from "./theme-provider";
import { Sun, Moon, Zap } from "lucide-react";

export function Navbar() {
  const { theme, toggle } = useTheme();

  return (
    <nav className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/80 backdrop-blur-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl">
          <Zap className="w-6 h-6 text-primary-600" />
          <span className="gradient-text">Brand2Context</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/brands" className="text-sm font-medium hover:text-primary-600 transition">
            Brands
          </Link>
          <Link href="/settings" className="text-sm font-medium hover:text-primary-600 transition">
            设置
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
    </nav>
  );
}
