# Implemented capability map

This page summarizes implemented owners. [Documentation](README.md) routes
actual workflows; [project status](PROJECT_STATUS.md) and [verification](verification.md)
record measured qualification rather than general production guarantees.

| Capability | Owning surface |
|---|---|
| Source-governed corpus acquisition and phase accounting | [Corpus workflow](user-guide.md) and [source guide](guides/download-workflow.md) |
| Captured source integrity, backup and recovery | [Local evidence methods](methods.md) |
| Portable captured bundles and explicit schema conversion | [Application contract](applications.md) |
| Source-aware retrieval and original spans | [Shared methods](shared-methods.md) and [text search](text-search.md) |
| Statistics, proximity, composition and reference hierarchy layout | [Shared contracts](shared-methods.md), [composition](methods/composition.md) |
| Authored-decision custody and deterministic blank review workloads | [Review planning](methods/review-planning.md) |
| Optional NLP, vision and cross-modal work analysis | [API owners](api-reference.md#analysis-and-visualization) |
| Static/interactive figures and dashboards | [Visualization package](../blake/viz/README.md) and [figure brief](visualization-publication-brief.md) |
| Export formats and optional HTTP serving | [API reference](api-reference.md#export) |
| Streamlit and terminal exploration | [User guide](user-guide.md) and [terminal guide](guides/interactive-orchestrator.md) |
| Project-specific manuscript projection and native publication | [Manuscript guide](manuscript/README.md) |

Portable methods use the small default installation. The corpus pipeline needs
`full`; GUI/API add their own surface extras. Active `download_all`,
`analyze_work`, `analyze_all` and `clear_cache` are awaited instance methods of
`BlakeCorpus`. The [API reference](api-reference.md) supplies actual signatures
and source links; this map introduces no second orchestrator or compatibility
engine.

Software version, captured corpus, saved analyses, paper edition and deposited
assets are distinct identities. [publication.json](../publication.json) identifies
the retained paper and Zenodo deposit. Later code or documentation changes do not
retroactively rerun its analyses, inspect its entire source/image inventory or
publish a new manuscript. Applications retain their own domain claims.

The repository supplies local functionality and scoped evidence, without an
unqualified production/security/performance or scientific-completeness claim.
Future source expansion, rights policy, hosted automation and scholarly
acceptance remain in the [scoped backlog](../TODO.md).
