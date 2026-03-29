"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createBrand } from "@/lib/api";
import { Zap, Globe, Brain, Database, ArrowRight, Loader2 } from "lucide-react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const brand = await createBrand(url.trim());
      router.push(`/brands/${brand.id}`);
    } catch {
      setError("Failed to submit URL. Check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-50 via-white to-blue-50 dark:from-primary-950/20 dark:via-[var(--background)] dark:to-blue-950/20" />
        <div className="relative max-w-5xl mx-auto px-4 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 text-sm font-medium mb-8">
            <Zap className="w-4 h-4" /> AI-Powered Brand Intelligence
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight mb-6">
            Turn any website into a
            <br />
            <span className="gradient-text">brand knowledge base</span>
          </h1>
          <p className="text-xl text-[var(--muted-foreground)] max-w-2xl mx-auto mb-12">
            Enter a URL and get a structured, AI-ready brand knowledge base covering identity, products, trust signals, and more — in minutes.
          </p>

          {/* URL Input */}
          <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--muted-foreground)]" />
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.example.com"
                  className="w-full pl-12 pr-4 py-4 rounded-xl border border-[var(--border)] bg-[var(--card)] text-lg focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent transition"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="px-8 py-4 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-semibold text-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    Generate <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            </div>
            {error && <p className="mt-3 text-red-500 text-sm">{error}</p>}
          </form>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 py-20">
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { icon: Globe, title: "Crawl & Extract", desc: "Automatically crawls the website and extracts brand signals, clues, and structured data." },
            { icon: Brain, title: "AI Structuring", desc: "Uses LLMs to structure raw data into 10 brand dimensions following a rigorous schema." },
            { icon: Database, title: "MCP Ready", desc: "Exposes brand knowledge via MCP protocol — ready for AI agents to consume directly." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="p-6 rounded-2xl border border-[var(--border)] bg-[var(--card)] hover:shadow-lg transition">
              <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
                <Icon className="w-6 h-6 text-primary-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{title}</h3>
              <p className="text-[var(--muted-foreground)]">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Schema dimensions */}
      <section className="max-w-4xl mx-auto px-4 pb-20">
        <h2 className="text-3xl font-bold text-center mb-10">10 Brand Dimensions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {["Identity", "Offerings", "Differentiation", "Trust", "Experience", "Access", "Content", "Perception", "Decision Factors", "Vitality"].map(
            (dim) => (
              <div key={dim} className="text-center p-4 rounded-xl bg-[var(--muted)] hover:bg-primary-50 dark:hover:bg-primary-900/20 transition">
                <span className="text-sm font-medium">{dim}</span>
              </div>
            )
          )}
        </div>
      </section>
    </div>
  );
}
