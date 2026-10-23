# Rights and Distribution Controls {#sec:legal_distribution}

This section records the release's operational distribution policy, not legal advice or item-level clearance. Underlying authorship, publication history, editorial contributions, digital files, provider terms, database rights, and a particular proposed use are separate questions. The release publishes project code, manuscript prose, aggregate figures, and reproducibility metadata while withholding the expressive provider corpus.

## Duration and Reproduction Layers

William Blake died in {{BLAKE_DEATH_YEAR}}. His death date supports a public-domain baseline for ordinary life-plus-{{LIFE_PLUS_TERM_YEARS}} author-term works, but it is insufficient to decide every source file's status. U.S. pre-{{US_PRE_1978_THRESHOLD}} publication rules differ from modern author-term rules. The Copyright Office's circular states that works published in the United States before {{US_PUBLIC_DOMAIN_2026_CUTOFF}} are in the public domain as of {{PUBLICATION_YEAR}}; that statement must not be generalized without regard to publication history or other legal categories [@uscopyright_chapter3; @uscopyright_circular15a].

Special unpublished-work rules also matter. U.S. section {{USC_PRE_1978_UNPUBLISHED_SECTION}} can preserve a floor through {{US_303_PUBLICATION_FLOOR_EXPIRY}} for qualifying older works first published by the end of {{US_303_PUBLICATION_FLOOR_CUTOFF}}. U.K. guidance describes protection through {{UK_2039_RULE_EXPIRY_YEAR}} for specified older unpublished works and engravings. The E.U. term directive provides a {{EU_UNPUBLISHED_PUBLICATION_TERM_YEARS}}-year economic-rights term for qualifying first lawful publication or communication of a previously unpublished work after copyright expiry [@uscopyright_chapter3; @ukipo_duration; @eudirective2006term]. These are reasons to retain item-level publication-history questions, especially for manuscripts and later editions.

Underlying public-domain art and a supplied digital file must likewise be distinguished. *Feist* separates unprotectable facts from original selection or arrangement. *Bridgeman* addresses originality in exact photographic copies of public-domain two-dimensional art, without supplying a worldwide license for every image file. E.U. DSM Article {{EU_DSM_PUBLIC_DOMAIN_ARTICLE}} excludes copyright or related-rights protection for reproductions of expired visual-art works unless the reproduction itself meets the originality criterion [@feist_rural; @bridgeman_corel; @eudirective2019dsm; @petri_public_domain_museum]. Modern editorial apparatus may contain original expression even where Blake's own text is public domain. Whether a particular file or contribution qualifies requires source-specific assessment.

## Provider Policies and Release Decisions

Provider terms are not automatically copyright, nor does every online term necessarily bind every user. Ordinary notice and assent remain relevant to contract analysis [@specht_netscape; @nguyen_barnes]. This release nevertheless follows a conservative publication policy: potential provider, edition, database, contract, and access restrictions are reviewed independently from underlying public-domain status [@mazzone_copyfraud; @wallace_culture_copyright].

The historical static Blake Archive conditions page describes restrictions on Archive texts and images. It is historical evidence of a policy, not a verified current permission grant; the current permissions route could not be refreshed during the publication check. Keep raw Archive files and full image mirrors out of the public deposit unless an applicable item-level permission or reuse basis has been documented [@blakearchiveconditions; @blakearchivepermissions]. This withholding policy does not assert that every faithful reproduction necessarily has a new copyright.

The default release rules are:

- **Code, tests, scripts, and project-authored prose:** include under the repository license to the extent the authors hold the relevant rights.
- **Aggregate counts, checksums, source URLs, authority labels, and charts without source images:** include with provenance and citations. The release does not relicense the underlying provider material [@feist_rural].
- **Blake-authored underlying material:** assess separately from its supplied edition, transcription, apparatus, or image file. Public-domain authorship is not an automatic license for every surrounding contribution.
- **Project Gutenberg material:** distinguish underlying text from Project Gutenberg branding and license wrappers; any proposed distribution must follow the applicable source and trademark conditions [@projectgutenberglicense]. This release includes no fallback source texts.
- **Wikisource material:** inspect the specific revision, footer, history, and attribution requirements. Current Wikimedia terms use CC BY-SA {{WIKIMEDIA_CC_BY_SA_VERSION}} for contributed text, with provisions and exceptions for imported material and public-domain content. Do not assume a universal license from a page's presence on Wikisource or fold contributor text into MIT [@wikimediaterms].
- **Archive TEI/XML, transcriptions, images, private indexes, backups, and restore copies:** retain locally; omit from the public repository and deposit.
- **Museum and catalogue leads:** cite as corroborating metadata or future review leads unless a compatible reuse basis is established for a proposed file.
- **Generated cover and project-authored diagrams:** include with provenance and a non-evidence label. The release license conveys only rights the authors can license; inclusion does not assert exclusive copyright in generated output.
- **Mosaics containing acquired source images:** retain as private inspection artifacts. They are omitted from the public PDF, HTML, and reproduction archive.

The code can be open source; the entire local evidence cache is not thereby open source. The Archive-all acquisition option describes evidence depth, not a permission grant. Public assets exclude `blake_data/` and other provider-payload territories. [@sec:supp_rights_matrix] records the corresponding artifact-level checklist [@candela_collections_data].

## Use-Specific Review

U.S. section {{USC_FAIR_USE_SECTION}} weighs purpose, nature, amount, and market effect for the particular use. Research or indexing is not an automatic blanket exemption. *HathiTrust* and *Google Books* concern specific transformative uses; they do not authorize this project to publish a bulk mirror of provider files [@uscopyright_chapter1; @hathitrust; @google_books]. A proposal to distribute excerpts, thumbnails, images, or expressive derived material requires its own source, attribution, amount, venue, and permission or exception review.

The deposited set therefore makes the workflow inspectable through software, source identities, aggregate evidence, and commands while keeping the provider corpus local. Byte integrity, access, authorship, and distribution authority remain separate properties [@owens2018digitalpreservation].
