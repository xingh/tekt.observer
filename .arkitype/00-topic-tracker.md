# Topic Tracker (SignalFlow) — 00 Arkitype

Purpose-layer spec for the AI topic tracker built on top of tekt.observer. Extends the base site profile in `00-arkitype.md`; reuses `01-infrastructure.md`, `02-database.md`, `03-software.md`, and `04-interface.md` where compatible. Source of the taxonomy: GitHub issue [xingh/tekt.observer#14](https://github.com/xingh/tekt.observer/issues/14).

```yaml
TOPIC_TRACKER:
  extends: SITE_PROFILE
  name: ai_topics
  intent: >
    Watch, classify, rank, and digest AI-related content so an audience-tuned
    signal reaches Builders, Operators, Managers, Architects, and Leaders
    daily.
  verbs:
    - explore
    - seek
    - gather
    - organize
    - understand
    - generate
  verb_semantics:
    explore:  discover new candidate sources per topic using search providers
    seek:     turn each promising candidate into a repeatable crawl script
    gather:   run the scheduled crawls and land raw items in discovery artifacts
    organize: classify each item into Topic x Type x Category x Audience
    understand: rerank items per audience using profile and prior feedback
    generate: render per-audience digests and deliver via existing channels
  topics:
    - id: ai_knowledge_memory
      label: AI Knowledge and Memory
      facets: [knowledge_storage, knowledge_graph, context_graph]
    - id: ai_capabilities
      label: AI Capabilities
      facets: [vision, document_vision, document_formulate, agent_fleet_management]
    - id: open_source_ai
      label: Open Source AI
      facets: [applications, harnesses]
    - id: models_intelligence_inference
      label: Models / Intelligence Inference
      facets: [open, local, cloud]
    - id: models_inference_strategy
      label: Models / Inference Strategy
      facets: [open, fusion, edge, cloud]
    - id: models_family
      label: Models
      facets: [open_source, foundation, frontier]
    - id: news_ai
      label: News / AI
      facets: []
  content_types:
    - id: post
      label: Post
      applies_categories_from: [topics, post_video_podcast_book_categories]
    - id: video
      label: Video
      applies_categories_from: [topics, post_video_podcast_book_categories]
    - id: podcast
      label: Podcast
      applies_categories_from: [topics, post_video_podcast_book_categories]
    - id: book
      label: Book
      applies_categories_from: [topics, book_paper_categories]
    - id: resource
      label: Resource
      applies_categories_from: [topics, resource_categories]
    - id: paper
      label: Paper
      applies_categories_from: [topics, book_paper_categories]
  category_groups:
    post_video_podcast_book_categories:
      derived_from: topics
      extra: []
    book_paper_categories:
      derived_from: topics
      extra:
        - energy
        - policy
        - machine_learning_ai
        - quantum
        - networking
    resource_categories:
      derived_from: topics
      extra:
        - skills
        - tools
        - workflows
        - connectors
        - agents
        - patterns
        - architectures
        - applications
        - harnesses
        - fleets
        - company_harness
        - department_harness
        - team_harness
        - knowledge
        - templates
        - news
  audiences:
    - id: builders
      label: Builders
      lens: hands-on implementation, code, prototypes
    - id: operators
      label: Operators
      lens: reliability, on-call, cost, throughput
    - id: managers
      label: Managers
      lens: team throughput, roadmap alignment, hiring
    - id: architects
      label: Architects
      lens: system shape, tradeoffs, invariants across layers
    - id: leaders
      label: Leaders
      lens: strategy, portfolio bets, external narrative
  source_providers:
    - id: google
      kind: web_search
      discovery_mode_candidate: html
      credentials_required: false
    - id: exa
      kind: web_search_api
      discovery_mode_candidate: to_be_added
      credentials_required: true
    - id: perplexity
      kind: qa_search_api
      discovery_mode_candidate: to_be_added
      credentials_required: true
    - id: browser_use
      kind: agentic_browser
      discovery_mode_candidate: browser
      credentials_required: false
    - id: claude_desktop_chrome
      kind: agentic_browser
      discovery_mode_candidate: browser
      credentials_required: true
    - id: chatgpt_code_chrome
      kind: agentic_browser
      discovery_mode_candidate: browser
      credentials_required: true
  audience_glossary:
    intent: consistent audience vocabulary across ranking, digest section titles, and delivery variants
    entries: [builders, operators, managers, architects, leaders]
  data_extensions:
    note: >
      Adds two logical collections layered on top of the schemas documented in
      02-database.md. Physical layout lands in later iterations; the shape is
      declared here so downstream stages can validate against it.
    collections:
      - name: artifacts/organized/ai_topics/<date>.json
        purpose: per-item classification output
        fields:
          schema_version: {type: int, const: 1}
          track: {type: string, const: ai_topics}
          date: {type: string, format: YYYY-MM-DD}
          items:
            type: array
            items:
              item_key: {type: string}
              source_id: {type: string}
              url: {type: string}
              title: {type: string}
              topic: {type: string, enum_source: TOPIC_TRACKER.topics[].id}
              content_type: {type: string, enum_source: TOPIC_TRACKER.content_types[].id}
              categories: {type: array, items: {type: string}}
              audiences: {type: array, items: {type: string, enum_source: TOPIC_TRACKER.audiences[].id}}
              confidence: {type: number}
              rationale: {type: string}
      - name: artifacts/ranked/ai_topics/<audience>/<date>.json
        purpose: audience-scoped rerank output
        fields:
          schema_version: {type: int, const: 1}
          track: {type: string, const: ai_topics}
          audience: {type: string, enum_source: TOPIC_TRACKER.audiences[].id}
          date: {type: string, format: YYYY-MM-DD}
          items:
            type: array
            items:
              item_key: {type: string}
              rank: {type: int}
              score: {type: number}
              why: {type: array, items: string}
  iteration_plan:
    - id: I0
      goal: scaffold ai_topics track and topic-tracker arkitype spec
      test_round_data: track boots end-to-end with local fixture; empty topic classification
    - id: I1
      goal: encode taxonomy as machine-readable schema; add data_extensions collections
      test_round_data: 30 hand-labeled fixture items validate; unknown-category rejection counted
    - id: I2
      goal: explore stage seeds candidate sources per topic
      test_round_data: candidates-per-topic count; provider dedupe rate; topic coverage gaps
    - id: I3
      goal: seek stage generates crawl scripts under tracks/ai_topics/sources
      test_round_data: script success/fail per candidate; canary validation; cost per source
    - id: I4
      goal: gather stage runs crawls and writes discovery artifacts
      test_round_data: items/day/source; error rate; cross-day dedupe
    - id: I5
      goal: organize stage classifies items using taxonomy
      test_round_data: confidence distribution; unclassified rate; per-category volume
    - id: I6
      goal: understand stage reranks per audience
      test_round_data: top-K precision on gold set; A/B agreement; ranker cost per 100 items
    - id: I7
      goal: generate stage renders per-audience digests via existing delivery
      test_round_data: digest length distribution; deliverability; self-rated click-worthiness
    - id: I8
      goal: SignalFlow feedback loop wires delivery signals back into ranker weights
      test_round_data: precision lift vs I6 baseline; weight drift over 7 days
  metrics_artifact_path: artifacts/metrics/ai_topics/IN-<iteration>.json
  open_decisions:
    - which search provider to wire first for I2 (google html vs EXA api vs perplexity)
    - whether audience assignment is single-label or multi-label
    - whether the ranker is a single model prompt or a retrieval+rerank pair
```
