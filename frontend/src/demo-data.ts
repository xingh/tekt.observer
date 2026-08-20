import type { WorkspaceState } from "./types";

export const demoState: WorkspaceState = {
  workspace: { id: "local", name: "My observation workspace", revision: 1 },
  watchers: [
    { id: "topic_watch", slug: "topic_watch", name: "AI in Business", description: "Adoption, productivity, governance, customer operations, and operating models.", enabled: true, status: "healthy", sourceCount: 8 },
    { id: "career_watch", slug: "career_watch", name: "Career opportunities & intelligence", description: "Roles, professional shifts, company signals, skills, and news that can change career decisions.", enabled: true, status: "healthy", sourceCount: 5 },
    { id: "market_watch", slug: "market_watch", name: "AI Markets & Regulation", description: "Public companies, semiconductors, cloud platforms, regulation, and policy.", enabled: true, status: "attention", sourceCount: 9 },
  ],
  sources: [
    { id: "topic_watch:starter", watcher: "topic_watch", name: "Enterprise AI sources", url: "", discoveryMode: "feed", cadence: "every_run", status: "ready" },
    { id: "career_watch:starter", watcher: "career_watch", name: "Official career sources", url: "", discoveryMode: "api", cadence: "every_run", status: "ready" },
    { id: "market_watch:starter", watcher: "market_watch", name: "Market and policy sources", url: "", discoveryMode: "feed", cadence: "every_run", status: "ready" },
  ],
  items: [
    ["topic_watch", "enterprise-adoption", "Measuring enterprise AI adoption beyond pilot counts", "Deployment depth, active use, workflow change, and measurable value are replacing pilot counts as the useful adoption signal.", "enterprise adoption", 94],
    ["topic_watch", "customer-operations", "Redesigning customer-support workflows around AI", "Agent assist, escalation design, quality controls, and customer outcomes form a practical operating system for support teams.", "customer operations", 89],
    ["topic_watch", "governance-model", "An operating model for accountable AI deployment", "Ownership, risk tiers, evaluation, monitoring, and approval paths are becoming durable organizational capabilities.", "governance", 86],
    ["career_watch", "platform-engineer", "Senior AI Platform Engineer", "Production LLM systems, retrieval, evaluations, and platform reliability remain a high-signal role shape.", "profession", 92],
    ["career_watch", "governance-lead", "AI Governance and Model Risk Lead", "Policy, controls, evaluations, auditability, and regulatory readiness converge in this emerging leadership role.", "profession", 88],
    ["career_watch", "solutions-architect", "AI Solutions Architect", "Customer discovery, architecture, implementation, and value realization meet in an increasingly important profession.", "profession", 84],
    ["market_watch", "ai-capex", "Hyperscaler AI capital spending and demand signals", "Cloud capital expenditure connects semiconductor capacity, data centers, networking, and downstream AI demand.", "public markets", 91],
    ["market_watch", "semiconductor-chain", "Reading AI semiconductor supply-chain signals", "Accelerators, memory, foundries, lithography, networking, and export exposure reveal constraints before headlines do.", "supply chain", 87],
    ["market_watch", "ai-regulation", "AI rules, copyright, antitrust, and chip export controls", "Policy changes affect compliance costs, product constraints, market access, and competitive positioning.", "regulation", 90],
  ].map(([watcher, id, title, description, topic, score], index) => ({
    id: String(id), watcher: String(watcher), title: String(title), description: String(description), topic: String(topic), score: Number(score),
    url: `https://example.com/tekt-observer/${id}`, status: "new" as const,
    observedAt: new Date(Date.now() - index * 43 * 60_000).toISOString(),
    provenance: ["Starter watcher specification", "Normalized by tekt.observer", "Sample content — replace with a live run"],
  })),
  operations: [
    { id: "starter-run", label: "Starter watchers initialized", status: "complete", progress: 100, updatedAt: new Date().toISOString() },
  ],
  digests: [],
  exports: [],
};
