"""
Blake metadata management module.
"""

from .manager import MetadataManager
from .processor import MetadataProcessor
from .search import MetadataSearcher
from .database import MetadataDatabase

__all__ = [
    "MetadataManager",
    "MetadataProcessor", 
    "MetadataSearcher",
    "MetadataDatabase",
]

