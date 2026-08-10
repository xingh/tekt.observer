# Job Watch (SignalFlow) — 00 Arkitype

Purpose-layer spec for the AI-enabled job watch tracker built on top of
tekt.observer. Sibling of `00-topic-tracker.md` and `00-market-watch.md`;
reuses the shared 01–04 layers. Persona lives in
`profile/personas/ai_technologist.md`.

```yaml
JOB_WATCH:
  extends: SITE_PROFILE
  name: job_watch
  intent: >
    Surface high-signal AI-enabled engineering, research, teaching, and
    devrel roles from open-web job feeds and community threads, ranked
    per seniority-audience for a technologist actively hunting.
  verbs:
    - explore
    - seek
    - gather
    - organize
    - understand
    - generate
  verb_semantics:
    explore:  seed candidate job feeds per role_type
    seek:     turn each promising feed into a repeatable ingest
    gather:   run scheduled ingest of feeds and community threads
    organize: classify each posting by role_type + seniority + company
    understand: rerank per seniority audience and persona preferences
    generate: render per-audience digest with fit + comp signal
  role_types:
    - id: ai_engineer
      label: AI Engineer
      keywords: ["ai engineer", "llm engineer", "agent", "rag", "retrieval augmented", "orchestration", "prompt engineer"]
    - id: prompt_engineer
      label: Prompt Engineer
      keywords: ["prompt engineer", "prompt engineering"]
    - id: ml_engineer
      label: ML Engineer
      keywords: ["ml engineer", "machine learning engineer", "mle", "feature engineering", "training pipeline"]
    - id: ai_researcher
      label: AI Researcher
      keywords: ["ai researcher", "research scientist", "research engineer", "applied research"]
    - id: ai_instructor
      label: AI Instructor / Trainer
      keywords: ["instructor", "trainer", "curriculum", "workshop", "course", "teach"]
    - id: ai_devrel
      label: AI Developer Advocate
      keywords: ["developer advocate", "devrel", "community engineer", "developer relations"]
    - id: ai_pm
      label: AI Product Manager
      keywords: ["product manager", "pm", "product lead"]
    - id: ai_augmented_generalist
      label: AI-augmented Generalist SWE
      keywords: ["staff engineer", "senior engineer", "principal engineer", "generalist"]
  audiences:
    - id: individual_contributor
      label: Individual contributor (IC)
      lens: shipping, building, learning; comp on par with senior IC market
    - id: senior_ic
      label: Senior IC / Staff
      lens: architecture reach, tech-lead influence without formal mgmt
    - id: tech_lead
      label: Tech Lead
      lens: small team leadership + hands-on code, roadmap responsibility
    - id: manager
      label: Manager
      lens: people leadership, hiring, cross-team collaboration
    - id: instructor
      label: Instructor / Educator
      lens: teaching, curriculum, live delivery, cohort experience
  seniority_keywords:
    individual_contributor: ["junior", "mid", "ic"]
    senior_ic: ["senior", "staff", "principal", "lead engineer"]
    tech_lead: ["tech lead", "lead"]
    manager: ["manager", "director", "head of"]
    instructor: ["instructor", "trainer", "curriculum lead"]
  source_providers:
    - id: hn_jobs
      kind: rss
      credentials_required: false
    - id: hn_algolia
      kind: hn_algolia
      credentials_required: false
    - id: ai_jobs_net
      kind: rss
      credentials_required: false
    - id: we_work_remotely
      kind: rss
      credentials_required: false
  data_extensions:
    note: >
      Adds organized shape for job postings on top of the ai_topics
      schema. `topic` mirrors `role_type` and `content_type` reuses
      "posting" for uniformity with the shared viewer.
    collections:
      - name: artifacts/organized/job_watch/<date>.json
        purpose: per-posting classification output
        fields:
          schema_version: {type: int, const: 1}
          track: {type: string, const: job_watch}
          items:
            type: array
            items:
              item_key: {type: string}
              source_id: {type: string}
              url: {type: string}
              title: {type: string}
              company: {type: string}
              topic: {type: string, enum_source: JOB_WATCH.role_types[].id}
              content_type: {type: string, const: posting}
              categories: {type: array, items: string}
              audiences: {type: array, items: {type: string, enum_source: JOB_WATCH.audiences[].id}}
              role_type: {type: string, enum_source: JOB_WATCH.role_types[].id}
              seniority: {type: string, enum_source: JOB_WATCH.audiences[].id}
              is_remote_friendly: {type: boolean}
              confidence: {type: number}
              rationale: {type: string}
  iteration_plan:
    - id: I0
      goal: scaffold job_watch on the shared feed pipeline
      test_round_data: track boots, empty digest renders
    - id: I1
      goal: taxonomy JSON, deterministic classifier, seniority inference
      test_round_data: 30 fixture postings validate against role_type + seniority
    - id: I2
      goal: enrich with real feeds (HN Jobs, HN Algolia AI queries, ai-jobs.net, WWR)
      test_round_data: items per role_type, source coverage
    - id: I3
      goal: integrate two ATS discovery modes from scripts/discover/sources for a curated employer list
      test_round_data: postings per employer, dedupe rate
    - id: I5
      goal: LLM classifier that reads full JD to refine role_type + seniority
      test_round_data: agreement rate with I1 deterministic classifier
    - id: I6
      goal: audience rerank + audience digests (I6/I7 pattern)
      test_round_data: per-audience digest quality on gold set
  metrics_artifact_path: artifacts/metrics/job_watch/IN-<iteration>.json
  open_decisions:
    - which employer ATS shortlist to integrate first (Greenhouse vs Ashby vs Lever)
    - whether to require comp band presence for "strong match" scoring
    - how aggressively to filter recruiter-listed postings
```
