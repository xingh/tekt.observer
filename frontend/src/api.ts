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
