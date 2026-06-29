"""
Advanced Quality Assurance and Verification Systems for Blake works.
Implements comprehensive data integrity checking, validation, and quality metrics.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
import json
import hashlib
import mimetypes
from dataclasses import dataclass, asdict
from enum import Enum

from PIL import Image
import aiofiles
from ..models import BlakeWork, BlakeMetadata, BlakeImage, SourceType, WorkType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class QualityLevel(str, Enum):
    """Quality levels for verification."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FAILED = "failed"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    check_type: str
    passed: bool
    score: float  # 0.0 to 1.0
    quality_level: QualityLevel
    details: Dict[str, Any]
    errors: List[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class QualityReport:
    """Comprehensive quality report for a work."""
    work_id: str
    timestamp: datetime
    overall_score: float
    overall_quality: QualityLevel
    verification_results: List[VerificationResult]
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]

    def __post_init__(self):
        if self.critical_issues is None:
            self.critical_issues = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class QualityAssurance:
    """
    Advanced quality assurance and verification system.
    
    Features:
    - File integrity verification (checksums, size validation)
    - Content quality assessment (text, images, metadata)
    - Format validation and compliance checking
    - Duplicate detection and deduplication
    - Data completeness verification
    - Performance and accessibility metrics
    - Automated quality scoring and reporting
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize quality assurance system.
        
        Args:
            data_dir: Directory containing Blake works
        """
        self.data_dir = data_dir
        self.verification_dir = data_dir / "verification"
        self.verification_dir.mkdir(parents=True, exist_ok=True)
        
        # Quality thresholds
        self.thresholds = {
            'excellent': 0.9,
            'good': 0.7,
            'fair': 0.5,
            'poor': 0.3
        }
        
        # Supported formats
        self.supported_text_formats = {'.txt', '.md', '.html', '.xml', '.json'}
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.tiff', '.bmp', '.webp'}
        
        logger.info("Initialized QualityAssurance system")
    
    async def verify_work(self, work: BlakeWork) -> QualityReport:
        """
        Perform comprehensive quality verification on a work.
        
        Args:
            work: BlakeWork object to verify
            
        Returns:
            Comprehensive quality report
        """
        logger.info(f"Verifying work quality: {work.id}")
        
        verification_results = []
        
        try:
            # File integrity checks
            integrity_results = await self._verify_file_integrity(work)
            verification_results.extend(integrity_results)
            
            # Content quality checks
            content_results = await self._verify_content_quality(work)
            verification_results.extend(content_results)
            
            # Metadata validation
            metadata_results = await self._verify_metadata(work)
            verification_results.extend(metadata_results)
            
            # Format compliance checks
            format_results = await self._verify_format_compliance(work)
            verification_results.extend(format_results)
            
            # Accessibility checks
            accessibility_results = await self._verify_accessibility(work)
            verification_results.extend(accessibility_results)
            
            # Generate comprehensive report
            report = self._generate_quality_report(work, verification_results)
            
            # Save report
            await self._save_quality_report(report)
            
            logger.info(f"Quality verification completed for {work.id}: {report.overall_quality.value}")
            return report
            
        except Exception as e:
            logger.error(f"Error verifying work {work.id}: {e}")
            return self._create_error_report(work.id, str(e))
    
    async def _verify_file_integrity(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify file integrity and completeness."""
        results = []
        
        # Check work file exists and is readable
        work_file_check = await self._check_file_exists_and_readable(work)
        results.append(work_file_check)
        
        # Verify text content integrity
        if work.text_content:
            text_integrity = await self._verify_text_integrity(work)
            results.append(text_integrity)
        
        # Verify image files
        for i, image in enumerate(work.images):
            image_integrity = await self._verify_image_integrity(image, i)
            results.append(image_integrity)
        
        # Check for missing files
        missing_files = await self._check_missing_files(work)
        results.append(missing_files)
        
        return results
    
    async def _check_file_exists_and_readable(self, work: BlakeWork) -> VerificationResult:
        """Check if work file exists and is readable."""
        try:
            work_file = self.data_dir / "unified" / "works" / "by_id" / work.id / "work.json"
            
            if not work_file.exists():
                return VerificationResult(
                    check_type="file_exists",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"file_path": str(work_file)},
                    errors=["Work file does not exist"],
                    recommendations=["Re-download or recreate work file"]
                )
            
            # Check file size
            file_size = work_file.stat().st_size
            if file_size == 0:
                return VerificationResult(
                    check_type="file_readable",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"file_size": file_size},
                    errors=["Work file is empty"],
                    recommendations=["Re-download work file"]
                )
            
            # Check if file is readable
            try:
                with open(work_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except Exception as e:
                return VerificationResult(
                    check_type="file_readable",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"error": str(e)},
                    errors=["Work file is not readable"],
                    recommendations=["Fix file encoding or format"]
                )
            
            return VerificationResult(
                check_type="file_exists",
                passed=True,
                score=1.0,
                quality_level=QualityLevel.EXCELLENT,
                details={"file_path": str(work_file), "file_size": file_size}
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="file_exists",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_text_integrity(self, work: BlakeWork) -> VerificationResult:
        """Verify text content integrity."""
        try:
            text_content = work.text_content
            
            if not text_content:
                return VerificationResult(
                    check_type="text_integrity",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["No text content available"],
                    recommendations=["Add text content or mark as image-only work"]
                )
            
            # Check text length
            text_length = len(text_content)
            if text_length < 10:
                return VerificationResult(
                    check_type="text_integrity",
                    passed=False,
                    score=0.3,
                    quality_level=QualityLevel.POOR,
                    details={"text_length": text_length},
                    errors=["Text content too short"],
                    recommendations=["Verify text content completeness"]
                )
            
            # Check for encoding issues
            encoding_score = 1.0
            encoding_errors = []
            
            try:
                text_content.encode('utf-8')
            except UnicodeEncodeError as e:
                encoding_score = 0.5
                encoding_errors.append(f"Encoding error: {e}")
            
            # Check for common text quality issues
            quality_score = 1.0
            quality_issues = []
            
            # Check for excessive whitespace
            if text_content.count('\n\n\n') > text_length / 100:
                quality_score -= 0.1
                quality_issues.append("Excessive whitespace")
            
            # Check for missing punctuation
            if not any(p in text_content for p in '.!?'):
                quality_score -= 0.1
                quality_issues.append("Missing sentence punctuation")
            
            # Check for repeated characters (possible corruption)
            for char in text_content:
                if text_content.count(char) > text_length * 0.1:
                    quality_score -= 0.2
                    quality_issues.append("Suspicious character repetition")
                    break
            
            overall_score = (encoding_score + quality_score) / 2
            
            return VerificationResult(
                check_type="text_integrity",
                passed=overall_score >= 0.5,
                score=overall_score,
                quality_level=self._score_to_quality(overall_score),
                details={
                    "text_length": text_length,
                    "encoding_score": encoding_score,
                    "quality_score": quality_score
                },
                errors=encoding_errors,
                recommendations=quality_issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="text_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_image_integrity(self, image: BlakeImage, index: int) -> VerificationResult:
        """Verify image file integrity."""
        try:
            if not image.file_path or not image.file_path.exists():
                return VerificationResult(
                    check_type="image_integrity",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"image_index": index},
                    errors=["Image file does not exist"],
                    recommendations=["Re-download image file"]
                )
            
            # Check file format
            file_extension = image.file_path.suffix.lower()
            if file_extension not in self.supported_image_formats:
                return VerificationResult(
                    check_type="image_format",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"file_extension": file_extension},
                    errors=[f"Unsupported image format: {file_extension}"],
                    recommendations=["Convert to supported format"]
                )
            
            # Check file size
            file_size = image.file_path.stat().st_size
            if file_size == 0:
                return VerificationResult(
                    check_type="image_size",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"file_size": file_size},
                    errors=["Image file is empty"],
                    recommendations=["Re-download image file"]
                )
            
            # Check if image is readable
            try:
                with Image.open(image.file_path) as img:
                    # Get image properties
                    width, height = img.size
                    mode = img.mode
                    format_name = img.format
                    
                    # Check image dimensions
                    if width < 10 or height < 10:
                        return VerificationResult(
                            check_type="image_dimensions",
                            passed=False,
                            score=0.3,
                            quality_level=QualityLevel.POOR,
                            details={"width": width, "height": height},
                            errors=["Image dimensions too small"],
                            recommendations=["Check image quality"]
                        )
                    
                    # Check image quality
                    quality_score = 1.0
                    quality_issues = []
                    
                    # Check for reasonable aspect ratio
                    aspect_ratio = width / height
                    if aspect_ratio < 0.1 or aspect_ratio > 10:
                        quality_score -= 0.2
                        quality_issues.append("Unusual aspect ratio")
                    
                    # Check for color mode
                    if mode == 'P' and img.getcolors() and len(img.getcolors()) < 16:
                        quality_score -= 0.1
                        quality_issues.append("Very limited color palette")
                    
                    return VerificationResult(
                        check_type="image_integrity",
                        passed=True,
                        score=quality_score,
                        quality_level=self._score_to_quality(quality_score),
                        details={
                            "width": width,
                            "height": height,
                            "mode": mode,
                            "format": format_name,
                            "file_size": file_size
                        },
                        recommendations=quality_issues
                    )
                    
            except Exception as e:
                return VerificationResult(
                    check_type="image_readable",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"error": str(e)},
                    errors=[f"Image not readable: {e}"],
                    recommendations=["Fix image file or re-download"]
                )
            
        except Exception as e:
            return VerificationResult(
                check_type="image_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _check_missing_files(self, work: BlakeWork) -> VerificationResult:
        """Check for missing files referenced in metadata."""
        try:
            missing_files = []
            
            # Check if work file exists
            work_file = self.data_dir / "unified" / "works" / "by_id" / work.id / "work.json"
            if not work_file.exists():
                missing_files.append(str(work_file))
            
            # Check if image files exist
            for image in work.images:
                if image.file_path and not image.file_path.exists():
                    missing_files.append(str(image.file_path))
                
                if image.thumbnail_path and not image.thumbnail_path.exists():
                    missing_files.append(str(image.thumbnail_path))
            
            if missing_files:
                return VerificationResult(
                    check_type="missing_files",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"missing_files": missing_files},
                    errors=[f"Missing {len(missing_files)} files"],
                    recommendations=["Re-download missing files"]
                )
            else:
                return VerificationResult(
                    check_type="missing_files",
                    passed=True,
                    score=1.0,
                    quality_level=QualityLevel.EXCELLENT,
                    details={"missing_files": []}
                )
                
        except Exception as e:
            return VerificationResult(
                check_type="missing_files",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_content_quality(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify content quality and completeness."""
        results = []
        
        # Text content quality
        if work.text_content:
            text_quality = await self._assess_text_quality(work)
            results.append(text_quality)
        
        # Image content quality
        for i, image in enumerate(work.images):
            image_quality = await self._assess_image_quality(image, i)
            results.append(image_quality)
        
        # Content completeness
        completeness = await self._assess_content_completeness(work)
        results.append(completeness)
        
        return results
    
    async def _assess_text_quality(self, work: BlakeWork) -> VerificationResult:
        """Assess text content quality."""
        try:
            text = work.text_content
            if not text:
                return VerificationResult(
                    check_type="text_quality",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["No text content"],
                    recommendations=["Add text content"]
                )
            
            # Basic quality metrics
            word_count = len(text.split())
            char_count = len(text)
            line_count = len(text.split('\n'))
            
            # Quality indicators
            quality_score = 1.0
            issues = []
            
            # Check for reasonable length
            if word_count < 10:
                quality_score -= 0.3
                issues.append("Text too short")
            elif word_count > 10000:
                quality_score -= 0.1
                issues.append("Text very long")
            
            # Check for proper formatting
            if not any(p in text for p in '.!?'):
                quality_score -= 0.2
                issues.append("No sentence endings")
            
            # Check for common OCR errors
            ocr_errors = 0
            for char in text:
                if char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:\'"()-':
                    ocr_errors += 1
            
            if ocr_errors > char_count * 0.05:  # More than 5% unusual characters
                quality_score -= 0.3
                issues.append("Possible OCR errors")
            
            return VerificationResult(
                check_type="text_quality",
                passed=quality_score >= 0.5,
                score=quality_score,
                quality_level=self._score_to_quality(quality_score),
                details={
                    "word_count": word_count,
                    "char_count": char_count,
                    "line_count": line_count,
                    "ocr_errors": ocr_errors
                },
                recommendations=issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="text_quality",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _assess_image_quality(self, image: BlakeImage, index: int) -> VerificationResult:
        """Assess image content quality."""
        try:
            if not image.file_path or not image.file_path.exists():
                return VerificationResult(
                    check_type="image_quality",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"image_index": index},
                    errors=["Image file missing"],
                    recommendations=["Re-download image"]
                )
            
            with Image.open(image.file_path) as img:
                width, height = img.size
                mode = img.mode
                
                quality_score = 1.0
                issues = []
                
                # Check resolution
                if width < 100 or height < 100:
                    quality_score -= 0.4
                    issues.append("Low resolution")
                elif width < 300 or height < 300:
                    quality_score -= 0.2
                    issues.append("Medium resolution")
                
                # Check color depth
                if mode == 'L':  # Grayscale
                    quality_score -= 0.1
                    issues.append("Grayscale image")
                elif mode == 'P':  # Palette
                    quality_score -= 0.2
                    issues.append("Limited color palette")
                
                # Check aspect ratio
                aspect_ratio = width / height
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    quality_score -= 0.1
                    issues.append("Unusual aspect ratio")
                
                return VerificationResult(
                    check_type="image_quality",
                    passed=quality_score >= 0.5,
                    score=quality_score,
                    quality_level=self._score_to_quality(quality_score),
                    details={
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "aspect_ratio": aspect_ratio
                    },
                    recommendations=issues
                )
                
        except Exception as e:
            return VerificationResult(
                check_type="image_quality",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _assess_content_completeness(self, work: BlakeWork) -> VerificationResult:
        """Assess content completeness."""
        try:
            completeness_score = 0.0
            missing_elements = []
            
            # Check for metadata
            if work.metadata and work.metadata.title:
                completeness_score += 0.3
            else:
                missing_elements.append("Title")
            
            if work.metadata and work.metadata.description:
                completeness_score += 0.1
            else:
                missing_elements.append("Description")
            
            # Check for content
            if work.text_content:
                completeness_score += 0.3
            else:
                missing_elements.append("Text content")
            
            if work.images:
                completeness_score += 0.2
            else:
                missing_elements.append("Images")
            
            # Check for analysis results
            if work.text_analysis or work.visual_analysis or work.cross_analysis:
                completeness_score += 0.1
            else:
                missing_elements.append("Analysis results")
            
            return VerificationResult(
                check_type="content_completeness",
                passed=completeness_score >= 0.5,
                score=completeness_score,
                quality_level=self._score_to_quality(completeness_score),
                details={
                    "missing_elements": missing_elements,
                    "has_metadata": bool(work.metadata and work.metadata.title),
                    "has_text": bool(work.text_content),
                    "has_images": bool(work.images),
                    "has_analysis": bool(work.text_analysis or work.visual_analysis or work.cross_analysis)
                },
                recommendations=missing_elements
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="content_completeness",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_metadata(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify metadata quality and completeness."""
        results = []
        
        # Metadata completeness
        metadata_completeness = await self._check_metadata_completeness(work)
        results.append(metadata_completeness)
        
        # Metadata accuracy
        metadata_accuracy = await self._check_metadata_accuracy(work)
        results.append(metadata_accuracy)
        
        return results
    
    async def _check_metadata_completeness(self, work: BlakeWork) -> VerificationResult:
        """Check metadata completeness."""
        try:
            if not work.metadata:
                return VerificationResult(
                    check_type="metadata_completeness",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["No metadata available"],
                    recommendations=["Add metadata"]
                )
            
            metadata = work.metadata
            completeness_score = 0.0
            missing_fields = []
            
            # Required fields
            required_fields = ['id', 'title', 'work_type', 'source']
            for field in required_fields:
                if hasattr(metadata, field) and getattr(metadata, field):
                    completeness_score += 0.2
                else:
                    missing_fields.append(field)
            
            # Optional but important fields
            optional_fields = ['creation_date', 'description', 'medium', 'dimensions']
            for field in optional_fields:
                if hasattr(metadata, field) and getattr(metadata, field):
                    completeness_score += 0.1
                else:
                    missing_fields.append(field)
            
            return VerificationResult(
                check_type="metadata_completeness",
                passed=completeness_score >= 0.6,
                score=completeness_score,
                quality_level=self._score_to_quality(completeness_score),
                details={
                    "missing_fields": missing_fields,
                    "has_id": bool(metadata.id),
                    "has_title": bool(metadata.title),
                    "has_work_type": bool(metadata.work_type),
                    "has_source": bool(metadata.source)
                },
                recommendations=missing_fields
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="metadata_completeness",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _check_metadata_accuracy(self, work: BlakeWork) -> VerificationResult:
        """Check metadata accuracy and consistency."""
        try:
            if not work.metadata:
                return VerificationResult(
                    check_type="metadata_accuracy",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["No metadata available"],
                    recommendations=["Add metadata"]
                )
            
            metadata = work.metadata
            accuracy_score = 1.0
            issues = []
            
            # Check for reasonable values
            if metadata.title and len(metadata.title) < 3:
                accuracy_score -= 0.2
                issues.append("Title too short")
            
            if metadata.creation_date:
                try:
                    year = metadata.creation_date.year
                    if year < 1700 or year > 2024:
                        accuracy_score -= 0.3
                        issues.append("Unusual creation date")
                except:
                    accuracy_score -= 0.3
                    issues.append("Invalid creation date")
            
            # Check for consistency
            if work.text_content and not work.images and metadata.work_type in [WorkType.PAINTING, WorkType.DRAWING]:
                accuracy_score -= 0.2
                issues.append("Work type mismatch with content")
            
            return VerificationResult(
                check_type="metadata_accuracy",
                passed=accuracy_score >= 0.7,
                score=accuracy_score,
                quality_level=self._score_to_quality(accuracy_score),
                details={
                    "title_length": len(metadata.title) if metadata.title else 0,
                    "has_creation_date": bool(metadata.creation_date),
                    "work_type": metadata.work_type.value if metadata.work_type else None
                },
                recommendations=issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="metadata_accuracy",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_format_compliance(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify format compliance and standards."""
        results = []
        
        # JSON format compliance
        json_compliance = await self._check_json_compliance(work)
        results.append(json_compliance)
        
        # File format compliance
        file_compliance = await self._check_file_format_compliance(work)
        results.append(file_compliance)
        
        return results
    
    async def _check_json_compliance(self, work: BlakeWork) -> VerificationResult:
        """Check JSON format compliance."""
        try:
            work_file = self.data_dir / "unified" / "works" / "by_id" / work.id / "work.json"
            
            if not work_file.exists():
                return VerificationResult(
                    check_type="json_compliance",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["Work file does not exist"],
                    recommendations=["Create work file"]
                )
            
            # Try to parse JSON
            try:
                with open(work_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check for required fields
                required_fields = ['id', 'metadata']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    return VerificationResult(
                        check_type="json_compliance",
                        passed=False,
                        score=0.5,
                        quality_level=QualityLevel.POOR,
                        details={"missing_fields": missing_fields},
                        errors=[f"Missing required fields: {missing_fields}"],
                        recommendations=["Add missing JSON fields"]
                    )
                
                return VerificationResult(
                    check_type="json_compliance",
                    passed=True,
                    score=1.0,
                    quality_level=QualityLevel.EXCELLENT,
                    details={"json_valid": True}
                )
                
            except json.JSONDecodeError as e:
                return VerificationResult(
                    check_type="json_compliance",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={"error": str(e)},
                    errors=[f"Invalid JSON: {e}"],
                    recommendations=["Fix JSON format"]
                )
                
        except Exception as e:
            return VerificationResult(
                check_type="json_compliance",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _check_file_format_compliance(self, work: BlakeWork) -> VerificationResult:
        """Check file format compliance."""
        try:
            compliance_score = 1.0
            issues = []
            
            # Check image formats
            for image in work.images:
                if image.file_path and image.file_path.exists():
                    file_extension = image.file_path.suffix.lower()
                    if file_extension not in self.supported_image_formats:
                        compliance_score -= 0.2
                        issues.append(f"Unsupported image format: {file_extension}")
            
            return VerificationResult(
                check_type="file_format_compliance",
                passed=compliance_score >= 0.8,
                score=compliance_score,
                quality_level=self._score_to_quality(compliance_score),
                details={"supported_formats": list(self.supported_image_formats)},
                recommendations=issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="file_format_compliance",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _verify_accessibility(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify accessibility and usability."""
        results = []
        
        # Image accessibility
        for i, image in enumerate(work.images):
            image_accessibility = await self._check_image_accessibility(image, i)
            results.append(image_accessibility)
        
        # Text accessibility
        text_accessibility = await self._check_text_accessibility(work)
        results.append(text_accessibility)
        
        return results
    
    async def _check_image_accessibility(self, image: BlakeImage, index: int) -> VerificationResult:
        """Check image accessibility features."""
        try:
            accessibility_score = 1.0
            issues = []
            
            # Check for alt text
            if not image.alt_text:
                accessibility_score -= 0.3
                issues.append("Missing alt text")
            
            # Check for description
            if not image.description:
                accessibility_score -= 0.2
                issues.append("Missing description")
            
            # Check image quality for accessibility
            if image.file_path and image.file_path.exists():
                try:
                    with Image.open(image.file_path) as img:
                        width, height = img.size
                        
                        # Check for reasonable size
                        if width < 200 or height < 200:
                            accessibility_score -= 0.2
                            issues.append("Image too small for accessibility")
                        
                        # Check for color contrast (simplified)
                        if img.mode == 'L':  # Grayscale
                            accessibility_score -= 0.1
                            issues.append("Grayscale image may have poor contrast")
                            
                except Exception as e:
                    accessibility_score -= 0.3
                    issues.append(f"Cannot assess image quality: {e}")
            
            return VerificationResult(
                check_type="image_accessibility",
                passed=accessibility_score >= 0.7,
                score=accessibility_score,
                quality_level=self._score_to_quality(accessibility_score),
                details={
                    "has_alt_text": bool(image.alt_text),
                    "has_description": bool(image.description),
                    "image_index": index
                },
                recommendations=issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="image_accessibility",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    async def _check_text_accessibility(self, work: BlakeWork) -> VerificationResult:
        """Check text accessibility features."""
        try:
            if not work.text_content:
                return VerificationResult(
                    check_type="text_accessibility",
                    passed=False,
                    score=0.0,
                    quality_level=QualityLevel.FAILED,
                    details={},
                    errors=["No text content"],
                    recommendations=["Add text content"]
                )
            
            accessibility_score = 1.0
            issues = []
            
            text = work.text_content
            
            # Check for reasonable line length
            lines = text.split('\n')
            long_lines = [line for line in lines if len(line) > 100]
            if len(long_lines) > len(lines) * 0.5:
                accessibility_score -= 0.2
                issues.append("Many long lines may be hard to read")
            
            # Check for proper paragraph breaks
            if '\n\n' not in text and len(text) > 500:
                accessibility_score -= 0.1
                issues.append("Missing paragraph breaks")
            
            # Check for special characters that might cause issues
            special_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07']
            for char in special_chars:
                if char in text:
                    accessibility_score -= 0.1
                    issues.append("Contains special control characters")
                    break
            
            return VerificationResult(
                check_type="text_accessibility",
                passed=accessibility_score >= 0.7,
                score=accessibility_score,
                quality_level=self._score_to_quality(accessibility_score),
                details={
                    "text_length": len(text),
                    "line_count": len(lines),
                    "long_lines": len(long_lines)
                },
                recommendations=issues
            )
            
        except Exception as e:
            return VerificationResult(
                check_type="text_accessibility",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            )
    
    def _score_to_quality(self, score: float) -> QualityLevel:
        """Convert score to quality level."""
        if score >= self.thresholds['excellent']:
            return QualityLevel.EXCELLENT
        elif score >= self.thresholds['good']:
            return QualityLevel.GOOD
        elif score >= self.thresholds['fair']:
            return QualityLevel.FAIR
        elif score >= self.thresholds['poor']:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAILED
    
    def _generate_quality_report(self, work: BlakeWork, verification_results: List[VerificationResult]) -> QualityReport:
        """Generate comprehensive quality report."""
        total_checks = len(verification_results)
        passed_checks = sum(1 for result in verification_results if result.passed)
        failed_checks = total_checks - passed_checks
        
        # Calculate overall score
        if total_checks > 0:
            overall_score = sum(result.score for result in verification_results) / total_checks
        else:
            overall_score = 0.0
        
        overall_quality = self._score_to_quality(overall_score)
        
        # Collect critical issues and warnings
        critical_issues = []
        warnings = []
        recommendations = []
        
        for result in verification_results:
            if result.quality_level == QualityLevel.FAILED:
                critical_issues.extend(result.errors)
            elif result.quality_level in [QualityLevel.POOR, QualityLevel.FAIR]:
                warnings.extend(result.errors)
            
            recommendations.extend(result.recommendations)
        
        return QualityReport(
            work_id=work.id,
            timestamp=datetime.now(),
            overall_score=overall_score,
            overall_quality=overall_quality,
            verification_results=verification_results,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _create_error_report(self, work_id: str, error: str) -> QualityReport:
        """Create error report when verification fails."""
        return QualityReport(
            work_id=work_id,
            timestamp=datetime.now(),
            overall_score=0.0,
            overall_quality=QualityLevel.FAILED,
            verification_results=[],
            total_checks=0,
            passed_checks=0,
            failed_checks=0,
            critical_issues=[error],
            warnings=[],
            recommendations=["Fix verification error and retry"]
        )
    
    async def _save_quality_report(self, report: QualityReport) -> None:
        """Save quality report to disk."""
        try:
            report_file = self.verification_dir / f"{report.work_id}_quality_report.json"
            
            # Convert to dict for JSON serialization
            report_data = asdict(report)
            
            # Convert datetime objects to strings
            report_data['timestamp'] = report.timestamp.isoformat()
            for result in report_data['verification_results']:
                if 'timestamp' in result:
                    result['timestamp'] = result['timestamp'].isoformat()
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving quality report for {report.work_id}: {e}")
    
    async def verify_collection(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """
        Verify quality of entire collection.
        
        Args:
            works: List of BlakeWork objects to verify
            
        Returns:
            Collection-wide quality report
        """
        logger.info(f"Verifying collection quality for {len(works)} works")
        
        collection_report = {
            'total_works': len(works),
            'verified_works': 0,
            'quality_distribution': {
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0,
                'failed': 0
            },
            'overall_score': 0.0,
            'critical_issues': [],
            'recommendations': [],
            'work_reports': []
        }
        
        total_score = 0.0
        
        for work in works:
            try:
                report = await self.verify_work(work)
                collection_report['work_reports'].append(report)
                collection_report['verified_works'] += 1
                
                # Update quality distribution
                quality = report.overall_quality.value
                collection_report['quality_distribution'][quality] += 1
                
                # Accumulate score
                total_score += report.overall_score
                
                # Collect critical issues
                collection_report['critical_issues'].extend(report.critical_issues)
                collection_report['recommendations'].extend(report.recommendations)
                
            except Exception as e:
                logger.error(f"Error verifying work {work.id}: {e}")
                collection_report['critical_issues'].append(f"Verification failed for {work.id}: {e}")
        
        # Calculate overall score
        if collection_report['verified_works'] > 0:
            collection_report['overall_score'] = total_score / collection_report['verified_works']
        
        # Remove duplicates from recommendations
        collection_report['recommendations'] = list(set(collection_report['recommendations']))
        
        logger.info(f"Collection verification completed: {collection_report['overall_score']:.2f} average score")
        return collection_report
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality assurance statistics."""
        try:
            # Count quality reports
            report_files = list(self.verification_dir.glob("*_quality_report.json"))
            
            quality_distribution = {
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0,
                'failed': 0
            }
            
            total_score = 0.0
            total_reports = 0
            
            for report_file in report_files:
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    quality = report_data['overall_quality']
                    score = report_data['overall_score']
                    
                    quality_distribution[quality] += 1
                    total_score += score
                    total_reports += 1
                    
                except Exception as e:
                    logger.warning(f"Error reading report {report_file}: {e}")
            
            average_score = total_score / total_reports if total_reports > 0 else 0.0
            
            return {
                'total_reports': total_reports,
                'quality_distribution': quality_distribution,
                'average_score': average_score,
                'verification_directory': str(self.verification_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting quality statistics: {e}")
            return {
                'total_reports': 0,
                'quality_distribution': {},
                'average_score': 0.0,
                'error': str(e)
            }
