# Verification scope

The current 0.7.0 interval addition is qualified below, with exact structured
receipts in [the interval qualification record](interval-qualification-20261101.json).
The retained 0.5.0 source adds deterministic review planning and blank batch
custody. Active acquisition, NLP, vision, GUI and recovery capabilities remain.
The retained 0.4.0 paper/deposit keeps its exact identities in
[publication.json](../publication.json); this source update creates no new
package-index, manuscript or Zenodo release. There is no hosted test/lint/type
workflow; these are local source and installed-artifact qualifications.

| Surface | Actual qualification | Result |
|---|---|---|
| Integrated source | CPython 3.11.17; locked full/dev/GUI installation | 1,233 passed; 83.55% statement/branch coverage against the 80% floor |
| New planning modules | Synthetic ordering, exhaustive small capacity oracle, permutations, real-file corruption and semantic-forgery controls | 62 passed; 100% of statements and branches in all three modules |
| New module style/types | Declared isort, Black, flake8 and strict mypy | Three production modules pass; no whole-package strict typing claim |
| Installed SDK 3.9 | Normal wheel; CPython 3.9.25; copied methods/studies tests outside source checkout | 340 passed; 99.03% statement/branch coverage against the 90% floor |
| Installed SDK 3.11 | Same normal wheel; CPython 3.11.17; copied methods/studies tests outside source checkout | 340 passed; 99.12% statement/branch coverage against the 90% floor |
| Artifact/runtime identity | All 174 wheel package/resource files independently compared with canonical and installed bytes; both Python prefixes external | Same golden ordered selection and full-pool digest on 3.9 and 3.11; dependency checks pass |
| Metadata refusal | Actual repaired test on copied publication metadata | Unchanged records pass; falsely relabelled deposit and preferred-citation versions each fail |

These rows retain the 0.5.0 producer. The later 0.6.0 and 0.7.0 qualifications
below describe their own source and installed artifacts.

The qualified wheel SHA-256 is
`83a730492da86d1290dbc94010f17a2b7041350416ba6df20a58a7645279ca27`.
Installed SDK tests used pytest 8.4.2 and pytest-cov 6.3.0; their actual resolved
dependency versions are retained separately for each interpreter. The source
full-stack gate uses the repository lock. Passing under these environments does
not qualify every optional dependency combination.

The original 1,230-pass/one-failure full gate remains retained: it exposed a test
that equated the retained deposit with current software. Its repaired assertions
bind the paper/deposit to the publication manifest. Two independently identified
ordinary-JSON plan contradictions first failed their refusal tests, then passed
after exclusion-cardinality and selected/excluded-disjointness guards were added.
Earlier interface, authoring and native qualifications remain attached to the
0.4.0 publication; no old analysis or rendering is relabelled by this work.

## Current runtime and lock repair — 2 November 2026

Current main admits Python **3.11+** and pins **3.11.17** for reproducible
methods and optional-stack work. The peer floor change left the older
universal lock stale; its real locked check refused. The repaired
210-package lock preserves every retained third-party version and removes
only inactive older-interpreter resolutions. The unrequested-upgrade
candidate and original cache/style failures remain retained.

Fresh full/dev/GUI setup installed **189 distributions**. All **1,382**
source tests pass at **83.06%** statement/branch coverage. The rebuilt
normal wheel passes **474** SDK tests outside the source tree at
**99.25%** coverage; all **163** runtime/resource members agree with
source and installation. Dependency checks and actual Torch/spaCy model
smokes pass. The new wheel refuses installation on a real Python 3.9
environment. The interval family passes the configured Python 3.11
mypy, Black, isort and explicit 88-column flake8 checks. Four full-suite
warnings are retained; no whole-package strict typing pass is claimed.

[Current structured qualification](runtime-profile-20261102.json). The
Python 3.9 results below describe their original retained wheels, not
this new current-main packaging. Analysis/native/deposit producers and
caller-held application pins remain unchanged.

## Reproduce the source and authoring gates

Use Python 3.11.17 for the qualified optional full stack. The setup command
writes the local, intentionally ignored `.python-version`; later `uv run`
commands then select the same interpreter as the locked installation:

```bash
uv python pin 3.11.17
uv sync --locked --python 3.11.17 --extra full --extra dev --extra gui
uv run --locked pytest tests/ -q --cov=blake --cov-branch --cov-fail-under=80
```

The suite uses fixed local fixtures and local HTTP controls. It does not establish
live provider availability or a complete acquired corpus. The GUI extra is needed
at test collection even when no interactive server is started.

The authoring type gate uses the actual renderer source, independently of the
methods-only environment:

```bash
MYPYPATH="$TEMPLATE_REPO_ROOT" uv run --no-sync mypy --strict --follow-imports=silent   manuscript_tools/variables.py manuscript_tools/figures.py   manuscript_tools/method_types.py scripts/generate_manuscript_figures.py   scripts/z_generate_manuscript_variables.py
```

The template is a separate project. Without its declared source path, the same
isolated authoring check reports the missing renderer import. No local stub or
import suppression substitutes for that dependency. A whole-package strict typing
pass is not claimed; unchanged diagnostics elsewhere remain separate.

## Installed artifact checks

Build with `uv build`, install the wheel into a separate external environment,
and run dependency-light `test_methods_*.py` and `test_studies.py` copies without
the full-stack `tests/conftest.py`. Run outside the source checkout so coverage
does not discover an unexecuted second package copy. Confirm that `blake.__file__`
resolves inside the installed environment. The Python 3.9 SDK gate uses pytest 8,
pytest-cov 6 and a 90% branch-aware methods/studies floor.

The optional full stack is qualified separately on Python 3.11. Python 3.9 methods
qualification does not qualify that optional stack. Historical analysis producers,
source roles and evidence hashes remain unchanged by interface removal. Browser
interaction, accessibility, specialist scientific acceptance, complete oeuvre
coverage and redistribution rights require their own evidence.

## 0.6.0 installed provenance addition

The new installed Git verifier passes 60 real metadata/file/import controls, with 100%
statement/branch coverage across its three production modules. Strict mypy, isort/Black
and flake8 pass for the changed module family. The repaired full-stack source suite
passes 1,290 tests at 83.78% statement/branch coverage. The final packaging-only delta
includes the new method guide in the sdist; normal wheel/source/resource checks
separately qualify that closure. No dependency or qualified Python-source change
follows. The same normally installed wheel passes 400 SDK tests on each of Python 3.9.25
(99.13% statement/branch coverage) and Python 3.11.17 (99.21%), against the 90% floor.
Every one of its 162 package/resource members matches both source and installation;
observed imported Blake files resolve inside the selected external environment. A wrong
wheel pin is refused before producing identity output. These results do not replace
earlier 0.5.0 or deposited-paper receipts.

Independent review reproduced stale post-import receipts, line-ending changes in
metadata hashes, malformed RECORD parser exceptions and invalid scalar selection. Those
defects have new refusing controls. The original 1,262-pass / 3-failure run and its
unchanged-baseline reproduction remain retained. Exactly three obsolete tests that
pinned duplicated overview commands or superseded TODO phrases were retired after
independent review; no production behavior assertion was removed. Documentation remains
subject to real source/link/command checks. The final count is not the old denominator
relabeled.

Exact raw receipts are retained under
`Local/blake-sdk-scholarship-20261101T000147Z/evidence/`; source, normal-install,
independent-review and publication claims stay separate.

Subprocess instrumentation is explicit. The initial uninstrumented 32% observation and
the first Python 3.9 instrumented SDK attempt are retained. That 3.9 attempt exposed
coverage 7.10.7 subprocess tracing output that polluted strict child stdout controls;
raw outputs were neither stripped nor accepted. Both normal consumer environments use
pytest-cov 6.3.0's own subprocess support without the additional coverage subprocess
patch, retaining all methods in the denominator. Python 3.11 source controls separately
measure every new verifier statement/branch with subprocess tracing enabled.

A second independent review found that normalized-text equality still allowed a decoy metadata directory. The revised locator requires the unique normal directory for the selected distribution name and restricts metadata RECORD members to that directory. Equal-normalized CRLF/LF decoys for all three metadata files now refuse; physical-byte positives remain valid. The rejected candidates and the incorrect 177-member documentation statement remain in their sealed preimages; the actual wheel has 162 package/resource members and 167 total files.

The final locator binds the exact standard filesystem PathDistribution selected by Python through its guarded `_path` interface before inspecting metadata. It refuses a non-normal selection instead of substituting a different normal directory. Nonstandard providers, missing paths and non-filesystem metadata have real refusing controls. This explicit CPython implementation dependency is qualified on the declared Python 3.9/3.11 environments; it is not a universal provider adapter.

## 0.7.0 exact interval addition

The final Python 3.11.17 full-stack source suite passes 1,364 tests at 83.07%
statement/branch coverage against the 80% floor. Its 74 interval tests cover all
86 statements and 38 branches of the new module. Independent finite integer-set
and multiplicity oracles cover adjacency, empty support, duplicates, nesting,
fragmentation, permutations, large integers and invalid constructed/copied
models. Strict mypy, isort, Black and flake8 pass for the new module family.

The same normal wheel passes 474 methods/studies tests on each of Python 3.9.25
and 3.11.17: 99.17% and 99.25% statement/branch coverage respectively, against the
90% SDK floor. All 163 package/resource members match source and both installed
copies; observed imports remain inside the selected external environment.
Dependency compatibility checks pass. The 234-package lock preserves every
non-Blake package version from the preceding lock.

Five plausible wrong rules fail the same real contract tests on independent
ordinary source copies: strict versus closed intersection, record deduplication,
raw-length summation, lost subtraction fragments and an incorrect depth
threshold. The valid copy passes; the production module is unchanged by these
controls. The initial new-feature import failures, formatting refusals, occupied
lock-copy refusal and an incorrectly supplied wheel digest remain retained. The
last was refused before installed identity/test output; the final wheel digest
was read from the built artifact. None is relabelled as a successful attempt.
An initial documentation extractor selected zero links and was insufficient;
the corrected check traverses 95 links, executes the installed API example and
refuses an extracted missing-link control. Its earlier output remains retained.

The [structured qualification](interval-qualification-20261101.json) names exact
evidence and wheel identities. Source, normal-wheel, installed-Git consumer,
application, native, scientific and publication claims remain separate. This
addition supplies no new matching profile, reading decision or paper/deposit.

Independent review approved the Python/API and earlier normal wheel after
33,003 new oracle comparisons and 63 refusals on each interpreter. Its
nonblocking DOC-01 found the qualification JSON missing from the sdist. The
owner added that file and reproduced a second packaging discrepancy: direct
wheel builds included 15 agent-guidance files omitted by source-archive builds.
Explicit wheel exclusions align the two runtime manifests. The replacement
wheel changes only packaged `pyproject.toml` and RECORD bytes, preserves every
Python member and passes 474 tests in each fresh normal SDK environment. The
final archive/source/resource checks qualify this packaging delta separately;
the earlier independent verdict is retained on its original candidate.
