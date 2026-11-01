# Installed Git provenance

`blake.methods.installed.verify_installed_git(package, expected_commit,
distribution_name="")` checks a caller-selected normal Git installation before
an application admits a new producer stage. `expected_commit` is a full,
lowercase Git SHA, held by the caller independently of the installed metadata.
This method is available in the dependency-light Python 3.9+ profile.

```python
from blake.methods.installed import verify_installed_git

# selected_commit comes from the application's reviewed Git dependency pin.
receipt = verify_installed_git("blake", selected_commit)
```

The method requires one normal distribution-name metadata directory, independently of paths claimed in RECORD; ambiguous directories refuse. It checks the actual distribution name/version and PEP 610
`direct_url.json`, requiring Git metadata and the selected commit. It verifies
every recorded package member against its SHA-256 and size in `RECORD`, refuses
missing, duplicate, escaping, symbolic or unrecorded package files, and compares
all currently imported modules and package search paths with that same package
root. Cache directories are excluded from source membership; an unhashed
recorded package member is refused. Source-only normal uv installations satisfy
this contract; editable, archive-only and bytecode-only qualification require
their own source-bound workflows.

The immutable `InstalledGitPackage` receipt binds the distribution, selected
commit, package root, all verified file hashes/sizes, imported module names and
hashes of the physical origin, METADATA and RECORD bytes, preserving line endings. The verifier repeats package inventory and metadata checks after the selected package's import, refusing initializer side effects that would leave a stale receipt. Refusals use `EvidenceError`
with `installed_*` codes. The verifier writes no files, acquires no corpus data
and starts no optional analysis engine of its own. Importing the caller-selected package can execute that package's initializer; this is not a sandbox.

Applications own allowed commits, producer admission, repeated checks around
staging, receipt custody and native transport. A template worker running in a
separate environment must describe a host SDK receipt as host evidence; it must
not claim to have imported that SDK itself. Preserve historical profiles and
receipts without silently retagging them when adopting a new dependency pin.

This is local consistency evidence at one observation. PEP 610 and RECORD are
mutable local metadata, not authenticated attestations of a remote Git tree or
protection against a malicious same-user writer. Separately compare installed
package bytes with the reviewed source or wheel, preserve the environment's
external runtime identity, and revalidate bindings before delivery. No literary,
native-output, hosted-CI, rights or release acceptance follows from this check.

The filesystem provider is bound to CPython’s selected `PathDistribution._path` before its metadata accessors run; a guessed directory is never substituted. This is an explicit standard-library implementation boundary. Nonstandard providers, missing paths, non-filesystem metadata and a selected directory inconsistent with the supported normal layout refuse. Python 3.9 and 3.11 normal installations are qualified separately. See [CPython’s implementation](https://github.com/python/cpython/blob/v3.11.17/Lib/importlib/metadata/__init__.py).
