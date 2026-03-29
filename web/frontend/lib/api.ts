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
