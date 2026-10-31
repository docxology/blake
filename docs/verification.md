# Verification scope

The current 0.5.0 source adds deterministic review planning and blank batch
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

## Reproduce the source and authoring gates

Use Python 3.11 for the qualified optional full stack:

```bash
uv sync --locked --python 3.11 --extra full --extra dev --extra gui
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
