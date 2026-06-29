"""
Tests for Blake export module.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from blake.models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, ExportConfig
from blake.export import BlakeAPI, BlakeExporter, CSVExporter, JSONExporter


class TestBlakeExporter:
    """Tests for BlakeExporter class."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for exports."""
        return tmp_path
    
    @pytest.fixture
    def exporter(self, temp_dir):
        """Create BlakeExporter instance."""
        return BlakeExporter(temp_dir)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata."""
        return BlakeMetadata(
            id="test_work_1",
            title="Songs of Innocence",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            description="A collection of poems",
            source_url="https://blakearchive.org/work/test",
            source_id="test",
            checksum="abc123",
            analysis_results={"source_authority_tier": "archive_primary"},
        )
    
    @pytest.fixture
    def sample_work(self, sample_metadata):
        """Create sample BlakeWork."""
        return BlakeWork(
            id="test_work_1",
            metadata=sample_metadata,
            text_content="Piping down the valleys wild...",
        )
    
    def test_exporter_initialization(self, exporter, temp_dir):
        """Exporter initializes with correct data directory."""
        assert exporter.data_dir == temp_dir

    def test_exporter_supports_public_formats(self, exporter):
        assert set(['json', 'csv', 'pdf', 'html', 'markdown', 'md', 'parquet']).issubset(
            set(exporter.get_supported_formats())
        )
    
    @pytest.mark.asyncio
    async def test_export_works_json(self, exporter, sample_work, temp_dir):
        """Export works to JSON format."""
        config = ExportConfig(
            format="json",
            output_dir=temp_dir / "exports",
            include_images=False,
            include_analysis=True
        )
        
        result = await exporter.export_works([sample_work], config)
        assert result.exists()
    
    @pytest.mark.asyncio
    async def test_export_with_no_works(self, exporter, temp_dir):
        """Export with empty list handles gracefully."""
        config = ExportConfig(
            format="json",
            output_dir=temp_dir / "exports"
        )
        
        result = await exporter.export_works([], config)
        assert result.exists()


class TestJSONExporter:
    """Tests for JSONExporter class."""
    
    @pytest.fixture
    def json_exporter(self):
        """Create JSONExporter instance."""
        return JSONExporter()
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for export."""
        return {
            "works": [
                {"id": "work1", "title": "Songs of Innocence"},
                {"id": "work2", "title": "Songs of Experience"}
            ]
        }
    
    def test_json_exporter_initialization(self, json_exporter):
        """JSONExporter initializes correctly."""
        assert json_exporter is not None

    def test_json_exporter_includes_provenance(self, json_exporter):
        metadata = BlakeMetadata(
            id="work",
            title="Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            source_url="https://blakearchive.org/work/work",
            source_id="work",
            checksum="checksum",
            analysis_results={"source_authority_tier": "archive_primary"},
        )
        work = BlakeWork(id="work", metadata=metadata, text_content="text")

        payload = json_exporter._work_to_dict(
            work,
            ExportConfig(output_dir=Path("."), include_metadata=True),
        )

        assert payload["provenance"]["source_url"] == metadata.source_url
        assert payload["provenance"]["source_authority_tier"] == "archive_primary"
        assert (
            payload["provenance"]["rights_disposition"]
            == "exclude_raw_source_materials_from_public_bundle"
        )
        assert payload["provenance"]["checksum"] == "checksum"


class TestCSVExporter:
    """Tests for CSVExporter class."""
    
    @pytest.fixture
    def csv_exporter(self):
        """Create CSVExporter instance."""
        return CSVExporter()
    
    def test_csv_exporter_initialization(self, csv_exporter):
        """CSVExporter initializes correctly."""
        assert csv_exporter is not None

    @pytest.mark.asyncio
    async def test_csv_exporter_includes_provenance_columns(self, csv_exporter, tmp_path):
        metadata = BlakeMetadata(
            id="work",
            title="Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG,
            source_url="https://www.gutenberg.org/ebooks/1",
            analysis_results={"source_authority_tier": "fallback_text_validated"},
        )
        work = BlakeWork(id="work", metadata=metadata, text_content="text")
        output_path = await csv_exporter.export_works(
            [work],
            tmp_path,
            ExportConfig(output_dir=tmp_path),
        )

        text = output_path.read_text(encoding="utf-8")

        assert "source_authority_tier" in text
        assert "rights_disposition" in text
        assert "fallback_text_validated" in text


class TestBlakeAPI:
    """Tests for BlakeAPI class."""
    
    @pytest.fixture
    def api(self, tmp_path):
        """Create BlakeAPI instance."""
        from blake import BlakeCorpus
        blake = BlakeCorpus(tmp_path)
        return BlakeAPI(blake)
    
    def test_api_initialization(self, api):
        """API initializes correctly."""
        assert api is not None
    
    def test_api_has_app(self, api):
        """API has FastAPI app attribute."""
        assert hasattr(api, 'app')

    def test_single_work_export_route_uses_exporter_service(self, tmp_path):
        from fastapi.testclient import TestClient
        from blake import BlakeCorpus

        blake = BlakeCorpus(tmp_path / "data", output_dir=tmp_path / "out")
        work = BlakeWork(
            id="api_work",
            metadata=BlakeMetadata(
                id="api_work",
                title="API Work",
                work_type=WorkType.POEM,
                source=SourceType.BLAKE_ARCHIVE,
            ),
            text_content="A test work",
        )
        (tmp_path / "out").mkdir(parents=True, exist_ok=True)
        (tmp_path / "out" / "corpus_manifest.json").write_text(
            json.dumps(
                {
                    "work_records": [
                        {
                            "id": "api_work",
                            "target_id": "target-api",
                            "source_authority_tier": "archive_primary",
                            "has_text": True,
                            "has_images": False,
                            "image_count": 0,
                        }
                    ],
                    "target_records": [
                        {
                            "target_id": "target-api",
                            "title": "API Target",
                            "status": "partial",
                            "notes": ["Expected image evidence is not available locally."],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        async def load_work(work_id):
            return work if work_id == "api_work" else None

        blake.get_work = load_work
        client = TestClient(BlakeAPI(blake).app)
        response = client.get("/export/api_work?format=json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_api_returns_standard_error_envelope(self, tmp_path):
        from fastapi.testclient import TestClient
        from blake import BlakeCorpus

        blake = BlakeCorpus(tmp_path / "data", output_dir=tmp_path / "out")

        async def load_work(_work_id):
            return None

        blake.get_work = load_work
        client = TestClient(BlakeAPI(blake).app)
        response = client.get("/works/missing")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "not_found"
        assert payload["error"]["message"] == "Work not found"
        assert payload["error"]["details"] == {}

    def test_api_work_payload_includes_provenance(self, tmp_path):
        from fastapi.testclient import TestClient
        from blake import BlakeCorpus

        blake = BlakeCorpus(tmp_path / "data", output_dir=tmp_path / "out")
        work = BlakeWork(
            id="api_work",
            metadata=BlakeMetadata(
                id="api_work",
                title="API Work",
                work_type=WorkType.POEM,
                source=SourceType.BLAKE_ARCHIVE,
                source_url="https://blakearchive.org/work/api_work",
                analysis_results={"source_authority_tier": "archive_primary"},
            ),
            text_content="A test work",
        )
        (tmp_path / "out").mkdir(parents=True, exist_ok=True)
        (tmp_path / "out" / "corpus_manifest.json").write_text(
            json.dumps(
                {
                    "work_records": [
                        {
                            "id": "api_work",
                            "target_id": "target-api",
                            "source_authority_tier": "archive_primary",
                            "has_text": True,
                            "has_images": False,
                            "image_count": 0,
                        }
                    ],
                    "target_records": [
                        {
                            "target_id": "target-api",
                            "title": "API Target",
                            "status": "partial",
                            "notes": [
                                "Expected image evidence is not available locally."
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        async def load_work(work_id):
            return work if work_id == "api_work" else None

        blake.get_work = load_work
        client = TestClient(BlakeAPI(blake).app)
        response = client.get("/works/api_work")

        assert response.status_code == 200
        provenance = response.json()["provenance"]
        assert provenance["source_authority_tier"] == "archive_primary"
        assert provenance["source_url"] == "https://blakearchive.org/work/api_work"
        manifest_context = response.json()["corpus_manifest"]
        assert manifest_context["target_id"] == "target-api"
        assert manifest_context["coverage_status"] == "partial"


def test_gui_work_details_use_evidence_and_rights_language():
    text = Path("blake/gui/gui.py").read_text(encoding="utf-8")

    for phrase in [
        "Authority Tier",
        "Coverage Status",
        "Target ID",
        "Text Evidence",
        "Image Evidence",
        "Rights Status",
        "Local Image Evidence",
    ]:
        assert phrase in text
