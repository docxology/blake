# Primary-text search and evidence boundaries

`blake-text` is a local passage index alongside the existing corpus pipeline and
metadata browser. It uses SQLite FTS5 candidates followed by exact token/span
verification. No model, embedding service, download, account, or GUI is needed.
It never acquires sources automatically. Keep indexes and rights-controlled
inputs under ignored `blake_data/` or an explicitly private external directory.
An index contains the original expression, so it inherits its inputs' restrictions.

## What is available

The versioned `canonical_target.json` (2026-06-22) describes **104 work-level
targets**, including **39 expecting text**. Its categories include 20 illuminated
book entries, 11 manuscripts and two letter-category records. Those are targets,
not acquired transcriptions, and grouped records are not a letter/plate census.
Some entries overlap intentionally, such as separate and combined Songs. Do not
sum them as independent texts. The ledger remains unchanged by this search index.

The public repository supplies code, target metadata, documentation, and seven
explicitly selected primary-text excerpts from **one work and one edition**:
*The Marriage of Heaven and Hell*, Boston: John W. Luce and Company, 1906,
printed pages 7, 11, 14, 20, 27, 31 and 43. See
[`primary-passages.jsonl`](../examples/primary-passages.jsonl). These excerpts are
the underlying public-domain primary text transcribed in
[eBook 45315](https://www.gutenberg.org/ebooks/45315), updated 2024-10-24, with
source attribution. The provider license wrapper, transcriber's cover, images
and modern annotations are excluded. The sample is neither the whole *Marriage*
nor the Blake corpus. Zeros from it say nothing about unsampled passages.

At the initial 2026-10-22 inspection, the canonical checkout and inspected older backup
checkout had no `blake_data/` or `analysis_output/` directory. No saved manifest,
text cache, source XML, letters, manuscript images or local analysis could be read
from those locations. This bounded observation does not prove that other copies
or a protected corpus are absent. Restoring access to a retained private corpus
was necessary. A subsequent recovery retained a pinned source snapshot locally;
the private workflow below supersedes that initial absence observation. Unlocking
must use the owner's normal supported process.

## Reproduce searches

In an existing qualified environment:

```sh
blake-text --index blake_data/search/demo.sqlite build examples/primary-passages.jsonl
blake-text --index blake_data/search/demo.sqlite coverage
blake-text --index blake_data/search/demo.sqlite query state
blake-text --index blake_data/search/demo.sqlite query states --mode variants
blake-text --index blake_data/search/demo.sqlite query 'Eternity is in love with the productions of time' --mode phrase
blake-text --index blake_data/search/demo.sqlite query 'federation-hypothesis' --mode concept
blake-text --index blake_data/search/demo.sqlite concepts
blake-text --index blake_data/search/demo.sqlite suite
```

The same CLI is available as `python -m blake.text_search`; the lightweight
profile needs only the existing Click and Pydantic dependencies plus SQLite with
FTS5. Importing this search surface defers the optional NLP stack. The full `blake`
CLI and `BlakeCorpus` public names remain available in their full environment.

`word` searches whole normalized tokens, including stopwords; `phrase` requires
contiguous tokens in one passage and tolerates punctuation/line breaks. Both use
NFKC, casefolding and tokenization. Possessive `Albion’s` contains token `Albion`.
`literal` searches exact, case-sensitive characters, including substrings and
whitespace; it intentionally scans the selected snapshot. `variants` explicitly
expands the listed inflection/spelling families. No generic stemming is applied.
`fourfold`, `four-fold` and `four fold` can be expanded together; `identity` and
`individual` remain distinct words. Normalization does not silently turn
`measur’d` into `measured`, resolve abbreviations, or join print line-end hyphens.

Results retain original text, character offsets, matched expression, stable
work/passage/edition/copy fields, the source locator and URL, passage SHA-256 and
optional source-file SHA-256. Original spelling is never overwritten. Counts
include every matched occurrence before the display limit; edition duplicates
remain separate records, not independent historical witnesses by assumption.
Use `--work-id` and `--edition-id` to restrict a query. Metadata, editorial and
unverified passages are excluded from primary occurrence search. An occurrence
of “Jerusalem” does not identify the work, the hymn, a place or a character: use
the stable work identity and read its context. The default author ID is specifically
William Blake (1757–1827), not another person named Blake.

## Restored private corpus

After recovery and verification, build the additional private search projection:

```sh
uv run --python 3.11 blake-text build-recovered
uv run --python 3.11 blake-text --recovered coverage
uv run --python 3.11 blake-text --recovered query state
uv run --python 3.11 blake-text --recovered query 'Eternity is in love with the productions of time' --mode phrase
uv run --python 3.11 blake-text --recovered query federation-hypothesis --mode concept
uv run --python 3.11 blake-text --recovered query state --scope exploratory --plane erdman
uv run --python 3.11 blake-text --recovered query phystext --scope exploratory --plane xml
uv run --python 3.11 blake-text --recovered query Blake --scope exploratory --plane reading --role unverified
```

Use global `--data-dir PATH` for a different private recovery directory. The
captured `recovery/search.sqlite` remains unchanged. The additional index lives
under ignored `blake_data/search/recovered/`, with a directory identity derived
from the captured manifest and producer code, normalization, runtime and lockfile.
Its manifest binds every consumed input, index bytes, exact passage membership,
role/plane counts and omitted empty Erdman pages. Changed inputs refuse a rebuild;
a damaged derived index refuses to open rather than silently replacing evidence.

The retained capture contains 727 Archive source documents and 540 extracted
reading passages: 199 labeled primary and 341 unverified. The projection also
indexes retained Erdman pages and all 727 raw Archive XML documents, plus the four
Erdman XML parts. Raw XML includes markup, metadata, variants, deletions and
apparatus. Erdman pages/parts are mixed edition material, labeled editorial with
author `mixed-edition`; raw Archive XML has unverified author and role. Empty
Erdman pages are disclosed separately. Coverage reports the actual indexed counts.

Primary scope defaults to William Blake and the primary reading plane. Explicit
`--scope exploratory` searches labeled source matches across all authors unless
`--author-id` restricts them. Use `--plane`, `--role`, `--work-id` and `--edition-id`
to narrow the selection. Exploratory totals are divided by role, plane and author,
with Blake-primary occurrences reported separately. A match in markup or mixed
editorial text does not become evidence that Blake wrote that expression.

The private CLI omits full passage bodies and displays up to 20 matches per hit,
with 120 characters of context on each side. Counts still cover the full selected
scope before display limits. The Python API retains full original passages and
spans. Opening a projection checks its index bytes, captured-manifest identity,
producer and metadata consistency. It does not rehash every physical source file
or image on every query; rebuilding revalidates consumed files, and recovery
`verify` checks the complete retained capture. Keep all these indexes private.

For the older flattened-cache contract:

```sh
blake-text --index /PRIVATE/search.sqlite import-cache /PRIVATE/corpus_manifest.json /PRIVATE/blake_data
blake-text --index /PRIVATE/search.sqlite coverage
```

The importer accepts the existing `CorpusManifest` work-record contract, requires
an explicit Boolean `has_text` and non-fixture run, reads only selected IDs, reports
missing selected files, and retains direct and suffixed file variants separately.
It does not enumerate unrelated documents, assistant notes or drafts. It refuses
unsafe IDs, escaping/symlink files, duplicate IDs, missing source URLs and empty
selected texts. It cannot recover an erased copy/plate identity from flattened
text. Such cache records receive only truthful **file-line** locators and
**unverified** edition/primary status; they cannot appear as primary occurrences.
They are available only as labeled exploratory source matches.

Review the selected files against their editions before promoting them to search
evidence. The Python API exposes this review material without modifying it:

```python
from pathlib import Path
from blake.text_search.cache import import_cache

selection = import_cache(Path('/PRIVATE/corpus_manifest.json'), Path('/PRIVATE/blake_data'))
# Keep this review file private. Check author, work, edition, copy, locator,
# primary/editorial boundary and rights against the source before setting
# text_role='primary' in reviewed JSONL. Do not invent unavailable identifiers.
with Path('/PRIVATE/review.jsonl').open('x', encoding='utf-8') as handle:
    for passage in selection.passages:
        handle.write(passage.model_dump_json() + '\n')
```

Build the reviewed JSONL with `blake-text ... build /PRIVATE/reviewed.jsonl`.
Malformed or duplicate input aborts the atomic rebuild and retains the previous
index. Coverage is an exact snapshot of indexed passages, not a freshness claim
about a subsequently changed cache. Rebuild after reviewed inputs change.

## Authority, variants and gaps

The [William Blake Archive](https://blakearchive.org/) supplies scholarly
copy/object-specific editions. Its original transcriptions, images and editorial
apparatus have provider terms distinct from the underlying Blake work. The
[source-owned copy D XML](https://raw.githubusercontent.com/blakearchive/data/master/works/mhh.d.xml)
explicitly reserves edition/image rights. Inspect it for verification; this
repository does not redistribute that file. Source adapters now mark Archive
file rights as unknown pending review rather than granting blanket public-domain
status. Follow the existing [rights matrix](manuscript/13_supplement_rights_matrix.md).

The requested proverb is verified as *The Marriage of Heaven and Hell*,
**copy D, object 7 (Bentley/Erdman/Keynes plate 7), line `mhh.d.illbk.07.16`**:
“Eternity is in love with the productions of time.” It appears in the sample's
1906 edition on **printed page 14**, not plate 14. The wording of this sentence
agrees between those two checked witnesses. Do not infer universal copy agreement.
Nearby edition differences show why the edition distinction matters: the Archive
has `plow`, `measur'd`, `wholsom` and a line-broken `wis-` / `-dom`; the 1906
reading has `plough`, `measured`, `wholesome`, and unbroken `wisdom`, with
punctuation differences. These are editorial/spelling/lineation differences,
not automatically Blake-authored substantive revisions. Full copy collation is open.

Two source extraction routes now share a reading-layer parser. It selects BAD
`phystext` or TEI `body`, avoids overlapping parent/child duplication, excludes
notes/descriptive annotations and deletions, selects original `choice` readings,
and exposes existing block `n`/XML identifiers. Corrected/expanded alternatives
remain in source XML; they are not concatenated into the primary reading. This
is not a diplomatic manuscript/variant apparatus. Raw source XML must be retained
privately to recover additions/deletions, layout, variants and editorial decisions.
Existing flattened caches are not repaired automatically; re-extract and review
them before comparing counts. The metadata browser remains discovery
search, with substring relevance and metadata fields; use passage search for
literal occurrence evidence.

The demonstration includes no *Milton*, *Jerusalem*, *Four Zoas*, Notebook,
Pickering Manuscript, correspondence, visual inscriptions beyond the selected
prose, complete illuminated copies, manuscript facsimiles, images or modern
annotations. Work IDs/plate numbers are not interchangeable across copies or
editions. The ledger's 39 expected-text entries and 104 total targets do not
measure exhaustive letters, marginalia, textual variants or all Blake materials.

## Concept navigation and research testing

The versioned concept registry gives **editorial query expansions**, primary
checking links and explicit rationales. It makes no semantic occurrence claim.
Every returned passage still shows the actual expanded word matched. No embedding
similarity is treated as a quotation. `federation-hypothesis` deliberately returns
states/nations/individual/contraries as testing leads; use separate `word`
queries for `federal` and `federation`. Neither an expanded hit nor a zero in
the sample establishes a Blakean political doctrine, a state-to-nation mapping,
or a metaphysics of eternal essences.

For close reading after corpus restoration, prioritize *Milton* plate 32[35]
(states versus individual identities), *Jerusalem* with edition/copy identification
(Albion and emanation vocabulary), and the letter to Thomas Butts of 22 November
1802 (one/two/three/fourfold vision). These are **checking leads**, absent from
the demonstration, and require authoritative passage verification before quoting.
Political scholarship and interpretation belong to the separate research lane.

A targeted source-owned XML check on 2026-10-22 verified the *Milton* states
passage in **copy C, object 35, Bentley/Keynes e, Erdman 32[35]**:
`milton.c.illbk.35.11` concerns combinations of individuals; `.23-.24`
distinguish states from individuals and changing states from persistent individual
identities; `.33-.39` distinguish imagination, states and eternal forms. See the
[copy C XML](https://raw.githubusercontent.com/blakearchive/data/master/works/milton.c.xml).
The [copy B metadata](https://raw.githubusercontent.com/blakearchive/data/master/works/milton.b.xml)
explicitly excludes added plates a-e, so this passage cannot be recovered from
copy B alone. This creates a textual test for any hypothesis about eternal states;
it supplies neither a political doctrine nor proof of Platonic essences.

The same check found hyphenated **Four-fold** at `milton.b.illbk.35.24`
(copy B, object 35, Bentley/Keynes 35, Erdman 35[39]) and a distinction between
negation and contraries at `milton.b.illbk.42.33-.35`. Object 35 in copy B is
**not** object 35 in copy C. These are externally checked reading leads, not
additional indexed texts or an exhaustive concordance. No provider XML or
annotations were incorporated into the sample or committed.

Related publication metadata is maintained independently in
[docxology/docxology's bibliography](https://github.com/docxology/docxology/blob/main/pages/BIBLIOGRAPHY.md).
The *Mapping William Blake* artifact is [10.5281/zenodo.21047574](https://doi.org/10.5281/zenodo.21047574),
whose concept DOI is [10.5281/zenodo.21047573](https://doi.org/10.5281/zenodo.21047573).
Publication full text is scholarship, not primary Blake corpus membership.

## Focused verification

```sh
uv run --python 3.11 pytest tests/test_passage_search.py tests/test_search_scopes.py tests/test_recovered_search.py tests/test_private_search_display.py --noconftest -o addopts='' -q
```

The focused suite exercises real SQLite, primary/edition/author boundaries,
normalization, original spans, fixtures, cache membership, atomic failure and the
actual CLI. This minimal profile does not qualify the complete optional NLP,
GUI, downloader network, visualization, or manuscript pipeline. Run the existing
full tests in a separately qualified full environment before making those claims.
