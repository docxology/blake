# Manuscript authoring contract

Read [root guidance](../../AGENTS.md), the [documentation contract](../AGENTS.md),
[style guide](../style-guide.md) and [reproducibility](08_reproducibility.md)
before editing. This file and the authoring README are guidance, not paper body
inputs. A guide-only correction does not update the deposited paper.

## Quantitative claims and hydration

The numbered body files use `{{UPPERCASE_TOKEN}}` values computed by
[variables.py](../../manuscript_tools/variables.py) and the publication-evidence
owners from the selected saved artifacts. Do not hard-type a result count,
percentage or word count into a body paragraph or caption. Historical dates,
edition locators, labels and bibliographic facts retain their actual source.

The allowed quantitative keys are the generated
`output/data/manuscript_variables.json` keys. Strict hydration refuses an unknown
or empty used token; leaving a literal placeholder is not an accepted fallback.
The [hydration entry point](../../scripts/z_generate_manuscript_variables.py)
checks that contract before writing the generated `output/manuscript/` sources.
Configuration metadata has its own template contract; do not assume a body-token
substitution also changes `config.yaml` titles or native PDF metadata.

Keep authoring, evidence-read and output roots explicit. Selecting an evidence
root does not change the saved analysis producer or qualify recovery from an
incomplete aggregate staging directory. Follow the actual reproduction guide
for `BLAKE_MANUSCRIPT_EVIDENCE_ROOT` and `TEMPLATE_REPO_ROOT` bindings.

## Figures and assets

[Figure production](../../manuscript_tools/figures.py) writes to repository-root
`output/figures/`. The authored body uses paths such as
`../../output/figures/coverage_status.png`; the hydrated copy has its own staged
paths. Assign the registered `fig:` label and cross-reference it with the
template's `[@fig:label]` syntax.

The complete [visualization brief](../visualization-publication-brief.md) lists
the encodings, source bindings and QA requirements, including the source-derived
`core_profile_ownership` diagnostic. Such a code diagram has its own digest; it
is not a new corpus analysis. Captions retain their denominators, availability
and rights limits. See [binary asset guidance](assets/AGENTS.md) for the generated
cover, which is outside corpus evidence.

## Research and distribution limits

The paper describes a partial, target-aware captured corpus. Preserve direct
source roles, copy/edition distinctions, component errors and missingness. Do
not turn successful infrastructure, a search hit or a zero over selected inputs
into complete-oeuvre or literary acceptance. MIT project code and provider text,
TEI, images and caches have distinct terms and custody.

## Native production

[Reproducibility](08_reproducibility.md) is the command owner. Prepare a new
accounted epoch, verify its inputs, generate figures and strictly hydrate before
using the recorded template API and compatible external environment. The current
documented template lane is `active/blake`; the renderer and validator are
`scripts/pipeline/stage_03_render.py` and `stage_04_validate.py` in that separately
pinned checkout. Preserve the ignored lifecycle binding and every previous output.

Acquisition, analysis, recovery and native production have different resource
effects and admission. They are not a single routine "regenerate everything"
command. Retained native/recovery receipts do not renew consumed grants. Changed
paper outputs need actual complete page, citation/cross-reference and browser
checks, with source, native and publication identities recorded separately.
