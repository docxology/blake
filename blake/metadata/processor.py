"""
Metadata processing and enhancement utilities.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from ..models import BlakeWork, BlakeMetadata, BlakeImage, WorkType, SourceType
from ..exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataProcessor:
    """Processes and enhances metadata for Blake works."""
    
    def __init__(self):
        """Initialize metadata processor."""
        self.date_patterns = [
            r'\b(17|18|19|20)\d{2}\b',  # 4-digit year
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month day, year
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
        ]
        
        # Common Blake themes and subjects
        self.blake_themes = [
            'innocence', 'experience', 'prophecy', 'vision', 'mysticism',
            'revolution', 'liberty', 'imagination', 'creativity', 'divine',
            'nature', 'love', 'death', 'rebirth', 'transcendence',
            'good', 'evil', 'duality', 'unity', 'eternity'
        ]
        
        self.blake_subjects = [
            'angels', 'demons', 'gods', 'goddesses', 'prophets', 'poets',
            'children', 'animals', 'flowers', 'trees', 'mountains', 'rivers',
            'cities', 'temples', 'gardens', 'deserts', 'heaven', 'hell',
            'lamb', 'tiger', 'rose', 'lily', 'eagle', 'serpent'
        ]
    
    async def process_work(self, work: BlakeWork) -> BlakeWork:
        """
        Process and enhance metadata for a work.
        
        Args:
            work: BlakeWork to process
            
        Returns:
            Enhanced BlakeWork
        """
        logger.info(f"Processing work: {work.id}")
        
        try:
            # Enhance metadata
            work.metadata = await self._enhance_metadata(work.metadata)
            
            # Process text content
            if work.text_content:
                work.text_content = self._clean_text(work.text_content)
            
            # Process images
            for image in work.images:
                await self._process_image(image)
            
            # Extract themes and subjects from text
            if work.text_content:
                themes, subjects = self._extract_themes_subjects(work.text_content)
                work.metadata.themes.extend(themes)
                work.metadata.subjects.extend(subjects)
                work.metadata.themes = list(set(work.metadata.themes))  # Remove duplicates
                work.metadata.subjects = list(set(work.metadata.subjects))
            
            # Mark as processed
            work.metadata.processed = True
            work.metadata.updated_at = datetime.now()
            
            logger.info(f"Successfully processed work: {work.id}")
            return work
            
        except Exception as e:
            logger.error(f"Error processing work {work.id}: {e}")
            raise MetadataError(f"Failed to process work {work.id}: {e}")
    
    async def _enhance_metadata(self, metadata: BlakeMetadata) -> BlakeMetadata:
        """Enhance metadata with additional information."""
        # Parse dates if not already parsed
        if not metadata.creation_date and metadata.description:
            metadata.creation_date = self._extract_date(metadata.description)
        
        # Determine work type if not set
        if metadata.work_type == WorkType.POEM:  # Default, try to determine better
            metadata.work_type = self._determine_work_type(metadata.title, metadata.description)
        
        # Extract tags from title and description
        if not metadata.tags:
            metadata.tags = self._extract_tags(metadata.title, metadata.description)
        
        # Set series if not set
        if not metadata.series:
            metadata.series = self._determine_series(metadata.title)
        
        # Generate checksum if file exists
        if metadata.file_path and metadata.file_path.exists():
            metadata.checksum = self._generate_checksum(metadata.file_path)
            metadata.file_size = metadata.file_path.stat().st_size
        
        return metadata
    
    async def _process_image(self, image: BlakeImage) -> None:
        """Process image metadata."""
        # Extract text from image if not already done
        if not image.extracted_text and image.file_path.exists():
            image.extracted_text = await self._extract_text_from_image(image.file_path)
        
        # Analyze composition if not already done
        if not image.composition and image.file_path.exists():
            image.composition = await self._analyze_composition(image.file_path)
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove common Gutenberg headers/footers
        text = re.sub(r'^\s*Project Gutenberg.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*End of Project Gutenberg.*?$', '', text, flags=re.MULTILINE)
        
        # Normalize line breaks
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        return text.strip()
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group()
                    # Try to parse the date
                    if re.match(r'\b(17|18|19|20)\d{2}\b', date_str):
                        year = int(date_str)
                        return datetime(year, 1, 1)
                    # Add more date parsing logic as needed
                except ValueError:
                    continue
        
        return None
    
    def _determine_work_type(self, title: str, description: Optional[str] = None) -> WorkType:
        """Determine work type from title and description."""
        text = f"{title} {description or ''}".lower()
        
        if any(word in text for word in ['poem', 'song', 'verse', 'stanza']):
            return WorkType.POEM
        elif any(word in text for word in ['letter', 'correspondence']):
            return WorkType.LETTER
        elif any(word in text for word in ['manuscript', 'draft', 'sketch']):
            return WorkType.MANUSCRIPT
        elif any(word in text for word in ['plate', 'engraving', 'etching']):
            return WorkType.PLATE
        elif any(word in text for word in ['drawing', 'sketch', 'pencil']):
            return WorkType.DRAWING
        elif any(word in text for word in ['painting', 'watercolor', 'oil']):
            return WorkType.PAINTING
        else:
            return WorkType.POEM  # Default
    
    def _extract_tags(self, title: str, description: Optional[str] = None) -> List[str]:
        """Extract tags from title and description."""
        text = f"{title} {description or ''}".lower()
        tags = []
        
        # Extract common Blake terms
        blake_terms = [
            'songs of innocence', 'songs of experience', 'prophetic books',
            'illuminated books', 'jerusalem', 'milton', 'america', 'europe',
            'the marriage of heaven and hell', 'the book of thel',
            'visions of the daughters of albion', 'the first book of urizen'
        ]
        
        for term in blake_terms:
            if term in text:
                tags.append(term)
        
        # Extract other meaningful terms
        words = re.findall(r'\b[a-z]{4,}\b', text)
        for word in words:
            if word in self.blake_themes or word in self.blake_subjects:
                tags.append(word)
        
        return list(set(tags))
    
    def _determine_series(self, title: str) -> Optional[str]:
        """Determine series from title."""
        title_lower = title.lower()
        
        if 'songs of innocence' in title_lower:
            return 'Songs of Innocence'
        elif 'songs of experience' in title_lower:
            return 'Songs of Experience'
        elif 'prophetic books' in title_lower:
            return 'Prophetic Books'
        elif 'illuminated books' in title_lower:
            return 'Illuminated Books'
        elif any(book in title_lower for book in ['jerusalem', 'milton', 'america', 'europe']):
            return 'Prophetic Books'
        
        return None
    
    def _extract_themes_subjects(self, text: str) -> Tuple[List[str], List[str]]:
        """Extract themes and subjects from text."""
        text_lower = text.lower()
        
        themes = []
        subjects = []
        
        # Find themes
        for theme in self.blake_themes:
            if theme in text_lower:
                themes.append(theme)
        
        # Find subjects
        for subject in self.blake_subjects:
            if subject in text_lower:
                subjects.append(subject)
        
        return themes, subjects
    
    def _generate_checksum(self, file_path: Path) -> str:
        """Generate SHA-256 checksum for file."""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _extract_text_from_image(self, image_path: Path) -> Optional[str]:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image
            
            # Load image
            image = Image.open(image_path)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            return text.strip() if text else None
            
        except ImportError:
            logger.warning("pytesseract not available for OCR")
            return None
        except Exception as e:
            logger.error(f"Error extracting text from image {image_path}: {e}")
            return None
    
    async def _analyze_composition(self, image_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze image composition."""
        try:
            from PIL import Image
            import numpy as np
            
            # Load image
            image = Image.open(image_path)
            img_array = np.array(image)
            
            # Basic composition analysis
            height, width = img_array.shape[:2]
            
            # Rule of thirds analysis
            rule_of_thirds = {
                'horizontal_lines': [height // 3, 2 * height // 3],
                'vertical_lines': [width // 3, 2 * width // 3],
            }
            
            # Color distribution
            if len(img_array.shape) == 3:
                # Color image
                r_mean = np.mean(img_array[:, :, 0])
                g_mean = np.mean(img_array[:, :, 1])
                b_mean = np.mean(img_array[:, :, 2])
                
                color_balance = {
                    'red': float(r_mean),
                    'green': float(g_mean),
                    'blue': float(b_mean),
                }
            else:
                # Grayscale
                color_balance = {
                    'grayscale': float(np.mean(img_array))
                }
            
            return {
                'dimensions': {'width': width, 'height': height},
                'aspect_ratio': width / height,
                'rule_of_thirds': rule_of_thirds,
                'color_balance': color_balance,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing composition of {image_path}: {e}")
            return None

