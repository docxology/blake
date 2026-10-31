# Blake architecture

Blake combines a source-governed optional corpus pipeline with a dependency-light
portable methods layer. Applications select exact corpus/software identities
and own their research questions. [Shared contracts](shared-methods.md) and the
[application boundary](applications.md) define that integration.

## Implemented layers

| Layer | Owner and contract |
|---|---|
| Capture/recovery | [Recovery commands](../blake/recovery_commands.py) and [source clients](../blake/downloader/README.md) retain declared bytes, provenance, roles and failures. |
| Corpus orchestration | [BlakeCorpus](../blake/corpus/pipeline.py) coordinates discovery, acquisition, metadata, analysis, figures, export and reports. |
| Portable custody | [applications](../blake/applications.py) verifies bundles against caller-held pins; [studies](../blake/studies.py) retains source-bound candidates and zero cells. |
| Shared methods | [methods](../blake/methods/) owns explicit conversion, matching, statistics, proximity, composition, hierarchy, annotation custody and review planning. |
| Stored metadata | [metadata](../blake/metadata/README.md) persists work/image/analysis records and supports discovery search. Its database layout is not an application interchange API. |
| Optional analysis | [analysis](../blake/analysis/README.md) contains NLP, vision and cross-modal components with their own input/model/error scope. |
| Presentation | [viz](../blake/viz/README.md), [export](../blake/export/README.md), [GUI](../blake/gui/README.md) and terminal interfaces consume the admitted local collection. |
| Manuscript | [manuscript tools](../manuscript_tools/README.md) produce project figures/variables; the separately pinned template owns native writers and counters. |

~~~mermaid
flowchart LR
    S[Captured source bytes and provenance] --> C[Optional corpus pipeline]
    S --> B[Pinned portable bundle]
    B --> M[Shared retrieval and evidence methods]
    M --> A[Application policy and authored research]
    C --> D[Diagnostics and local interfaces]
    D --> P[Source-bound manuscript inputs]
    A --> P
    P --> T[Pinned native document framework]
~~~

The diagram describes data ownership. It does not establish that every source,
analysis, image, application or publication has been independently qualified.

## Corpus flow

`BlakeCorpus` is the single corpus orchestrator, with a configurable source
registry. [CorpusConfig and run models](../blake/corpus/models.py) specify the
requested profile and report phase outcomes. Raw/cached data normally lives in
`blake_data/`; derived run artifacts normally live in `analysis_output/`.
Callers can select different accounted paths. Use new output epochs and retain
source manifests, failures and original analytical producers.

Quick mode runs offline and may seed a labelled fixture when its declared
fixture policy permits. Live acquisition is explicit. Target coverage uses the
versioned target ledger and distinguishes present, partial, missing, duplicate
and unverified evidence. Fixture success or record availability is not complete
oeuvre, edition, copy or object coverage.

The metadata implementation uses `metadata/metadata.db` under the configured
data root. Discovery search inspects loaded metadata/text using substring
relevance. Source-bound occurrence retrieval uses the explicit methods/search
contracts, preserving original offsets and witnesses instead of inferring them
from a discovery result.

## Portable application flow

Bundles, projections, hits, authored decisions and planning batches have
different schemas and producer identities. Conversion is explicit. Regex
IGNORECASE, literal casefold and NFKC token matching retain distinct semantics.
Review planning supplies deterministic ranking, unit caps, full-pool binding and
blank queues; application policy controls eligibility and authored judgments.
No selected candidate becomes a literary mention or an independent observation
merely by entering a queue.

New output receipts bind the actual consumed source, input and method bytes.
Original corpus captures and earlier producers remain historical when software
advances. Consumer qualification checks the exact selected SDK and installed
files. [Verification](verification.md) distinguishes Python 3.9 methods from the
Python 3.11 optional stack and native/browser/scientific work.

## Resource and deployment boundary

Async interfaces support I/O; concurrency and model memory depend on the actual
component. There is no receipt-backed generic throughput or production-scale
guarantee. The utility [CircuitBreaker](../blake/utils/error_handling.py) exists;
its presence alone does not establish that every source path uses it.

GUI, terminal and HTTP entry points are local interfaces. Built-in service
authentication, load balancing, autoscaling, hosted CI/CD and rollback are not
supplied as an integrated deployment platform by this source tree. Such work
needs explicit design and its own checks. Source tests, diagnostics, rendered
output, accessibility, rights and public release have separate acceptance.

Use [configuration](configuration.md), [API reference](api-reference.md) and
[developer guidance](developer-guide.md) for the implemented interfaces rather
than treating this architecture map as an executable setup recipe.
