"""
Tests for Blake data models.
"""

import pytest
from datetime import datetime
from pathlib import Path

from blake.models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, LicenseType


class TestBlakeMetadata:
    """Test BlakeMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating BlakeMetadata."""
        metadata = BlakeMetadata(
            id="test_work_1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE,
            license_type=LicenseType.PUBLIC_DOMAIN
        )
        
        assert metadata.id == "test_work_1"
        assert metadata.title == "Test Work"
        assert metadata.work_type == WorkType.POEM
        assert metadata.source == SourceType.BLAKE_ARCHIVE
        assert metadata.license_type == LicenseType.PUBLIC_DOMAIN
        assert metadata.processed == False
        assert isinstance(metadata.created_at, datetime)
    
    def test_metadata_validation(self):
        """Test metadata validation."""
        # Test required fields
        with pytest.raises(ValueError):
            BlakeMetadata()
        
        # Test valid metadata
        metadata = BlakeMetadata(
            id="test",
            title="Test",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        assert metadata.id == "test"

    def test_referenced_license_values_exist(self):
        assert LicenseType.CC_BY_NC_ND.value == "cc_by_nc_nd"
        assert LicenseType.ACADEMIC_USE.value == "academic_use"


class TestBlakeImage:
    """Test BlakeImage model."""
    
    def test_image_creation(self):
        """Test creating BlakeImage."""
        image = BlakeImage(
            id="img_1",
            metadata_id="work_1",
            title="Test Image",
            file_path=Path("/test/image.jpg")
        )
        
        assert image.id == "img_1"
        assert image.metadata_id == "work_1"
        assert image.title == "Test Image"
        assert image.file_path == Path("/test/image.jpg")
    
    def test_image_validation(self):
        """Test image validation."""
        # Test required fields
        with pytest.raises(ValueError):
            BlakeImage()


class TestBlakeWork:
    """Test BlakeWork model."""
    
    def test_work_creation(self):
        """Test creating BlakeWork."""
        metadata = BlakeMetadata(
            id="work_1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        
        work = BlakeWork(
            id="work_1",
            metadata=metadata,
            text_content="This is a test poem."
        )
        
        assert work.id == "work_1"
        assert work.metadata.title == "Test Work"
        assert work.text_content == "This is a test poem."
        assert work.fully_processed == False
        assert len(work.images) == 0
    
    def test_work_with_images(self):
        """Test BlakeWork with images."""
        metadata = BlakeMetadata(
            id="work_1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        
        image = BlakeImage(
            id="img_1",
            metadata_id="work_1",
            title="Test Image",
            file_path=Path("/test/image.jpg")
        )
        
        work = BlakeWork(
            id="work_1",
            metadata=metadata,
            images=[image]
        )
        
        assert len(work.images) == 1
        assert work.primary_image == image  # Should be set automatically
    
    def test_work_validation(self):
        """Test work validation."""
        # Test required fields
        with pytest.raises(ValueError):
            BlakeWork()
        
        # Test valid work
        metadata = BlakeMetadata(
            id="work_1",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.BLAKE_ARCHIVE
        )
        
        work = BlakeWork(id="work_1", metadata=metadata)
        assert work.id == "work_1"
