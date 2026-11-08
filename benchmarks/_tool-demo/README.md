# Tool demo: `scripts/shacl_delta.py` on GeoDCAT-AP 3.0.0

**This is a tool demo, not benchmark gold.** GeoDCAT-AP 3.0.0 has not been
confirmed as the RQ2 benchmark version (RQ2 must use the RQ1 benchmark
versions). Nothing here was reviewed; do not cite these numbers.

Inputs (read from the SEMICeu GitHub repositories, shallow clones):

| File | Repository | Commit |
|------|------------|--------|
| `releases/3.0.0/shacl/geodcat-ap-SHACL.ttl` | SEMICeu/GeoDCAT-AP | `7e7d6a82f4bd4491c68f774f185193439881ab42` |
| `releases/3.0.0/shacl/dcat-ap-SHACL.ttl` | SEMICeu/DCAT-AP | `4470b8ea907b7eb9ec55ab22befd1ecd2210ff32` |

Base version: DCAT-AP 3.0.0, taken from GeoDCAT-AP's own
`releases/3.0.0/CHANGELOG.md` ("Alignment with DCAT-AP 3.0.0", lines 35–43)
and `index.html` ("extension of ... [[DCAT-AP-3]]"). The SHACL file itself
has no `owl:imports`.

Command:

```bash
python scripts/shacl_delta.py \
  --base <DCAT-AP>/releases/3.0.0/shacl/dcat-ap-SHACL.ttl \
  --profile <GeoDCAT-AP>/releases/3.0.0/shacl/geodcat-ap-SHACL.ttl \
  --profile-id geodcat-ap-3.0.0-demo --base-id dcat-ap-3.0.0 \
  --profile-namespace http://data.europa.eu/930/ \
  -o benchmarks/_tool-demo/geodcat-ap-3.0.0.delta.yaml \
  --report benchmarks/_tool-demo/geodcat-ap-3.0.0.report.yaml
```

Raw counts: 171 added, 0 tightened, 123 unchanged (excluded), 6 loosened;
plus 11 class additions; 54 elements under the GeoDCAT-AP namespace (`mint`).
No unhandled constructs were reported for either file.

Observations to check in WP1 (verify):

- Many "added" elements carry only a range facet (`sh:nodeKind`) and no
  cardinality, e.g. on `dcat:DatasetSeries` (GeoDCAT-AP copies Dataset
  properties onto Dataset Series). Whether range-only additions count as gold
  elements is a WP1 decision.
- The 6 "loosened" elements all drop a base `sh:maxCount` (e.g. `dcat:version`
  on Dataset, `dct:rights` on Catalog and Distribution). Check against the
  GeoDCAT-AP spec text whether this is intended or a SHACL generation artefact.
- Severity is merged per (class, path) as the strongest one; recommended-level
  shapes in separate files are not used here.
