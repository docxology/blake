"""Native, read-only controls for recorded recovery and scoped source search."""

from pathlib import Path
import sqlite3

import streamlit as st

from blake.evidence import read_evidence_summary, read_projection_summary
from blake.text_search.models import Query, SearchMode
from blake.text_search.recovered import open_recovered_search
from blake.text_search.recovered_cli import query_payload
from blake.version import version_info


def render_evidence_panel(data_dir: Path) -> None:
    """Show recorded counts; validate full index bytes only on explicit search."""
    st.header("Local evidence")
    identity = version_info()
    st.caption(
        f"Blake {identity['package_version']} · Methods {identity['methods_profile']} · "
        f"Dashboard schema {identity['dashboard_schema_version']}"
    )
    try:
        evidence = read_evidence_summary(data_dir)
    except FileNotFoundError:
        st.info("No captured recovery manifest is available in this data directory.")
        st.code(
            "uv run --python 3.11 python -m blake.recovery recover --help",
            language="bash",
        )
        return
    except (OSError, ValueError) as exc:
        st.error(f"Recovery manifest cannot be read: {exc}")
        return
    st.subheader("Recorded snapshot")
    st.caption(
        "Counts below come from the saved manifest. This view does not reverify all corpus bytes."
    )
    st.write(
        f"Retained files: {evidence.file_count:,} · Captured bytes: {evidence.captured_bytes:,}"
    )
    st.write(
        f"Archive documents: {evidence.archive_documents:,} · Reading passages: {evidence.reading_passages:,}"
    )
    st.write(f"Saved images: {evidence.saved_images:,} / {evidence.expected_images:,}")
    if evidence.unresolved_images:
        st.warning(
            f"{evidence.unresolved_images:,} unresolved image references; "
            f"{evidence.unattempted_images:,} were not attempted."
        )
    if evidence.lower_resolution_images:
        st.write(
            f"Lower-resolution images recorded: {evidence.lower_resolution_images:,}"
        )
    st.write(
        f"Source recovery: {evidence.source_status} · Oeuvre coverage: {evidence.oeuvre_coverage}"
    )
    st.caption(f"Capture verification recorded at: {evidence.captured_at}")
    with st.expander("Snapshot identity and recovery commands"):
        st.text("Manifest SHA-256: " + evidence.manifest_sha256)
        st.text("Archive commit: " + evidence.archive_commit)
        st.json({"reading_roles": evidence.roles})
        st.code("uv run --python 3.11 python -m blake.recovery verify", language="bash")
    try:
        projection = read_projection_summary(data_dir, evidence)
    except (OSError, ValueError) as exc:
        st.error(f"Projection receipt cannot be used: {exc}")
        return
    if projection.status == "missing":
        st.info("No recovered-search index is recorded for the current producer.")
        st.code("uv run --python 3.11 blake-text build-recovered", language="bash")
        return
    st.subheader("Search recovered sources")
    st.caption(
        f"Projection receipt reports {projection.passages:,} records. "
        "Receipt inspection is not an index checksum check; search validates bytes and membership."
    )
    with st.form("recovered-source-search"):
        text = st.text_input("Occurrence query", max_chars=1000)
        scope = st.selectbox("Evidence scope", ["primary", "exploratory"])
        mode = st.selectbox("Occurrence mode", [mode.value for mode in SearchMode])
        plane = st.selectbox("Source plane", ["all", "reading", "erdman", "xml"])
        st.caption(
            "Primary scope uses William Blake's primary reading text. "
            "Exploratory scope can include other authors, editorial text, unverified readings and raw XML. "
            "Literal mode is case-sensitive. "
            "Concept mode is curated term navigation, not a semantic inference."
        )
        submitted = st.form_submit_button("Search recovered corpus")
    if not submitted:
        return
    if not text.strip():
        st.error("Enter an occurrence query.")
        return
    if scope == "primary" and plane not in ("all", "reading"):
        st.error(
            "Primary scope requires the reading plane; choose exploratory scope for Erdman or XML."
        )
        return
    try:
        with st.spinner("Validating and searching the recorded index"):
            snapshot = open_recovered_search(data_dir)
            result = snapshot.index.search(
                Query(
                    text=text,
                    mode=mode,
                    scope=scope,
                    limit=20,
                    author_id="william-blake-1757-1827" if scope == "primary" else None,
                    source_plane="reading"
                    if scope == "primary"
                    else (None if plane == "all" else plane),
                )
            )
            payload = query_payload(result, private=True)
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"Recovered search refused the query: {exc}")
        return
    st.metric("Occurrences in selected scope", result.total_occurrences)
    st.caption(
        f"Blake-primary occurrences: {result.blake_primary_occurrences:,}. {result.interpretation}"
    )
    st.json(
        {"by_role": result.occurrences_by_role, "by_plane": result.occurrences_by_plane}
    )
    if not result.hits:
        st.info(
            "No matches in the selected indexed scope; this is not whole-oeuvre absence."
        )
    for position, hit in enumerate(payload["hits"], 1):
        passage = hit["passage"]
        with st.expander(f"Source match {position}"):
            st.text(passage["title"])
            st.text(f"{passage['work_id']} · {passage['locator']}")
            st.caption(
                f"{passage['text_role']} · {passage['source_plane']} · {passage['author_id']}"
            )
            st.text("Edition: " + passage["edition"])
            st.text("Source: " + passage["source_url"])
            st.text("Rights: " + passage["rights"])
            for match in hit["matches"]:
                st.text(match["context"])
    st.caption(payload["display"])
