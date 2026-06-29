"""
Source Discovery Engine for comprehensive Blake work detection and cataloging.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

from .scraper import WebScraper
from ..models import SourceType, WorkType, LicenseType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a data source."""
    name: str
    source_type: SourceType
    base_url: str
    search_url: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    rate_limit: int = 1  # requests per second
    priority: int = 1  # 1=highest, 5=lowest
    enabled: bool = True
    last_checked: Optional[datetime] = None
    works_count: int = 0
    success_rate: float = 0.0
    error_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkMetadata:
    """Metadata for a discovered work."""
    id: str
    title: str
    source: SourceType
    source_url: str
    work_type: WorkType
    creation_date: Optional[datetime] = None
    description: Optional[str] = None
    image_urls: List[str] = None
    text_url: Optional[str] = None
    license: LicenseType = LicenseType.UNKNOWN
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkUpdate:
    """Information about a work update."""
    work_id: str
    source: SourceType
    update_type: str  # 'new', 'modified', 'deleted'
    timestamp: datetime
    changes: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = {}
        if self.metadata is None:
            self.metadata = {}


class SourceDiscoveryEngine:
    """
    Discovers and catalogs available Blake works across the web.
    
    This engine implements comprehensive source discovery with:
    - Multi-source work detection
    - Incremental update detection
    - Source health monitoring
    - Work deduplication
    - Metadata enrichment
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize the source discovery engine.
        
        Args:
            data_dir: Directory to store discovery data
        """
        self.data_dir = data_dir
        self.discovery_dir = data_dir / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        
        self.scraper = WebScraper(data_dir)
        self.sources_config = self._load_sources_config()
        self.known_works: Dict[str, WorkMetadata] = {}
        self.work_index: Dict[str, Set[str]] = {}  # title -> work_ids
        
        # Load existing discovery data
        self._load_discovery_data()
        
        logger.info(f"Initialized SourceDiscoveryEngine with {len(self.sources_config)} sources")
    
    def _load_sources_config(self) -> Dict[SourceType, SourceConfig]:
        """Load configuration for all sources."""
        sources = {
            # Tier 1: Primary Sources
            SourceType.BLAKE_ARCHIVE: SourceConfig(
                name="Blake Archive",
                source_type=SourceType.BLAKE_ARCHIVE,
                base_url="https://blakearchive.org",
                search_url="https://blakearchive.org/search",
                priority=1,
                rate_limit=2
            ),
            SourceType.PROJECT_GUTENBERG: SourceConfig(
                name="Project Gutenberg",
                source_type=SourceType.PROJECT_GUTENBERG,
                base_url="https://www.gutenberg.org",
                search_url="https://www.gutenberg.org/ebooks/search/?query=William+Blake",
                priority=1,
                rate_limit=1
            ),
            SourceType.INTERNET_ARCHIVE: SourceConfig(
                name="Internet Archive",
                source_type=SourceType.INTERNET_ARCHIVE,
                base_url="https://archive.org",
                search_url="https://archive.org/search.php?query=William+Blake",
                priority=1,
                rate_limit=1
            ),
            
            # Tier 2: Museum and Library Sources
            SourceType.BRITISH_MUSEUM: SourceConfig(
                name="British Museum",
                source_type=SourceType.BRITISH_MUSEUM,
                base_url="https://www.britishmuseum.org",
                search_url="https://www.britishmuseum.org/collection/search?q=William+Blake",
                api_endpoint="https://collection.britishmuseum.org/api/object",
                priority=2,
                rate_limit=1
            ),
            SourceType.TATE: SourceConfig(
                name="Tate Gallery",
                source_type=SourceType.TATE,
                base_url="https://www.tate.org.uk",
                search_url="https://www.tate.org.uk/search?q=William+Blake",
                api_endpoint="https://www.tate.org.uk/api/v1/artworks",
                priority=2,
                rate_limit=1
            ),
            
            # Tier 3: Academic Sources
            SourceType.HATHITRUST: SourceConfig(
                name="HathiTrust",
                source_type=SourceType.HATHITRUST,
                base_url="https://www.hathitrust.org",
                search_url="https://catalog.hathitrust.org/Search/Home?lookfor=William+Blake",
                priority=3,
                rate_limit=1
            ),
            SourceType.WIKIMEDIA: SourceConfig(
                name="Wikimedia Commons",
                source_type=SourceType.WIKIMEDIA,
                base_url="https://commons.wikimedia.org",
                search_url="https://commons.wikimedia.org/w/index.php?search=William+Blake",
                priority=3,
                rate_limit=2
            ),
            SourceType.GOOGLE_ARTS: SourceConfig(
                name="Google Arts & Culture",
                source_type=SourceType.GOOGLE_ARTS,
                base_url="https://artsandculture.google.com",
                search_url="https://artsandculture.google.com/search?q=William+Blake",
                priority=3,
                rate_limit=1
            )
        }
        
        return sources
    
    async def discover_sources(self) -> List[SourceConfig]:
        """
        Discover and validate all available sources.
        
        Returns:
            List of validated source configurations
        """
        logger.info("Discovering and validating sources")
        
        valid_sources = []
        
        for source_type, config in self.sources_config.items():
            if not config.enabled:
                continue
                
            try:
                # Test source availability
                is_available = await self._test_source_availability(config)
                if is_available:
                    valid_sources.append(config)
                    logger.info(f"Source validated: {config.name}")
                else:
                    logger.warning(f"Source unavailable: {config.name}")
                    
            except Exception as e:
                logger.error(f"Error validating source {config.name}: {e}")
                config.error_count += 1
        
        logger.info(f"Discovered {len(valid_sources)} valid sources")
        return valid_sources
    
    async def _test_source_availability(self, config: SourceConfig) -> bool:
        """Test if a source is available and accessible."""
        try:
            # Test basic connectivity
            response = await self.scraper.session.get(config.base_url, timeout=10)
            if response.status == 200:
                config.last_checked = datetime.now()
                return True
            return False
        except Exception as e:
            logger.debug(f"Source {config.name} test failed: {e}")
            return False
    
    async def catalog_works(self, source: SourceConfig) -> List[WorkMetadata]:
        """
        Catalog all available works from a source.
        
        Args:
            source: Source configuration
            
        Returns:
            List of discovered work metadata
        """
        logger.info(f"Cataloging works from {source.name}")
        
        try:
            works = []
            
            if source.source_type == SourceType.BLAKE_ARCHIVE:
                works = await self._catalog_blake_archive(source)
            elif source.source_type == SourceType.PROJECT_GUTENBERG:
                works = await self._catalog_project_gutenberg(source)
            elif source.source_type == SourceType.INTERNET_ARCHIVE:
                works = await self._catalog_internet_archive(source)
            elif source.source_type == SourceType.BRITISH_MUSEUM:
                works = await self._catalog_british_museum(source)
            elif source.source_type == SourceType.TATE:
                works = await self._catalog_tate(source)
            elif source.source_type == SourceType.HATHITRUST:
                works = await self._catalog_hathitrust(source)
            elif source.source_type == SourceType.WIKIMEDIA:
                works = await self._catalog_wikimedia(source)
            elif source.source_type == SourceType.GOOGLE_ARTS:
                works = await self._catalog_google_arts(source)
            
            # Update source statistics
            source.works_count = len(works)
            source.success_rate = 1.0 if works else 0.0
            
            # Store discovered works
            for work in works:
                self.known_works[work.id] = work
                self._index_work(work)
            
            logger.info(f"Cataloged {len(works)} works from {source.name}")
            return works
            
        except Exception as e:
            logger.error(f"Error cataloging works from {source.name}: {e}")
            source.error_count += 1
            return []
    
    async def _catalog_blake_archive(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Blake Archive."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find work links
            work_links = soup.find_all('a', href=re.compile(r'/works/'))
            
            for link in work_links:
                work_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and work_url:
                    work_id = self._extract_work_id(work_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=work_url,
                        work_type=WorkType.POEM,  # Default for Blake Archive
                        license=LicenseType.PUBLIC_DOMAIN
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging Blake Archive: {e}")
        
        return works
    
    async def _catalog_project_gutenberg(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Project Gutenberg."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find book links
            book_links = soup.find_all('a', href=re.compile(r'/ebooks/\d+'))
            
            for link in book_links:
                book_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    work_id = self._extract_work_id(book_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=book_url,
                        work_type=WorkType.POEM,
                        license=LicenseType.PUBLIC_DOMAIN
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging Project Gutenberg: {e}")
        
        return works
    
    async def _catalog_internet_archive(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Internet Archive."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find item links
            item_links = soup.find_all('a', href=re.compile(r'/details/'))
            
            for link in item_links:
                item_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    work_id = self._extract_work_id(item_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=item_url,
                        work_type=WorkType.MANUSCRIPT,
                        license=LicenseType.PUBLIC_DOMAIN
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging Internet Archive: {e}")
        
        return works
    
    async def _catalog_british_museum(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from British Museum."""
        works = []
        
        try:
            if source.api_endpoint:
                # Use API if available
                response = await self.scraper.session.get(
                    source.api_endpoint,
                    params={'q': 'William Blake', 'limit': 100}
                )
                if response.status == 200:
                    data = await response.json()
                    # Process API response
                    # Implementation depends on specific API format
            else:
                # Fallback to web scraping
                soup = await self.scraper.scrape_page(source.search_url)
                
                # Find collection item links
                item_links = soup.find_all('a', href=re.compile(r'/collection/object/'))
                
                for link in item_links:
                    item_url = urljoin(source.base_url, link['href'])
                    title = link.get_text(strip=True)
                    
                    if title and 'blake' in title.lower():
                        work_id = self._extract_work_id(item_url)
                        
                        work = WorkMetadata(
                            id=work_id,
                            title=title,
                            source=source.source_type,
                            source_url=item_url,
                            work_type=WorkType.DRAWING,
                            license=LicenseType.CC_BY_NC_SA
                        )
                        
                        works.append(work)
                        
        except Exception as e:
            logger.error(f"Error cataloging British Museum: {e}")
        
        return works
    
    async def _catalog_tate(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Tate Gallery."""
        works = []
        
        try:
            if source.api_endpoint:
                # Use API if available
                response = await self.scraper.session.get(
                    source.api_endpoint,
                    params={'q': 'William Blake', 'limit': 100}
                )
                if response.status == 200:
                    data = await response.json()
                    # Process API response
                    # Implementation depends on specific API format
            else:
                # Fallback to web scraping
                soup = await self.scraper.scrape_page(source.search_url)
                
                # Find artwork links
                artwork_links = soup.find_all('a', href=re.compile(r'/art/artworks/'))
                
                for link in artwork_links:
                    artwork_url = urljoin(source.base_url, link['href'])
                    title = link.get_text(strip=True)
                    
                    if title and 'blake' in title.lower():
                        work_id = self._extract_work_id(artwork_url)
                        
                        work = WorkMetadata(
                            id=work_id,
                            title=title,
                            source=source.source_type,
                            source_url=artwork_url,
                            work_type=WorkType.PAINTING,
                            license=LicenseType.CC_BY_NC_ND
                        )
                        
                        works.append(work)
                        
        except Exception as e:
            logger.error(f"Error cataloging Tate: {e}")
        
        return works
    
    async def _catalog_hathitrust(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from HathiTrust."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find catalog item links
            item_links = soup.find_all('a', href=re.compile(r'/catalog/'))
            
            for link in item_links:
                item_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    work_id = self._extract_work_id(item_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=item_url,
                        work_type=WorkType.MANUSCRIPT,
                        license=LicenseType.PUBLIC_DOMAIN
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging HathiTrust: {e}")
        
        return works
    
    async def _catalog_wikimedia(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Wikimedia Commons."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find media file links
            media_links = soup.find_all('a', href=re.compile(r'/wiki/File:'))
            
            for link in media_links:
                media_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    work_id = self._extract_work_id(media_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=media_url,
                        work_type=WorkType.ENGRAVING,
                        license=LicenseType.CC_BY_SA
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging Wikimedia: {e}")
        
        return works
    
    async def _catalog_google_arts(self, source: SourceConfig) -> List[WorkMetadata]:
        """Catalog works from Google Arts & Culture."""
        works = []
        
        try:
            soup = await self.scraper.scrape_page(source.search_url)
            
            # Find artwork links
            artwork_links = soup.find_all('a', href=re.compile(r'/asset/'))
            
            for link in artwork_links:
                artwork_url = urljoin(source.base_url, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    work_id = self._extract_work_id(artwork_url)
                    
                    work = WorkMetadata(
                        id=work_id,
                        title=title,
                        source=source.source_type,
                        source_url=artwork_url,
                        work_type=WorkType.PAINTING,
                        license=LicenseType.CC_BY_NC_ND
                    )
                    
                    works.append(work)
                    
        except Exception as e:
            logger.error(f"Error cataloging Google Arts: {e}")
        
        return works
    
    async def detect_updates(self, source: SourceConfig) -> List[WorkUpdate]:
        """
        Detect new or updated works since last check.
        
        Args:
            source: Source configuration
            
        Returns:
            List of work updates
        """
        logger.info(f"Detecting updates for {source.name}")
        
        try:
            # Get current work list
            current_works = await self.catalog_works(source)
            current_work_ids = {work.id for work in current_works}
            
            # Get previously known works for this source
            known_work_ids = {
                work_id for work_id, work in self.known_works.items()
                if work.source == source.source_type
            }
            
            updates = []
            
            # Detect new works
            new_work_ids = current_work_ids - known_work_ids
            for work_id in new_work_ids:
                work = next(w for w in current_works if w.id == work_id)
                update = WorkUpdate(
                    work_id=work_id,
                    source=source.source_type,
                    update_type='new',
                    timestamp=datetime.now(),
                    changes={'title': work.title}
                )
                updates.append(update)
            
            # Detect deleted works
            deleted_work_ids = known_work_ids - current_work_ids
            for work_id in deleted_work_ids:
                update = WorkUpdate(
                    work_id=work_id,
                    source=source.source_type,
                    update_type='deleted',
                    timestamp=datetime.now()
                )
                updates.append(update)
            
            # Detect modified works (simplified - would need more sophisticated comparison)
            for work in current_works:
                if work.id in known_work_ids:
                    known_work = self.known_works[work.id]
                    if work.title != known_work.title:
                        update = WorkUpdate(
                            work_id=work.id,
                            source=source.source_type,
                            update_type='modified',
                            timestamp=datetime.now(),
                            changes={'title': work.title}
                        )
                        updates.append(update)
            
            logger.info(f"Detected {len(updates)} updates for {source.name}")
            return updates
            
        except Exception as e:
            logger.error(f"Error detecting updates for {source.name}: {e}")
            return []
    
    def _extract_work_id(self, url: str) -> str:
        """Extract work ID from URL."""
        return urlparse(url).path.split('/')[-1]
    
    def _index_work(self, work: WorkMetadata) -> None:
        """Index work for deduplication."""
        title_key = work.title.lower().strip()
        if title_key not in self.work_index:
            self.work_index[title_key] = set()
        self.work_index[title_key].add(work.id)
    
    def find_duplicates(self, work_id: str) -> List[str]:
        """Find potential duplicates of a work."""
        work = self.known_works.get(work_id)
        if not work:
            return []
        
        title_key = work.title.lower().strip()
        duplicates = self.work_index.get(title_key, set())
        duplicates.discard(work_id)  # Remove self
        return list(duplicates)
    
    def _load_discovery_data(self) -> None:
        """Load existing discovery data from disk."""
        discovery_file = self.discovery_dir / "discovery_data.json"
        
        if discovery_file.exists():
            try:
                with open(discovery_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load known works
                for work_data in data.get('known_works', []):
                    work = WorkMetadata(**work_data)
                    self.known_works[work.id] = work
                    self._index_work(work)
                
                logger.info(f"Loaded {len(self.known_works)} known works")
                
            except Exception as e:
                logger.warning(f"Error loading discovery data: {e}")
    
    def _save_discovery_data(self) -> None:
        """Save discovery data to disk."""
        discovery_file = self.discovery_dir / "discovery_data.json"
        
        try:
            data = {
                'known_works': [asdict(work) for work in self.known_works.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(discovery_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Error saving discovery data: {e}")
    
    async def get_comprehensive_work_list(self) -> List[WorkMetadata]:
        """
        Get comprehensive list of all discovered works.
        
        Returns:
            List of all work metadata
        """
        logger.info("Getting comprehensive work list")
        
        # Discover all sources
        valid_sources = await self.discover_sources()
        
        # Catalog works from all sources
        all_works = []
        for source in valid_sources:
            works = await self.catalog_works(source)
            all_works.extend(works)
        
        # Save discovery data
        self._save_discovery_data()
        
        logger.info(f"Comprehensive work list: {len(all_works)} works from {len(valid_sources)} sources")
        return all_works
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about source discovery."""
        stats = {
            'total_sources': len(self.sources_config),
            'enabled_sources': sum(1 for s in self.sources_config.values() if s.enabled),
            'total_works': len(self.known_works),
            'sources': {}
        }
        
        for source_type, config in self.sources_config.items():
            stats['sources'][source_type.value] = {
                'name': config.name,
                'enabled': config.enabled,
                'works_count': config.works_count,
                'success_rate': config.success_rate,
                'error_count': config.error_count,
                'last_checked': config.last_checked.isoformat() if config.last_checked else None
            }
        
        return stats
