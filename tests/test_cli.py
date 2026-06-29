"""
Tests for Blake CLI module.
"""

import pytest
import json
from click.testing import CliRunner
from blake.cli import main as cli


class TestBlakeCLI:
    """Tests for Blake CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """CLI --help works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Blake" in result.output or "Usage" in result.output

    def test_cli_version(self, runner):
        """CLI --version works."""
        result = runner.invoke(cli, ["--version"])
        # May return 0 or show version info
        assert result.exit_code == 0 or "version" in result.output.lower()

    def test_download_help(self, runner):
        """Download command --help works."""
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0

    def test_analyze_help(self, runner):
        """Analyze command --help works."""
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0

    def test_export_help(self, runner):
        """Export command --help works."""
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0

    def test_public_release_preflight_help(self, runner):
        result = runner.invoke(cli, ["corpus", "public-release-preflight", "--help"])
        assert result.exit_code == 0

    def test_public_release_package_help(self, runner):
        result = runner.invoke(cli, ["corpus", "public-release-package", "--help"])
        assert result.exit_code == 0

    def test_corpus_help_uses_source_governed_release_language(self, runner):
        for args, required in [
            (
                ["corpus", "--help"],
                ["source-governed", "generated artifacts"],
            ),
            (
                ["corpus", "run", "--help"],
                ["Local Blake Archive image evidence depth", "not redistribution permission"],
            ),
            (
                ["corpus", "acquire-evidence", "--help"],
                ["validated fallback text", "manual source leads remain review-only"],
            ),
            (
                ["corpus", "private-release-preflight", "--help"],
                ["no publish", "redistribution action"],
            ),
            (
                ["corpus", "public-release-package", "--help"],
                ["Stage", "does not publish or deposit"],
            ),
        ]:
            result = runner.invoke(cli, args)
            assert result.exit_code == 0
            output = " ".join(result.output.split())
            for phrase in required:
                assert phrase in output

    def test_explore_help(self, runner):
        """Explore command --help works."""
        result = runner.invoke(cli, ["explore", "--help"])
        assert result.exit_code == 0

    def test_stats_help(self, runner):
        """Stats command --help works."""
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0

    def test_legacy_shortcuts_point_to_corpus_workflow(self, runner):
        for command in ["download", "analyze", "export"]:
            result = runner.invoke(cli, [command, "--help"])
            assert result.exit_code == 0
            assert "Compatibility" in result.output
        assert "blake corpus run" in runner.invoke(cli, ["download", "--help"]).output

    def test_corpus_run_quick(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "run",
                "--quick",
                "--skip-analysis",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "out" / "pipeline_summary.json").exists()
        assert (tmp_path / "out" / "corpus_manifest.json").exists()
        assert (tmp_path / "out" / "visualizations" / "corpus_workbench.html").exists()
        assert (
            tmp_path / "out" / "visualizations" / "dataset_statistics.json"
        ).exists()

    def test_corpus_run_accepts_archive_all_image_flags(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "run",
                "--quick",
                "--skip-analysis",
                "--image-mode",
                "archive-all",
                "--archive-scope",
                "archive-inventory",
                "--image-dpi",
                "300",
                "--max-images-per-work",
                "none",
            ],
        )
        assert result.exit_code == 0
        manifest = json.loads((tmp_path / "out" / "corpus_manifest.json").read_text())
        assert manifest["fixture_mode"] is True

    def test_corpus_run_help_defaults_to_archive_all_release_profile(self, runner):
        result = runner.invoke(cli, ["corpus", "run", "--help"])

        assert result.exit_code == 0
        output = " ".join(result.output.split())
        assert "--image-mode [representative|archive-all]" in output
        assert "[default:" in output
        assert "archive-all]" in output
        assert "[default: archive-inventory]" in output
        assert "[default: 300]" in output
        assert "[default: none]" in output

    def test_corpus_audit_sources_accepts_archive_scope(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "audit-sources",
                "--no-live",
                "--archive-scope",
                "archive-inventory",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "out" / "data" / "source_audit.json").exists()

    def test_corpus_audit_sources_reports_provider_reason_code(self, runner, monkeypatch):
        async def fake_audit_sources(self, include_live, limit):
            return {
                "path": "analysis_output/data/source_audit.json",
                "matched_target_count": 0,
                "target_total": 1,
                "missing_evidence_summary": {"candidate_count": 0},
                "provider_discovery": {
                    "providers": [
                        {
                            "provider": "internet_archive",
                            "status": "error",
                            "reason_code": "timeout",
                            "error": "timeout",
                        }
                    ]
                },
                "live": {},
            }

        monkeypatch.setattr(
            "blake.cli.BlakeCorpus.audit_sources",
            fake_audit_sources,
        )

        result = runner.invoke(cli, ["corpus", "audit-sources", "--no-live"])

        assert result.exit_code == 0
        assert "[timeout]" in result.output

    def test_corpus_audit_sources_prints_provider_warnings(
        self, runner, tmp_path, monkeypatch
    ):
        async def fake_audit_sources(self, include_live=True, limit=12):
            return {
                "path": str(tmp_path / "out" / "data" / "source_audit.json"),
                "matched_target_count": 1,
                "target_total": 2,
                "missing_evidence_summary": {"candidate_count": 0},
                "provider_discovery": {
                    "providers": [
                        {
                            "provider": "Internet Archive",
                            "source_type": "internet_archive",
                            "status": "error",
                            "record_count": 0,
                            "error": "simulated outage",
                        }
                    ],
                    "failure_count": 1,
                },
                "live": {
                    "archive_metadata_enrichment": {
                        "status": "degraded",
                        "attempted": 2,
                        "succeeded": 0,
                        "skipped_after_budget": 4,
                    }
                },
            }

        monkeypatch.setattr("blake.cli.BlakeCorpus.audit_sources", fake_audit_sources)

        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "audit-sources",
            ],
        )

        assert result.exit_code == 0
        assert "Provider warnings: 1" in result.output
        assert "Internet Archive: error [error] (simulated outage)" in result.output
        assert "Archive metadata enrichment: degraded" in result.output

    def test_corpus_status_coverage(self, runner, tmp_path):
        run_result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "run",
                "--quick",
                "--skip-analysis",
            ],
        )
        assert run_result.exit_code == 0

        status_result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "status",
                "--coverage",
            ],
        )
        assert status_result.exit_code == 0
        assert '"coverage_status": "partial"' in status_result.output
        assert '"target_records"' in status_result.output

    def test_corpus_visualize_command(self, runner, tmp_path):
        run_result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "run",
                "--quick",
                "--skip-analysis",
                "--skip-viz",
            ],
        )
        assert run_result.exit_code == 0

        viz_result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "visualize",
                "--profile",
                "core",
            ],
        )
        assert viz_result.exit_code == 0
        assert (
            tmp_path / "out" / "visualizations" / "target_coverage_matrix.json"
        ).exists()
        assert (
            tmp_path / "out" / "visualizations" / "dataset_statistics.json"
        ).exists()

    def test_corpus_audit_sources_no_live(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "audit-sources",
                "--no-live",
            ],
        )
        assert result.exit_code == 0
        audit_path = tmp_path / "out" / "data" / "source_audit.json"
        assert audit_path.exists()
        payload = json.loads(audit_path.read_text())
        assert payload["target_total"] > 38
        assert payload["live"]["enabled"] is False

    def test_corpus_acquire_evidence_dry_run_skips_bounded_rows(self, runner, tmp_path):
        audit_path = tmp_path / "source_audit.json"
        audit_path.write_text(
            json.dumps(
                {
                    "target_profile": "canonical",
                    "missing_evidence": [
                        {
                            "target_id": "songsie",
                            "title": "Songs of Innocence and of Experience",
                            "evidence_type": "text",
                            "candidate_source": "Project Gutenberg author page",
                            "candidate_url": "https://www.gutenberg.org/ebooks/author/915",
                            "ok": True,
                            "match_confidence": 0.2,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "corpus",
                "acquire-evidence",
                "--from-audit",
                str(audit_path),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "0 accepted" in result.output
        assert "1 skipped" in result.output
        assert "Review:" in result.output
        review_path = audit_path.parent / "evidence_acquisition_review.json"
        assert review_path.exists()
        review = json.loads(review_path.read_text())
        assert review["target_reviews"][0]["recommended_action"]

    def test_private_release_preflight_command_never_publishes(self, runner, tmp_path):
        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "private-release-preflight",
            ],
        )

        assert result.exit_code == 0
        assert "Publish action: none" in result.output
        preflight_path = tmp_path / "out" / "reports" / "private_release_preflight.json"
        rights_path = tmp_path / "out" / "reports" / "rights_gate_report.json"
        assert preflight_path.exists()
        assert rights_path.exists()
        preflight = json.loads(preflight_path.read_text())
        rights = json.loads(rights_path.read_text())
        assert preflight["publish_action"] == "none"
        assert preflight["no_public_release_performed"] is True
        assert "blake_data/**" in preflight["public_exclusions"]
        assert "output/figures/*mosaic*.png" in preflight["public_exclusions"]
        assert rights["status"] == "blocked_for_public_redistribution"

    def test_public_release_preflight_command_reports_status(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "blake.cli.write_public_release_preflight",
            lambda **kwargs: {
                "path": str(tmp_path / "out" / "reports" / "public_release_preflight.json"),
                "status": "ready",
                "release_dir": str(tmp_path / "out" / "releases" / "public_release"),
                "included_asset_count": 3,
                "excluded_asset_count": 1,
                "corroborated_fallback_target_count": 1,
                "blocked_reasons": [],
            },
        )

        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "public-release-preflight",
            ],
        )

        assert result.exit_code == 0
        assert "Public release preflight:" in result.output
        assert "Status: ready" in result.output
        assert "Included assets: 3" in result.output

    def test_public_release_package_command_reports_artifacts(
        self, runner, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            "blake.cli.write_public_release_package",
            lambda **kwargs: {
                "status": "ready",
                "release_dir": str(tmp_path / "out" / "releases" / "public_release"),
                "archive_path": str(
                    tmp_path / "out" / "releases" / "public_release" / "public_release_bundle.zip"
                ),
                "manifest_path": str(
                    tmp_path / "out" / "releases" / "public_release" / "public_release_manifest.json"
                ),
                "github_release_notes_path": str(
                    tmp_path / "out" / "releases" / "public_release" / "github_release.md"
                ),
                "zenodo_metadata_path": str(
                    tmp_path / "out" / "releases" / "public_release" / "zenodo_metadata.json"
                ),
                "checksums_path": str(
                    tmp_path / "out" / "releases" / "public_release" / "checksums.sha256"
                ),
                "corroborated_fallback_target_count": 1,
                "blocked_reasons": [],
            },
        )

        result = runner.invoke(
            cli,
            [
                "--data-dir",
                str(tmp_path / "data"),
                "--output-dir",
                str(tmp_path / "out"),
                "corpus",
                "public-release-package",
            ],
        )

        assert result.exit_code == 0
        assert "Public release package:" in result.output
        assert "Bundle archive:" in result.output
        assert "Checksums:" in result.output
