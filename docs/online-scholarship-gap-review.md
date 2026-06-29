# Online Scholarship Gap Review

Review date: 2026-06-25; refreshed 2026-06-26

This note records source-owned leads found during a live web/scholarship pass over the unresolved target ledger. It does not promote any target to complete evidence, validate fallback text, change coverage counts, or grant redistribution rights. The acquisition rule remains conservative: exact title/source ownership, fetchability, checksum, attribution, licensing, and validation markers must all pass before a source can alter the corpus manifest.

Machine-readable lead registry: `docs/source-leads.json` (schema `1.1`). Those rows are fed into the missing-evidence review as `manual_review` candidates only; they are intentionally not eligible for automatic corpus acceptance. Schema `1.1` adds `review_priority`, `direct_source_basis`, and `scholarship_note` so a reviewer can distinguish a direct source-owned lead from a generic search hit.

## Durable Leads

| Target | Lead | What It Adds | Local Decision |
| --- | --- | --- | --- |
| `bb126` / *The Pickering Manuscript* | Morgan Library, *William Blake's World* collection page | A source-owned collection record with provenance and a visible transcription excerpt for the manuscript page. | Treat as corroborating manuscript evidence and a candidate source for manual review, not as an automated bulk text source. |
| `bb126` / *The Pickering Manuscript* | Morgan Library, source-owned digital facsimile root | Page sequence and institutional metadata for MA 2879. | Higher-priority exact-source review lead; still requires page enumeration, attribution, rights, checksum, and completeness validation before acquisition. |
| `bb126` / *The Pickering Manuscript* | Morgan Library, MA 2879 pp. 16-17 page record | Page-level metadata and a text-bearing transcription for part of *Auguries of Innocence*. | Negative-control lead for a future extractor: the page proves source-owned page text exists without proving whole-work completeness. |
| `bb209` / *VALA, or The Four Zoas* | Wikisource, *Vala, or The Four Zoas/Night the First* | A text-bearing public page that identifies Blake and records Erdman/Blake Archive sourcing. | Candidate fallback lead only; requires full-work completeness, attribution, license, and checksum review. |
| `bb209` / *VALA, or The Four Zoas* | William Blake Archive work route | Source-owned work route for the manuscript target. | Use for target identity and object/copy scoping; do not treat app-route visibility as acquired text. |
| `bb209` / *VALA, or The Four Zoas* | Blake/An Illustrated Quarterly, work-specific Four Zoas bibliography | Demonstrates that *Four Zoas* is an unusually complex textual/editorial scholarship surface. | Scholarship context only; prevents a single fallback transcription from being treated as a settled edition. |
| `bb74` / *An Island in the Moon* | Wikisource, *An Island in the Moon* | Text-bearing pages exist, but the page flags second-hand transcription provenance. | Keep as a cautionary fallback lead; second-hand provenance prevents automatic acceptance. |
| `everlasting-gospel` / *The Everlasting Gospel* | Wikisource, complete page | Text-bearing page says it reflects Erdman textual notes and Blake Archive sourcing. | Candidate targeted fallback lead only; current corpus status does not change without source/license/checksum validation. |
| `poetical-sketches` / *Poetical Sketches* | Wikisource subpages such as "To Spring" | Individual text pages are available even when collection/catalog pages are unsuitable. | Future acquisition should target exact subpages/page sequences rather than search or table-of-contents pages. |
| `bb134` / Receipts | Yale finding aid for Osborn MSS 87 | Collection-level description names receipts paid to Blake by John Linnell and describes the account material. | Bibliographic/material corroboration only; not a redistributable corpus text. |
| `bb196` / "then She bore Pale desire" and "Woe cried the muse" | Blake Archive blog/source leads | Confirms the target is a fragmentary manuscript/transcription problem rather than an ordinary title page lookup. | Manual source-owned review remains required. |
| `bbwba1` / *The Phoenix to Mrs Butts* | Joseph Viscomi page and Blake Archive update leads | Confirms a specialized attribution/corroboration path exists outside generic catalog search. | Treat as scholarly lead for attribution review, not as acquired evidence. |
| `bb37` / "A Fairy leapt" | Wikisource/Sampson and Bentley leads surfaced in search results | Suggests the poem can be pursued through edition-specific page extraction. | Future task is exact-page source extraction with license and checksum metadata. |
| `bb122`, `bb125`, `bb206`, `bb69`, `but828` | William Blake Archive work/copy pages surfaced as public leads | Confirms target identifiers route through the Archive web app. | Do not accept from app-shell pages or unstable API probes; a source-owned resolver or manual review is still needed. |

## Scholarship Context Added

The refresh adds a distinction that the earlier ledger did not make strongly enough: some sources are acquisition candidates, while others are scholarship controls. The Morgan Pickering Manuscript pages are source-owned, page-level, and text-bearing, so they are useful future extraction targets. The *Four Zoas* bibliography and Blake/An Illustrated Quarterly article index are not corpus evidence, but they are important reviewer context because they show why *VALA, or The Four Zoas* should be treated as a manuscript/editorial problem rather than an ordinary title lookup. The Yale collection guides and Blake Archive route pages likewise help institutional source discovery, but they remain corroborating context unless they lead to exact, rights-reviewed, checksum-backed item evidence.

## Red-Team Assessment

The pass found leads, not missing completed evidence. The strongest practical improvement is to make the next partial-evidence pass source-specific: exact Wikisource subpages for text-bearing fallback candidates, Morgan page-sequence records for Pickering Manuscript review, Yale records for manuscript and collection corroboration, Blake/An Illustrated Quarterly scholarship controls for complex works such as *Four Zoas*, and a rights-gated Blake Archive resolver only if it can fetch source-owned files reproducibly. Generic search pages, catalog landing pages, version pages, app-shell pages, bibliography-only pages, and throttled/short pulls remain rejection cases.

## Next Local Actions

1. Add exact direct-source candidate rows for the Wikisource text leads, preserving Wikimedia attribution and license metadata.
2. Add Morgan page-sequence review for *The Pickering Manuscript* with one negative-control page proving that partial page text is not whole-work evidence.
3. Add Yale and Blake/An Illustrated Quarterly sources as corroborating/manual-review candidate context rather than corpus text providers.
4. Investigate a rights-gated Blake Archive resolver for stable source files, but keep raw Archive text, TEI, object images, and mirrors excluded from public bundles unless permission or venue-specific clearance exists.
5. Re-run coverage, source audit, acquisition review, manuscript variables, and figure generation only after a candidate source passes fetch, exact-title, attribution, checksum, and validation gates.
