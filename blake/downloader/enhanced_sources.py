"""
Enhanced Source Downloaders

Comprehensive, modular downloaders for all available sources
with support for multiple formats and robust error handling.
"""

import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import re
from urllib.parse import urljoin, urlparse
import hashlib

from .scraper import WebScraper
from ..models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, LicenseType

logger = logging.getLogger(__name__)


class BaseSourceDownloader:
    """Base class for all source downloaders."""
    
    def __init__(self, data_dir: Path, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the downloader."""
        self.data_dir = data_dir
        self.session = session or aiohttp.ClientSession()
        self.scraper = WebScraper(data_dir)
        self.rate_limit_delay = 1.0  # Default rate limit
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.session.close()
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of available works."""
        raise NotImplementedError
        
    async def download_work(self, work_id: str) -> Optional[BlakeWork]:
        """Download a specific work."""
        raise NotImplementedError
        
    async def _rate_limit(self):
        """Apply rate limiting."""
        await asyncio.sleep(self.rate_limit_delay)


class EnhancedProjectGutenbergDownloader(BaseSourceDownloader):
    """Enhanced Project Gutenberg downloader with comprehensive format support."""
    
    def __init__(self, data_dir: Path, session: Optional[aiohttp.ClientSession] = None):
        super().__init__(data_dir, session)
        self.base_url = "https://www.gutenberg.org"
        self.api_url = "https://www.gutenberg.org/ebooks/search/?query=William+Blake&submit_search=on"
        self.rate_limit_delay = 0.5  # Be respectful to PG
        
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get comprehensive list of Blake works from Project Gutenberg."""
        logger.info("Fetching comprehensive work list from Project Gutenberg")
        
        works = []
        
        try:
            # Search for William Blake works
            async with self.session.get(self.api_url) as response:
                if response.status == 200:
                    content = await response.text()
                    works.extend(self._parse_search_results(content))
            
            # Also try direct author search
            author_url = "https://www.gutenberg.org/ebooks/author/William+Blake"
            async with self.session.get(author_url) as response:
                if response.status == 200:
                    content = await response.text()
                    works.extend(self._parse_author_page(content))
            
            # Remove duplicates
            seen_ids = set()
            unique_works = []
            for work in works:
                if work['id'] not in seen_ids:
                    seen_ids.add(work['id'])
                    unique_works.append(work)
            
            logger.info(f"Found {len(unique_works)} Blake works in Project Gutenberg")
            return unique_works
            
        except Exception as e:
            logger.error(f"Error fetching work list from Project Gutenberg: {e}")
            return []
    
    def _parse_search_results(self, content: str) -> List[Dict[str, Any]]:
        """Parse search results from Project Gutenberg."""
        works = []
        
        # Look for work entries in search results
        work_pattern = r'<li class="booklink">.*?<a href="/ebooks/(\d+)".*?>(.*?)</a>'
        matches = re.findall(work_pattern, content, re.DOTALL)
        
        for work_id, title in matches:
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            title = re.sub(r'\s+', ' ', title)
            
            works.append({
                'id': work_id,
                'title': title,
                'url': f"{self.base_url}/ebooks/{work_id}",
                'source': 'project_gutenberg'
            })
        
        return works
    
    def _parse_author_page(self, content: str) -> List[Dict[str, Any]]:
        """Parse author page from Project Gutenberg."""
        works = []
        
        # Look for work entries in author page
        work_pattern = r'<li class="booklink">.*?<a href="/ebooks/(\d+)".*?>(.*?)</a>'
        matches = re.findall(work_pattern, content, re.DOTALL)
        
        for work_id, title in matches:
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            title = re.sub(r'\s+', ' ', title)
            
            works.append({
                'id': work_id,
                'title': title,
                'url': f"{self.base_url}/ebooks/{work_id}",
                'source': 'project_gutenberg'
            })
        
        return works
    
    async def download_work(self, work_id: str) -> Optional[BlakeWork]:
        """Download a work with support for multiple formats."""
        logger.info(f"Downloading work from Project Gutenberg: {work_id}")
        
        try:
            await self._rate_limit()
            
            # Get work details page
            work_url = f"{self.base_url}/ebooks/{work_id}"
            async with self.session.get(work_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to access work {work_id}: {response.status}")
                    return None
                
                content = await response.text()
            
            # Parse work details
            work_info = self._parse_work_details(content, work_id)
            if not work_info:
                return None
            
            # Try to download in multiple formats
            text_content = None
            images = []
            
            # Try plain text first
            text_content = await self._download_text_format(work_id)
            
            # Try HTML format for better structure
            if not text_content:
                text_content = await self._download_html_format(work_id)
            
            # Try EPUB format
            if not text_content:
                text_content = await self._download_epub_format(work_id)
            
            # Download images if available
            images = await self._download_images(work_id, work_url)
            
            # Create BlakeWork object
            work = BlakeWork(
                id=work_id,
                metadata=BlakeMetadata(
                    id=work_id,
                    title=work_info['title'],
                    work_type=work_info['work_type'],
                    creation_date=work_info.get('creation_date'),
                    publication_date=work_info.get('publication_date'),
                    description=work_info.get('description'),
                    source=SourceType.PROJECT_GUTENBERG,
                    source_url=work_url,
                    source_id=work_id,
                    license_type=LicenseType.PUBLIC_DOMAIN,
                    attribution="Project Gutenberg",
                    usage_terms="Public Domain"
                ),
                text_content=text_content,
                images=images,
                fully_processed=bool(text_content or images)
            )
            
            logger.info(f"Successfully downloaded work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_id}: {e}")
            return None
    
    def _parse_work_details(self, content: str, work_id: str) -> Optional[Dict[str, Any]]:
        """Parse work details from Project Gutenberg page."""
        try:
            # Extract title
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
            title = title_match.group(1).strip() if title_match else f"Work {work_id}"
            
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            title = re.sub(r'\s+', ' ', title)
            
            # Determine work type
            work_type = WorkType.POEM
            if any(word in title.lower() for word in ['prophecy', 'vision', 'marriage']):
                work_type = WorkType.PROPHECY
            elif any(word in title.lower() for word in ['song', 'poem', 'poetry']):
                work_type = WorkType.POEM
            elif any(word in title.lower() for word in ['drawing', 'painting', 'illustration']):
                work_type = WorkType.ILLUSTRATION
            
            # Extract description
            description = None
            desc_match = re.search(r'<p[^>]*>(.*?)</p>', content)
            if desc_match:
                description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
            
            return {
                'title': title,
                'work_type': work_type,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error parsing work details for {work_id}: {e}")
            return None
    
    async def _download_text_format(self, work_id: str) -> Optional[str]:
        """Download work in plain text format."""
        try:
            text_url = f"{self.base_url}/files/{work_id}/{work_id}-0.txt"
            async with self.session.get(text_url) as response:
                if response.status == 200:
                    content = await response.text()
                    # Save to file
                    text_file = self.data_dir / "texts" / f"{work_id}.txt"
                    text_file.parent.mkdir(parents=True, exist_ok=True)
                    text_file.write_text(content, encoding='utf-8')
                    return content
        except Exception as e:
            logger.debug(f"Plain text not available for {work_id}: {e}")
        return None
    
    async def _download_html_format(self, work_id: str) -> Optional[str]:
        """Download work in HTML format and extract text."""
        try:
            html_url = f"{self.base_url}/files/{work_id}/{work_id}-h/{work_id}-h.htm"
            async with self.session.get(html_url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    # Extract text from HTML
                    text_content = self._extract_text_from_html(html_content)
                    if text_content:
                        # Save to file
                        text_file = self.data_dir / "texts" / f"{work_id}.txt"
                        text_file.parent.mkdir(parents=True, exist_ok=True)
                        text_file.write_text(text_content, encoding='utf-8')
                        return text_content
        except Exception as e:
            logger.debug(f"HTML format not available for {work_id}: {e}")
        return None
    
    async def _download_epub_format(self, work_id: str) -> Optional[str]:
        """Download work in EPUB format and extract text."""
        try:
            epub_url = f"{self.base_url}/ebooks/{work_id}.epub.noimages"
            async with self.session.get(epub_url) as response:
                if response.status == 200:
                    epub_content = await response.read()
                    # For now, just save the EPUB file
                    epub_file = self.data_dir / "texts" / f"{work_id}.epub"
                    epub_file.parent.mkdir(parents=True, exist_ok=True)
                    epub_file.write_bytes(epub_content)
                    # TODO: Extract text from EPUB
                    return f"EPUB file saved: {epub_file}"
        except Exception as e:
            logger.debug(f"EPUB format not available for {work_id}: {e}")
        return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        # Remove script and style elements
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # Extract text from HTML tags
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Clean up whitespace
        text_content = re.sub(r'\s+', ' ', text_content)
        text_content = text_content.strip()
        
        return text_content
    
    async def _download_images(self, work_id: str, work_url: str) -> List[BlakeImage]:
        """Download images associated with the work."""
        images = []
        
        try:
            # Look for image links in the work page
            async with self.session.get(work_url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Find image URLs
                    image_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
                    image_matches = re.findall(image_pattern, content)
                    
                    for img_url in image_matches:
                        if not img_url.startswith('http'):
                            img_url = urljoin(work_url, img_url)
                        
                        # Download image
                        try:
                            async with self.session.get(img_url) as img_response:
                                if img_response.status == 200:
                                    img_data = await img_response.read()
                                    
                                    # Save image
                                    img_filename = f"{work_id}_{len(images)}.jpg"
                                    img_file = self.data_dir / "images" / img_filename
                                    img_file.parent.mkdir(parents=True, exist_ok=True)
                                    img_file.write_bytes(img_data)
                                    
                                    # Create BlakeImage object
                                    image = BlakeImage(
                                        id=f"{work_id}_img_{len(images)}",
                                        metadata_id=work_id,
                                        title=img_filename,
                                        file_path=img_file,
                                        original_url=img_url
                                    )
                                    images.append(image)
                                    
                        except Exception as e:
                            logger.debug(f"Error downloading image {img_url}: {e}")
                            
        except Exception as e:
            logger.debug(f"Error downloading images for {work_id}: {e}")
        
        return images


class EnhancedBlakeArchiveDownloader(BaseSourceDownloader):
    """Enhanced Blake Archive downloader."""
    
    def __init__(self, data_dir: Path, session: Optional[aiohttp.ClientSession] = None):
        super().__init__(data_dir, session)
        self.base_url = "https://blakearchive.org"
        self.rate_limit_delay = 1.0
        
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of works from Blake Archive."""
        logger.info("Fetching work list from Blake Archive")
        
        works = []
        
        try:
            # Try different Blake Archive endpoints
            endpoints = [
                "/works",
                "/browse",
                "/search"
            ]
            
            for endpoint in endpoints:
                url = f"{self.base_url}{endpoint}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        works.extend(self._parse_blake_archive_results(content))
                        break
            
            logger.info(f"Found {len(works)} works in Blake Archive")
            return works
            
        except Exception as e:
            logger.error(f"Error fetching work list from Blake Archive: {e}")
            return []
    
    def _parse_blake_archive_results(self, content: str) -> List[Dict[str, Any]]:
        """Parse results from Blake Archive."""
        works = []
        
        # Look for work entries
        work_pattern = r'<a[^>]*href="(/works/[^"]*)"[^>]*>(.*?)</a>'
        matches = re.findall(work_pattern, content, re.DOTALL)
        
        for work_url, title in matches:
            work_id = work_url.split('/')[-1]
            title = re.sub(r'<[^>]+>', '', title).strip()
            
            works.append({
                'id': work_id,
                'title': title,
                'url': f"{self.base_url}{work_url}",
                'source': 'blake_archive'
            })
        
        return works
    
    async def download_work(self, work_id: str) -> Optional[BlakeWork]:
        """Download a work from Blake Archive."""
        logger.info(f"Downloading work from Blake Archive: {work_id}")
        
        try:
            await self._rate_limit()
            
            work_url = f"{self.base_url}/works/{work_id}"
            async with self.session.get(work_url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to access work {work_id}: {response.status}")
                    return None
                
                content = await response.text()
            
            # Parse work details
            work_info = self._parse_work_details(content, work_id)
            if not work_info:
                return None
            
            # Download text content
            text_content = await self._download_text_content(work_id, work_url)
            
            # Download images
            images = await self._download_images(work_id, work_url)
            
            # Create BlakeWork object
            work = BlakeWork(
                id=work_id,
                metadata=BlakeMetadata(
                    id=work_id,
                    title=work_info['title'],
                    work_type=work_info['work_type'],
                    creation_date=work_info.get('creation_date'),
                    description=work_info.get('description'),
                    source=SourceType.BLAKE_ARCHIVE,
                    source_url=work_url,
                    source_id=work_id,
                    license_type=LicenseType.ACADEMIC_USE,
                    attribution="Blake Archive"
                ),
                text_content=text_content,
                images=images,
                fully_processed=bool(text_content or images)
            )
            
            logger.info(f"Successfully downloaded work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_id}: {e}")
            return None
    
    def _parse_work_details(self, content: str, work_id: str) -> Optional[Dict[str, Any]]:
        """Parse work details from Blake Archive page."""
        try:
            # Extract title
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
            title = title_match.group(1).strip() if title_match else f"Work {work_id}"
            
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            
            # Determine work type
            work_type = WorkType.POEM
            if any(word in title.lower() for word in ['prophecy', 'vision']):
                work_type = WorkType.PROPHECY
            elif any(word in title.lower() for word in ['drawing', 'painting']):
                work_type = WorkType.ILLUSTRATION
            
            return {
                'title': title,
                'work_type': work_type
            }
            
        except Exception as e:
            logger.error(f"Error parsing work details for {work_id}: {e}")
            return None
    
    async def _download_text_content(self, work_id: str, work_url: str) -> Optional[str]:
        """Download text content from Blake Archive."""
        try:
            # Look for text content in the work page
            async with self.session.get(work_url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Extract text content
                    text_content = self._extract_text_from_html(content)
                    
                    if text_content:
                        # Save to file
                        text_file = self.data_dir / "texts" / f"{work_id}.txt"
                        text_file.parent.mkdir(parents=True, exist_ok=True)
                        text_file.write_text(text_content, encoding='utf-8')
                        return text_content
                        
        except Exception as e:
            logger.debug(f"Error downloading text content for {work_id}: {e}")
        
        return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        # Remove script and style elements
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # Extract text from HTML tags
        text_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Clean up whitespace
        text_content = re.sub(r'\s+', ' ', text_content)
        text_content = text_content.strip()
        
        return text_content
    
    async def _download_images(self, work_id: str, work_url: str) -> List[BlakeImage]:
        """Download images from Blake Archive."""
        images = []
        
        try:
            async with self.session.get(work_url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Find image URLs
                    image_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
                    image_matches = re.findall(image_pattern, content)
                    
                    for img_url in image_matches:
                        if not img_url.startswith('http'):
                            img_url = urljoin(work_url, img_url)
                        
                        # Download image
                        try:
                            async with self.session.get(img_url) as img_response:
                                if img_response.status == 200:
                                    img_data = await img_response.read()
                                    
                                    # Save image
                                    img_filename = f"{work_id}_{len(images)}.jpg"
                                    img_file = self.data_dir / "images" / img_filename
                                    img_file.parent.mkdir(parents=True, exist_ok=True)
                                    img_file.write_bytes(img_data)
                                    
                                    # Create BlakeImage object
                                    image = BlakeImage(
                                        id=f"{work_id}_img_{len(images)}",
                                        metadata_id=work_id,
                                        title=img_filename,
                                        file_path=img_file,
                                        original_url=img_url
                                    )
                                    images.append(image)
                                    
                        except Exception as e:
                            logger.debug(f"Error downloading image {img_url}: {e}")
                            
        except Exception as e:
            logger.debug(f"Error downloading images for {work_id}: {e}")
        
        return images


class MuseumAPIDownloader(BaseSourceDownloader):
    """Downloader for museum APIs (British Museum, Tate, etc.)."""
    
    def __init__(self, data_dir: Path, session: Optional[aiohttp.ClientSession] = None):
        super().__init__(data_dir, session)
        self.rate_limit_delay = 2.0  # Be very respectful to museum APIs
        
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of works from museum APIs."""
        logger.info("Fetching work list from museum APIs")
        
        works = []
        
        # British Museum API
        try:
            bm_works = await self._get_british_museum_works()
            works.extend(bm_works)
        except Exception as e:
            logger.debug(f"British Museum API not available: {e}")
        
        # Tate API
        try:
            tate_works = await self._get_tate_works()
            works.extend(tate_works)
        except Exception as e:
            logger.debug(f"Tate API not available: {e}")
        
        logger.info(f"Found {len(works)} works from museum APIs")
        return works
    
    async def _get_british_museum_works(self) -> List[Dict[str, Any]]:
        """Get works from British Museum API."""
        works = []
        
        try:
            # British Museum Collection API
            api_url = "https://collection.britishmuseum.org/api/object"
            params = {
                'q': 'William Blake',
                'limit': 100
            }
            
            async with self.session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('records', []):
                        works.append({
                            'id': item.get('id', ''),
                            'title': item.get('title', ''),
                            'url': f"https://collection.britishmuseum.org/object/{item.get('id', '')}",
                            'source': 'british_museum'
                        })
                        
        except Exception as e:
            logger.debug(f"Error accessing British Museum API: {e}")
        
        return works
    
    async def _get_tate_works(self) -> List[Dict[str, Any]]:
        """Get works from Tate API."""
        works = []
        
        try:
            # Tate Collection API
            api_url = "https://www.tate.org.uk/api/collection/search"
            params = {
                'q': 'William Blake',
                'limit': 100
            }
            
            async with self.session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('results', []):
                        works.append({
                            'id': item.get('id', ''),
                            'title': item.get('title', ''),
                            'url': f"https://www.tate.org.uk/art/artworks/{item.get('id', '')}",
                            'source': 'tate'
                        })
                        
        except Exception as e:
            logger.debug(f"Error accessing Tate API: {e}")
        
        return works
    
    async def download_work(self, work_id: str) -> Optional[BlakeWork]:
        """Download a work from museum APIs."""
        # This would implement the actual download logic
        # For now, return None as museum APIs require more complex implementation
        return None
