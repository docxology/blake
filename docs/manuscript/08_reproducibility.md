# Reproducibility: Source Snapshot, Analysis Epoch, and Publication {#sec:reproducibility}

This is a local revised working draft. The earlier deposited working paper remains a separate archival record; no new deposit is claimed.

Reproduction requires the captured source inventory, its private local files, the recorded analysis producer, and a compatible environment. The public release supplies project-owned source, the manuscript, aggregate evidence, producer identities, and checksums; it does not supply the provider corpus. The preservation chain connects inputs, commands, derived results, figures, and rendered bytes [@peng2011reproducible; @sandve2013ten; @wilson2014best; @w3cprov2013overview; @owens2018digitalpreservation].

## Verify Retained Inputs Before Analysis

Use a fresh reproduction checkout with the recorded dependency lock and the documented Python environment. Restore or acquire the local evidence under applicable provider terms, then run the integrity verifier:

```bash
uv run python -m blake.recovery verify
```

The saved recovery-manifest digest is `{{RECOVERY_MANIFEST_SHA256}}`. A different capture defines a different input epoch. Source inventory recovery, unresolved images, and the historical restore drill are reported in [@sec:supp_recoverability]. Fresh remote acquisition can produce a different inventory and must not be substituted for the recorded capture without updating the evidence identities.

## Create and Analyze a New Local Epoch

Preserve previous outputs before using a fresh checkout or an unused output directory. The preparation command refuses an occupied destination and writes a new metadata database and copied transcriptions; it references original local image files without copying or altering them.

```bash
uv run python scripts/prepare_manuscript_epoch.py \
  --destination blake_data/publication/reproduction
uv run python scripts/reproduce_manuscript_analysis.py \
  --data-dir blake_data/publication/reproduction \
  --seed {{ANALYSIS_SEED}}
```

The driver uses the corpus API with offline reuse, no synthetic fixtures, the core visualization profile, Archive-inventory scope, and Archive-all image metadata. It seeds Python and NumPy and limits numerical-library and OpenCV threads. The analyzed publication epoch used software `{{ANALYSIS_PRODUCER_VERSION}}`, seed {{ANALYSIS_SEED}}, and run ID `{{ANALYSIS_RUN_ID}}`. The reproduction bundle records its exact producer-file digests separately from the final publication software. The original run saved its model payloads in JSON but omitted the SQLite handoff consumed by reports and the dashboard. A separately receipted derived refresh restored those exact payloads to the independent publication database and regenerated reports without repeating inference. The repair command, when needed for an already sealed legacy epoch, is:

```bash
uv run python scripts/refresh_manuscript_epoch.py
```

Reseal after that command. New analyses persist each component directly. The original model receipt remains unchanged; derived-artifact provenance names its own producer. Subsequent manuscript diagnostics select the saved run's actual data directory and identified result ledger.

The saved pipeline status is `{{RUN_STATUS}}`, with {{ANALYSIS_WORKS_ANALYZED}}/{{ANALYSIS_WORKS_TOTAL}} records analyzed and current-results status `{{ANALYSIS_RESULTS_CURRENT}}`. Its top-level ledger reports {{ANALYSIS_ERROR_COUNT}} errors; the recursive component census reports {{ANALYSIS_NESTED_ERROR_COUNT}} nested errors, including {{TOPIC_INSUFFICIENT_WORKS}} insufficient-text and {{TOPIC_PRUNED_WORKS}} pruned-vocabulary topic results. Successful pipeline completion does not erase component unavailability.

## Generate Figures and Hydrate the Manuscript

### Authoring, Evidence and Output Roots

Preparation normally reads evidence and writes derived outputs in the authoring
project. A staged authoring candidate may instead name an explicit evidence read
root with `--evidence-root` or `BLAKE_MANUSCRIPT_EVIDENCE_ROOT`. This changes the
saved analysis and custody inputs while keeping manuscript prose, legal-claim
ledger and executing producer code in the authoring tree. Generated figures and
hydrated sources remain under its `output/` directory. No other checkout is
searched and an invalid explicit read root fails even if authoring caches exist.

```bash
uv run python scripts/generate_manuscript_figures.py --public-only \
  --evidence-root "$BLAKE_EVIDENCE_ROOT"
TEMPLATE_REPO_ROOT=../template \
  uv run python scripts/z_generate_manuscript_variables.py \
  --evidence-root "$BLAKE_EVIDENCE_ROOT"
```

Figure preparation reads diagnostic inputs without rewriting their saved files.
A bounded aggregate/text stage cannot satisfy full recovery verification merely
by being selected as a read root. Strict publication-token admission retains its
saved-epoch and input-binding checks; full recovery and backup verification still
require their original complete local sources. Preserve existing output artifacts
before producing a new display epoch. A source-code profile diagram has its own
source digest and never changes the analytical producer identity.

With the retained backup and historical restore-control files available locally,
the publication seal freshly verifies the captured inventory, existing backup,
private search projection, and the retained repaired/corrupted control copies:

```bash
uv run python scripts/seal_manuscript_evidence.py \
  --analysis-receipt analysis_output/data/analysis_epoch_receipt.json
```

This verifies the existing restore evidence; it does not run another restore drill.
The commands require the private corpus for analytical regeneration. The public
reproduction archive separately includes hydrated manuscript sources and aggregate
figures for rendering the deposited paper without redistributing those source files.

The figure producer reads the saved analysis artifacts:

```bash
uv run python scripts/generate_manuscript_figures.py --public-only
TEMPLATE_REPO_ROOT=../template \
  uv run python scripts/z_generate_manuscript_variables.py
```

The cover is a labeled project-authored generated asset with provenance, outside the corpus evidence ledger. Local source-image mosaics can be generated for private inspection but are excluded from the public manuscript and reproduction archive. Publication hydration requires every used quantitative token to resolve from the saved artifacts and verified publication evidence. The input membership and content digests remain inspectable.

## Render and Validate

The shared template renderer uses a separate compatible environment. The release records its exact source commit. Bind its local ignored `projects/active/blake` lifecycle leaf link to this checkout without changing other project bindings. After strict hydration succeeds, run from that template checkout:

```bash
uv run python scripts/pipeline/stage_03_render.py \
  --project active/blake --skip-manuscript-hydration
uv run python scripts/pipeline/stage_04_validate.py --project active/blake
```

The explicit hydration step preserves Blake's analysis environment while using the template's native rendering infrastructure. The skip flag reuses already validated hydrated sources; it does not authorize unresolved tokens or stale results. Rendered-page inspection, citation and cross-reference checks, privacy checks, source tests, installed-package checks, and release-asset checksums qualify the final artifact set. The deposited PDF and software assets must match the independently verified download bytes. Publication and an identifier do not themselves establish peer review, scientific validation, or whole-oeuvre completeness [@smith2016software; @rocrate2022].
