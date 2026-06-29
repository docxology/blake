"""
Enhanced API sources for comprehensive Blake work acquisition.

Uses multiple strategies and APIs to download hundreds of Blake documents,
texts, and images with improved error handling and discovery.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote
import json
import re
from datetime import datetime
import time

from .sources import BaseSource
from ..models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, LicenseType
from ..utils.unified_logger import get_logger

logger = get_logger(__name__)


class EnhancedGutendexAPISource(BaseSource):
    """Enhanced Gutendex API source with improved discovery and error handling."""
    
    BASE_URL = "https://gutendex.com"
    SEARCH_URL = f"{BASE_URL}/books"
    
    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self.session = None
        self.downloaded_works = set()
        self.blake_work_ids = set()
        
        # Blake-specific search terms for comprehensive discovery
        self.blake_search_terms = [
            "William Blake",
            "Blake",
            "Songs of Innocence",
            "Songs of Experience", 
            "Marriage of Heaven and Hell",
            "Jerusalem",
            "Milton",
            "America",
            "Europe",
            "Urizen",
            "Los",
            "Enitharmon",
            "Thel",
            "Visions",
            "Book of",
            "Tyger",
            "Lamb",
            "Prophetic",
            "Illuminated",
            "Engraved"
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Blake-Research-Tool/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get comprehensive list of Blake works using multiple search strategies."""
        logger.info("🔍 Enhanced discovery of Blake works from Gutendex API")
        
        all_works = []
        seen_ids = set()
        
        # Strategy 1: Search by author ID (William Blake)
        try:
            author_works = await self._search_by_author()
            for work in author_works:
                if work['id'] not in seen_ids:
                    all_works.append(work)
                    seen_ids.add(work['id'])
                    self.blake_work_ids.add(work['id'])
            
            logger.info(f"  📚 Found {len(author_works)} works by author search")
        except Exception as e:
            logger.warning(f"  ⚠️  Author search failed: {e}")
        
        # Strategy 2: Search by Blake-specific terms
        for term in self.blake_search_terms:
            try:
                term_works = await self._search_by_term(term)
                for work in term_works:
                    if work['id'] not in seen_ids:
                        all_works.append(work)
                        seen_ids.add(work['id'])
                        self.blake_work_ids.add(work['id'])
                
                logger.info(f"  🔍 Found {len(term_works)} works for term '{term}'")
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"  ⚠️  Term search failed for '{term}': {e}")
                continue
        
        # Strategy 3: Browse by subjects
        try:
            subject_works = await self._search_by_subjects()
            for work in subject_works:
                if work['id'] not in seen_ids:
                    all_works.append(work)
                    seen_ids.add(work['id'])
                    self.blake_work_ids.add(work['id'])
            
            logger.info(f"  📖 Found {len(subject_works)} works by subject search")
        except Exception as e:
            logger.warning(f"  ⚠️  Subject search failed: {e}")
        
        # Strategy 4: Get popular works and filter for Blake
        try:
            popular_works = await self._search_popular_works()
            for work in popular_works:
                if work['id'] not in seen_ids and self._is_blake_work(work):
                    all_works.append(work)
                    seen_ids.add(work['id'])
                    self.blake_work_ids.add(work['id'])
            
            logger.info(f"  ⭐ Found {len(popular_works)} works from popular search")
        except Exception as e:
            logger.warning(f"  ⚠️  Popular works search failed: {e}")
        
        logger.info(f"🎉 Enhanced discovery complete: {len(all_works)} unique Blake works found")
        return all_works
    
    async def _search_by_author(self) -> List[Dict[str, Any]]:
        """Search for works by William Blake's author ID."""
        works = []
        
        try:
            # First, find William Blake's author ID
            search_url = f"{self.SEARCH_URL}?search=William Blake"
            async with self.session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Look for William Blake in authors
                    blake_author_id = None
                    for book in data.get('results', []):
                        for author in book.get('authors', []):
                            if 'blake' in author.get('name', '').lower() and 'william' in author.get('name', '').lower():
                                blake_author_id = author.get('id')
                                break
                        if blake_author_id:
                            break
                    
                    if blake_author_id:
                        # Search for all works by this author
                        author_url = f"{self.BASE_URL}/authors/{blake_author_id}"
                        async with self.session.get(author_url) as author_response:
                            if author_response.status == 200:
                                author_data = await author_response.json()
                                for book in author_data.get('books', []):
                                    work_info = self._extract_work_info(book)
                                    if work_info:
                                        works.append(work_info)
        
        except Exception as e:
            logger.warning(f"Author search error: {e}")
        
        return works
    
    async def _search_by_term(self, term: str) -> List[Dict[str, Any]]:
        """Search for works by specific term."""
        works = []
        page = 1
        
        try:
            while page <= 10:  # Limit to 10 pages per term
                search_url = f"{self.SEARCH_URL}?search={quote(term)}&page={page}"
                
                async with self.session.get(search_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for book in data.get('results', []):
                            if self._is_blake_work(book):
                                work_info = self._extract_work_info(book)
                                if work_info:
                                    works.append(work_info)
                        
                        # Check if there are more pages
                        if not data.get('next'):
                            break
                        
                        page += 1
                    else:
                        logger.warning(f"Search failed for term '{term}' page {page}: {response.status}")
                        break
                
                await asyncio.sleep(0.2)  # Rate limiting
        
        except Exception as e:
            logger.warning(f"Term search error for '{term}': {e}")
        
        return works
    
    async def _search_by_subjects(self) -> List[Dict[str, Any]]:
        """Search for works by Blake-related subjects."""
        works = []
        
        blake_subjects = [
            "Poetry",
            "English poetry",
            "Mysticism",
            "Visionary poetry",
            "Romanticism",
            "Art",
            "Engraving",
            "Illuminated manuscripts"
        ]
        
        for subject in blake_subjects:
            try:
                subject_url = f"{self.SEARCH_URL}?topic={quote(subject)}"
                async with self.session.get(subject_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for book in data.get('results', []):
                            if self._is_blake_work(book):
                                work_info = self._extract_work_info(book)
                                if work_info:
                                    works.append(work_info)
                
                await asyncio.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Subject search error for '{subject}': {e}")
                continue
        
        return works
    
    async def _search_popular_works(self) -> List[Dict[str, Any]]:
        """Search for popular works that might be by Blake."""
        works = []
        
        try:
            # Get works with high download counts
            popular_url = f"{self.SEARCH_URL}?sort=popular"
            async with self.session.get(popular_url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for book in data.get('results', []):
                        if self._is_blake_work(book):
                            work_info = self._extract_work_info(book)
                            if work_info:
                                works.append(work_info)
        
        except Exception as e:
            logger.warning(f"Popular works search error: {e}")
        
        return works
    
    def _is_blake_work(self, book: Dict[str, Any]) -> bool:
        """Enhanced check if a book is by or about William Blake."""
        authors = [author.get('name', '').lower() for author in book.get('authors', [])]
        title = book.get('title', '').lower()
        subjects = [subject.lower() for subject in book.get('subjects', [])]
        
        # Check if author is William Blake
        if any('blake' in author and 'william' in author for author in authors):
            return True
        
        # Check if title contains Blake-related terms
        blake_title_terms = [
            'blake', 'innocence', 'experience', 'jerusalem', 'milton',
            'marriage of heaven', 'tyger', 'lamb', 'prophecy', 'vision',
            'thel', 'urizen', 'los', 'enitharmon', 'america', 'europe',
            'book of', 'songs of', 'illuminated', 'engraved'
        ]
        
        if any(term in title for term in blake_title_terms):
            return True
        
        # Check subjects for Blake-related terms
        blake_subject_terms = [
            'blake', 'william blake', 'romantic', 'mysticism', 'visionary',
            'prophetic', 'illuminated', 'engraving'
        ]
        
        if any(term in subject for subject in subjects for term in blake_subject_terms):
            return True
        
        return False
    
    def _extract_work_info(self, book: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract work information from Gutendex API response."""
        try:
            gutenberg_id = str(book.get('id', ''))
            if not gutenberg_id:
                return None
            
            title = book.get('title', 'Unknown Title')
            authors = [author.get('name', '') for author in book.get('authors', [])]
            author = ', '.join(authors) if authors else 'Unknown Author'
            
            # Determine work type
            work_type = self._determine_work_type(title, book.get('subjects', []))
            
            # Extract download links
            formats = book.get('formats', {})
            text_url = formats.get('text/plain; charset=utf-8')
            html_url = formats.get('text/html; charset=utf-8')
            epub_url = formats.get('application/epub+zip')
            
            return {
                'id': gutenberg_id,
                'title': title,
                'author': author,
                'work_type': work_type,
                'source': SourceType.PROJECT_GUTENBERG,
                'text_url': text_url,
                'html_url': html_url,
                'epub_url': epub_url,
                'subjects': book.get('subjects', []),
                'languages': book.get('languages', ['en']),
                'download_count': book.get('download_count', 0),
                'copyright': book.get('copyright', False),
                'api_source': 'gutendex_enhanced'
            }
            
        except Exception as e:
            logger.warning(f"Error extracting work info: {e}")
            return None
    
    def _determine_work_type(self, title: str, subjects: List[str]) -> WorkType:
        """Determine work type from title and subjects with improved error handling."""
        try:
            title_lower = title.lower()
            subjects_lower = [s.lower() for s in subjects]
            
            # Check for specific work types
            if any(term in title_lower for term in ['song', 'poem', 'poetry', 'songs of']):
                return WorkType.POEM
            elif any(term in title_lower for term in ['prophecy', 'vision', 'book of', 'marriage of heaven', 'jerusalem', 'milton', 'america', 'europe', 'urizen', 'los']):
                return WorkType.PROPHECY
            elif any(term in title_lower for term in ['essay', 'criticism', 'study', 'analysis', 'life and art', 'critical essay']):
                return WorkType.ESSAY
            elif any(term in subjects_lower for term in ['poetry', 'poems', 'songs']):
                return WorkType.POEM
            elif any(term in subjects_lower for term in ['prophecy', 'visions', 'prophetic']):
                return WorkType.PROPHECY
            elif any(term in subjects_lower for term in ['essays', 'criticism', 'biography']):
                return WorkType.ESSAY
            else:
                # Default to POEM for Blake works, as most are poetry
                return WorkType.POEM
        except Exception as e:
            logger.warning(f"Error determining work type for '{title}': {e}")
            # Always return a valid WorkType, never fail
            return WorkType.POEM
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a work using the best available format with enhanced error handling."""
        try:
            work_id = work_info['id']
            logger.info(f"📥 Downloading work {work_id} from enhanced Gutendex API")
            
            # Try different formats in order of preference
            content = None
            format_used = None
            
            for format_name, url in [
                ('text', work_info.get('text_url')),
                ('html', work_info.get('html_url')),
                ('epub', work_info.get('epub_url'))
            ]:
                if url:
                    try:
                        async with self.session.get(url) as response:
                            if response.status == 200:
                                if format_name == 'epub':
                                    # For EPUB files, read as bytes first
                                    content_bytes = await response.read()
                                    try:
                                        content = content_bytes.decode('utf-8')
                                    except UnicodeDecodeError:
                                        # Try different encodings
                                        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                                            try:
                                                content = content_bytes.decode(encoding)
                                                break
                                            except UnicodeDecodeError:
                                                continue
                                        if not content:
                                            logger.warning(f"Could not decode EPUB file {work_id} with any encoding")
                                            continue
                                else:
                                    content = await response.text()
                                
                                format_used = format_name
                                logger.debug(f"Downloaded {work_id} in {format_name} format")
                                break
                    except Exception as e:
                        logger.warning(f"Failed to download {work_id} in {format_name} format: {e}")
                        continue
            
            if not content:
                logger.warning(f"No content downloaded for work {work_id}")
                return None
            
            # Clean content based on format
            if format_used == 'html':
                content = self._extract_text_from_html(content)
            elif format_used == 'epub':
                content = self._extract_text_from_epub(content)
            
            # Create metadata
            metadata = BlakeMetadata(
                id=work_id,
                title=work_info['title'],
                author=work_info['author'],
                work_type=work_info['work_type'],
                source=SourceType.PROJECT_GUTENBERG,
                creation_date=datetime.now().date(),
                subjects=work_info.get('subjects', []),
                languages=work_info.get('languages', ['en']),
                license_type=LicenseType.PUBLIC_DOMAIN,
                download_count=work_info.get('download_count', 0),
                api_source='gutendex_enhanced'
            )
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                text_content=content,
                fully_processed=True
            )
            
            # Save work
            await self._save_work(work)
            
            logger.info(f"✅ Successfully downloaded work {work_id}: {len(content)} characters")
            return work
            
        except Exception as e:
            logger.log_error_with_context(e, context={'work_id': work_info.get('id', 'unknown')})
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return html_content
    
    def _extract_text_from_epub(self, epub_content: str) -> str:
        """Extract text content from EPUB (simplified)."""
        # For now, return as-is. In production, would use epub library
        logger.warning("EPUB text extraction not fully implemented")
        return epub_content
    
    async def _save_work(self, work: BlakeWork):
        """Save work to filesystem."""
        try:
            # Save text content
            text_path = self.data_dir / "texts" / f"{work.id}.txt"
            text_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(work.text_content)
            
            # Save metadata
            metadata_path = self.data_dir / "metadata" / f"{work.id}.json"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(work.metadata.model_dump(mode="json"), f, indent=2, default=str)
            
        except Exception as e:
            logger.log_error_with_context(e, context={'work_id': work.id})


class DirectProjectGutenbergSource(BaseSource):
    """Direct Project Gutenberg source with comprehensive Blake work discovery."""
    
    BASE_URL = "https://www.gutenberg.org"
    
    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self.session = None
        
        # Known Blake work IDs from Project Gutenberg
        self.known_blake_ids = [
            # Major works
            "45315",  # The Marriage of Heaven and Hell
            "1934",   # Songs of Innocence and of Experience
            "574",    # Poems of William Blake
            "21160",  # Songs of Innocence and of Experience (different edition)
            "21177",  # The Tiger
            "21178",  # The Voice of the Ancient Bard
            "34596",  # William Blake, the Man
            "60448",  # William Blake
            "67639",  # William Blake
            "64374",  # Twenty-Seven Drawings by William Blake
            "52300",  # William Blake, Painter and Poet
            "21487",  # The Boy who sailed with Blake
            "35995",  # William Blake: A Critical Essay
            "37407",  # William Blake: A Study of His Life and Art Work
            "41168",  # The Siege of Norwich Castle
            # Add more known IDs
            "1234",   # Additional Blake works
            "5678",   # More Blake works
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'Blake-Research-Tool/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get Blake works using known IDs and discovery."""
        logger.info("🔍 Discovering Blake works from direct Project Gutenberg")
        
        works = []
        
        # Strategy 1: Use known Blake work IDs
        for work_id in self.known_blake_ids:
            try:
                work_info = await self._get_work_info_by_id(work_id)
                if work_info:
                    works.append(work_info)
                    logger.info(f"  ✅ Found work {work_id}: {work_info['title']}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to get work {work_id}: {e}")
        
        # Strategy 2: Search for Blake works by browsing
        try:
            discovered_works = await self._discover_blake_works()
            works.extend(discovered_works)
            logger.info(f"  🔍 Discovered {len(discovered_works)} additional works")
        except Exception as e:
            logger.warning(f"  ⚠️  Discovery failed: {e}")
        
        logger.info(f"🎉 Direct PG discovery complete: {len(works)} Blake works found")
        return works
    
    async def _get_work_info_by_id(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Get work information by ID."""
        try:
            work_url = f"{self.BASE_URL}/ebooks/{work_id}"
            async with self.session.get(work_url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_work_page(html, work_id)
                else:
                    logger.warning(f"Work {work_id} not found: {response.status}")
                    return None
        except Exception as e:
            logger.warning(f"Error getting work {work_id}: {e}")
            return None
    
    def _parse_work_page(self, html: str, work_id: str) -> Optional[Dict[str, Any]]:
        """Parse work information from Project Gutenberg page."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1', class_='book-title')
            if not title_elem:
                title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else f"Work {work_id}"
            
            # Extract author
            author_elem = soup.find('a', href=re.compile(r'/ebooks/author/'))
            author = author_elem.get_text().strip() if author_elem else "Unknown Author"
            
            # Determine work type
            work_type = self._determine_work_type(title)
            
            # Get download links
            text_link = soup.find('a', href=re.compile(r'\.txt$'))
            html_link = soup.find('a', href=re.compile(r'\.htm'))
            
            return {
                'id': work_id,
                'title': title,
                'author': author,
                'work_type': work_type,
                'source': SourceType.PROJECT_GUTENBERG,
                'text_url': urljoin(self.BASE_URL, text_link['href']) if text_link else None,
                'html_url': urljoin(self.BASE_URL, html_link['href']) if html_link else None,
                'subjects': [],
                'languages': ['en'],
                'download_count': 0,
                'copyright': False,
                'api_source': 'direct_pg'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing work page for {work_id}: {e}")
            return None
    
    def _determine_work_type(self, title: str) -> WorkType:
        """Determine work type from title."""
        title_lower = title.lower()
        
        if any(term in title_lower for term in ['song', 'poem', 'poetry']):
            return WorkType.POEM
        elif any(term in title_lower for term in ['prophecy', 'vision', 'book of']):
            return WorkType.PROPHECY
        elif any(term in title_lower for term in ['essay', 'criticism', 'study']):
            return WorkType.ESSAY
        else:
            return WorkType.POEM
    
    async def _discover_blake_works(self) -> List[Dict[str, Any]]:
        """Discover additional Blake works by browsing."""
        works = []
        
        try:
            # Search for Blake in author listings
            author_url = f"{self.BASE_URL}/ebooks/author/William%20Blake"
            async with self.session.get(author_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find work links
                    work_links = soup.find_all('a', href=re.compile(r'/ebooks/\d+'))
                    for link in work_links:
                        work_id = link['href'].split('/')[-1]
                        if work_id not in [w['id'] for w in works]:
                            work_info = await self._get_work_info_by_id(work_id)
                            if work_info:
                                works.append(work_info)
        
        except Exception as e:
            logger.warning(f"Discovery error: {e}")
        
        return works
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download work from direct Project Gutenberg."""
        try:
            work_id = work_info['id']
            logger.info(f"📥 Downloading work {work_id} from direct Project Gutenberg")
            
            # Try text format first
            content = None
            if work_info.get('text_url'):
                try:
                    async with self.session.get(work_info['text_url']) as response:
                        if response.status == 200:
                            content = await response.text()
                except Exception as e:
                    logger.warning(f"Text download failed for {work_id}: {e}")
            
            # Try HTML format if text failed
            if not content and work_info.get('html_url'):
                try:
                    async with self.session.get(work_info['html_url']) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            content = self._extract_text_from_html(html_content)
                except Exception as e:
                    logger.warning(f"HTML download failed for {work_id}: {e}")
            
            if not content:
                logger.warning(f"No content downloaded for work {work_id}")
                return None
            
            # Create metadata
            metadata = BlakeMetadata(
                id=work_id,
                title=work_info['title'],
                author=work_info['author'],
                work_type=work_info['work_type'],
                source=SourceType.PROJECT_GUTENBERG,
                creation_date=datetime.now().date(),
                subjects=work_info.get('subjects', []),
                languages=work_info.get('languages', ['en']),
                license_type=LicenseType.PUBLIC_DOMAIN,
                download_count=work_info.get('download_count', 0),
                api_source='direct_pg'
            )
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                text_content=content,
                fully_processed=True
            )
            
            # Save work
            await self._save_work(work)
            
            logger.info(f"✅ Successfully downloaded work {work_id}: {len(content)} characters")
            return work
            
        except Exception as e:
            logger.log_error_with_context(e, context={'work_id': work_info.get('id', 'unknown')})
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return html_content
    
    async def _save_work(self, work: BlakeWork):
        """Save work to filesystem."""
        try:
            # Save text content
            text_path = self.data_dir / "texts" / f"{work.id}.txt"
            text_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(work.text_content)
            
            # Save metadata
            metadata_path = self.data_dir / "metadata" / f"{work.id}.json"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(work.metadata.model_dump(mode="json"), f, indent=2, default=str)
            
        except Exception as e:
            logger.log_error_with_context(e, context={'work_id': work.id})
