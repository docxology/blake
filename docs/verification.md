# Verification scope

The 0.3.0 implementation at
[`d020f47767996a061b6f60e93a82da9386a7926c`](https://github.com/docxology/blake/commit/d020f47767996a061b6f60e93a82da9386a7926c)
was qualified on 2026-10-29. Subsequent setup-documentation corrections do not
change that implementation. These are recorded local results, not hosted test
CI or a package-index release.

| Surface | Actual qualification | Result |
|---|---|---|
| Full source workflow | CPython 3.11.17, full/development/GUI dependencies | 1,155 tests passed; 83.30% branch-aware coverage against the 80% repository floor |
| Dependency-light methods and studies | Normal wheel installed on CPython 3.9.25; isolated tests without source-package shadowing | 278 tests passed; 99.01% branch-aware coverage against the 90% methods/studies floor |
| Normal minimal installation | CPython 3.9.25 | Eight installed distributions; package code and resources verified |
| New composition arithmetic | Independent numerical oracle and invalid-input controls | Positive cases and deliberate refusals passed |

The independent software review covered exact source bytes, installed resources,
arithmetic, input refusals and reproducibility. The complete full suite above is
an owner-run regression; the reviewer independently ran a bounded selection.
These are distinct evidence scopes.

## Reproduce the full source gate

Use Python 3.11 for the qualified optional full stack:

```bash
uv sync --locked --python 3.11 --extra full --extra dev --extra gui
uv run --locked pytest tests/ -q --cov=blake --cov-branch --cov-fail-under=80
```

The suite uses local fixtures and local HTTP controls. It does not establish live
provider availability or a complete acquired corpus. The GUI extra is needed at
test collection, even when no interactive server is started.

Methods-only consumers can use `uv sync --locked` in a source checkout.
Installing only the methods dependencies does not make the legacy full-suite
fixtures or acquisition/NLP/GUI imports available. For installed-wheel checks,
build with `uv build`, install the wheel into a separate environment, and run the
dependency-light `test_methods_*.py` and `test_studies.py` modules from an isolated
copy without the legacy `tests/conftest.py`. Run from outside the source checkout
so coverage does not also discover an unexecuted second copy of the package.
Confirm that `blake.__file__` resolves inside the installed environment. The Python 3.9
qualification used pytest 8 and pytest-cov 6.

## Remaining boundaries

- Thirty existing legacy core typing diagnostics remain. A full-package typing
  pass is not claimed.
- Python 3.9 methods qualification does not qualify the optional legacy full stack
  on Python 3.9; that stack was exercised separately on Python 3.11.
- Historical producer identities and recovery/publication holds are preserved.
  Moving methods does not retroactively change an earlier analytical run.
- Browser interaction, accessibility, specialist scientific acceptance, complete
  oeuvre coverage and source redistribution rights require their own evidence.
- There is currently no GitHub test/lint/type workflow. A passing GitGuardian
  check is security evidence and does not represent a test-suite run.
