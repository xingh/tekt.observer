# Market Watch (SignalFlow) — 00 Arkitype

Purpose-layer spec for the investor market-watch tracker built on top of tekt.observer. Parallel to `.arkitype/00-topic-tracker.md`; reuses `01-infrastructure.md`, `02-database.md`, `03-software.md`, and `04-interface.md` where compatible. Persona lives in `profile/personas/investor.md`.

```yaml
MARKET_WATCH:
  extends: SITE_PROFILE
  name: market_watch
  intent: >
    Produce a twice-daily situational digest for an investor monitoring a
    diversified portfolio across public equities, private equity / venture,
    and fixed income / macro. Split into portfolio-affecting alerts and
    broader situational awareness.
  verbs:
    - explore
    - seek
    - gather
    - organize
    - understand
    - generate
  verb_semantics:
    explore:  discover candidate news sources per asset class and desk
    seek:     turn each promising source into a repeatable ingest script
    gather:   run scheduled ingest across newswires, filings, macro feeds
    organize: classify each item by asset class, event type, and watchlist match
    understand: rerank per persona watchlist and asset allocation
    generate: render portfolio-alert + situational-awareness digest and deliver
  asset_classes:
    - id: public_equities
      label: Public equities
      instruments: [stock, etf, adr, index]
      event_types_of_interest:
        - earnings_release
        - guidance_change
        - rating_action
        - regulatory_action
        - m_and_a
        - exec_change
        - insider_transaction
        - activist_filing
        - product_launch_with_material_impact
        - major_customer_or_supplier_news
    - id: private_equity
      label: Private equity / venture
      instruments: [direct_position, fund_lp_interest, secondary]
      event_types_of_interest:
        - funding_round
        - exit_or_acquisition
        - exec_change
        - product_launch
        - competitor_or_peer_round
        - regulatory_action
        - down_round_signal
        - board_change
    - id: fixed_income_macro
      label: Fixed income / macro
      instruments: [treasury, ig_corp, hy_corp, cash, macro_indicator]
      event_types_of_interest:
        - central_bank_policy
        - cpi_pce_print
        - payrolls_print
        - yield_curve_shift
        - credit_spread_shift
        - sovereign_debt_action
        - rate_decision
        - qt_qe_change
  digest_sections:
    - id: portfolio_alerts
      order: 1
      inclusion_rule: >
        must name a watchlist entity or a direct competitor / customer /
        regulator of one, AND describe a specific event from
        asset_classes[].event_types_of_interest
      required_fields_per_item: [affected_entity, event_type, mechanism, source_url, published_at]
    - id: situational_awareness
      order: 2
      inclusion_rule: >
        moves a named benchmark, index, sector, or macro indicator, OR
        reflects a policy shift with concrete numbers or explicit central-bank
        / regulator language
      required_fields_per_item: [indicator_or_benchmark, mechanism, source_url, published_at]
  audiences:
    - id: investors
      label: Investors
      lens: portfolio P&L over 1-5 sessions, capital allocation, risk exposure
    - id: portfolio_managers
      label: Portfolio managers
      lens: mandate-relative positioning, factor exposures, drawdown control
    - id: allocators
      label: Allocators
      lens: manager selection, cross-asset allocation, benchmark relative
    - id: gps
      label: GPs
      lens: private-market pipeline, exit windows, comp sets for portfolio companies
    - id: lps
      label: LPs
      lens: fund performance drivers, capital call cadence, sector concentration
  source_providers:
    - id: reuters
      kind: newswire
      discovery_mode_candidate: html
      credentials_required: false
    - id: bloomberg
      kind: newswire
      discovery_mode_candidate: browser
      credentials_required: true
    - id: wsj
      kind: publication
      discovery_mode_candidate: html
      credentials_required: true
    - id: ft
      kind: publication
      discovery_mode_candidate: html
      credentials_required: true
    - id: sec_edgar
      kind: filings_api
      discovery_mode_candidate: to_be_added
      credentials_required: false
    - id: fed_press
      kind: central_bank_press
      discovery_mode_candidate: html
      credentials_required: false
    - id: ecb_press
      kind: central_bank_press
      discovery_mode_candidate: html
      credentials_required: false
    - id: boj_press
      kind: central_bank_press
      discovery_mode_candidate: html
      credentials_required: false
    - id: pitchbook
      kind: private_market_data
      discovery_mode_candidate: browser
      credentials_required: true
    - id: crunchbase
      kind: private_market_data
      discovery_mode_candidate: html
      credentials_required: true
    - id: term_sheet_newsletter
      kind: newsletter
      discovery_mode_candidate: html
      credentials_required: false
    - id: fred
      kind: macro_data_api
      discovery_mode_candidate: to_be_added
      credentials_required: false
  data_extensions:
    note: >
      Adds three logical collections layered on top of the schemas documented
      in 02-database.md. Physical layout lands in later iterations; the shape
      is declared here so downstream stages can validate against it.
    collections:
      - name: profile/personas/<persona>/watchlist.json
        purpose: structured watchlist derived from the persona markdown
        fields:
          schema_version: {type: int, const: 1}
          persona: {type: string}
          entries:
            type: array
            items:
              id: {type: string}
              kind: {type: string, enum: [ticker, private_company, fund, macro_indicator]}
              symbol_or_name: {type: string}
              asset_class: {type: string, enum_source: MARKET_WATCH.asset_classes[].id}
              related: {type: array, items: string}
      - name: artifacts/classified/market_watch/<date>.json
        purpose: per-item asset-class + event-type classification
        fields:
          schema_version: {type: int, const: 1}
          track: {type: string, const: market_watch}
          date: {type: string, format: YYYY-MM-DD}
          items:
            type: array
            items:
              item_key: {type: string}
              source_id: {type: string}
              url: {type: string}
              title: {type: string}
              published_at: {type: string, format: ISO8601}
              asset_class: {type: string, enum_source: MARKET_WATCH.asset_classes[].id}
              event_type: {type: string}
              named_entities: {type: array, items: string}
              watchlist_matches: {type: array, items: string}
              is_portfolio_alert: {type: boolean}
              confidence: {type: number}
              rationale: {type: string}
      - name: artifacts/alerts/market_watch/<date>.json
        purpose: audience-scoped alert scoring
        fields:
          schema_version: {type: int, const: 1}
          track: {type: string, const: market_watch}
          audience: {type: string, enum_source: MARKET_WATCH.audiences[].id}
          date: {type: string, format: YYYY-MM-DD}
          portfolio_alerts:
            type: array
            items:
              item_key: {type: string}
              affected_entity: {type: string}
              event_type: {type: string}
              impact_score: {type: number}
              mechanism: {type: string}
          situational_awareness:
            type: array
            items:
              item_key: {type: string}
              indicator_or_benchmark: {type: string}
              impact_score: {type: number}
              mechanism: {type: string}
  iteration_plan:
    - id: I0
      goal: scaffold market_watch track, investor persona, arkitype spec
      test_round_data: track boots end-to-end with local fixture; digest schema accepts both sections empty
    - id: I1
      goal: derive structured watchlist from persona markdown; classify against asset_classes and event_types
      test_round_data: 30 hand-labeled fixture items validate; unknown-event-type rejection counted
    - id: I2
      goal: explore stage seeds candidate sources per asset class using Reuters + fed_press + SEC EDGAR
      test_round_data: candidates per asset class; provider dedupe rate; missing-coverage gaps
    - id: I3
      goal: seek stage generates ingest scripts under tracks/market_watch/sources
      test_round_data: script success/fail per candidate; canary validation; cost per source
    - id: I4
      goal: gather stage runs ingest and writes discovery artifacts
      test_round_data: items/day/source; latency to publish; cross-day dedupe
    - id: I5
      goal: organize stage classifies items and computes watchlist_matches
      test_round_data: precision/recall of watchlist_matches on gold set; is_portfolio_alert base rate
    - id: I6
      goal: understand stage scores impact and reranks per audience
      test_round_data: top-K precision on gold set; A/B agreement between two scorers
    - id: I7
      goal: generate stage renders portfolio_alerts + situational_awareness sections; delivery via email/telegram
      test_round_data: digest length distribution per section; deliverability; investor self-rated usefulness
    - id: I8
      goal: SignalFlow feedback wires read/save signals back into impact scoring weights
      test_round_data: precision lift vs I6 baseline; watchlist weight drift over 7 days
  metrics_artifact_path: artifacts/metrics/market_watch/IN-<iteration>.json
  open_decisions:
    - whether SEC EDGAR ingestion uses the JSON API or scrapes the HTML index
    - whether Bloomberg / paywalled sources are in scope or replaced with open equivalents
    - single vs. multi-audience runs (one digest for the persona vs. per-audience variants)
    - refresh cadence: once daily pre-market vs. twice daily (pre-market and post-close)
```
