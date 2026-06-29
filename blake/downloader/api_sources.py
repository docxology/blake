"""
API-based sources for comprehensive Blake work acquisition.

Uses multiple Project Gutenberg APIs and other web resources to download
hundreds of documents, texts, and images.
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re
from datetime import datetime

from .sources import BaseSource
from ..models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, LicenseType

logger = logging.getLogger(__name__)


class GutendexAPISource(BaseSource):
    """Gutendex API source for comprehensive Project Gutenberg access."""
    
    BASE_URL = "https://gutendex.com"
    SEARCH_URL = f"{BASE_URL}/books"
    
    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self.session = None
        self.downloaded_works = set()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get comprehensive list of Blake works using Gutendex API."""
        logger.info("Fetching Blake works from Gutendex API")
        
        works = []
        page = 1
        
        while True:
            try:
                # Search for Blake works with multiple search terms
                search_terms = [
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
                    "Enitharmon"
                ]
                
                for search_term in search_terms:
                    url = f"{self.SEARCH_URL}?search={search_term}&page={page}"
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for book in data.get('results', []):
                                if self._is_blake_work(book):
                                    work_info = self._extract_work_info(book)
                                    if work_info and work_info['id'] not in self.downloaded_works:
                                        works.append(work_info)
                                        self.downloaded_works.add(work_info['id'])
                            
                            # Check if there are more pages
                            if not data.get('next'):
                                break
                        else:
                            logger.warning(f"Failed to fetch page {page}: {response.status}")
                            break
                
                page += 1
                if page > 50:  # Safety limit
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching from Gutendex API: {e}")
                break
        
        # Remove duplicates
        unique_works = []
        seen_ids = set()
        for work in works:
            if work['id'] not in seen_ids:
                unique_works.append(work)
                seen_ids.add(work['id'])
        
        logger.info(f"Found {len(unique_works)} unique Blake works from Gutendex API")
        return unique_works
    
    def _is_blake_work(self, book: Dict[str, Any]) -> bool:
        """Check if a book is by or about William Blake."""
        authors = [author.get('name', '').lower() for author in book.get('authors', [])]
        title = book.get('title', '').lower()
        
        # Check if author is William Blake
        if any('blake' in author and 'william' in author for author in authors):
            return True
        
        # Check if title contains Blake-related terms
        blake_terms = [
            'blake', 'innocence', 'experience', 'jerusalem', 'milton',
            'marriage of heaven', 'tyger', 'lamb', 'prophecy', 'vision'
        ]
        
        if any(term in title for term in blake_terms):
            return True
        
        # Check subjects for Blake-related terms
        subjects = [subject.lower() for subject in book.get('subjects', [])]
        if any('blake' in subject for subject in subjects):
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
                'api_source': 'gutendex'
            }
            
        except Exception as e:
            logger.error(f"Error extracting work info: {e}")
            return None
    
    def _determine_work_type(self, title: str, subjects: List[str]) -> WorkType:
        """Determine work type from title and subjects."""
        try:
            title_lower = title.lower()
            subjects_lower = [s.lower() for s in subjects]
            
            # Check for specific work types
            if any(term in title_lower for term in ['song', 'poem', 'poetry']):
                return WorkType.POEM
            elif any(term in title_lower for term in ['prophecy', 'vision', 'book']):
                return WorkType.PROPHECY
            elif any(term in title_lower for term in ['essay', 'criticism', 'study']):
                return WorkType.ESSAY
            elif any(term in subjects_lower for term in ['poetry', 'poems']):
                return WorkType.POEM
            elif any(term in subjects_lower for term in ['prophecy', 'visions']):
                return WorkType.PROPHECY
            else:
                return WorkType.POEM  # Default fallback
        except Exception as e:
            logger.warning(f"Error determining work type for '{title}': {e}")
            return WorkType.POEM  # Safe fallback
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a work using the best available format."""
        try:
            work_id = work_info['id']
            logger.info(f"Downloading work {work_id} from Gutendex API")
            
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
                api_source='gutendex'
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
            
            logger.info(f"Successfully downloaded work {work_id}: {len(content)} characters")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_info.get('id', 'unknown')}: {e}")
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
            logger.error(f"Error saving work {work.id}: {e}")


class ProjectGutenbergAPISource(BaseSource):
    """Direct Project Gutenberg API source."""
    
    BASE_URL = "https://www.gutenberg.org"
    API_URL = "https://gutengerg.org/api"
    
    def __init__(self, data_dir: Path):
        super().__init__(data_dir)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get Blake works from Project Gutenberg API."""
        logger.info("Fetching Blake works from Project Gutenberg API")
        
        works = []
        
        try:
            # Search for Blake works
            search_url = f"{self.API_URL}/books"
            params = {
                'search': 'William Blake',
                'format': 'json'
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for book in data.get('books', []):
                        if self._is_blake_work(book):
                            work_info = self._extract_work_info(book)
                            if work_info:
                                works.append(work_info)
                
        except Exception as e:
            logger.error(f"Error fetching from Project Gutenberg API: {e}")
        
        logger.info(f"Found {len(works)} Blake works from Project Gutenberg API")
        return works
    
    def _is_blake_work(self, book: Dict[str, Any]) -> bool:
        """Check if book is by or about William Blake."""
        # Implementation similar to GutendexAPISource
        return True  # Simplified for now
    
    def _extract_work_info(self, book: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract work information from Project Gutenberg API response."""
        # Implementation similar to GutendexAPISource
        return None  # Simplified for now
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download work from Project Gutenberg API."""
        # Implementation similar to GutendexAPISource
        return None  # Simplified for now


class ImageDownloader:
    """Download images associated with Blake works."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.session = None
        self.image_dir = data_dir / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def download_images_for_work(self, work_id: str, work_title: str) -> List[BlakeImage]:
        """Download images associated with a specific work."""
        images = []
        
        try:
            # Search for images in Project Gutenberg
            image_urls = await self._find_image_urls(work_id, work_title)
            
            for i, url in enumerate(image_urls):
                try:
                    image_path = self.image_dir / f"{work_id}_{i:03d}.jpg"
                    
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            
                            with open(image_path, 'wb') as f:
                                f.write(content)
                            
                            # Create BlakeImage
                            image = BlakeImage(
                                id=f"{work_id}_{i:03d}",
                                metadata_id=work_id,
                                title=f"{work_title} - Image {i+1}",
                                file_path=image_path,
                                original_url=url
                            )
                            
                            images.append(image)
                            logger.info(f"Downloaded image {image_path.name}")
                
                except Exception as e:
                    logger.warning(f"Failed to download image {url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error downloading images for work {work_id}: {e}")
        
        return images
    
    async def _find_image_urls(self, work_id: str, work_title: str) -> List[str]:
        """Find image URLs for a work."""
        image_urls = []
        
        try:
            # Check Project Gutenberg for images
            pg_url = f"https://www.gutenberg.org/files/{work_id}/"
            
            async with self.session.get(pg_url) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Find image links
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            full_url = urljoin(pg_url, href)
                            image_urls.append(full_url)
        
        except Exception as e:
            logger.warning(f"Error finding images for work {work_id}: {e}")
        
        return image_urls
