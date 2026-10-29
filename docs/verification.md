# Verification scope

The current 0.4.0 source removes obsolete interface paths while retaining the
acquisition, NLP, vision, GUI and recovery capabilities. [publication.json](../publication.json)
binds the final source commit, installed artifacts, rendered PDF and deposit.
Results below are local qualification; there is no hosted test/lint/type workflow.

| Surface | Actual qualification | Result |
|---|---|---|
| Integrated source | CPython 3.11.17; locked full/dev/GUI/API installation | 1,171 tests passed; 83.34% branch-aware coverage against the 80% floor |
| Interface migration | Recovery, method contracts, installed-layout fixtures and real CLI refusals | 403 tests passed; six new controls first reproduced the obsolete-interface failures |
| Manuscript typing | Actual pinned template source supplied through MYPYPATH | Five source files pass strict mypy; 29 code errors repaired |
| Numerical preservation | Offline fixture and nonzero display controls | 149 variable values and 20 statistical payloads unchanged |
| Installed SDK | Separate normal wheel environment, outside the source checkout | Exact wheel digest, test count and coverage recorded in the publication manifest |

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
