# CLAUDE.md — vpe-rq2-prototype

Guidance for Claude Code sessions working in this repository.

## What this fork is for

This is a hard fork of [visual-profile-editor](https://github.com/jundahuang9123/visual-profile-editor)
(VPE, kept as the `upstream` remote) for **RQ2** of Junda Huang's PhD
(University of Wuppertal, TMDT): requirements-driven, reuse-first DCAT-AP
application profile generation, with LLMs used as bounded tools.

Requirement atoms go in; benchmark profiles are held out. The generated
profile **delta** is scored against the benchmark delta (published profile
minus its base). Full plan: [docs/rq2-plan.md](docs/rq2-plan.md).

## Three experiment rules (do not break these)

1. **Score the delta.** Only what a profile adds or tightens on top of its
   base counts. Inherited base constraints earn no credit.
2. **Keep the answer out of the input.** Atoms carry no IRIs and no profile
   names. For each run the vocabulary index excludes the target profile's own
   namespace and shapes.
3. **Freeze gold before any LLM run.** Gold deltas, atoms, atom-to-element
   alignment and counterfactual variants are frozen as git tag `rq2-gold-v1`.
   Later fixes get a new tag and a rerun; never edit gold under an existing tag.

## Bounded-LLM design

- The LLM **fills typed `ProfileChange` records** (schema:
  `requirement-reuse-service/schema/profile_change.linkml.yaml`). In the main
  condition it never writes SHACL.
- The symbolic side **retrieves** candidate terms, **verifies** every proposal
  (V1–V6: term exists, domain/range fit, legal refinement, reuse before mint,
  internal consistency, SHACL-SHACL), sends violations to **repair** (≤ 3
  rounds, then the review queue) and **compiles** deterministically: LinkML,
  SHACL and DSV all come from one `ProfileChangeSet`.
- **Reuse-first ordering:** reuse an existing term > refine (tighten) a base
  term > mint a new term. A mint must store the reason no candidate fit.

## Where RQ2 code goes

- Engine code: `requirement-reuse-service/requirement_reuse_service/`
- Schemas/contracts: `requirement-reuse-service/schema/`
- CLI tools and evaluators: `scripts/` (e.g. `scripts/shacl_delta.py`, later `scripts/evaluate_rq2.py`)
- Benchmark gold and per-profile material: `benchmarks/<profile>/`
  (`benchmarks/_tool-demo/` is tool output only, never gold)
- Small example instances: `examples/rq2-benchmark/`

## Running tests

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt -r requirement-reuse-service/requirements.txt pytest pyshacl
RRS_LLM_PROVIDER=mock python -m pytest -q
```

Tests must never call an external LLM API; use `RRS_LLM_PROVIDER=mock`.
If GitHub archive downloads are blocked, install General-Ontology-Editor from
a `git clone --branch v0.1.0` checkout instead (`pip install ../goe`).

## Working style

- Propose before multi-file changes; Junda reviews step by step.
- Keep diffs small and reviewable; one concern per commit.
- Do not change existing VPE behaviour (API, UI, generator output) without asking.
- Mark unverified facts as **"verify"**. Never put invented claims, numbers or
  citations into docs meant for papers.
- Do not pick benchmark profile versions yourself; RQ2 uses the same versions
  as the RQ1 benchmark. Leave version fields as `TODO` until confirmed.
- When editing LaTeX, keep macros such as `\acs{}`, `\ac{}`, `\cite{}` intact.
