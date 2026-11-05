# Saved-run membership evidence

This workflow checks a retained publication epoch without acquiring sources,
rerunning models, regenerating figures or changing its seal. The
[dated aggregate receipt](run-membership-20261105.json) describes the current
retained run. The [consistency review](publication-consistency-review.md)
preserves the older manuscript discrepancy separately.

## Three producer identities

- The analysis receipt and publication epoch identify the stored record-analysis
  producer, run ID and seed.
- The retained NLP diagnostic identifies its own producer and source digest.
- The audit identifies the current exporter, its helper-file digests and actual
  Python implementation/version separately. A new export timestamp does not
  make either earlier producer current or attest to new inference.

The selected paper remains manuscript 0.5.0 with accompanying software 0.7.0,
as recorded in [publication.json](../publication.json). This source maintenance
does not change the deposited PDF, native output or release assets.

## Check a retained epoch

Use the configured project environment and an explicit evidence root containing
the authorized private capture and its sealed publication store:

```sh
uv run python scripts/audit_manuscript_membership.py \
  --evidence-root /authorized/blake-evidence-root \
  --output /unused/membership-audit.json
```

In managed GitVault work, execute through the qualified offline test workflow
with a bounded intent and output in its supervised namespace. The output name
must be unused; the CLI preserves an occupied file. Omit `--output` to print
the JSON. A source-only public checkout cannot verify the private files merely
from the published aggregate receipt.

The audit reuses saved-epoch admission, compares the complete work-ID sets in
epoch inputs, manifest, metrics and result ledger, and requires matching explicit
text-modality flags. It checks the retained diagnostic's source digests,
eligible/embedded/missing/filtered partition and embedded text hashes against
the epoch inputs. New publication seals persist `membership_bindings`; manuscript
token admission refuses changed metric bytes and mismatched IDs or modalities.
Legacy nonpublication diagnostics retain their separate compatibility behavior.

The receipt's `metric_binding` states what supports the metric bytes:

| Value | Meaning |
|---|---|
| `publication_membership_bindings` | A new publication seal explicitly binds the compared artifacts. |
| `derived_receipt` | The admitted historical derived-artifact receipt binds these metric bytes. |
| `reviewed_at_export_only` | Today's exporter checked agreement; the older seal has no metric-byte binding. This is no retrospective producer or seal proof. |

The exporter does not rewrite a historical seal to upgrade its evidence.

## Public scope and historical limits

The aggregate contains counts, ID-set hashes, relative artifact paths and source
digests. It contains no provider transcriptions, raw work-ID lists or absolute
machine paths. The retained private corpus, indexes, backups and source images
remain under their existing custody and terms.

Matching the current saved run does not identify the six records behind the
older coverage/embedding discrepancy. The receipt retains
`historical_discrepancy.status: not_recovered`. It supplies no whole-oeuvre,
literary, scientific, image-census, visual-review or redistribution certification.
