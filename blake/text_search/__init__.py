"""Source-bound passage search; imports no NLP models or network clients."""

from .index import PassageIndex
from .models import Passage, Query, SearchMode, SearchScope

__all__ = ["Passage", "PassageIndex", "Query", "SearchMode", "SearchScope"]
