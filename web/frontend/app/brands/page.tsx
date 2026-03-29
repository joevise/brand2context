"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { listBrands, deleteBrand, Brand } from "@/lib/api";
import { Globe, Trash2, Clock, CheckCircle, AlertCircle, Loader2, Plus } from "lucide-react";

const statusConfig = {
  pending: { icon: Clock, color: "text-yellow-500", bg: "bg-yellow-100 dark:bg-yellow-900/30", label: "Pending" },
  processing: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/30", label: "Processing" },
  done: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-100 dark:bg-green-900/30", label: "Done" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-100 dark:bg-red-900/30", label: "Error" },
};

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await listBrands();
      setBrands(data);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this brand?")) return;
    await deleteBrand(id);
    load();
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>;

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Brand Knowledge Bases</h1>
        <Link href="/" className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition">
          <Plus className="w-4 h-4" /> New Brand
        </Link>
      </div>

      {brands.length === 0 ? (
        <div className="text-center py-20 text-[var(--muted-foreground)]">
          <Globe className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No brands yet. Generate your first one!</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {brands.map((brand) => {
            const s = statusConfig[brand.status] || statusConfig.pending;
            const Icon = s.icon;
            return (
              <div key={brand.id} className="group relative rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 hover:shadow-lg transition">
                <Link href={`/brands/${brand.id}`} className="block">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold text-lg truncate pr-2">{brand.name || "Generating..."}</h3>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.bg} ${s.color}`}>
                      <Icon className={`w-3 h-3 ${brand.status === "processing" ? "animate-spin" : ""}`} />
                      {s.label}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--muted-foreground)] truncate mb-3">{brand.url}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    {new Date(brand.created_at).toLocaleDateString()}
                  </p>
                </Link>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(brand.id); }}
                  className="absolute top-4 right-4 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
