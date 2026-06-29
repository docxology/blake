"""
Blake downloader module for acquiring works from various sources.
"""

from .downloader import BlakeDownloader
from .sources import BlakeArchiveSource, ProjectGutenbergSource, InternetArchiveSource
from .scraper import WebScraper, ImageDownloader
from .blake_archive_scraper import BlakeArchiveScraper, scrape_blake_archive

__all__ = [
    "BlakeDownloader",
    "BlakeArchiveSource",
    "BlakeArchiveScraper",
    "ProjectGutenbergSource", 
    "InternetArchiveSource",
    "WebScraper",
    "ImageDownloader",
    "scrape_blake_archive",
]


