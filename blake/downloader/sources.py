"""
Data source implementations for different Blake work repositories.
"""

import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from urllib.parse import urljoin, urlparse

from .scraper import WebScraper, ImageDownloader
from ..models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType, LicenseType
from ..exceptions import DownloadError
from ..utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)


class BaseSource:
    """Base class for data sources."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.scraper = WebScraper(data_dir)
        self.image_downloader = ImageDownloader(data_dir)
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of available works."""
        raise NotImplementedError
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a specific work."""
        raise NotImplementedError
    
    def _extract_work_id(self, url: str) -> str:
        """Extract work ID from URL."""
        return urlparse(url).path.split('/')[-1]


class BlakeArchiveSource(BaseSource):
    """Source for Blake Archive (https://blakearchive.org)."""
    
    BASE_URL = "https://blakearchive.org"
    SEARCH_URL = "https://blakearchive.org/search"
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of works from Blake Archive."""
        logger.info("Fetching work list from Blake Archive")
        
        try:
            # Try multiple search approaches
            works = []
            
            # Try main search page
            soup = await self.scraper.scrape_page(self.SEARCH_URL)
            works.extend(self._extract_works_from_page(soup))
            
            # Try browsing by work type
            browse_urls = [
                urljoin(self.BASE_URL, path)
                for path in ("/works", "/browse", "/works/poems", "/works/prophecies")
            ]
            
            for url in browse_urls:
                try:
                    soup = await self.scraper.scrape_page(url)
                    works.extend(self._extract_works_from_page(soup))
                except Exception as e:
                    logger.debug(f"Could not access {url}: {e}")
            
            # Remove duplicates
            seen_ids = set()
            unique_works = []
            for work in works:
                if work['id'] not in seen_ids:
                    seen_ids.add(work['id'])
                    unique_works.append(work)
            
            logger.info(f"Found {len(unique_works)} works in Blake Archive")
            return unique_works
            
        except Exception as e:
            logger.error(f"Error fetching work list from Blake Archive: {e}")
            raise DownloadError(f"Failed to fetch work list: {e}") from e
    
    def _extract_works_from_page(self, soup) -> List[Dict[str, Any]]:
        """Extract works from a Blake Archive page."""
        works = []
        
        # Look for various link patterns
        link_patterns = [
            'a[href*="/works/"]',
            'a[href*="/object/"]',
            'a[href*="/item/"]'
        ]
        
        for pattern in link_patterns:
            links = soup.select(pattern)
            for link in links:
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                if title and len(title) > 3:  # Avoid very short titles
                    work_url = urljoin(self.BASE_URL, href)
                    work_id = self._extract_work_id(work_url)
                    
                    works.append({
                        'id': work_id,
                        'title': title,
                        'url': work_url,
                        'source': SourceType.BLAKE_ARCHIVE,
                    })
        
        return works
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a work from Blake Archive."""
        work_url = work_info['url']
        work_id = work_info['id']
        
        logger.info(f"Downloading work from Blake Archive: {work_id}")
        
        try:
            # Get work page
            soup = await self.scraper.scrape_page(work_url)
            
            # Extract metadata
            metadata = await self._extract_metadata(soup, work_info)
            
            # Extract text content
            text_content = await self._extract_text_content(soup)
            
            # Download images
            images = await self._download_images(soup, work_id)
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                text_content=text_content,
                images=images,
            )
            
            # Set primary image
            if images:
                work.primary_image = images[0]
            
            logger.info(f"Successfully downloaded work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_id}: {e}")
            return None
    
    async def _extract_metadata(self, soup, work_info: Dict[str, Any]) -> BlakeMetadata:
        """Extract metadata from work page."""
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else work_info['title']
        
        # Extract description
        desc_elem = soup.find('div', class_='description') or soup.find('p', class_='description')
        description = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Extract date information
        date_elem = soup.find('span', class_='date') or soup.find('div', class_='date')
        creation_date = None
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            creation_date = self._parse_date(date_text)
        
        # Determine work type
        work_type = self._determine_work_type(soup, title)
        
        # Extract medium
        medium_elem = soup.find('span', class_='medium') or soup.find('div', class_='medium')
        medium = medium_elem.get_text(strip=True) if medium_elem else None
        
        # Extract dimensions
        dims_elem = soup.find('span', class_='dimensions') or soup.find('div', class_='dimensions')
        dimensions = dims_elem.get_text(strip=True) if dims_elem else None
        
        # Extract location
        loc_elem = soup.find('span', class_='location') or soup.find('div', class_='location')
        location = loc_elem.get_text(strip=True) if loc_elem else None
        
        return BlakeMetadata(
            id=work_info['id'],
            title=title,
            work_type=work_type,
            creation_date=creation_date,
            description=description,
            medium=medium,
            dimensions=dimensions,
            location=location,
            source=SourceType.BLAKE_ARCHIVE,
            source_url=work_info['url'],
            license_type=LicenseType.UNKNOWN,
            usage_terms="Source-provider edition and image terms require review.",
        )
    
    async def _extract_text_content(self, soup) -> Optional[str]:
        """Extract text content from work page."""
        # Look for text content in various containers
        text_selectors = [
            'div.text-content',
            'div.poem-text',
            'div.work-text',
            'div.content',
            'article',
            'main',
        ]
        
        for selector in text_selectors:
            text_elem = soup.select_one(selector)
            if text_elem:
                return text_elem.get_text(' ', strip=True)
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(' ', strip=True)
        
        return None
    
    async def _download_images(self, soup, work_id: str) -> List[BlakeImage]:
        """Download images associated with the work."""
        images = []
        
        # Find image links
        img_links = soup.find_all('a', href=re.compile(r'\.(jpg|jpeg|png|gif|tiff|bmp)$', re.I))
        
        for i, link in enumerate(img_links):
            img_url = urljoin(self.BASE_URL, link['href'])
            filename = f"{work_id}_img_{i+1}.jpg"
            
            # Download image
            blake_image = await self.image_downloader.download_image(
                img_url, filename, create_thumbnail=True
            )
            
            if blake_image:
                blake_image.metadata_id = work_id
                blake_image.title = f"Image {i+1}"
                images.append(blake_image)
        
        return images
    
    def _determine_work_type(self, soup, title: str) -> WorkType:
        """Determine work type from page content and title."""
        # Check for specific indicators
        if 'poem' in title.lower() or 'song' in title.lower():
            return WorkType.POEM
        elif 'letter' in title.lower():
            return WorkType.LETTER
        elif 'manuscript' in title.lower():
            return WorkType.MANUSCRIPT
        elif 'plate' in title.lower() or 'engraving' in title.lower():
            return WorkType.PLATE
        elif 'drawing' in title.lower():
            return WorkType.DRAWING
        elif 'painting' in title.lower():
            return WorkType.PAINTING
        else:
            return WorkType.POEM  # Default
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from text."""
        # Simple date parsing - can be enhanced
        import re
        
        # Look for 4-digit year
        year_match = re.search(r'\b(17|18|19|20)\d{2}\b', date_text)
        if year_match:
            year = int(year_match.group())
            return datetime(year, 1, 1)
        
        return None


class ProjectGutenbergSource(BaseSource):
    """Source for Project Gutenberg Blake texts."""
    
    BASE_URL = "https://www.gutenberg.org"
    SEARCH_URL = "https://www.gutenberg.org/ebooks/search/?query=William+Blake"
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of Blake works from Project Gutenberg."""
        logger.info("Fetching work list from Project Gutenberg")
        
        try:
            soup = await self.scraper.scrape_page(self.SEARCH_URL)
            
            works = []
            
            # Find book links
            book_links = soup.find_all('a', href=re.compile(r'/ebooks/\d+'))
            
            for link in book_links:
                book_url = urljoin(self.BASE_URL, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    works.append({
                        'id': self._extract_work_id(book_url),
                        'title': title,
                        'url': book_url,
                        'source': SourceType.PROJECT_GUTENBERG,
                    })
            
            logger.info(f"Found {len(works)} Blake works in Project Gutenberg")
            return works
            
        except Exception as e:
            logger.error(f"Error fetching work list from Project Gutenberg: {e}")
            raise DownloadError(f"Failed to fetch work list: {e}")
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a work from Project Gutenberg with multiple format support."""
        work_url = work_info['url']
        work_id = work_info['id']
        
        logger.info(f"Downloading work from Project Gutenberg: {work_id}")
        
        try:
            # Get work page
            soup = await self.scraper.scrape_page(work_url)
            
            # Try multiple formats in order of preference
            text_content = None
            text_path = None
            
            # Check if file already exists first
            text_path = None
            
            # Look for any file starting with this ID
            existing_files = sorted((self.data_dir / "texts").glob(f"{work_id}_*.txt"))
            direct_file = self.data_dir / "texts" / f"{work_id}.txt"
            if direct_file.is_file():
                existing_files.insert(0, direct_file)
            if existing_files:
                text_path = existing_files[0]
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
                    logger.info(f"Using existing file for {work_id}: {text_path.name}")
                except Exception as e:
                    logger.warning(f"Error reading existing file for {work_id}: {e}")
                    text_content = None
            
            # Try plain text first
            text_link = soup.find('a', href=re.compile(r'\.txt$'))
            
            # Try plain text first
            text_link = soup.find('a', href=re.compile(r'\.txt$'))
            if text_link:
                text_url = urljoin(self.BASE_URL, text_link['href'])
                
                # We need the title to make the filename, use work_info for now
                safe_title = sanitize_filename(work_info.get('title', ''))
                text_filename = f"{work_id}_{safe_title}.txt" if safe_title else f"{work_id}.txt"
                text_path = self.data_dir / "texts" / text_filename
                
                success = await self.scraper.download_file(text_url, text_path)
                if success and text_path.exists():
                    with open(text_path, 'r', encoding='utf-8') as f:
                        text_content = f.read()
            
            # Try HTML format if plain text failed
            if not text_content:
                html_link = soup.find('a', href=re.compile(r'\.htm'))
                if html_link:
                    html_url = urljoin(self.BASE_URL, html_link['href'])
                    # Verify this is actually a work page, not a contact page
                    if 'contact' not in html_url.lower() and 'about' not in html_url.lower():
                        html_filename = f"{work_id}.html"
                        html_path = self.data_dir / "texts" / html_filename
                        
                        success = await self.scraper.download_file(html_url, html_path)
                        if success:
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            text_content = self._extract_text_from_html(html_content)
                            text_path = html_path
            
            # Try direct file access patterns
            if not text_content:
                text_content = await self._try_direct_file_access(work_id)
                if text_content:
                    safe_title = sanitize_filename(work_info.get('title', ''))
                    text_filename = f"{work_id}_{safe_title}.txt" if safe_title else f"{work_id}.txt"
                    text_path = self.data_dir / "texts" / text_filename
                    text_path.parent.mkdir(parents=True, exist_ok=True)
                    text_path.write_text(text_content, encoding='utf-8')
            
            if not text_content:
                logger.warning(f"No readable text version found for {work_id}")
                return None
            
            # Clean text content
            original_length = len(text_content) if text_content else 0
            text_content = self._clean_gutenberg_text(text_content)
            if not text_content:
                logger.warning("No body text remains after wrapper removal for %s", work_id)
                return None
            cleaned_length = len(text_content) if text_content else 0
            logger.debug(f"Text cleaning for {work_id}: {original_length} -> {cleaned_length} characters")
            
            # Extract better metadata from the work page
            title = self._extract_title_from_page(soup, work_info['title'])
            try:
                work_type = self._determine_work_type_from_page(soup, title)
            except Exception as e:
                logger.warning(f"Error determining work type for {work_id}: {e}")
                work_type = WorkType.POEM  # Default fallback
            
            # Create metadata
            metadata = BlakeMetadata(
                id=work_id,
                title=title,
                work_type=work_type,
                source=SourceType.PROJECT_GUTENBERG,
                source_url=work_url,
                license_type=LicenseType.PUBLIC_DOMAIN,
                file_path=text_path,
            )
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                text_content=text_content,
            )
            
            logger.info(f"Successfully downloaded work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_id}: {e}")
            return None
    
    def _clean_gutenberg_text(self, text: str) -> str:
        """Clean Project Gutenberg text by removing headers and footers."""
        lines = text.split('\n')
        cleaned_lines = []
        
        # Skip Gutenberg header
        skip_header = True
        for line in lines:
            if '*** START OF' in line or '***START OF' in line:
                skip_header = False
                continue
            elif '*** END OF' in line or '***END OF' in line:
                break
            elif not skip_header:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract text content from HTML."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text('\n')
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    async def _try_direct_file_access(self, work_id: str) -> Optional[str]:
        """Try to access text files directly using common patterns."""
        import aiohttp
        
        # Common file patterns for Project Gutenberg
        patterns = [
            urljoin(self.BASE_URL, f"/files/{work_id}/{work_id}-0.txt"),
            urljoin(self.BASE_URL, f"/files/{work_id}/{work_id}.txt"),
            urljoin(self.BASE_URL, f"/files/{work_id}/pg{work_id}.txt"),
            urljoin(self.BASE_URL, f"/files/{work_id}/{work_id}-h/{work_id}-h.htm"),
            urljoin(self.BASE_URL, f"/files/{work_id}/{work_id}-h/{work_id}-h.html")
        ]
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.scraper.timeout)
        ) as session:
            for url in patterns:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Check if this looks like actual content, not an error page
                            if len(content) > 1000 and 'project gutenberg' in content.lower():
                                if url.endswith(('.htm', '.html')):
                                    return self._extract_text_from_html(content)
                                else:
                                    return content
                except Exception:
                    continue
        
        return None
    
    def _extract_title_from_page(self, soup, fallback_title: str) -> str:
        """Extract title from the work page."""
        # Try to find title in various places
        title_selectors = [
            'h1',
            '.book-title',
            '.title',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 3:  # Avoid very short titles
                    return title
        
        return fallback_title
    
    def _determine_work_type_from_page(self, soup, title: str) -> WorkType:
        """Determine work type from page content and title."""
        # Check title first
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['poem', 'song', 'poetry']):
            return WorkType.POEM
        elif any(word in title_lower for word in ['prophecy', 'vision', 'marriage']):
            return WorkType.PROPHECY
        elif any(word in title_lower for word in ['letter', 'correspondence']):
            return WorkType.LETTER
        elif any(word in title_lower for word in ['drawing', 'painting', 'illustration']):
            return WorkType.DRAWING
        elif any(word in title_lower for word in ['manuscript', 'ms']):
            return WorkType.MANUSCRIPT
        elif any(word in title_lower for word in ['plate', 'engraving']):
            return WorkType.PLATE
        
        # Check page content for additional clues
        page_text = soup.get_text().lower()
        
        if 'prophecy' in page_text or 'vision' in page_text:
            return WorkType.PROPHECY
        elif 'poem' in page_text or 'poetry' in page_text:
            return WorkType.POEM
        elif 'drawing' in page_text or 'painting' in page_text:
            return WorkType.DRAWING
        
        return WorkType.POEM  # Default


class InternetArchiveSource(BaseSource):
    """Source for Internet Archive Blake materials."""
    
    BASE_URL = "https://archive.org"
    SEARCH_URL = "https://archive.org/search.php?query=William+Blake"
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        """Get list of Blake works from Internet Archive."""
        logger.info("Fetching work list from Internet Archive")
        
        try:
            soup = await self.scraper.scrape_page(self.SEARCH_URL)
            
            works = []
            
            # Find item links
            item_links = soup.find_all('a', href=re.compile(r'/details/'))
            
            for link in item_links:
                item_url = urljoin(self.BASE_URL, link['href'])
                title = link.get_text(strip=True)
                
                if title and 'blake' in title.lower():
                    works.append({
                        'id': self._extract_work_id(item_url),
                        'title': title,
                        'url': item_url,
                        'source': SourceType.INTERNET_ARCHIVE,
                    })
            
            logger.info(f"Found {len(works)} Blake works in Internet Archive")
            return works
            
        except Exception as e:
            logger.error(f"Error fetching work list from Internet Archive: {e}")
            raise DownloadError(f"Failed to fetch work list: {e}")
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        """Download a work from Internet Archive."""
        work_url = work_info['url']
        work_id = work_info['id']
        
        logger.info(f"Downloading work from Internet Archive: {work_id}")
        
        try:
            # Get work page
            soup = await self.scraper.scrape_page(work_url)
            
            # Extract metadata
            metadata = await self._extract_metadata(soup, work_info)
            
            # Download available files
            files = await self._download_files(soup, work_id)
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                images=files.get('images', []),
            )
            
            # Add text content if available
            if files.get('text'):
                work.text_content = files['text']
            
            logger.info(f"Successfully downloaded work: {work_id}")
            return work
            
        except Exception as e:
            logger.error(f"Error downloading work {work_id}: {e}")
            return None
    
    async def _extract_metadata(self, soup, work_info: Dict[str, Any]) -> BlakeMetadata:
        """Extract metadata from Internet Archive item page."""
        # Extract title
        title_elem = soup.find('h1', class_='item-title') or soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else work_info['title']
        
        # Extract description
        desc_elem = soup.find('div', class_='item-description')
        description = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Extract date
        date_elem = soup.find('span', string=re.compile(r'\d{4}'))
        creation_date = None
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            creation_date = self._parse_date(date_text)
        
        return BlakeMetadata(
            id=work_info['id'],
            title=title,
            work_type=WorkType.MANUSCRIPT,  # Default for IA
            creation_date=creation_date,
            description=description,
            source=SourceType.INTERNET_ARCHIVE,
            source_url=work_info['url'],
            license_type=LicenseType.UNKNOWN,
            usage_terms="Source-provider edition and image terms require review.",
        )
    
    async def _download_files(self, soup, work_id: str) -> Dict[str, Any]:
        """Download available files from Internet Archive item."""
        files = {'images': [], 'text': None}
        
        # Find file links
        file_links = soup.find_all('a', href=re.compile(r'\.(jpg|jpeg|png|gif|tiff|bmp|txt|pdf)$', re.I))
        
        for link in file_links:
            file_url = urljoin(self.BASE_URL, link['href'])
            filename = link.get_text(strip=True)
            
            # Determine file type
            if re.search(r'\.(jpg|jpeg|png|gif|tiff|bmp)$', file_url, re.I):
                # Image file
                blake_image = await self.image_downloader.download_image(
                    file_url, f"{work_id}_{filename}", create_thumbnail=True
                )
                if blake_image:
                    blake_image.metadata_id = work_id
                    files['images'].append(blake_image)
            
            elif re.search(r'\.txt$', file_url, re.I):
                # Text file
                text_path = self.data_dir / "texts" / f"{work_id}.txt"
                success = await self.scraper.download_file(file_url, text_path)
                if success:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        files['text'] = f.read()
        
        return files
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse date from text."""
        import re
        
        # Look for 4-digit year
        year_match = re.search(r'\b(17|18|19|20)\d{2}\b', date_text)
        if year_match:
            year = int(year_match.group())
            return datetime(year, 1, 1)
        
        return None

