# Supplement: Bounded Missing-Evidence Search Queue {#sec:supp_missing_evidence}

The search queue translates missing or partial target evidence into reviewable candidate actions. It is intentionally conservative: a row can guide review without changing corpus status, because source ownership, title matching, attribution, checksum, and rights metadata must be verified before a candidate becomes corpus evidence.

| Target ID | Title | Evidence | Candidate source | Status | Confidence | Action |
|---|---|---|---|---:|---:|---|
{{MISSING_EVIDENCE_TABLE_ROWS}}

: Bounded missing-evidence search candidates. The table records where the next pass should look and whether the relevant endpoint was checked during this run; it does not treat fallback sources as replacements for William Blake Archive authority. {#tbl:supp_missing_evidence}

The manual-review rows include source-owned leads and scholarship controls. For example, Morgan Library page-level records for *The Pickering Manuscript* show that exact page transcriptions can be reviewed, while a single page remains insufficient for whole-work evidence. Conversely, the Blake/An Illustrated Quarterly *Four Zoas* bibliography is review context: it helps explain why *VALA, or The Four Zoas* requires manuscript-aware editorial handling, but it cannot itself satisfy text or image evidence [@morgan_pickering; @morgan_pickering_auguries; @bq_fourzoas_bibliography]. The table therefore preserves uncertainty as actionable metadata rather than forcing uncertain leads into a binary acquired/missing label.
