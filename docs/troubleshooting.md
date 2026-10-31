# Troubleshooting

Start with the failed command, interpreter identity, source/input pins, output
epoch and complete error. Keep the original files and logs. Select the profile
from [verification](verification.md); an import failure in a methods-only
environment does not diagnose the full optional stack.

## Installation and imports

| Operation | Required profile |
|---|---|
| Portable methods/studies/applications | Default dependencies |
| Recovery module commands | `recovery` |
| Corpus pipeline, NLP, vision and `blake` CLI | `full` |
| GUI | `full` plus `gui` |
| HTTP API | `full` plus `api` |
| Complete test collection | `full`, `dev`, `gui` (and declared API dependencies) |

In the managed checkout, use its pinned toolchain and external environment:

~~~sh
uv run --locked python -c 'import sys; print(sys.version); print(sys.prefix); print(sys.base_prefix)'
# Provision the complete profile only when this is the selected environment.
uv sync --locked --python 3.11 --extra full --extra dev --extra gui --extra api
~~~

Verify both prefixes, not just the `.venv` pathname. Preserve old qualified
environments; do not repair one by installing into its site-packages manually.
All task-specific TMP, caches and outputs stay on the mounted external workspace.

Python import names may differ from distribution names: BeautifulSoup is
`bs4`, Pillow is `PIL`, scikit-learn is `sklearn`, and OpenCV is `cv2`.
Diagnose the selected environment with real imports and dependency metadata.
Optional model/data availability is a separate check; installation success
does not prove that a model was run or that an offline resource is present.

## Async API and cache behavior

Keep one explicit corpus instance in the async context. Methods such as
`download_all`, `search_works`, `analyze_work` and `clear_cache` must be awaited.

~~~python
import asyncio
from pathlib import Path
from blake import BlakeCorpus

async def main():
    corpus = BlakeCorpus(Path("blake_data"), output_dir=Path("analysis_output"))
    print(await corpus.get_statistics())
    await corpus.clear_cache()

asyncio.run(main())
~~~

`clear_cache()` clears in-memory work objects. It does not delete stored corpus,
images, metadata or retained analyses. See the [actual API](api-reference.md).
If analyzing a selected batch, await `analyze_work(work.id)` for each selected
work; `analyze_all()` always traverses the whole loaded collection.

## Data and database inspection

The active implementation stores metadata at `metadata/metadata.db` under
the configured corpus data directory. This is an implementation detail, not a
portable application API. Prefer corpus status/statistics and the
[source-bound search contracts](text-search.md).

For a specific SQLite diagnostic, select the existing exact path and open it
read-only so a typo cannot create another database:

~~~python
import sqlite3
from pathlib import Path

database = Path("blake_data/metadata/metadata.db").resolve(strict=True)
with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
    print(connection.execute("PRAGMA quick_check").fetchall())
~~~

Database readability is not source/corpus integrity. Use the appropriate
captured manifest and caller-held pin for that verification. The metadata API
does not offer `recreate_database` or `rebuild_search_index`. Discovery search
computes relevance over loaded records; the source-bound search projection has
its own explicit build/verification workflow.

## Pins, occupied destinations and failed runs

Wrong source hashes, altered spans/membership, symlinks and occupied artifact
destinations should refuse. Retain the exact error and original epoch. Choose a
new destination after accounting for the failed command; do not delete a marker,
lock or partial run to bypass the refusal. Recovery/restore needs its recorded
source, supported admission and independently held pins; see [methods](methods.md).

Before disk-space work, inspect ownership and sizes read-only and coordinate
with the active job owner. Keep generated runs, caches and temporary roots on
external storage. Broad `.tmp` deletion or recursive cleanup can destroy active
custody and retained failures; it is not a troubleshooting recipe.

## Empty results and analysis limits

Check the declared query profile, source role/plane, author, vocabulary and
denominator. A paginated display is not the total match count; a zero is scoped
to admitted inputs. Verify whether fixture mode, skipped phases, missing local
files or component errors explain an empty result. Source acquisition, model
availability and interpretation are separate outcomes.

## Manuscripts and optional interfaces

Use the [native reproduction guide](manuscript/08_reproducibility.md) for a
changed manuscript. A missing render-time figure in a clean clone is different
from a missing qualified output; check the staged input and its receipt before
editing authored paths. Inspect physical pages and browser behavior in the
proper new epoch. A valid PDF header is not output acceptance.

GUI and HTTP serving require their declared extras and admitted local data.
Check the actual registered command/options and owning source. Authentication,
hosted deployment and accessibility require their own qualification; a local
functional test supplies no blanket acceptance.

For a report, retain the minimal reproducible input, exact command/error,
selected source/runtime/dependency identities and all original failed evidence.
