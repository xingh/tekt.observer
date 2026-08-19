/// <reference path="../pb_data/types.d.ts" />

// tekt.observer's operational schema. Keep this migration compatible with the
// unmodified PocketBase executable pinned in ../VERSION.
migrate((app) => {
  const json = (name, required = false) => ({ name, type: "json", required });
  const text = (name, required = false) => ({ name, type: "text", required });
  const number = (name, required = false) => ({ name, type: "number", required });
  const bool = (name) => ({ name, type: "bool" });
  const relation = (name, collectionId, required = true, maxSelect = 1) =>
    ({ name, type: "relation", collectionId, required, maxSelect, cascadeDelete: true });

  const users = new Collection({
    type: "auth",
    name: "users",
    fields: [text("name"), text("mode", true)],
    indexes: ["CREATE INDEX idx_users_mode ON users (mode)"],
  });
  app.save(users);

  const workspaces = new Collection({
    type: "base",
    name: "workspaces",
    fields: [text("name", true), text("slug", true), number("revision", true), json("definition", true)],
    indexes: ["CREATE UNIQUE INDEX idx_workspaces_slug ON workspaces (slug)"],
    listRule: "@request.auth.id != '' && memberships_via_workspace.user ?= @request.auth.id",
    viewRule: "@request.auth.id != '' && memberships_via_workspace.user ?= @request.auth.id",
  });
  app.save(workspaces);

  const memberships = new Collection({
    type: "base",
    name: "memberships",
    fields: [relation("workspace", workspaces.id), relation("user", users.id), text("role", true)],
    indexes: [
      "CREATE UNIQUE INDEX idx_membership_identity ON memberships (workspace, user)",
      "CREATE INDEX idx_membership_role ON memberships (workspace, role)",
    ],
    listRule: "@request.auth.id != '' && user = @request.auth.id",
    viewRule: "@request.auth.id != '' && user = @request.auth.id",
    createRule: "@request.auth.id != '' && workspace.memberships_via_workspace.user ?= @request.auth.id && workspace.memberships_via_workspace.role ?= 'owner'",
    updateRule: "@request.auth.id != '' && workspace.memberships_via_workspace.user ?= @request.auth.id && workspace.memberships_via_workspace.role ?= 'owner'",
    deleteRule: "@request.auth.id != '' && workspace.memberships_via_workspace.user ?= @request.auth.id && workspace.memberships_via_workspace.role ?= 'owner'",
  });
  app.save(memberships);

  const memberRead = "@request.auth.id != '' && workspace.memberships_via_workspace.user ?= @request.auth.id";
  const editorWrite = memberRead + " && (workspace.memberships_via_workspace.role ?= 'owner' || workspace.memberships_via_workspace.role ?= 'editor')";
  const ownerWrite = memberRead + " && workspace.memberships_via_workspace.role ?= 'owner'";

  const watchers = new Collection({
    type: "base", name: "watchers",
    fields: [relation("workspace", workspaces.id), text("slug", true), text("name", true), bool("enabled"), json("definition", true)],
    indexes: ["CREATE UNIQUE INDEX idx_watcher_slug ON watchers (workspace, slug)"],
    listRule: memberRead, viewRule: memberRead, createRule: editorWrite, updateRule: editorWrite, deleteRule: ownerWrite,
  });
  app.save(watchers);

  const sources = new Collection({
    type: "base", name: "sources",
    fields: [relation("workspace", workspaces.id), relation("watcher", watchers.id), text("source_key", true), text("name", true), text("url", true), text("discovery_mode", true), text("status", true), json("configuration", true), json("health")],
    indexes: ["CREATE UNIQUE INDEX idx_source_key ON sources (watcher, source_key)"],
    listRule: memberRead, viewRule: memberRead, createRule: editorWrite, updateRule: editorWrite, deleteRule: editorWrite,
  });
  app.save(sources);

  const runs = new Collection({
    type: "base", name: "runs",
    fields: [relation("workspace", workspaces.id), relation("watcher", watchers.id), text("run_key", true), text("status", true), text("started_at"), text("finished_at"), json("summary"), json("provenance")],
    indexes: ["CREATE UNIQUE INDEX idx_run_key ON runs (watcher, run_key)"],
    listRule: memberRead, viewRule: memberRead, createRule: editorWrite, updateRule: editorWrite, deleteRule: ownerWrite,
  });
  app.save(runs);

  const items = new Collection({
    type: "base", name: "items",
    fields: [relation("workspace", workspaces.id), relation("watcher", watchers.id), relation("run", runs.id, false), text("item_key", true), text("title", true), text("url"), text("status", true), number("score"), json("content", true), json("ranking"), json("provenance", true)],
    indexes: ["CREATE UNIQUE INDEX idx_item_key ON items (watcher, item_key)"],
    listRule: memberRead, viewRule: memberRead, createRule: editorWrite, updateRule: editorWrite, deleteRule: editorWrite,
  });
  app.save(items);

  const feedback = new Collection({
    type: "base", name: "feedback",
    fields: [relation("workspace", workspaces.id), relation("item", items.id), relation("user", users.id), text("kind", true), text("note"), json("context")],
    indexes: ["CREATE INDEX idx_feedback_item ON feedback (workspace, item)"],
    listRule: memberRead, viewRule: memberRead, createRule: editorWrite, updateRule: editorWrite, deleteRule: editorWrite,
  });
  app.save(feedback);

  const operations = new Collection({
    type: "base", name: "operations",
    fields: [relation("workspace", workspaces.id), relation("watcher", watchers.id, false), text("kind", true), text("status", true), text("claim_token"), text("claimed_at"), number("attempt", true), number("max_attempts", true), bool("cancel_requested"), json("input"), json("progress"), json("result"), text("error")],
    indexes: ["CREATE INDEX idx_operation_queue ON operations (status, created)"],
    listRule: memberRead, viewRule: memberRead, createRule: ownerWrite, updateRule: ownerWrite, deleteRule: ownerWrite,
  });
  app.save(operations);

  const exportsCollection = new Collection({
    type: "base", name: "exports",
    fields: [relation("workspace", workspaces.id), text("bundle_id", true), number("workspace_revision", true), text("status", true), text("path"), text("sha256"), json("manifest", true), text("published_to"), text("error")],
    indexes: ["CREATE UNIQUE INDEX idx_export_bundle ON exports (workspace, bundle_id)"],
    listRule: memberRead, viewRule: memberRead, createRule: ownerWrite, updateRule: ownerWrite, deleteRule: ownerWrite,
  });
  app.save(exportsCollection);
}, (app) => {
  for (const name of ["exports", "operations", "feedback", "items", "runs", "sources", "watchers", "memberships", "workspaces", "users"]) {
    try { app.delete(app.findCollectionByNameOrId(name)); } catch (_) {}
  }
});
