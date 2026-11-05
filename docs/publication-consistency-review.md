# Publication consistency review

The historical sections below retain their original review scope.
The [current saved-run audit](run-membership.md) and dated addendum distinguish
later retained evidence from recovery of the older discrepancy.

## Text coverage and embedding denominators

The archived manuscript reports 156 text-bearing works for coverage and 162 for
TF-IDF/PCA. The clean repository does not include that run’s private local text
cache and complete analysis artifacts. The six-record difference therefore
cannot be assigned to named works or corrected to a historical number from this
checkout alone.

The source review identifies a surviving mechanism for such drift:
`manuscript_tools/nlp_diagnostics.py` previously scanned every cached text and
analysis file, using the saved run’s `text_metrics.json` only for display titles.
A stale cache file could enter embeddings despite being absent from the run or
having `has_text: false` in its text metrics. This is a demonstrated code defect,
not proof that it caused every record in the archived discrepancy.

The diagnostics now restrict text, entity, and text-analysis inputs to the saved
run’s text-bearing work IDs. `nlp_diagnostics.json` records the allowed IDs,
embedded IDs, excluded cache IDs, missing transcriptions, token-empty members,
and digests of the decoded embedded text. Missing saved membership admits no
cached inputs. Saved metric rows without `has_text` retain their recorded ID
membership; current pipeline rows explicitly include a boolean modality flag. A present non-boolean flag is not text-bearing evidence.

The embedding denominator can still be smaller than coverage when a saved
text-bearing work lacks a local file or yields no retained tokens. Such a
subset difference is explicit rather than silently importing unrelated records.
Membership and content digests do not prove original acquisition time, provider
rights, or that an old analysis file was regenerated against current text.

## Publication follow-up

Regenerate diagnostics and manuscript variables against the authorized saved
corpus before rendering a revised publication. Compare the row-level membership
with coverage and inspect every missing or filtered member. Preserve the old
publication and its source epoch; publish revised counts only with the new run’s
artifacts. No text or image acquisition, provider-rights change, or private
corpus upload is part of this correction.


## Reconciled current manuscript contract (2026-10-19)

Diagnostics now bind the exact saved-membership bytes, reject duplicate work
identities, and partition eligible IDs into embedded, missing, and token-filtered
sets. The partition must reconcile exactly; excluded cache IDs must be disjoint,
and the embedding count must match its identified work set. Publication-mode coverage must also match the saved eligible text membership. Publication-mode
variable generation refuses missing, implicit, or invalid modality
evidence. Draft-mode diagnostics retain explicit implicit/invalid lists.

The current manuscript reports each generated denominator and the membership
digest. No historical replacement count is asserted. A revised numerical result
still requires the authorized corpus/run artifacts, which are absent from this
clean checkout; fixture tests establish the contract, not a Blake corpus result.


## Fresh publication epoch

The current publication uses a new analysis store rather than attempting to
reconstruct or retrospectively correct the archived run. Its membership and
transcription hashes reconcile with the captured source ledger. The completed
record analyses retain their original producer version; subsequent diagnostic
and rendering identities are separate.

Two additional defects were reproduced before correction: diagnostics selected
the default cache rather than the saved manifest's data directory, and
filename-based model summaries missed the analyzer's title-bearing filenames.
Current summaries use the saved, identified result ledger. A rank-one projection
also exposed duplicated explained variance in the former power-iteration
fallback; covariance eigendecomposition now passes an independent singular-value
oracle and the degenerate-input controls.

The new epoch's row-level diagnostics, component-error census and publication
evidence live under `analysis_output/data/` locally. They do not establish the
cause of the older publication's six-record discrepancy.

## Retained current-run membership — 5 November 2026

The [dated aggregate audit](run-membership-20261105.json) checks the retained
publication epoch, not the earlier 156-versus-162 manuscript population. Its
manifest, epoch inputs, metrics and result ledger agree on 727 source/copy IDs;
540 are text-bearing. The retained NLP diagnostic partitions those eligible IDs
into 530 embedded and 10 token-filtered members, with none missing or imported
from an unmatched cache. Artifact and ID-set digests record that comparison.

The analytical producer remains `0.2.0rc1`; the saved diagnostic retains its
`0.2.0` producer and source digest. The current exporter has a separate source
identity and review time. The existing derived receipt binds the metric bytes;
no historical seal, model result, deposited PDF or native output was rewritten.
These observations do not name the six records in the older discrepancy or
establish its cause. Provider expression and full local evidence remain private.
