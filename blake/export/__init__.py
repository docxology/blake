"""
Blake export module for data export and API functionality.

Supports JSON, CSV, PDF, HTML, and Markdown export formats.
"""

from .exporter import BlakeExporter
from .formats import (
    JSONExporter, 
    CSVExporter, 
    PDFExporter,
    HTMLExporter,
    MarkdownExporter,
    ParquetExporter,
    EXPORTERS,
    get_exporter,
)

__all__ = [
    "BlakeExporter",
    "JSONExporter",
    "CSVExporter", 
    "PDFExporter",
    "HTMLExporter",
    "MarkdownExporter",
    "ParquetExporter",
    "EXPORTERS",
    "get_exporter",
    "BlakeAPI",
]


def __getattr__(name):
    if name == "BlakeAPI":
        from .api import BlakeAPI

        return BlakeAPI
    raise AttributeError(name)
