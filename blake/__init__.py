__version__ = "0.2.0.dev0"
__author__ = "Daniel Ari Friedman"
__email__ = "daniel@activeinference.institute"
__orcid__ = "0000-0001-6232-9096"
__affiliation__ = "Active Inference Institute"

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .corpus import BlakeCorpus, CorpusConfig, CorpusManifest, CorpusRunSummary, PhaseResult
    from .models import BlakeWork, BlakeImage, BlakeMetadata
    from .exceptions import BlakeError, DownloadError, AnalysisError, ExportError, ValidationError


def __getattr__(name: str) -> type:
    """Load legacy public classes on demand, keeping text search free of NLP imports."""
    modules = {
        "BlakeCorpus": ".corpus", "CorpusConfig": ".corpus",
        "CorpusManifest": ".corpus", "CorpusRunSummary": ".corpus",
        "PhaseResult": ".corpus", "BlakeWork": ".models",
        "BlakeImage": ".models", "BlakeMetadata": ".models",
        "BlakeError": ".exceptions", "DownloadError": ".exceptions",
        "AnalysisError": ".exceptions", "ExportError": ".exceptions",
        "ValidationError": ".exceptions",
    }
    if name not in modules:
        raise AttributeError(name)
    value = getattr(import_module(modules[name], __name__), name)
    globals()[name] = value
    return value

__all__ = [
    "BlakeCorpus",
    "CorpusConfig",
    "CorpusManifest",
    "CorpusRunSummary",
    "PhaseResult",
    "BlakeWork",
    "BlakeImage",
    "BlakeMetadata",
    "BlakeError",
    "DownloadError", 
    "AnalysisError",
    "ExportError",
    "ValidationError",
]
