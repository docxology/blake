"""Software and interface identities, independent of captured corpus evidence."""

__version__ = "0.2.0"
METHODS_PROFILE = "local-source-evidence-v2"
DASHBOARD_SCHEMA_VERSION = 2


def version_info() -> dict[str, object]:
    """Describe software contracts without loading analysis or corpus data."""
    return {
        "package_version": __version__,
        "methods_profile": METHODS_PROFILE,
        "dashboard_schema_version": DASHBOARD_SCHEMA_VERSION,
    }
