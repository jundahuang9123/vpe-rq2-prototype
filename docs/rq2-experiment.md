# RQ2 experiment design (short)

Contracts: [`profile_element.linkml.yaml`](../requirement-reuse-service/schema/profile_element.linkml.yaml)
(scoring unit) and [`rq2_atom.linkml.yaml`](../requirement-reuse-service/schema/rq2_atom.linkml.yaml)
(input). Background: [rq2-plan.md](rq2-plan.md).

## Conditions

Each condition from C1 to C5 adds one component, so a gain traces to one step.

| Id | Generator | Output | Retrieval | Verify + repair | Human review |
|----|-----------|--------|-----------|-----------------|--------------|
| C0 | rules (existing) | change set → compiled | – | – | – |
| C1 | LLM | SHACL text | – | – | – |
| C2 | LLM | typed change set → compiled | – | – | – |
| C3 | LLM | typed change set → compiled | ✓ | – | – |
| **C4** | LLM | typed change set → compiled | ✓ | ✓ (≤ 3 rounds) | – |
| C5 | LLM | typed change set → compiled | ✓ | ✓ | ✓ (subset, in VPE) |

Inputs: A-gold for all conditions; A-rq1 for C4 where RQ1 atoms exist.

## Metrics (unit: `ProfileElement` = (target class, path))

- **Correctness:** element P/R/F1, strict (same IRIs) and relaxed (RDFS
  sub/super-property, then adjudication; minted terms match by class and
  meaning, never by IRI). Matched elements: agreement on obligation,
  cardinality, range, vocabulary.
- **Reuse-first:** extension rate vs gold, unjustified mints, invented IRIs.
- **Validity (layered):** parse → SHACL-SHACL → known terms → legal refinement.
- **Behaviour:** same verdicts as gold shapes on test records.
- **Traceability:** atom coverage, elements without a source atom, elements per atom.
- **Effort and cost:** review actions (C5), repair rounds, tokens, runtime.

## Leakage controls

- **L1** name-only probe per model; C3/C4 reported as gains above it.
- **L2** atoms term-free; index excludes target namespace and shapes per run.
- **L3** unseen cases: Construct-DCAT; releases newer than a model's cutoff.
- **L4** counterfactual atoms (`counterfactual_of`, `expected_change`); output
  that still follows the publication indicates recall.

## Run budget (≈ 230 runs, from the plan page)

| Block | Runs |
|-------|------|
| C1–C4 × 2 models × 5 benchmarks × 3 repeats | 120 |
| C0 once per benchmark | 5 |
| L1 name-only probes | 24 |
| L4 counterfactuals, C2 and C4, four public profiles | 48 |
| A-rq1 on C4 | 30 |
| **Total** | **227** |

C5 runs as review sessions on two benchmarks (not counted above). Models,
repeats and the probe count are provisional (verify in WP0 model shortlist).
