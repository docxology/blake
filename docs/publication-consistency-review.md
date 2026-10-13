# Publication consistency review

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
cached inputs. Legacy metric rows without `has_text` retain their recorded ID
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
