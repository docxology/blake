# Reproduce the current paper's native rendering

Paper **0.5.0** is the [94-page working draft](../Blake-0.5.0.pdf).
Its [public reproduction archive](../Blake-0.5.0-reproduction.zip) contains the
frozen Markdown, metadata, quantitative variables, project-authored aggregate
graphics, generated cover, checksums and native adapter. These inputs reproduce
the rendering; they do not reconstruct provider text, images or the private
analytical store. [Analytical reproduction](manuscript/08_reproducibility.md)
has a separate evidence and custody contract.

The software dependency remains Blake **0.7.0** at Git
`263d7c83abe6f1309a64af3285a683c1b7672269`. The saved corpus analysis remains
`0.2.0rc1`. The profile/ownership and interval illustrations have current-source
producer records; an illustration's arbitrary coordinates are not corpus data.

## Build a reader copy with the current Template pin

Use a clean [Template checkout at `87704feae0a4490ef7dad9c931d268e8c30273c2`](https://github.com/docxology/template/tree/87704feae0a4490ef7dad9c931d268e8c30273c2)
with its locked Python 3.14 environment, Pandoc, pandoc-crossref and XeLaTeX.
Set `TEMPLATE_ROOT` to that checkout and `ZIP` to the absolute path of the
public reproduction archive. From the Blake repository root, run the following.

~~~sh
project="$TEMPLATE_ROOT/projects/working/blake"
git worktree add --detach "$project" HEAD
cd "$TEMPLATE_ROOT"
uv run --no-sync python "$project/manuscript_tools/stage_published_reader.py" \
  --template-root "$TEMPLATE_ROOT" --archive "$ZIP" \
  --archive-sha256 95114e666f15130d2bf2b97044e0c2f4dd6a0fdfcb39142e31b9fad36c94a94e
uv run --no-sync python scripts/pipeline/stage_03_render.py --project working/blake
uv run --no-sync python scripts/pipeline/stage_04_validate.py --project working/blake
~~~

The staging command verifies the ZIP against the release record, verifies every
archive member and compares the numbered sources and support files with
`docs/manuscript/`. It hydrates the canonical sections with the deposited
variables, stages the approved aggregate graphics and generated cover, and
records the retained text values for render validation. The build writes
`output/pdf/blake_combined.pdf`, `output/web/index.html` and validation reports
under the Blake worktree. This reader uses the shared Template styling. The
deposited edition and its native renderer below define the released typography,
responsive article stylesheet, pagination and artifact hashes.

## Prepare an external replay epoch

Extract the archive into a new directory on mounted GitVault. Preserve the
archive and every previous output. The bundle verifier checks all declared
member bytes and rejects a changed input. The native adapter rejects an occupied
output epoch before invoking a writer.

Select the exact `docxology/template` source commit
`efce6d6f5b3c4e8e2bbf92d8250855a0a9389ae8` and its compatible locked external
Python **3.14** rendering environment. Set `TEMPLATE_ROOT` and `TEMPLATE_ENV`
to those already qualified selections; do not replace another owner's binding
or environment. Keep `TMPDIR`, caches and both Python prefixes on GitVault, and
use the supported repository/common-store admission for the actual run.

From the extracted archive root:

~~~sh
uv run --no-project --offline --python "${TEMPLATE_ENV}/bin/python" \
  python -B reproduce/verify_bundle.py .

UV_PROJECT_ENVIRONMENT="${TEMPLATE_ENV}" UV_PYTHON="${TEMPLATE_ENV}/bin/python" \
  uv run --no-sync --frozen --project "${TEMPLATE_ROOT}" python -B \
  reproduce/render_native.py --template-root "${TEMPLATE_ROOT}" --stage paper
~~~

The adapter calls `PDFRenderer.render_combined` and the actual
`WebRenderer.render_combined` implementation. Its source-owned CSS hook embeds
the admitted article stylesheet through the pinned framework, preserving print
dimensions and natural HTML image proportions. No generated TeX is edited by
the adapter. Native receipts bind the actual template sources, interpreter
prefixes, staged inputs, writer calls and PDF/HTML bytes.

## Verify the resulting edition

The qualified PDF SHA-256 is
`812e53237b40f808b4502e3dd358cbee5cda7d587e493ba95e41f02c11ad03eb`.
The corrected HTML SHA-256 is
`ec90070f2d696ddef7a5d232367263e2676e70f007696d87711bdaf5413f5160`.
Different source, fonts, framework or tool versions require a new epoch and
their own comparison; a writer exit code alone is insufficient.

Inspect physical pages, metadata, references, equations, figure labels and
desktop/mobile HTML. The long evidence table scrolls within its own region;
its caption stays at the visible width. Image heights adapt proportionally
when the viewport constrains their widths. The retained defective HTML is a
real refusing control for these checks. Browser layout tests do not certify
specialist accessibility or every device.

The independent final review accepted the exact current 94-page PDF and
responsive HTML for bounded working-draft use. It also recorded one
representation limit: the concept DOI appears in the PDF and configuration,
while the current HTML has no literal DOI or DOI link. Do not claim full
PDF/HTML bibliographic metadata parity. Exact review, replay and software
bindings are in [the working-draft record](../paper-working-draft.json).

The [publication manifest](../publication.json) identifies deposited paper **0.5.0**
at [10.5281/zenodo.23921364](https://doi.org/10.5281/zenodo.23921364), accompanying software **0.7.0**.
The concept DOI remains stable across paper editions. Source, software, native
rendering, scientific interpretation, hosted CI and publication evidence retain
separate scopes. The preceding 0.4.0 manifest remains preserved in history.
