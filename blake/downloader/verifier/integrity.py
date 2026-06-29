"""
File integrity verification for Blake works.

Handles checksum validation, size verification, and file existence checks.
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import aiofiles

from ...models import BlakeWork, BlakeImage
from .models import VerificationResult, QualityLevel

logger = logging.getLogger(__name__)


class FileIntegrityVerifier:
    """Verifies file integrity and completeness."""
    
    def __init__(self, data_dir: Path):
        """Initialize file integrity verifier."""
        self.data_dir = data_dir
        self.texts_dir = data_dir / "texts"
        self.images_dir = data_dir / "images"
    
    async def verify_work(self, work: BlakeWork) -> List[VerificationResult]:
        """Verify file integrity for a work."""
        results = []
        
        # Check text file
        if work.text_content:
            results.append(await self._check_text_file(work))
        
        # Check image files
        for i, image in enumerate(work.images):
            results.append(await self._check_image_file(image, i))
        
        return results
    
    async def _check_text_file(self, work: BlakeWork) -> VerificationResult:
        """Check text file integrity."""
        text_path = self.texts_dir / f"{work.id}.txt"
        
        errors = []
        details = {
            "file_path": str(text_path),
            "expected": True,
            "exists": text_path.exists()
        }
        
        if not text_path.exists():
            errors.append(f"Text file not found: {text_path}")
            return VerificationResult(
                check_type="text_file_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details=details,
                errors=errors
            )
        
        # Calculate checksum
        try:
            async with aiofiles.open(text_path, 'rb') as f:
                content = await f.read()
                checksum = hashlib.md5(content).hexdigest()
                details["checksum"] = checksum
                details["size_bytes"] = len(content)
        except Exception as e:
            errors.append(f"Error reading text file: {e}")
        
        passed = len(errors) == 0
        return VerificationResult(
            check_type="text_file_integrity",
            passed=passed,
            score=1.0 if passed else 0.0,
            quality_level=QualityLevel.EXCELLENT if passed else QualityLevel.FAILED,
            details=details,
            errors=errors if errors else None
        )
    
    async def _check_image_file(self, image: BlakeImage, index: int) -> VerificationResult:
        """Check image file integrity."""
        errors = []
        details = {
            "image_id": image.id,
            "index": index
        }
        
        if not image.local_path:
            errors.append(f"No local path for image {image.id}")
            return VerificationResult(
                check_type="image_file_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details=details,
                errors=errors
            )
        
        image_path = Path(image.local_path)
        details["file_path"] = str(image_path)
        details["exists"] = image_path.exists()
        
        if not image_path.exists():
            errors.append(f"Image file not found: {image_path}")
            return VerificationResult(
                check_type="image_file_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details=details,
                errors=errors
            )
        
        # Get file stats
        try:
            stat = image_path.stat()
            details["size_bytes"] = stat.st_size
            
            if stat.st_size == 0:
                errors.append("Image file is empty")
        except Exception as e:
            errors.append(f"Error checking image file: {e}")
        
        passed = len(errors) == 0
        score = 1.0 if passed else 0.5 if details.get("exists") else 0.0
        
        return VerificationResult(
            check_type="image_file_integrity",
            passed=passed,
            score=score,
            quality_level=QualityLevel.EXCELLENT if passed else QualityLevel.POOR,
            details=details,
            errors=errors if errors else None
        )
    
    async def compute_checksum(self, file_path: Path) -> Optional[str]:
        """Compute MD5 checksum for a file."""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.error(f"Error computing checksum for {file_path}: {e}")
            return None
