export type Watcher = {
  id: string;
  slug: string;
  name: string;
  description: string;
  enabled: boolean;
  status: "healthy" | "attention" | "paused";
  sourceCount: number;
};

export type Signal = {
  id: string;
  watcher: string;
  title: string;
  description: string;
  url: string;
  topic: string;
  score: number;
  status: "new" | "saved" | "dismissed";
  observedAt: string;
  provenance: string[];
  image?: string;
  siteName?: string;
  author?: string;
};

export type Source = { id: string; watcher: string; name: string; url: string; discoveryMode: string; cadence: string; status: "ready" | "attention" | "failed" };

export type Operation = { id: string; label: string; status: "queued" | "running" | "complete" | "failed"; progress: number; updatedAt: string };
export type Digest = { id: string; title: string; summary: string; createdAt: string; itemIds: string[]; status: "ready" };
export type ExportRecord = { id: string; filename: string; createdAt: string; workspaceRevision: number; sha256: string };
export type WorkspaceState = { workspace: { id: string; name: string; revision: number }; watchers: Watcher[]; sources: Source[]; items: Signal[]; operations: Operation[]; digests: Digest[]; exports: ExportRecord[] };
