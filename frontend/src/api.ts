import type { WorkspaceState } from "./types";

export async function getWorkspace(): Promise<WorkspaceState> {
  const response = await fetch("/api/v1/workspace", { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Workspace unavailable (${response.status})`);
  return response.json();
}

export async function updateItem(id: string, status: "new" | "saved" | "dismissed"): Promise<void> {
  const response = await fetch(`/api/v1/items/${encodeURIComponent(id)}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error(`Could not update item (${response.status})`);
}

async function mutate(path: string, method: "POST" | "PATCH", body?: unknown) {
  const response = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

export const updateWatcher = (id: string, enabled: boolean) => mutate(`/api/v1/watchers/${encodeURIComponent(id)}`, "PATCH", { enabled });
export const createDigest = () => mutate("/api/v1/digests", "POST");
export const createExport = () => mutate("/api/v1/exports", "POST") as Promise<{ downloadUrl: string }>;
export const ingestLatestRun = () => mutate("/api/v1/runs/ingest", "POST");
export const startLiveRun = () => mutate("/api/v1/runs", "POST");
