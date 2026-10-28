# Methods: Local Text, Image, Cross-Modal, and Theme Diagnostics {#sec:methods_analysis}

## Shared Mechanisms and Application Policy {#sec:shared_methods}

The public core separates reusable evidence mechanisms from caller-owned
research decisions. Projection and portable-bundle adapters retain source/copy
identity, edition, locator, rights, role and plane under caller-held pins. Explicit
schema conversion validates those fields without supplying missing provenance or
promoting unverified text. Shared methods perform retrieval, counted aggregation,
artifact admission and review-queue membership checks. Applications supply query
forms, scope, review labels and interpretation. This division permits selected
corpus evidence to be reused without treating the applications' questions or
conclusions as properties of the corpus itself.

The current source declares {{CORE_RETRIEVAL_PROFILE_COUNT}} retrieval profiles.
The profile and responsibility diagnostic binds
{{CORE_ARCHITECTURE_SOURCE_FILES}} source files under SHA-256
`{{CORE_ARCHITECTURE_SOURCE_SHA256}}`. [@fig:core_profile_ownership] is generated
from those profile declarations and explicit public API responsibility references.
It measures the source candidate, independently of the saved analytical producer
`{{ANALYSIS_PRODUCER_VERSION}}`; it does not represent another NLP run.

![Source-derived retrieval contracts and declared responsibility boundaries. Profile normalization and boundary descriptions come from the executable registry; the companion artifact binds the referenced public source files. Application policy names required caller inputs, without measuring private application outcomes. This code diagnostic does not update the saved corpus analysis.](../../output/figures/core_profile_ownership.png){#fig:core_profile_ownership}

The generic evidence-tree API validates a connected rooted hierarchy and computes
a deterministic layout without recursion. Sibling traversal follows declared
order; placements return in declared node order. Leaves receive consecutive rows
and an internal row is the arithmetic mean of all descendant leaf rows. Averaging
only immediate child rows would over-weight small subtrees. Depth counts parent
edges. Neither depth nor row represents elapsed time, evolutionary distance or
confidence, and the API supplies no domain taxonomy or identity judgment.

## Retrieval Profiles and Counting Units

The regex profile uses Python IGNORECASE with explicit escaped alternatives and
source word boundaries. Literal search uses Unicode casefold while retaining
original-source spans and exact punctuation and whitespace. The normalized-token
profile applies NFKC and casefold before contiguous-token matching; punctuation
and line breaks separate tokens. These contracts can disagree, so a new profile
is never substituted for an old query epoch. Runtime Python and Unicode versions
are recorded separately from stable semantic identity.

Counts name their units: occurrences, eligible stored source units, copy-retaining
documents, exact-text groups or distinct work identifiers. Eligible zero-hit
groups and token denominators precede display caps. A source unit without word
tokens has an unavailable normalized rate. Exact-text grouping tests sensitivity
to repetition while preserving the original source/copy identities. Proximity
restricts retrieval within a declared source unit or complete word window; it
does not establish semantic or historical relatedness.

## Source-Bound Occurrence Search

The private search profile keeps reading passages, Erdman editorial pages, and raw XML in separate source planes. Primary scope requires identified authorship and primary reading text. Exploratory scope retains unverified and editorial labels. Normalized token and phrase matches preserve offsets into the original expression; exact matching is case-sensitive. Curated variants and concept vocabularies aid navigation without establishing semantic equivalence or whole-oeuvre occurrence claims. Source and index integrity failures refuse a query. Search counts name the selected indexed scope before display limits; the versioned contract is documented in `docs/methods.md`.

## Analysis Population and Authorship Boundary

The saved analysis population is {{WORKS_PRESENT}} local source/copy records, including {{WORKS_WITH_TEXT}} with text, {{WORKS_WITH_IMAGES}} with images, and {{WORKS_WITH_BOTH}} with both. The recovered reading layer separates {{RECOVERY_PRIMARY_RECORDS}} primary-reading transcriptions from {{RECOVERY_UNVERIFIED_RECORDS}} transcriptions with unverified authorship. The exploratory natural language processing (NLP) described below includes the saved text-bearing subset without promoting every transcription to Blake-authored primary text. Archive-primary metadata authority and reading-text authorship are different classifications.

Counts are descriptive for this retained population. Copy repetition, editorial material, shared image files, transcription variants, and missing sources preclude treating records as independent samples of Blake's oeuvre. Corpus construction therefore bounds every downstream result [@atkins1992corpus; @biber1993representativeness; @bode2018world].

## Text and Model Diagnostics

The text module writes basic token counts, per-record vocabulary size, type-token ratio, lexical sentiment, named entities, sentence-level topic descriptors, style metrics, readability estimates, and theme matches. The lexical-signature artifact applies its own documented deterministic tokenizer, stopword and editorial-apparatus filters, adjacent-term phrase counts, and distinctive-term scores. Tokenizers and filters define different quantities; their totals are not assumed interchangeable. Type-token ratios remain length-sensitive [@derose1990text; @teiP5; @tweediebaayen1998lexical; @mccarthyjarvis2010lexical].

Sentiment uses the Natural Language Toolkit (NLTK) Valence Aware Dictionary and sEntiment Reasoner (VADER) lexicon [@huttogilbert2014vader]. Readability uses the implementation's sentence, word, and syllable heuristics to compute Flesch-style estimates. Neither is validated here against Blake scholarship or annotated historical-language judgments [@flesch1948new; @panglee2008sentiment; @kimklinger2019sentiment]. Topic extraction fits latent Dirichlet allocation to sentence-level TF-IDF weights. That is an exploratory weighted-input heuristic rather than a validated generative model of word counts. Short texts and vocabularies emptied by document-frequency pruning produce explicit unavailable/error results; they do not contribute fabricated topic components [@blei2003lda; @blei2012topic].

Entity extraction combines the pretrained spaCy `en_core_web_sm` statistical model with bounded rule-based Blake vocabularies. The ontology layer caps entities and relationships and serializes its outputs. It is not a Blake-specific trained or validated entity recognizer. Named-entity strings, heuristic labels, co-occurrence relationships, and metadata-derived themes are navigation aids requiring editorial review; a graph edge does not establish a historically correct relation [@weingart2011networks; @moretti2011network; @ramsay2011readingmachines].

## Membership-Bound Text Projection

The manuscript diagnostic producer is version `{{NLP_DIAGNOSTIC_PRODUCER_VERSION}}`,
with source SHA-256 `{{NLP_DIAGNOSTIC_SOURCE_SHA256}}`. It is recorded separately
from the producer of the saved per-record analyses.

The manuscript diagnostic selects text-bearing IDs from the saved `text_metrics.json` and resolves transcriptions through that run's manifest data directory. It rejects external or symlinked data-directory substitutions, excludes unmatched cached IDs, and partitions saved members into embedded, missing-file, and token-empty groups. Content and membership digests bind those selections. This fixes the source-selection boundary; it does not retrospectively explain numerical discrepancies in earlier published epochs.

The projection uses {{NLP_EMBEDDING_FEATURES}} selected terms across {{NLP_EMBEDDING_WORKS}} transcriptions. Term-frequency/inverse-document-frequency (TF-IDF) vectors are normalized to unit length and centered. A symmetric covariance eigendecomposition computes the leading principal components, with a fixed sign convention. Explained-variance fractions are nonnegative eigenvalues divided by covariance trace. Rank-deficient and constant text spaces are checked against an independent singular-value oracle. The display is a principal-component projection, not an uncentered latent semantic analysis, a learned semantic encoder, or a stable map of Blake's oeuvre. A direct numerical comparison with an independent eigendecomposition checks the saved matrix and variance calculations. Missing, unverified, repetitive, and editorial transcriptions remain interpretive constraints [@biber1993representativeness; @bode2018world; @rockwellsinclair2016hermeneutica].

## Images, Cross-Modal Joins, and Error Accounting

Visual analysis computes image-level color and composition descriptors on local files. Repeated file associations can be processed under several source records. Cross-modal analysis joins available text and image evidence; it does not validate iconography, copy state, or a theory of Blake's composite art [@arnoldtilton2019distantviewing; @weverssmits2020visualdigitalturn; @mitchell1994picture; @viscomi1993blake]. The work-theme visualization is a separate descriptive index, with {{NETWORK_NODES}} nodes and {{NETWORK_EDGES}} edges including {{THEME_COUNT}} theme nodes. The graph uses available metadata themes, scored text-analyzer themes, and entity surface strings from the text module's categories, including its other-entity category. It preserves case after whitespace normalization and does not resolve spelling variants or authenticate historical identities. Its entity population differs from the selected labels and rules used by the ontology census. Each record/theme or record/entity pair contributes one edge; edge source labels distinguish metadata from model output. It is an exploratory index, with no validated knowledge-graph or entity-authentication claim.

Top-level completion and nested component availability are separate ledgers. A completed record can contain a topic or sentiment error. The publication census recursively counts explicit error fields and separately reports insufficient-text topic results, vocabulary-pruning failures, and any other nested errors. JSON artifacts, figure inputs, manuscript variables, and publication checks preserve those distinctions [@sandve2013ten; @owens2018digitalpreservation; @w3cprov2013overview].
