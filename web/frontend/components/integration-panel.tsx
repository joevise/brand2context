"use client";
import { useEffect, useState } from "react";
import { getEmbedConfig, getBrandStats } from "@/lib/api";
import { Copy, Check, Activity, Clock, Code2 } from "lucide-react";

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div>
      <label className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide">{label}</label>
      <div className="mt-1 flex items-center gap-2">
        <code className="flex-1 text-sm px-3 py-2 rounded-lg bg-[var(--muted)] truncate">{value}</code>
        <button onClick={copy} className="p-2 rounded-lg hover:bg-[var(--muted)] transition">
          {copied ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

const SNIPPETS = {
  curl: (url: string) => `curl -s "${url}" | jq .`,
  python: (url: string) => `import requests\ndata = requests.get("${url}").json()`,
  mcp: (url: string) => `{
  "mcpServers": {
    "brand2context": {
      "url": "${url}"
    }
  }
}`,
};

export function IntegrationPanel({ brandId }: { brandId: string }) {
  const [config, setConfig] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [tab, setTab] = useState<"curl" | "python" | "mcp">("curl");

  useEffect(() => {
    getEmbedConfig(brandId).then(setConfig).catch(() => {});
    getBrandStats(brandId).then(setStats).catch(() => {});
  }, [brandId]);

  if (!config) return null;

  const isLive = stats && stats.call_count > 0;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] overflow-hidden">
      <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--muted)]">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Code2 className="w-5 h-5 text-primary-600" />
          Integration
          <span className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${isLive ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" : "bg-gray-100 dark:bg-gray-800 text-gray-500"}`}>
            <span className={`w-2 h-2 rounded-full ${isLive ? "bg-green-500" : "bg-gray-400"}`} />
            {isLive ? "Live" : "No calls yet"}
          </span>
        </h2>
      </div>
      <div className="p-6 space-y-5">
        <div className="grid sm:grid-cols-2 gap-4">
          {stats && (
            <>
              <div className="flex items-center gap-3 p-3 rounded-xl bg-[var(--muted)]">
                <Activity className="w-5 h-5 text-primary-600" />
                <div>
                  <div className="text-lg font-bold">{stats.call_count}</div>
                  <div className="text-xs text-[var(--muted-foreground)]">Total API Calls</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 rounded-xl bg-[var(--muted)]">
                <Clock className="w-5 h-5 text-primary-600" />
                <div>
                  <div className="text-sm font-medium">{stats.last_accessed ? new Date(stats.last_accessed).toLocaleString() : "Never"}</div>
                  <div className="text-xs text-[var(--muted-foreground)]">Last Accessed</div>
                </div>
              </div>
            </>
          )}
        </div>

        <CopyField label="MCP Endpoint" value={config.mcp_endpoint} />
        <CopyField label="API Endpoint" value={config.api_endpoint} />

        {/* Code snippets */}
        <div>
          <div className="flex gap-1 mb-2">
            {(["curl", "python", "mcp"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition ${tab === t ? "bg-primary-600 text-white" : "bg-[var(--muted)] hover:bg-primary-100 dark:hover:bg-primary-900/30"}`}
              >
                {t === "mcp" ? "MCP Config" : t}
              </button>
            ))}
          </div>
          <pre className="text-xs p-3 rounded-lg bg-[var(--muted)] overflow-x-auto whitespace-pre-wrap">
            {SNIPPETS[tab](tab === "mcp" ? config.mcp_endpoint : config.api_endpoint)}
          </pre>
        </div>
      </div>
    </div>
  );
}
