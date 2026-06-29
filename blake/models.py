"""
Data models for Blake works, images, and metadata.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from enum import Enum
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict, model_validator


class WorkType(str, Enum):
    """Types of Blake works."""
    POEM = "poem"
    PROSE = "prose"
    LETTER = "letter"
    MANUSCRIPT = "manuscript"
    PLATE = "plate"
    DRAWING = "drawing"
    PAINTING = "painting"
    ENGRAVING = "engraving"
    PROPHECY = "prophecy"
    ILLUMINATED_BOOK = "illuminated_book"
    ILLUSTRATION = "illustration"
    ESSAY = "essay"


class SourceType(str, Enum):
    """Types of data sources."""
    BLAKE_ARCHIVE = "blake_archive"
    PROJECT_GUTENBERG = "project_gutenberg"
    INTERNET_ARCHIVE = "internet_archive"
    BRITISH_MUSEUM = "british_museum"
    TATE = "tate"
    WIKIMEDIA = "wikimedia"
    HATHITRUST = "hathitrust"
    GOOGLE_ARTS = "google_arts"


class LicenseType(str, Enum):
    """Types of licenses."""
    PUBLIC_DOMAIN = "public_domain"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    CC_BY_NC = "cc_by_nc"
    CC_BY_NC_SA = "cc_by_nc_sa"
    CC_BY_NC_ND = "cc_by_nc_nd"
    ACADEMIC_USE = "academic_use"
    COPYRIGHT = "copyright"
    UNKNOWN = "unknown"


class BlakeMetadata(BaseModel):
    """Metadata for a Blake work."""
    
    # Basic identification
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Title of the work")
    author: Optional[str] = Field(None, description="Author of the work")
    work_type: WorkType = Field(..., description="Type of work")
    
    # Temporal information
    creation_date: Optional[datetime] = Field(None, description="Date of creation")
    publication_date: Optional[datetime] = Field(None, description="Date of publication")
    period: Optional[str] = Field(None, description="Artistic period")
    
    # Content information
    description: Optional[str] = Field(None, description="Description of the work")
    medium: Optional[str] = Field(None, description="Medium used")
    dimensions: Optional[str] = Field(None, description="Physical dimensions")
    location: Optional[str] = Field(None, description="Current location")
    
    # Source information
    source: SourceType = Field(..., description="Primary source")
    source_url: Optional[str] = Field(None, description="URL of the source")
    source_id: Optional[str] = Field(None, description="ID in source system")
    api_source: Optional[str] = Field(None, description="API source used for acquisition")
    
    # Licensing and rights
    license_type: LicenseType = Field(LicenseType.UNKNOWN, description="License type")
    attribution: Optional[str] = Field(None, description="Required attribution")
    usage_terms: Optional[str] = Field(None, description="Usage terms")
    
    # Relationships
    related_works: List[str] = Field(default_factory=list, description="Related work IDs")
    parent_work: Optional[str] = Field(None, description="Parent work ID")
    series: Optional[str] = Field(None, description="Series or collection name")
    
    # Tags and classification
    tags: List[str] = Field(default_factory=list, description="Tags")
    themes: List[str] = Field(default_factory=list, description="Thematic tags")
    subjects: List[str] = Field(default_factory=list, description="Subject tags")
    languages: List[str] = Field(default_factory=list, description="Languages")
    
    # Technical metadata
    file_path: Optional[Path] = Field(None, description="Path to file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    checksum: Optional[str] = Field(None, description="File checksum")
    
    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Metadata creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    processed: bool = Field(False, description="Whether work has been processed")
    
    # Analysis results
    analysis_results: Dict[str, Any] = Field(default_factory=dict, description="Analysis results")
    
    model_config = ConfigDict(use_enum_values=True)

    @field_serializer('creation_date', 'publication_date', 'created_at', 'updated_at')
    @classmethod
    def serialize_datetime(cls, v: datetime) -> str | None:
        return v.isoformat() if v else None

    @field_serializer('file_path')
    @classmethod
    def serialize_path(cls, v: Path) -> str | None:
        return str(v) if v else None


class BlakeImage(BaseModel):
    """Represents a Blake image or illustration."""
    
    id: str = Field(..., description="Unique identifier")
    metadata_id: str = Field(..., description="Associated metadata ID")
    
    # Image information
    title: str = Field(..., description="Image title")
    description: Optional[str] = Field(None, description="Image description")
    alt_text: Optional[str] = Field(None, description="Alternative text")
    
    # File information
    file_path: Path = Field(..., description="Path to image file")
    thumbnail_path: Optional[Path] = Field(None, description="Path to thumbnail")
    original_url: Optional[str] = Field(None, description="Original source URL")
    
    # Technical specifications
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    dpi: Optional[float] = Field(None, description="Dots per inch")
    format: Optional[str] = Field(None, description="Image format")
    color_space: Optional[str] = Field(None, description="Color space")
    
    # Visual analysis
    dominant_colors: List[str] = Field(default_factory=list, description="Dominant colors")
    brightness: Optional[float] = Field(None, description="Average brightness")
    contrast: Optional[float] = Field(None, description="Contrast ratio")
    composition: Optional[Dict[str, Any]] = Field(None, description="Composition analysis")
    
    # OCR and text extraction
    extracted_text: Optional[str] = Field(None, description="Extracted text via OCR")
    text_regions: List[Dict[str, Any]] = Field(default_factory=list, description="Text regions")
    
    # Relationships
    related_text_id: Optional[str] = Field(None, description="Related text work ID")
    plate_number: Optional[int] = Field(None, description="Plate number if applicable")
    
    @field_serializer('file_path', 'thumbnail_path')
    @classmethod
    def serialize_path(cls, v: Path) -> str | None:
        return str(v) if v else None


class BlakeWork(BaseModel):
    """Represents a complete Blake work with text and associated images."""
    
    id: str = Field(..., description="Unique identifier")
    metadata: BlakeMetadata = Field(..., description="Work metadata")
    
    # Text content
    text_content: Optional[str] = Field(None, description="Full text content")
    text_versions: List[Dict[str, Any]] = Field(default_factory=list, description="Different text versions")
    
    # Associated images
    images: List[BlakeImage] = Field(default_factory=list, description="Associated images")
    primary_image: Optional[BlakeImage] = Field(None, description="Primary illustration")
    
    # Analysis results
    text_analysis: Dict[str, Any] = Field(default_factory=dict, description="Text analysis results")
    visual_analysis: Dict[str, Any] = Field(default_factory=dict, description="Visual analysis results")
    cross_analysis: Dict[str, Any] = Field(default_factory=dict, description="Text-image cross analysis")
    ontological_analysis: Dict[str, Any] = Field(default_factory=dict, description="Ontological analysis results")
    
    # Processing status
    fully_processed: bool = Field(False, description="Whether work is fully processed")
    processing_errors: List[str] = Field(default_factory=list, description="Processing errors")
    
    @model_validator(mode='after')
    def set_primary_image(self) -> 'BlakeWork':
        """Set primary image if not specified."""
        if self.primary_image is None and self.images:
            self.primary_image = self.images[0]
        return self


class AnalysisResult(BaseModel):
    """Results from various analysis operations."""
    
    work_id: str = Field(..., description="Work ID")
    analysis_type: str = Field(..., description="Type of analysis")
    timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")
    
    # Results
    results: Dict[str, Any] = Field(..., description="Analysis results")
    confidence: Optional[float] = Field(None, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_serializer('timestamp')
    @classmethod
    def serialize_timestamp(cls, v: datetime) -> str:
        return v.isoformat()


class ExportConfig(BaseModel):
    """Configuration for data export."""
    
    format: str = Field("json", description="Export format")
    output_dir: Path = Field(..., description="Output directory")
    include_images: bool = Field(True, description="Include images in export")
    include_metadata: bool = Field(True, description="Include metadata in export")
    include_analysis: bool = Field(True, description="Include analysis results")
    compress: bool = Field(False, description="Compress output")
    filter_works: Optional[List[str]] = Field(None, description="Filter specific works")
    
    @field_serializer('output_dir')
    @classmethod
    def serialize_path(cls, v: Path) -> str:
        return str(v)


from .viz.models import DashboardComponent, InteractiveDashboard, VisualizationConfig
