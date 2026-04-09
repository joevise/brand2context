const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import { getAuthHeaders } from "./auth";

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
  progress_step?: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
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
  brands_by_category: { name: string; count: number }[];
  brands_by_status: { done: number; processing: number; error: number; pending: number };
  recent_brands: { name: string; created_at: string; status: string }[];
  failed_brands: { name: string; error_message: string; created_at: string }[];
  outdated_count: number;
  queue_status: { running: number; queued: number; paused: boolean };
  total_api_calls: number;
}

export interface Seed {
  name: string;
  url: string;
  category: string;
  status: "new" | "done" | "outdated" | "processing" | "error";
  brand_id: string | null;
  last_refreshed: string | null;
}

export interface SeedsResponse {
  seeds: Seed[];
  total: number;
  categories: { name: string; count: number }[];
}

export interface BatchStatus {
  task_id: string | null;
  total: number;
  completed: number;
  processing: number;
  queued: number;
  failed: number;
  cancelled: number;
  paused: boolean;
  started_at: string | null;
  running_items: { name: string; url: string; brand_id: string; progress_step?: string; started_at?: string }[];
  completed_items: { name: string; url: string; brand_id: string; finished_at?: string }[];
  failed_items: { name: string; url: string; brand_id: string; error?: string }[];
  cancelled_items: { name: string; url: string; brand_id?: string }[];
}

export interface AdminSettings {
  refresh_cycle_days: number;
  max_concurrent: number;
}

export interface IndustryStats {
  name: string;
  total: number;
  done: number;
  processing: number;
  error: number;
  pending: number;
  completion_rate: number;
  last_updated: string | null;
}

export async function getAdminDashboard(): Promise<AdminDashboard> {
  const res = await fetch(`${API_URL}/api/admin/dashboard`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch admin dashboard");
  return res.json();
}

export async function getAdminSeeds(category?: string): Promise<SeedsResponse> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  const res = await fetch(`${API_URL}/api/admin/seeds?${params}`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch seeds");
  return res.json();
}

export async function createSeed(data: { name: string; url: string; category: string }): Promise<{ message: string; added: boolean; total: number }> {
  const res = await fetch(`${API_URL}/api/admin/seeds`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create seed");
  return res.json();
}

export async function aiGenerateSeeds(data: { category: string; count: number }): Promise<{ added: number; brands: Seed[]; total_seeds: number }> {
  const res = await fetch(`${API_URL}/api/admin/seeds/ai-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to generate seeds");
  return res.json();
}

export async function searchAddSeed(data: { brand_name: string; category?: string }): Promise<{ message: string; added: boolean; brand: { name: string; url: string } }> {
  const res = await fetch(`${API_URL}/api/admin/seeds/search-add`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to search and add seed");
  return res.json();
}

export async function startBatch(data: { category?: string; batch_size: number; filter: string }): Promise<{ task_id: string | null; total: number; message: string }> {
  const res = await fetch(`${API_URL}/api/admin/batch/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to start batch");
  return res.json();
}

export async function getBatchStatus(): Promise<BatchStatus> {
  const res = await fetch(`${API_URL}/api/admin/batch/status`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get batch status");
  return res.json();
}

export async function pauseBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/pause`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to pause batch");
}

export async function resumeBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/resume`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to resume batch");
}

export async function retryFailedBatch(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/retry-failed`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to retry failed");
}

export async function cancelBrandTask(brandId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/batch/cancel/${brandId}`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to cancel brand task");
}

export async function cancelAllTasks(): Promise<{ message: string; count: number }> {
  const res = await fetch(`${API_URL}/api/admin/batch/cancel-all`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to cancel all tasks");
  return res.json();
}

export async function resetStuckTasks(): Promise<{ message: string; stuck_reset: number; queue_drained: number }> {
  const res = await fetch(`${API_URL}/api/admin/batch/reset-stuck`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to reset stuck tasks");
  return res.json();
}

export async function getRefreshStatus(): Promise<{ total_brands: number; up_to_date: number; outdated: number; outdated_brands: { id: string; name: string; url: string; last_refreshed: string | null; days_since: number }[]; refresh_cycle_days: number }> {
  const res = await fetch(`${API_URL}/api/admin/refresh-status`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get refresh status");
  return res.json();
}

export async function refreshOutdated(data: { batch_size: number }): Promise<{ task_id: string; total: number; message: string }> {
  const res = await fetch(`${API_URL}/api/admin/refresh-outdated`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to refresh outdated");
  return res.json();
}

export async function getAdminSettings(): Promise<AdminSettings> {
  const res = await fetch(`${API_URL}/api/admin/settings`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get settings");
  return res.json();
}

export async function updateAdminSettings(data: AdminSettings): Promise<AdminSettings> {
  const res = await fetch(`${API_URL}/api/admin/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

export async function retryDBErrors(batchSize: number = 10): Promise<{ message: string; count: number }> {
  const res = await fetch(`${API_URL}/api/admin/batch/retry-db-errors`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ batch_size: batchSize }),
  });
  if (!res.ok) throw new Error("Failed to retry DB errors");
  return res.json();
}

export async function launchIndustry(data: { industry: string; count: number }): Promise<{ task_id: string; industry: string; brands_added: number; brands_started: number }> {
  const res = await fetch(`${API_URL}/api/admin/industry/launch`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to launch industry");
  return res.json();
}

export async function getIndustryStats(): Promise<{ industries: IndustryStats[] }> {
  const res = await fetch(`${API_URL}/api/admin/industry/stats`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get industry stats");
  return res.json();
}

export async function retryIndustry(industry: string): Promise<{ message: string; count: number }> {
  const res = await fetch(`${API_URL}/api/admin/industry/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ industry }),
  });
  if (!res.ok) throw new Error("Failed to retry industry");
  return res.json();
}

export async function refreshIndustry(industry: string): Promise<{ message: string; count: number }> {
  const res = await fetch(`${API_URL}/api/admin/industry/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ industry }),
  });
  if (!res.ok) throw new Error("Failed to refresh industry");
  return res.json();
}

export async function refreshAllIndustry(industry: string): Promise<{ message: string; count: number }> {
  const res = await fetch(`${API_URL}/api/admin/industry/refresh-all`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ industry }),
  });
  if (!res.ok) throw new Error("Failed to refresh all industry");
  return res.json();
}

export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Registration failed");
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Login failed");
  }
  return res.json();
}

export async function getMe(): Promise<AuthUser> {
  const res = await fetch(`${API_URL}/api/auth/me`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get user info");
  return res.json();
}

export async function createBrandWithName(url: string, name?: string, category?: string): Promise<Brand> {
  const res = await fetch(`${API_URL}/api/brands`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, name, category }),
  });
  if (!res.ok) throw new Error("Failed to create brand");
  return res.json();
}

export async function getAdminBrands(params: {page?: number; per_page?: number; category?: string; status?: string; q?: string}): Promise<{brands: Brand[]; total: number; page: number; per_page: number}> {
  const urlParams = new URLSearchParams();
  if (params.page) urlParams.set("page", params.page.toString());
  if (params.per_page) urlParams.set("per_page", params.per_page.toString());
  if (params.category) urlParams.set("category", params.category);
  if (params.status) urlParams.set("status", params.status);
  if (params.q) urlParams.set("q", params.q);
  const res = await fetch(`${API_URL}/api/admin/brands?${urlParams}`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to fetch admin brands");
  return res.json();
}

export async function updateBrand(brandId: string, data: {name?: string; category?: string; url?: string; description?: string}): Promise<Brand> {
  const res = await fetch(`${API_URL}/api/admin/brands/${brandId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update brand");
  return res.json();
}

export async function adminDeleteBrand(brandId: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/brands/${brandId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to delete brand");
}

export async function batchDeleteBrands(brandIds: string[]): Promise<{message: string; count: number}> {
  const res = await fetch(`${API_URL}/api/admin/brands/batch-delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ brand_ids: brandIds }),
  });
  if (!res.ok) throw new Error("Failed to batch delete brands");
  return res.json();
}

export async function batchRefreshBrands(brandIds: string[]): Promise<{message: string; count: number}> {
  const res = await fetch(`${API_URL}/api/admin/brands/batch-refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ brand_ids: brandIds }),
  });
  if (!res.ok) throw new Error("Failed to batch refresh brands");
  return res.json();
}

export async function refreshBrand(brandId: string): Promise<{message: string}> {
  const res = await fetch(`${API_URL}/api/admin/brands/${brandId}/refresh`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to refresh brand");
  return res.json();
}

// ============================================================
// AutoCrawl API
// ============================================================

export interface AutoCrawlIndustryProgress {
  total: number;
  done: number;
  failed: number;
  skipped: number;
  current_idx: number;
}

export interface AutoCrawlStatus {
  running: boolean;
  paused: boolean;
  current_industry: string | null;
  current_industry_idx: number;
  total_industries: number;
  current_brand: string | null;
  today_count: number;
  daily_limit: number;
  total_crawled: number;
  total_skipped: number;
  total_failed: number;
  industries_completed: string[];
  industry_progress: Record<string, AutoCrawlIndustryProgress>;
  config: {
    daily_limit: number;
    concurrent: number;
    brands_per_industry: number;
    pause_between_brands_sec: number;
    industries: string[];
  };
  recent_log: { time: string; msg: string }[];
}

export async function getAutoCrawlStatus(): Promise<AutoCrawlStatus> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/status`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to get autocrawl status");
  return res.json();
}

export async function startAutoCrawl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/start`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to start autocrawl");
}

export async function stopAutoCrawl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/stop`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to stop autocrawl");
}

export async function pauseAutoCrawl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/pause`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to pause autocrawl");
}

export async function resumeAutoCrawl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/resume`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to resume autocrawl");
}

export async function updateAutoCrawlConfig(config: Partial<AutoCrawlStatus["config"]>): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to update autocrawl config");
}

export async function resetAutoCrawl(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/reset`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to reset autocrawl");
}

export async function skipAutoCrawlIndustry(): Promise<void> {
  const res = await fetch(`${API_URL}/api/admin/autocrawl/skip-industry`, {
    method: "POST",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error("Failed to skip industry");
}
