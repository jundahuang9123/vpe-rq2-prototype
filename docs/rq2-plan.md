# RQ2 plan (essentials)

Full plan page (working draft, 8 Nov 2026):
<https://claude.ai/artifact/MjNSdesNDAbBKe1pZJEVHe>. This file is the
in-repo summary; where they differ, ask Junda which is current.

## Experiment logic

Mirrors RQ1: requirement atoms go in, benchmark profiles are held out. The
generated profile delta is scored against the benchmark delta (published
profile minus its base).

### Rules

1. **Score the delta.** Inherited base constraints earn no credit.
2. **Keep the answer out of the input.** Atoms carry no IRIs or profile names;
   for each run the vocabulary index excludes the target profile's own
   namespace and shapes.
3. **Freeze gold** (deltas, atoms, atom-to-element alignment, counterfactual
   variants) as git tag `rq2-gold-v1` before any LLM run.

### Inputs

- **A-gold**: curated term-free atoms (RQ1's gold atoms), used for all conditions.
- **A-rq1**: atoms extracted by the RQ1 pipeline, used for the end-to-end run.

## Architecture

VPE stays the workbench (atom sets, review queue, provenance). The engine in
`requirement-reuse-service` is the contribution:

```text
Atoms → Retrieve (top-k reusable terms per atom from a vocabulary index)
      → Propose (LLM fills a typed ProfileChange; no SHACL in the main condition)
      → Verify (V1–V6)
      → Repair on violations (LLM, ≤ 3 rounds; unresolved → VPE review queue)
      → ProfileChangeSet
      → Compile (deterministic; LinkML, SHACL and DSV from one change set)
```

Dataspecer is the publishing target via DSV (Data Specification Vocabulary).

### Verify checks

| Id | Check |
|----|-------|
| V1 | Term exists in the vocabulary index |
| V2 | Domain and range fit |
| V3 | Legal refinement of the base (may tighten, never loosen) |
| V4 | Reuse before mint, with the reason stored |
| V5 | Internal consistency (min ≤ max, mandatory ⇒ `sh:minCount 1`, one shape per path and class) |
| V6 | Compiled shapes pass SHACL-SHACL |

## Conditions

| Id | Description |
|----|-------------|
| C0 | Rules (existing generator) |
| C1 | LLM writes SHACL directly |
| C2 | LLM fills typed changes that are compiled |
| C3 | C2 + retrieval |
| C4 | C3 + verify + repair (**main condition**) |
| C5 | C4 + expert review in VPE, on a subset |

## Metrics

- Element P/R/F1 on (class, property), strict and relaxed (RDFS sub/super-
  property, then adjudication; minted terms match by class and meaning, never by IRI).
- Agreement on obligation, cardinality, range and vocabulary for matched elements.
- Reuse-first: extension rate, unjustified mints, invented IRIs.
- Layered validity: parse → SHACL-SHACL → known terms → legal refinement.
- Behaviour: same verdicts as gold shapes on test records.
- Traceability; effort and cost.

## Leakage controls

- **L1** closed-book (name-only) probe.
- **L2** answer held out (see rule 2).
- **L3** unseen cases (Construct-DCAT; releases newer than a model's training cutoff).
- **L4** counterfactual atoms: change a few atoms so the right answer departs
  from the published profile; if output still follows the publication, the
  model is recalling it.

Main claims rest on condition deltas and the unseen case; absolute scores on
public profiles are reported next to the L1 floor.

## Work packages

| WP | Content |
|----|---------|
| WP0 | Contracts and spikes |
| WP1 | Benchmark gold |
| WP2 | Symbolic core: vocabulary index from vocabulary files, refinement checker, profile model beyond `cx:` and the four DCAT classes, full SHACL compiler, DSV export |
| WP3 | Neural loop |
| WP4 | Evaluator (`scripts/evaluate_rq2.py`) |
| WP5a | VPE benchmark mode |
| WP5b | Dataspecer round-trip |
| WP6 | Runs and analysis |

## Benchmark cases and versions

RQ2 uses the same five cases and the same profile versions as the RQ1
benchmark (separate repo, branches `bench-a/b/c`): JRC, Stat, Geo, Health,
Mobility, plus Construct-DCAT as the unseen case.

| Case | Profile version | Base (per RQ1 brief) |
|------|-----------------|----------------------|
| JRC | TODO | DCAT-AP 1.1.0 (verify) |
| Stat | TODO | DCAT-AP 1.1.0 (verify) |
| Geo | TODO | DCAT-AP 1.1.0 (verify) |
| Health | TODO | DCAT-AP 3.0.0 (verify) |
| Mobility | TODO | DCAT-AP 2.0.1 (verify) |
| Construct-DCAT | TODO | DCAT-AP (version TODO) |

The plan page lists newer releases (GeoDCAT-AP 3.0.0, DCAT-AP-JRC v2,
HealthDCAT-AP r7, mobilityDCAT-AP 1.1.0); these are **unconfirmed** for RQ2
and must not be used as gold until Junda confirms against RQ1.
