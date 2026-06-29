__version__ = "0.1.0"
__author__ = "Daniel Ari Friedman"
__email__ = "daniel@activeinference.institute"
__orcid__ = "0000-0001-6232-9096"
__affiliation__ = "Active Inference Institute"

from .corpus import BlakeCorpus, CorpusConfig, CorpusManifest, CorpusRunSummary, PhaseResult
from .core import BlakeWorks
from .models import BlakeWork, BlakeImage, BlakeMetadata
from .exceptions import BlakeError, DownloadError, AnalysisError, ExportError, ValidationError

__all__ = [
    "BlakeCorpus",
    "CorpusConfig",
    "CorpusManifest",
    "CorpusRunSummary",
    "PhaseResult",
    "BlakeWorks",
    "BlakeWork", 
    "BlakeImage",
    "BlakeMetadata",
    "BlakeError",
    "DownloadError", 
    "AnalysisError",
    "ExportError",
    "ValidationError",
]
