const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Brand {
  id: string;
  name: string | null;
  url: string;
  status: "pending" | "processing" | "done" | "error";
  error_message: string | null;
  created_at: string;
  updated_at: string;
  data?: any;
  logo_url?: string;
  category?: string;
  slug?: string;
  description?: string;
  is_public?: boolean;
}

export async function createBrand(url: string): Promise<Brand> {
  const res = await fetch(`${API_URL}/api/brands`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error("Failed to create brand");
  return res.json();
}

export async function listBrands(): Promise<Brand[]> {
  const res = await fetch(`${API_URL}/api/brands`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch brands");
  return res.json();
}

export async function getBrand(id: string): Promise<Brand> {
  const res = await fetch(`${API_URL}/api/brands/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch brand");
  return res.json();
}

export async function getBrandStatus(id: string): Promise<{ id: string; status: string; error_message: string | null }> {
  const res = await fetch(`${API_URL}/api/brands/${id}/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch status");
  return res.json();
}

export async function deleteBrand(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/brands/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete brand");
}

export async function chatWithBrand(id: string, message: string): Promise<{ answer: string }> {
  const res = await fetch(`${API_URL}/api/brands/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

export async function updateKnowledge(id: string, data: any): Promise<any> {
  const res = await fetch(`${API_URL}/api/brands/${id}/knowledge`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update knowledge");
  return res.json();
}

export async function getPublicBrand(id: string): Promise<any> {
  const res = await fetch(`${API_URL}/api/brands/${id}/public`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch public brand");
  return res.json();
}

export async function getEmbedConfig(id: string): Promise<any> {
  const res = await fetch(`${API_URL}/api/brands/${id}/embed-config`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch embed config");
  return res.json();
}

export async function searchBrand(id: string, query: string): Promise<{ documents: string[]; distances: number[]; metadatas: any[] }> {
  const res = await fetch(`${API_URL}/api/brands/${id}/search?q=${encodeURIComponent(query)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function getBrandStats(id: string): Promise<{ brand_id: string; call_count: number; last_accessed: string | null }> {
  const res = await fetch(`${API_URL}/api/brands/${id}/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function searchBrands(
  q: string,
  category?: string,
  page?: number,
  perPage?: number
): Promise<{ brands: Brand[]; total: number; page: number; per_page: number }> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (page) params.set("page", page.toString());
  if (perPage) params.set("per_page", perPage.toString());
  const res = await fetch(`${API_URL}/api/brands/search?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to search brands");
  return res.json();
}

export async function getCategories(): Promise<{ categories: { name: string; count: number }[] }> {
  const res = await fetch(`${API_URL}/api/categories`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch categories");
  return res.json();
}

export async function getStatsOverview(): Promise<{
  total_brands: number;
  total_categories: number;
  total_api_calls: number;
}> {
  const res = await fetch(`${API_URL}/api/stats/overview`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function getBrandBySlug(slug: string): Promise<Brand> {
  const res = await fetch(`${API_URL}/api/brands/slug/${slug}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch brand by slug");
  return res.json();
}

export async function batchCreateBrands(
  brands: { url: string; category?: string; slug?: string }[]
): Promise<{ brand_ids: string[] }> {
  const res = await fetch(`${API_URL}/api/brands/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brands }),
  });
  if (!res.ok) throw new Error("Failed to batch create brands");
  return res.json();
}

export interface AdminDashboard {
  total_brands: number;
  total_categories: number;
  pending_updates: number;
  total_api_calls: number;
  category_distribution: { name: string; count: number }[];
  recent_failures: { id: string; name: string; url: string; category: string; error: string; updated_at: string }[];
}

export interface Seed {
  id: string;
  name: string;
  url: string;
  category: string;
  status: "new" | "done" | "outdated" | "processing" | "error";
  last_updated: string | null;
  error_message?: string;
}

export interface BatchStatus {
  total: number;
  completed: number;
  in_progress: number;
  queued: number;
  failed: number;
  brands: { id: string; name: string; status: string; error?: string }[];
}

export interface AdminSettings {
  update_interval_days: number;
  max_concurrency: number;
}

export async function getAdminDashboard(): Promise<AdminDashboard> {
  const res = await fetch(`${API_URL}/api/admin/dashboard`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch admin dashboard");
  return res.json();
}

export async function getAdminSeeds(category?: string): Promise<Seed[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  const res = await fetch(`${API_URL}/api/admin/seeds?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch seeds");
  return res.json();
}

export async function createSeed(data: { name: string; url: string; category: string }): Promise<Seed> {
  const res = await fetch(`${API_URL}/api/admin/seeds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create seed");
  return res.json();
}

export async function deleteSeed(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/seeds/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete seed");
}

export async function aiGenerateSeeds(data: { category: string; count: number }): Promise<{ generated: number }> {
  const res = await fetch(`${API_URL}/api/admin/seeds/ai-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to generate seeds");
  return res.json();
}

export async function searchAddSeed(data: { brand_name: string }): Promise<Seed> {
  const res = await fetch(`${API_URL}/api/admin/seeds/search-add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to search and add seed");
  return res.json();
}

export async function startBatch(data: { category?: string; batch_size: number; filter: string }): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to start batch");
}

export async function getBatchStatus(): Promise<BatchStatus> {
  const res = await fetch(`${API_URL}/api/admin/batch/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to get batch status");
  return res.json();
}

export async function pauseBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/pause`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to pause batch");
}

export async function resumeBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/resume`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to resume batch");
}

export async function retryFailedBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/retry-failed`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to retry failed");
}

export async function getRefreshStatus(): Promise<{ outdated_brands: { id: string; name: string; url: string; days_since_update: number }[] }> {
  const res = await fetch(`${API_URL}/api/admin/refresh-status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to get refresh status");
  return res.json();
}

export async function refreshOutdated(): Promise<{ refreshed: number }> {
  const res = await fetch(`${API_URL}/api/admin/refresh-outdated`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to refresh outdated");
  return res.json();
}

export async function getAdminSettings(): Promise<AdminSettings> {
  const res = await fetch(`${API_URL}/api/admin/settings`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to get settings");
  return res.json();
}

export async function updateAdminSettings(data: AdminSettings): Promise<AdminSettings> {
  const res = await fetch(`${API_URL}/api/admin/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}