# Blake documentation

Start with [project status](PROJECT_STATUS.md) for the qualified software and
retained paper, [quick start](quickstart.md) for installation, and
[verification](verification.md) for the actual check profiles. This is the
documentation map; [index.md](index.md) is a short entry point.

## Choose a workflow

| Need | Contract |
|---|---|
| Portable corpus and an independent research application | [Application contract](applications.md) and [shared methods](shared-methods.md) |
| Matching profiles, statistics, proximity, annotations, hierarchy, review planning or interval support | [Shared APIs](shared-methods.md), [composition](methods/composition.md), [review planning](methods/review-planning.md) and [intervals](methods/intervals.md) |
| Source acquisition, local corpus analysis, GUI or API | [User guide](user-guide.md), [configuration](configuration.md) and [API reference](api-reference.md) |
| Recovery, source-bound search and an offline workspace | [Local evidence methods](methods.md) and [text search](text-search.md) |
| Extend the implementation | [Developer guide](developer-guide.md), [architecture](ARCHITECTURE.md) and [technical specification](spec.md) |
| Diagnose a failed operation | [Troubleshooting](troubleshooting.md) |
| Author or reproduce a paper edition | [Manuscript guide](manuscript/README.md), [current native replay](paper-reproduction.md), [analytical reproducibility](manuscript/08_reproducibility.md) and [style guide](style-guide.md) |

## Installation profiles

The default package installs portable methods dependencies. Acquisition, NLP,
vision and the `BlakeCorpus` workflow require `full`. The GUI and HTTP API add
their surface extra to `full`; recovery has its own smaller profile. From an
existing checkout, choose the needed locked environment:

~~~sh
# Select the qualified local interpreter before sync/run
uv python pin 3.11.17

# Portable methods
uv sync --locked

# Corpus pipeline
uv sync --locked --extra full

# Complete test collection, including GUI/API dependencies
uv sync --locked --extra full --extra dev --extra gui --extra api
~~~

Current methods and optional-stack installations require Python 3.11 or newer;
the qualified local default is 3.11.17. Retained Python 3.9 wheel results belong
to their original source and metadata. Use [verification](verification.md) as the
runtime authority before selecting an interpreter or broadening a gate. In managed
GitVault work, use supported admission, external caches/TMP and both external
Python prefixes. A package-index installation selects the version available
there; it does not select the current Git source.

## Documentation and source ownership

Blake owns acquisition, source custody, portable schemas, retrieval and reusable
evidence/statistical methods. Applications own vocabulary, contextual decisions,
domain models, figures and manuscripts. The native document framework lives in
the separately pinned [docxology/template](https://github.com/docxology/template).
An installation or checksum supplies no new literary reading, image inventory,
scientific acceptance or redistribution clearance.

The [capability summary](COMPREHENSIVE_SYSTEM_SUMMARY.md) links each implemented
surface to its owner. [Architecture](ARCHITECTURE.md) explains the data flow;
operating instructions belong in the workflow guides above.

## Guides and research records

| Page or directory | Role |
|---|---|
| [Workflow guides](guides/README.md) | Acquisition and terminal interface |
| [Method notes](methods/README.md) | Focused reusable-method contracts |
| [Visualization brief](visualization-publication-brief.md) | Figure registry, intended encodings and QA requirements |
| [Source leads](source-leads.json) | Manual-review candidates, with no acquired-evidence credit |
| [Scholarship gap review](online-scholarship-gap-review.md) | Dated discovery and evidence-gaps note |
| [Publication consistency review](publication-consistency-review.md) | Historical discrepancy and current-run distinction |
| [Saved-run membership](run-membership.md) | Audit contract and dated aggregate receipt, with private source custody retained |
| [Manuscript sources and status](manuscript/README.md) | Retained paper inputs, generated assets and reproduction scope |
| [Current documentation reconciliation](documentation-review-20261102.json) | Frozen review, owner corrections and exact evidence scope |
| [Agent guidance](AGENTS.md) | Where to read before changing these documents |

Dated research and publication observations retain their original identities.
Current work is tracked in [PROJECT_STATUS.md](PROJECT_STATUS.md) and the
[scoped backlog](../TODO.md), rather than inferred from an old proposal.

These Markdown files are readable in the repository. No MkDocs configuration
or declared MkDocs build is shipped. The paper uses its recorded native template
workflow; it is a separate artifact from this documentation tree.

## Public editions — 3 November 2026

| Project | GitHub | Zenodo |
|---|---|---|
| Corpus and shared methods | [blake](https://github.com/docxology/blake) | [Paper 0.5.0](https://doi.org/10.5281/zenodo.23921364) |
| Invertebrate readings and concordance | [Blakean Entomology](https://github.com/docxology/Blakean_Entomology) | [1.0.0](https://doi.org/10.5281/zenodo.23900583) |
| Political argument and institutional models | [Blakean Federalism](https://github.com/docxology/Blakean_Federalism) | [1.0.0](https://doi.org/10.5281/zenodo.23900617) |

Core software **0.7.0** accompanies manuscript **0.5.0**. The application
releases keep their qualified SDK pin `263d7c83abe6f1309a64af3285a683c1b7672269`;
a later documentation or publication commit does not reassign their producer.
[Publication facts](../publication.json) bind the selected PDF and assets. Provider corpora remain in private ignored custody.

[Public edition and verification](publication-20261103.md) records the completed publication and separates
immutable release inputs from later documentation and remaining research.
