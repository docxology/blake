# Corpus and methods for independent application papers

Blake supplies reusable evidence infrastructure. An application paper supplies a
question, a versioned vocabulary or analysis specification, contextual review,
interpretation and its own manuscript. Private research questions and source text
do not need to be added to the public software repository.

## Ownership

| Shared Blake repository | Application repository |
|---|---|
| Acquisition, provider adapters, source capture and recovery | Research question and domain vocabulary |
| Source identities, authors, editions, copies, roles, planes and rights | Contextual classification and interpretive decisions |
| Normalization, original spans, portable snapshots, generic lexical studies | Selected passages, reading ledger, bibliography and manuscript |
| Infrastructure methods paper and software tests | Its own immutable result epochs and scientific argument |

Blakean Federalism is an existing private application with a historical frozen
reader. Blakean Entomology uses this portable interface for an independent
invertebrate study. Their arguments and acceptance records remain application
evidence. Existing pins should be retained until a deliberate migration compares
the old and new passage membership, text, roles, authors, editions and counts.

## Export a private application snapshot

First prepare and verify a recovered search projection using the existing
recovery workflow. Export never downloads sources or silently builds an index.
Choose an independent, new destination outside the source tree:

```bash
uv run --python 3.11 python -m blake.applications export \
  --data-dir blake_data \
  --destination ../../Private/YourStudy/local_data/corpus/v1
```

The command reports the SHA-256 of `manifest.json`. Record that digest as the
application's trusted pin. Keep the bundle under ignored private storage.
The bundle contains `passages.jsonl` and a completion `manifest.json`; the
manifest binds captured source, projection, index and exporter identities, exact
ordered membership, per-passage text/source hashes, and role/plane/author counts.
Export rehashes every consumed source input before and after copying. It refuses
occupied destinations, symlink paths and overlapping source/destination roots.
A failed incomplete destination is retained; use a new destination after diagnosis.

The recorded Archive commit identifies source metadata; it does not independently
attest the Git checkout that exported it. Source hashes, code identity, software
version and runtime identity are distinct. A portable historical bundle can be
read after the producer runtime changes without pretending to recreate it.

```python
from pathlib import Path
from blake.applications import load_bundle

# Obtain the expected digest from the application's reviewed pin, not the bundle.
bundle = load_bundle(Path("local_data/corpus/v1"), expected_manifest_sha256)
passages = bundle.passages
```

Opening verifies the caller's pinned manifest bytes, payload bytes, ordered IDs,
unique membership, all source/text bindings, and all declared counts. No upstream
data is modified. A successful export is a byte/membership result, not a new
authorship review, source acquisition, rights clearance or completeness verdict.

```bash
uv run --python 3.11 python -m blake.applications verify \
  --bundle ../../Private/YourStudy/local_data/corpus/v1 \
  --manifest-sha256 DIGEST_FROM_YOUR_REVIEWED_PIN
```

## Run an uncapped lexical study

```python
from blake.studies import StudySpec, StudyTerm, scan_passages, summarize

spec = StudySpec(
    study_id="example-v1",
    title="An explicit application question",
    terms=(StudyTerm(term_id="example", group="application", forms=("state", "states")),),
)
result = scan_passages(bundle.passages, spec)
summary = summarize(result)
```

The application owns the vocabulary; Blake has no domain-specific animal or
political roster in this engine. Forms use the existing
`nfkc-casefold-source-spans-v2` tokenization, including contiguous token phrases
across punctuation and line breaks. Original expression, offsets and provenance
remain attached to every hit. There is no stemming, fuzzy inference or display cap.
The matcher compiles the forms once and walks each passage's token stream once.

A hit is a **category/source/span**, not an adjudicated mention. Equivalent forms
inside a category share one original span; different categories may overlap. A
generic word and a compound category can both match. Summing categories therefore
does not count distinct animals, ideas, passages or historical observations.
Matched passage/edition and exact-text-group counts remain separately named.

Results bind canonical specification, normalization and method source hashes.
All nine role/plane cells are emitted for every category, including zeros. Source
unit and word-token denominators are retained per role, plane and author. Tokens
in raw XML include markup and apparatus; they are not a Blake prose denominator.
Blake-primary counts require the identified Blake author, primary role and reading
plane together. Other source matches remain exploratory.

`summarize` omits expressions, contexts and passage bodies. It is suitable for
text-free aggregate review. Full results and bundles duplicate provider expression
and must stay private and ignored unless separately cleared. A zero result means
absence from these explicit forms in these captured bytes, never absence from
the entire oeuvre. Image-only and uncaptured discussions remain open research.

## Versioning and application migration

Pin the corpus manifest and vocabulary, record method/exporter hashes, and write
new output directories for reruns. Never replace earlier result epochs silently.
A manuscript edit is not an automatic corpus repin. For an existing application,
compare exported passages by ID and text hash against its historical import,
then compare roles, authors, planes, editions and locators before considering new
analysis. Keep historical figures and conclusions bound to their original inputs.

The 0.4.0 source moves acquisition, NLP, vision and corpus orchestration
requirements into `full`. Plain `uv sync` installs methods dependencies;
`uv sync --extra full --extra dev` prepares the complete pipeline and tests.
GUI/API surfaces need `full` together with their respective extras. Clean
installed-package qualification is tracked separately from this documentation.

## Shared methods and application policy

[Shared methods](shared-methods.md) provide literal search, regex concordance,
counted statistics and sensitivity, configurable proximity, immutable review
queues, run verification and an offline search workspace. Import the relevant
module explicitly; a profile label does not silently change a matcher's behavior.
The existing `blake.text_search` and `blake.studies` implementations and their
source-hashed identities remain unchanged by this extraction.

Portable bundle and historical projection passage models are distinct contracts.
Use `bundle_to_projection` or `projection_to_bundle` from
`blake.methods.schema_conversion` when crossing that boundary. Conversion validates
existing fields; it cannot invent provenance or promote a source role. A bundle
manifest digest is not interchangeable with a projection pin.

Federalism and Entomology retain private query selections, decision vocabularies,
classification policy, branding and manuscript interpretation. Shared code has no
default political or animal interpretation. New application runs bind both their
own code and delegated shared methods with `source_binding_sha256`; changing
producer code requires a new epoch, while historical output receipts stay intact.
