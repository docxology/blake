"""
Verification data models for Blake quality assurance.

Defines VerificationResult, QualityLevel, and QualityReport models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional


class QualityLevel(Enum):
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
    score: float
    quality_level: QualityLevel
    details: Dict[str, Any]
    errors: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    
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
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.total_checks == 0:
            self.total_checks = len(self.verification_results)
            self.passed_checks = sum(1 for r in self.verification_results if r.passed)
            self.failed_checks = self.total_checks - self.passed_checks
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "work_id": self.work_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "overall_quality": self.overall_quality.value,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }
