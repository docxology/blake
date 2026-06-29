"""
Web scraping utilities for downloading Blake works.
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import logging
from bs4 import BeautifulSoup
import hashlib
import json
import time
from datetime import datetime
import os

# Optional imports with fallbacks
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from ..models import BlakeWork, BlakeImage, BlakeMetadata, WorkType, SourceType, LicenseType
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class WebScraper:
    """Web scraper for downloading content from various sources."""
    
    def __init__(self, data_dir: Path, max_concurrent: int = 5, 
                 timeout: int = 30, retry_attempts: int = 3):
        """
        Initialize web scraper.
        
        Args:
            data_dir: Directory to store downloaded data
            max_concurrent: Maximum concurrent downloads
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed downloads
        """
        self.data_dir = data_dir
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create directories
        self.texts_dir = data_dir / "texts"
        self.images_dir = data_dir / "images"
        self.raw_dir = data_dir / "raw"
        self.metadata_dir = data_dir / "metadata"
        
        for dir_path in [self.texts_dir, self.images_dir, self.raw_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Download tracking
        self.download_log = data_dir / "download_log.json"
        self._load_download_log()
    
    def _load_download_log(self) -> None:
        """Load download log from file."""
        if self.download_log.exists():
            try:
                with open(self.download_log, 'r', encoding='utf-8') as f:
                    self.downloaded_files = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading download log: {e}")
                self.downloaded_files = {}
        else:
            self.downloaded_files = {}
    
    def _save_download_log(self) -> None:
        """Save download log to file."""
        try:
            with open(self.download_log, 'w', encoding='utf-8') as f:
                json.dump(self.downloaded_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving download log: {e}")
    
    def _is_file_downloaded(self, url: str, file_path: Path) -> bool:
        """Check if file has already been downloaded and is complete."""
        if url in self.downloaded_files:
            recorded_path = self.downloaded_files[url].get('path')
            recorded_size = self.downloaded_files[url].get('size')
            
            if recorded_path and Path(recorded_path) == file_path:
                if file_path.exists():
                    actual_size = file_path.stat().st_size
                    if actual_size == recorded_size and actual_size > 0:
                        return True
        return False
    
    def _record_download(self, url: str, file_path: Path, success: bool = True) -> None:
        """Record download attempt in log."""
        self.downloaded_files[url] = {
            'path': str(file_path),
            'size': file_path.stat().st_size if file_path.exists() else 0,
            'timestamp': datetime.now().isoformat(),
            'success': success
        }
        self._save_download_log()
    
    async def scrape_page(self, url: str, headers: Optional[Dict[str, str]] = None) -> BeautifulSoup:
        """
        Scrape a web page and return parsed content.
        
        Args:
            url: URL to scrape
            headers: HTTP headers
            
        Returns:
            BeautifulSoup object
        """
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        if headers:
            default_headers.update(headers)
        
        async with self.semaphore:
            try:
                async with aiohttp.ClientSession(headers=default_headers) as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        content = await response.text()
                        return BeautifulSoup(content, 'html.parser')
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                raise DownloadError(f"Failed to scrape {url}: {e}")
    
    async def download_file(self, url: str, file_path: Path, 
                          headers: Optional[Dict[str, str]] = None, 
                          force: bool = False) -> bool:
        """
        Download a file from URL with retry logic and duplicate checking.
        
        Args:
            url: URL to download
            file_path: Local path to save file
            headers: HTTP headers
            force: Force re-download even if file exists
            
        Returns:
            True if successful
        """
        # Check if file already exists and is complete
        if not force and self._is_file_downloaded(url, file_path):
            logger.info(f"File already downloaded: {url}")
            return True
        
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        if headers:
            default_headers.update(headers)
        
        async with self.semaphore:
            for attempt in range(self.retry_attempts):
                try:
                    timeout = aiohttp.ClientTimeout(total=self.timeout)
                    async with aiohttp.ClientSession(
                        headers=default_headers, 
                        timeout=timeout
                    ) as session:
                        async with session.get(url) as response:
                            response.raise_for_status()
                            
                            # Create parent directory
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Download file
                            total_size = 0
                            async with aiofiles.open(file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(8192):
                                    await f.write(chunk)
                                    total_size += len(chunk)
                            
                            # Verify file was downloaded completely
                            if total_size > 0:
                                self._record_download(url, file_path, success=True)
                                logger.info(f"Downloaded: {url} -> {file_path} ({total_size} bytes)")
                                return True
                            else:
                                logger.warning(f"Downloaded empty file: {url}")
                                return False
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{self.retry_attempts})")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                except aiohttp.ClientError as e:
                    logger.warning(f"Client error downloading {url} (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                except Exception as e:
                    logger.error(f"Unexpected error downloading {url} (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
            
            # All attempts failed
            self._record_download(url, file_path, success=False)
            logger.error(f"Failed to download {url} after {self.retry_attempts} attempts")
            return False
    
    async def extract_text_from_html(self, html: str, selectors: List[str]) -> str:
        """
        Extract text content from HTML using CSS selectors.
        
        Args:
            html: HTML content
            selectors: List of CSS selectors to try
            
        Returns:
            Extracted text
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                text_parts = []
                for element in elements:
                    text_parts.append(element.get_text(strip=True))
                return '\n\n'.join(text_parts)
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(strip=True)
        
        return soup.get_text(strip=True)
    
    def generate_file_hash(self, file_path: Path) -> str:
        """
        Generate SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class ImageDownloader:
    """Specialized image downloader with processing capabilities."""
    
    def __init__(self, data_dir: Path, max_size: Tuple[int, int] = (2048, 2048)):
        """
        Initialize image downloader.
        
        Args:
            data_dir: Directory to store images
            max_size: Maximum image size (width, height) for processing
        """
        self.data_dir = data_dir
        self.images_dir = data_dir / "images"
        self.thumbnails_dir = data_dir / "images" / "thumbnails"
        self.max_size = max_size
        
        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    async def download_image(self, url: str, filename: str, 
                           create_thumbnail: bool = True,
                           force: bool = False) -> Optional[BlakeImage]:
        """
        Download an image and create metadata.
        
        Args:
            url: Image URL
            filename: Local filename
            create_thumbnail: Whether to create thumbnail
            force: Force re-download even if image exists
            
        Returns:
            BlakeImage object or None if failed
        """
        try:
            # Validate filename extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                logger.warning(f"Unsupported image format: {file_ext}")
                return None
            
            # Download image
            image_path = self.images_dir / filename
            scraper = WebScraper(self.data_dir)
            
            success = await scraper.download_file(url, image_path, force=force)
            if not success:
                return None
            
            # Verify file exists and has content
            if not image_path.exists() or image_path.stat().st_size == 0:
                logger.error(f"Downloaded file is empty or missing: {image_path}")
                return None
            
            # Process image
            image_info = await self._process_image(image_path)
            
            # Create thumbnail if requested
            thumbnail_path = None
            if create_thumbnail and PIL_AVAILABLE:
                thumbnail_path = await self._create_thumbnail(image_path, filename)
            
            # Create BlakeImage object
            blake_image = BlakeImage(
                id=f"img_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                metadata_id="",  # Will be set by caller
                title=filename,
                file_path=image_path,
                thumbnail_path=thumbnail_path,
                original_url=url,
                width=image_info.get('width'),
                height=image_info.get('height'),
                format=image_info.get('format'),
                dominant_colors=image_info.get('dominant_colors', []),
                brightness=image_info.get('brightness'),
                contrast=image_info.get('contrast'),
            )
            
            return blake_image
            
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None
    
    async def _process_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Process image and extract metadata.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary of image metadata
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, skipping image processing")
            return {
                'width': None,
                'height': None,
                'format': image_path.suffix[1:].upper() if image_path.suffix else None,
                'brightness': None,
                'contrast': None,
                'dominant_colors': [],
            }
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Get basic info
                width, height = img.size
                format_name = img.format
                
                # Resize if too large for processing
                if width > self.max_size[0] or height > self.max_size[1]:
                    img.thumbnail(self.max_size, Image.Resampling.LANCZOS)
                    width, height = img.size
                
                # Calculate brightness and contrast
                try:
                    import numpy as np
                    img_array = np.array(img)
                    
                    # Brightness (mean of all pixel values)
                    brightness = float(np.mean(img_array))
                    
                    # Contrast (standard deviation)
                    contrast = float(np.std(img_array))
                    
                    # Extract dominant colors (simplified)
                    dominant_colors = self._extract_dominant_colors(img_array)
                    
                except ImportError:
                    logger.warning("NumPy not available, skipping advanced processing")
                    brightness = None
                    contrast = None
                    dominant_colors = []
                
                return {
                    'width': width,
                    'height': height,
                    'format': format_name,
                    'brightness': brightness,
                    'contrast': contrast,
                    'dominant_colors': dominant_colors,
                }
                
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return {
                'width': None,
                'height': None,
                'format': image_path.suffix[1:].upper() if image_path.suffix else None,
                'brightness': None,
                'contrast': None,
                'dominant_colors': [],
            }
    
    def _extract_dominant_colors(self, img_array, num_colors: int = 5) -> List[str]:
        """
        Extract dominant colors from image.
        
        Args:
            img_array: Image as numpy array
            num_colors: Number of colors to extract
            
        Returns:
            List of hex color codes
        """
        try:
            # Try sklearn first
            try:
                from sklearn.cluster import KMeans
                
                # Reshape image array
                pixels = img_array.reshape(-1, 3)
                
                # Sample pixels for efficiency
                if len(pixels) > 10000:
                    import random
                    pixels = pixels[random.sample(range(len(pixels)), 10000)]
                
                # Cluster colors
                kmeans = KMeans(n_clusters=num_colors, random_state=42)
                kmeans.fit(pixels)
                
                # Get cluster centers
                colors = kmeans.cluster_centers_.astype(int)
                
                # Convert to hex
                hex_colors = []
                for color in colors:
                    hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                    hex_colors.append(hex_color)
                
                return hex_colors
                
            except ImportError:
                # Fallback: simple histogram-based approach
                logger.debug("sklearn not available, using simple color extraction")
                return self._extract_colors_simple(img_array, num_colors)
            
        except Exception as e:
            logger.error(f"Error extracting dominant colors: {e}")
            return []
    
    def _extract_colors_simple(self, img_array, num_colors: int = 5) -> List[str]:
        """Simple color extraction without sklearn."""
        try:
            # Reshape and sample
            pixels = img_array.reshape(-1, 3)
            if len(pixels) > 1000:
                import random
                pixels = pixels[random.sample(range(len(pixels)), 1000)]
            
            # Group similar colors
            color_groups = {}
            for pixel in pixels:
                # Quantize colors to reduce noise
                r, g, b = (pixel // 32) * 32
                key = (r, g, b)
                if key not in color_groups:
                    color_groups[key] = []
                color_groups[key].append(pixel)
            
            # Sort by frequency and take top colors
            sorted_groups = sorted(color_groups.items(), key=lambda x: len(x[1]), reverse=True)
            
            hex_colors = []
            for (r, g, b), _ in sorted_groups[:num_colors]:
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                hex_colors.append(hex_color)
            
            return hex_colors
            
        except Exception as e:
            logger.error(f"Error in simple color extraction: {e}")
            return []
    
    async def _create_thumbnail(self, image_path: Path, filename: str, 
                              size: Tuple[int, int] = (200, 200)) -> Optional[Path]:
        """
        Create thumbnail of image.
        
        Args:
            image_path: Path to original image
            filename: Original filename
            size: Thumbnail size
            
        Returns:
            Path to thumbnail or None if failed
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, skipping thumbnail creation")
            return None
        
        try:
            # Create thumbnail filename
            name_without_ext = Path(filename).stem
            thumbnail_path = self.thumbnails_dir / f"thumb_{name_without_ext}.jpg"
            
            # Skip if thumbnail already exists
            if thumbnail_path.exists():
                logger.debug(f"Thumbnail already exists: {thumbnail_path}")
                return thumbnail_path
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
                
                logger.debug(f"Created thumbnail: {thumbnail_path}")
                return thumbnail_path
                
        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_path}: {e}")
            return None
