"""
Metadata verification for Blake works.

Handles metadata completeness, accuracy, and format compliance checks.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ...models import BlakeWork, BlakeMetadata
from .models import VerificationResult, QualityLevel

logger = logging.getLogger(__name__)


class MetadataVerifier:
    """Verifies metadata quality and completeness."""
    
    # Required metadata fields
    REQUIRED_FIELDS = ['title', 'work_type', 'source']
    RECOMMENDED_FIELDS = ['creation_date', 'description', 'tags', 'themes']
    
    def __init__(self, data_dir: Path):
        """Initialize metadata verifier."""
        self.data_dir = data_dir
    
    async def verify_work(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify metadata for a work."""
        results = []
        
        results.append(await self._check_completeness(work))
        results.append(await self._check_accuracy(work))
        results.append(await self._check_consistency(work))
        
        return results
    
    async def _check_completeness(self, work: BlakeWork) -> VerificationResult:
        """Check metadata completeness."""
        metadata = work.metadata
        errors = []
        warnings = []
        details = {}
        
        # Check required fields
        missing_required = []
        for field in self.REQUIRED_FIELDS:
            value = getattr(metadata, field, None)
            if not value:
                missing_required.append(field)
            details[f"has_{field}"] = bool(value)
        
        if missing_required:
            errors.append(f"Missing required fields: {', '.join(missing_required)}")
        
        # Check recommended fields
        missing_recommended = []
        for field in self.RECOMMENDED_FIELDS:
            value = getattr(metadata, field, None)
            if not value:
                missing_recommended.append(field)
            details[f"has_{field}"] = bool(value)
        
        if missing_recommended:
            warnings.append(f"Missing recommended fields: {', '.join(missing_recommended)}")
        
        # Calculate score
        total_fields = len(self.REQUIRED_FIELDS) + len(self.RECOMMENDED_FIELDS)
        filled_fields = total_fields - len(missing_required) - len(missing_recommended)
        score = filled_fields / total_fields
        
        # Penalize missing required fields
        score -= len(missing_required) * 0.2
        score = max(0.0, min(1.0, score))
        
        return VerificationResult(
            check_type="metadata_completeness",
            passed=len(missing_required) == 0,
            score=score,
            quality_level=self._score_to_quality(score),
            details=details,
            errors=errors if errors else None,
            recommendations=warnings if warnings else None
        )
    
    async def _check_accuracy(self, work: BlakeWork) -> VerificationResult:
        """Check metadata accuracy."""
        metadata = work.metadata
        errors = []
        warnings = []
        details = {}
        
        # Check title format
        if metadata.title:
            details["title_length"] = len(metadata.title)
            if len(metadata.title) > 200:
                warnings.append("Title is unusually long")
            if metadata.title.isdigit():
                errors.append("Title is only numbers")
        
        # Check date validity
        if metadata.creation_date:
            year = metadata.creation_date.year
            details["creation_year"] = year
            
            # Blake lived 1757-1827
            if year < 1750 or year > 1850:
                warnings.append(f"Creation date ({year}) outside Blake's era")
        
        # Check work type consistency
        details["work_type"] = str(metadata.work_type)
        
        score = 1.0
        score -= len(errors) * 0.3
        score -= len(warnings) * 0.1
        score = max(0.0, min(1.0, score))
        
        return VerificationResult(
            check_type="metadata_accuracy",
            passed=len(errors) == 0,
            score=score,
            quality_level=self._score_to_quality(score),
            details=details,
            errors=errors if errors else None,
            recommendations=warnings if warnings else None
        )
    
    async def _check_consistency(self, work: BlakeWork) -> VerificationResult:
        """Check metadata consistency with content."""
        errors = []
        warnings = []
        details = {}
        
        # Check ID consistency
        details["work_id"] = work.id
        details["metadata_id"] = work.metadata.id
        
        if work.id != work.metadata.id:
            errors.append("Work ID does not match metadata ID")
        
        # Check content type consistency
        has_text = bool(work.text_content)
        has_images = len(work.images) > 0
        details["has_text"] = has_text
        details["has_images"] = has_images
        
        # Text works should have text
        if str(work.metadata.work_type) in ['poem', 'prose', 'letter']:
            if not has_text:
                warnings.append(f"Work type is {work.metadata.work_type} but has no text")
        
        score = 1.0
        score -= len(errors) * 0.4
        score -= len(warnings) * 0.1
        score = max(0.0, min(1.0, score))
        
        return VerificationResult(
            check_type="metadata_consistency",
            passed=len(errors) == 0,
            score=score,
            quality_level=self._score_to_quality(score),
            details=details,
            errors=errors if errors else None,
            recommendations=warnings if warnings else None
        )
    
    def _score_to_quality(self, score: float) -> QualityLevel:
        """Convert score to quality level."""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.FAIR
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAILED
