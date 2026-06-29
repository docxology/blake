"""
Content quality verification for Blake works.

Handles text quality assessment, image quality checks, and content completeness.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
import re

from PIL import Image

from ...models import BlakeWork, BlakeImage
from .models import VerificationResult, QualityLevel

logger = logging.getLogger(__name__)


class ContentQualityVerifier:
    """Verifies content quality and completeness."""
    
    def __init__(self, data_dir: Path):
        """Initialize content quality verifier."""
        self.data_dir = data_dir
        
        # Quality thresholds
        self.min_text_length = 100
        self.min_word_count = 20
        self.min_image_resolution = (100, 100)
    
    async def verify_work(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify content quality for a work."""
        results = []
        
        # Check text quality
        if work.text_content:
            results.append(await self._assess_text_quality(work))
        
        # Check image quality
        for i, image in enumerate(work.images):
            results.append(await self._assess_image_quality(image, i))
        
        # Check overall completeness
        results.append(await self._assess_completeness(work))
        
        return results
    
    async def _assess_text_quality(self, work: BlakeWork) -> VerificationResult:
        """Assess text content quality."""
        text = work.text_content or ""
        errors = []
        warnings = []
        
        details = {
            "length": len(text),
            "word_count": len(text.split()),
            "line_count": text.count('\n') + 1
        }
        
        # Check length
        if len(text) < self.min_text_length:
            warnings.append(f"Text length ({len(text)}) below minimum ({self.min_text_length})")
        
        # Check word count
        word_count = len(text.split())
        if word_count < self.min_word_count:
            warnings.append(f"Word count ({word_count}) below minimum ({self.min_word_count})")
        
        # Check for corruption patterns
        if '\x00' in text:
            errors.append("Text contains null bytes (possible corruption)")
        
        # Check encoding
        try:
            text.encode('utf-8')
            details["encoding_valid"] = True
        except UnicodeError:
            errors.append("Text contains invalid UTF-8 sequences")
            details["encoding_valid"] = False
        
        # Calculate quality score
        score = 1.0
        score -= len(errors) * 0.3
        score -= len(warnings) * 0.1
        score = max(0.0, min(1.0, score))
        
        quality_level = self._score_to_quality(score)
        
        return VerificationResult(
            check_type="text_quality",
            passed=score >= 0.5,
            score=score,
            quality_level=quality_level,
            details=details,
            errors=errors if errors else None,
            recommendations=warnings if warnings else None
        )
    
    async def _assess_image_quality(self, image: BlakeImage, index: int) -> VerificationResult:
        """Assess image content quality."""
        errors = []
        warnings = []
        details = {
            "image_id": image.id,
            "index": index
        }
        
        if not image.local_path:
            return VerificationResult(
                check_type="image_quality",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details=details,
                errors=["No local path for image"]
            )
        
        image_path = Path(image.local_path)
        if not image_path.exists():
            return VerificationResult(
                check_type="image_quality",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details=details,
                errors=["Image file not found"]
            )
        
        try:
            with Image.open(image_path) as img:
                details["width"] = img.width
                details["height"] = img.height
                details["format"] = img.format
                details["mode"] = img.mode
                
                # Check resolution
                if img.width < self.min_image_resolution[0] or img.height < self.min_image_resolution[1]:
                    warnings.append(f"Low resolution: {img.width}x{img.height}")
                
                # Check mode
                if img.mode not in ('RGB', 'RGBA', 'L'):
                    warnings.append(f"Unusual color mode: {img.mode}")
                
        except Exception as e:
            errors.append(f"Error opening image: {e}")
        
        score = 1.0
        score -= len(errors) * 0.4
        score -= len(warnings) * 0.1
        score = max(0.0, min(1.0, score))
        
        return VerificationResult(
            check_type="image_quality",
            passed=score >= 0.5,
            score=score,
            quality_level=self._score_to_quality(score),
            details=details,
            errors=errors if errors else None,
            recommendations=warnings if warnings else None
        )
    
    async def _assess_completeness(self, work: BlakeWork) -> VerificationResult:
        """Assess content completeness."""
        details = {
            "has_text": bool(work.text_content),
            "has_images": len(work.images) > 0,
            "image_count": len(work.images)
        }
        
        completeness_score = 0.0
        if work.text_content:
            completeness_score += 0.5
        if work.images:
            completeness_score += 0.5
        
        return VerificationResult(
            check_type="content_completeness",
            passed=completeness_score >= 0.5,
            score=completeness_score,
            quality_level=self._score_to_quality(completeness_score),
            details=details
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
