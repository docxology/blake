"""
Quality assurance orchestrator for Blake works.

Coordinates file integrity, content quality, and metadata verification.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from ...models import BlakeWork
from .models import VerificationResult, QualityLevel, QualityReport
from .integrity import FileIntegrityVerifier
from .content import ContentQualityVerifier
from .metadata import MetadataVerifier

logger = logging.getLogger(__name__)


class QualityAssurance:
    """
    Orchestrates quality verification across all verification modules.
    
    Combines file integrity, content quality, and metadata verification
    into a unified quality report.
    """
    
    def __init__(self, data_dir: Path):
        """Initialize quality assurance system."""
        self.data_dir = Path(data_dir)
        
        # Initialize sub-verifiers
        self.file_verifier = FileIntegrityVerifier(self.data_dir)
        self.content_verifier = ContentQualityVerifier(self.data_dir)
        self.metadata_verifier = MetadataVerifier(self.data_dir)
        
        # Statistics
        self.verified_count = 0
        self.passed_count = 0
        self.failed_count = 0
        
        logger.info(f"Initialized QualityAssurance with data_dir: {self.data_dir}")
    
    async def verify_work(self, work: BlakeWork) -> QualityReport:
        """
        Perform comprehensive quality verification on a work.
        
        Args:
            work: BlakeWork object to verify
            
        Returns:
            Comprehensive quality report
        """
        logger.info(f"Verifying work: {work.id}")
        
        all_results = []
        
        # File integrity checks
        try:
            file_results = await self.file_verifier.verify_work(work)
            all_results.extend(file_results)
        except Exception as e:
            logger.error(f"File verification error for {work.id}: {e}")
            all_results.append(VerificationResult(
                check_type="file_integrity",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            ))
        
        # Content quality checks
        try:
            content_results = await self.content_verifier.verify_work(work)
            all_results.extend(content_results)
        except Exception as e:
            logger.error(f"Content verification error for {work.id}: {e}")
            all_results.append(VerificationResult(
                check_type="content_quality",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            ))
        
        # Metadata checks
        try:
            metadata_results = await self.metadata_verifier.verify_work(work)
            all_results.extend(metadata_results)
        except Exception as e:
            logger.error(f"Metadata verification error for {work.id}: {e}")
            all_results.append(VerificationResult(
                check_type="metadata",
                passed=False,
                score=0.0,
                quality_level=QualityLevel.FAILED,
                details={"error": str(e)},
                errors=[str(e)]
            ))
        
        # Calculate overall quality
        report = self._create_quality_report(work.id, all_results)
        
        # Update statistics
        self.verified_count += 1
        if report.passed_checks == report.total_checks:
            self.passed_count += 1
        else:
            self.failed_count += 1
        
        logger.info(f"Verification complete for {work.id}: {report.overall_quality.value}")
        return report
    
    def _create_quality_report(self, work_id: str, results: List[VerificationResult]) -> QualityReport:
        """Create comprehensive quality report from verification results."""
        # Calculate overall score
        if results:
            overall_score = sum(r.score for r in results) / len(results)
        else:
            overall_score = 0.0
        
        # Determine overall quality level
        overall_quality = self._score_to_quality(overall_score)
        
        # Collect issues and recommendations
        critical_issues = []
        warnings = []
        recommendations = []
        
        for result in results:
            if result.errors:
                if result.quality_level == QualityLevel.FAILED:
                    critical_issues.extend(result.errors)
                else:
                    warnings.extend(result.errors)
            if result.recommendations:
                recommendations.extend(result.recommendations)
        
        return QualityReport(
            work_id=work_id,
            timestamp=datetime.now(),
            overall_score=overall_score,
            overall_quality=overall_quality,
            verification_results=results,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )
    
    async def verify_collection(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """Verify all works in a collection."""
        logger.info(f"Verifying collection of {len(works)} works")
        
        reports = []
        for work in works:
            try:
                report = await self.verify_work(work)
                reports.append(report)
            except Exception as e:
                logger.error(f"Error verifying work {work.id}: {e}")
        
        # Calculate collection statistics
        total_score = sum(r.overall_score for r in reports) / len(reports) if reports else 0.0
        
        return {
            "total_works": len(works),
            "verified_works": len(reports),
            "average_score": total_score,
            "excellent_count": sum(1 for r in reports if r.overall_quality == QualityLevel.EXCELLENT),
            "good_count": sum(1 for r in reports if r.overall_quality == QualityLevel.GOOD),
            "fair_count": sum(1 for r in reports if r.overall_quality == QualityLevel.FAIR),
            "poor_count": sum(1 for r in reports if r.overall_quality == QualityLevel.POOR),
            "failed_count": sum(1 for r in reports if r.overall_quality == QualityLevel.FAILED),
            "reports": [r.to_dict() for r in reports]
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get quality assurance statistics."""
        return {
            "verified_count": self.verified_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count
        }
    
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
