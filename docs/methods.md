# Local source evidence methods

Software: **0.2.0**. Methods profile: `local-source-evidence-v2`.
Dashboard schema: `2`. These labels describe software contracts. Captured source
commits, manifest hashes, target-ledger versions and search normalization remain
independently versioned evidence identities.

## Recovery and integrity

Recovery retains a pinned Archive repository and the captured Erdman response.
The manifest records each retained file's size, checksum and source URL, together
with extracted passages, source identifiers, image outcomes and limitations.
Primary readings, unverified readings, editorial material and raw XML are separate
roles or source planes. A successful source capture does not establish complete
coverage of Blake's surviving works or editions.

Integrity verification checks actual bytes against the captured inventory. Backup
and offline restore operate on that inventoried snapshot. Conflicting files are
quarantined; the restore drill deliberately damages a restored copy, requires
verification to reject it, then repairs it. The derived exploratory search index
is built separately and can be regenerated from the retained text inputs.

## Search and interpretation

`nfkc-casefold-source-spans-v2` normalizes Unicode composition and case while
retaining offsets into unchanged source expression. Word and phrase searches use
contiguous normalized tokens. Literal mode is case-sensitive exact matching.
Variants expand an explicit vocabulary; concept mode navigates curated terms and
does not count occurrences of an abstract idea or infer literary meaning.

Primary scope requires an identified author and primary reading text. The default
author is William Blake. Exploratory scope can include unverified readings,
editorial Erdman material and XML, whose matches may include markup and metadata.
Results retain author, edition, locator, role, plane, source URL, rights and source
hash. Totals describe the selected scope before display limits; a zero result is
not evidence of absence from the entire oeuvre.

The projection receipt binds its source manifest, consumed file receipts, producer
files, Python, SQLite, Pydantic and dependency lock. Wheels include the public
dependency lock under the same logical binding used by a source checkout.
A changed producer gets a new
derived directory; an incompatible or corrupted index is refused. Dashboard
search opens the index read-only and validates its bytes and membership before
returning bounded excerpts. It never builds an index or acquires sources implicitly.

## Dashboard and saved analyses

The Streamlit Local evidence view shows counts reported by the captured manifest
and identifies its hash. Viewing counts is not a fresh physical corpus verification.
Projection-receipt inspection is distinguished from the checksum and membership
validation performed on search. Unknown, absent or malformed evidence is disclosed.

The Streamlit browser can use a separate publication analysis database while
Local evidence continues to inspect the original captured store. Admission
requires a completed pipeline, matching run identities and hashes of the saved
manifest, results, metadata databases, preparation receipt and transcriptions.
A changed or malformed epoch is disclosed; it is not presented as current analysis.
New analyses persist all component payloads to SQLite. The explicit
`scripts/refresh_manuscript_epoch.py` repair command can restore an admitted
legacy epoch from its exact identified JSON ledger. It refuses conflicts, backs
up the affected derived files, and regenerates reports without repeating model
inference. Resealing binds the separate derived receipt and its artifact hashes.
Record/theme/entity links deduplicate record pairs and retain metadata versus
model provenance; categorized entity values supply their actual labels.

Publication postprocessing uses the identified saved result ledger rather than
guessing analyzer filenames. Its schema `1.3` separates saved text membership,
missing and filtered inputs, entity summaries, and text-analysis summaries.
Covariance principal components are checked with an independent singular-value
oracle, including rank-deficient and constant inputs. Top-level completion and
nested component errors remain separate counts.

The generated HTML workbench reports the software version and methods profile
alongside the saved run's target profile and coverage. A rendering or package
version change does not retrospectively rerun the record analyses.

## Reproduction

Run from the repository with the supported environment:

```bash
uv run --python 3.11 blake --version
uv run --python 3.11 python -m blake.recovery verify
uv run --python 3.11 blake-text build-recovered
uv run --python 3.11 blake-text --recovered query eternity
uv run --python 3.11 blake-text --recovered query state --scope exploratory --plane erdman
uv run --python 3.11 streamlit run blake/gui/gui.py
```

Source and image terms still apply. Raw corpus data, private indexes, backups and
provider text stay local. The current software assets accompany the versioned working paper at
[10.5281/zenodo.23601681](https://doi.org/10.5281/zenodo.23601681). The earlier
record contains the earlier PDF. Saved record analyses retain their actual
producer identity independently from the current package and manuscript diagnostics.
