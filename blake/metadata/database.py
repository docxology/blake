"""
Database management for Blake metadata.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from ..models import BlakeWork, BlakeMetadata, BlakeImage
from ..exceptions import MetadataError

logger = logging.getLogger(__name__)


class MetadataDatabase:
    """SQLite database for storing Blake metadata."""
    
    def __init__(self, db_path: Path):
        """
        Initialize metadata database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create works table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS works (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    work_type TEXT NOT NULL,
                    creation_date TEXT,
                    publication_date TEXT,
                    period TEXT,
                    description TEXT,
                    medium TEXT,
                    dimensions TEXT,
                    location TEXT,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    source_id TEXT,
                    license_type TEXT,
                    attribution TEXT,
                    usage_terms TEXT,
                    parent_work TEXT,
                    series TEXT,
                    tags TEXT,  -- JSON array
                    themes TEXT,  -- JSON array
                    subjects TEXT,  -- JSON array
                    file_path TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    checksum TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    processed BOOLEAN DEFAULT 0,
                    analysis_results TEXT  -- JSON object
                )
            """)
            
            # Create images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id TEXT PRIMARY KEY,
                    metadata_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    alt_text TEXT,
                    file_path TEXT NOT NULL,
                    thumbnail_path TEXT,
                    original_url TEXT,
                    width INTEGER,
                    height INTEGER,
                    dpi REAL,
                    format TEXT,
                    color_space TEXT,
                    dominant_colors TEXT,  -- JSON array
                    brightness REAL,
                    contrast REAL,
                    composition TEXT,  -- JSON object
                    extracted_text TEXT,
                    text_regions TEXT,  -- JSON array
                    related_text_id TEXT,
                    plate_number INTEGER,
                    FOREIGN KEY (metadata_id) REFERENCES works (id)
                )
            """)
            
            # Create analysis results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    results TEXT NOT NULL,  -- JSON object
                    confidence REAL,
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (work_id) REFERENCES works (id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_title ON works (title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_type ON works (work_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_source ON works (source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_works_date ON works (creation_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_metadata ON images (metadata_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_work ON analysis_results (work_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_type ON analysis_results (analysis_type)")
            
            conn.commit()
    
    def save_work(self, work: BlakeWork) -> None:
        """Save a BlakeWork to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Save metadata
            cursor.execute("""
                INSERT OR REPLACE INTO works (
                    id, title, work_type, creation_date, publication_date, period,
                    description, medium, dimensions, location, source, source_url,
                    source_id, license_type, attribution, usage_terms, parent_work,
                    series, tags, themes, subjects, file_path, file_size, mime_type,
                    checksum, created_at, updated_at, processed, analysis_results
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work.metadata.id,
                work.metadata.title,
                work.metadata.work_type,
                work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
                work.metadata.publication_date.isoformat() if work.metadata.publication_date else None,
                work.metadata.period,
                work.metadata.description,
                work.metadata.medium,
                work.metadata.dimensions,
                work.metadata.location,
                work.metadata.source,
                work.metadata.source_url,
                work.metadata.source_id,
                work.metadata.license_type,
                work.metadata.attribution,
                work.metadata.usage_terms,
                work.metadata.parent_work,
                work.metadata.series,
                json.dumps(work.metadata.tags),
                json.dumps(work.metadata.themes),
                json.dumps(work.metadata.subjects),
                str(work.metadata.file_path) if work.metadata.file_path else None,
                work.metadata.file_size,
                work.metadata.mime_type,
                work.metadata.checksum,
                work.metadata.created_at.isoformat(),
                work.metadata.updated_at.isoformat(),
                work.metadata.processed,
                json.dumps(work.metadata.analysis_results),
            ))
            
            # Save images
            for image in work.images:
                cursor.execute("""
                    INSERT OR REPLACE INTO images (
                        id, metadata_id, title, description, alt_text, file_path,
                        thumbnail_path, original_url, width, height, dpi, format,
                        color_space, dominant_colors, brightness, contrast, composition,
                        extracted_text, text_regions, related_text_id, plate_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    image.id,
                    image.metadata_id,
                    image.title,
                    image.description,
                    image.alt_text,
                    str(image.file_path),
                    str(image.thumbnail_path) if image.thumbnail_path else None,
                    image.original_url,
                    image.width,
                    image.height,
                    image.dpi,
                    image.format,
                    image.color_space,
                    json.dumps(image.dominant_colors),
                    image.brightness,
                    image.contrast,
                    json.dumps(image.composition) if image.composition else None,
                    image.extracted_text,
                    json.dumps(image.text_regions),
                    image.related_text_id,
                    image.plate_number,
                ))
            
            conn.commit()

    def delete_work(self, work_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM images WHERE metadata_id = ?", (work_id,))
            cursor.execute("DELETE FROM analysis_results WHERE work_id = ?", (work_id,))
            cursor.execute("DELETE FROM works WHERE id = ?", (work_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
    
    def load_work(self, work_id: str) -> Optional[BlakeWork]:
        """Load a BlakeWork from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load metadata
            cursor.execute("SELECT * FROM works WHERE id = ?", (work_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Convert row to BlakeMetadata
            metadata = self._row_to_metadata(row)
            
            # Load images
            cursor.execute("SELECT * FROM images WHERE metadata_id = ?", (work_id,))
            image_rows = cursor.fetchall()
            
            images = [self._row_to_image(row) for row in image_rows]
            
            # Load text content from text file if it exists
            text_content = None
            texts_dir = self.db_path.parent.parent / "texts"
            
            # Look for file matching pattern {work_id}_*.txt or {work_id}.txt
            text_file = None
            if texts_dir.exists():
                # Direct match
                direct_file = texts_dir / f"{work_id}.txt"
                if direct_file.exists():
                    text_file = direct_file
                else:
                    # Pattern match
                    matches = list(texts_dir.glob(f"{work_id}_*.txt"))
                    if matches:
                        text_file = matches[0]
            
            if text_file and text_file.exists():
                try:
                    text_content = text_file.read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Failed to load text content for work {work_id}: {e}")
            
            # Create BlakeWork
            work = BlakeWork(
                id=work_id,
                metadata=metadata,
                images=images,
                text_content=text_content,
            )
            
            # Set primary image
            if images:
                work.primary_image = images[0]
            
            return work
    
    def load_all_works(self) -> List[BlakeWork]:
        """Load all works from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load all work IDs
            cursor.execute("SELECT id FROM works ORDER BY title")
            work_ids = [row[0] for row in cursor.fetchall()]
            
            # Load each work
            works = []
            for work_id in work_ids:
                work = self.load_work(work_id)
                if work:
                    works.append(work)
            
            return works
    
    def search_works(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[BlakeWork]:
        """Search works by query and filters."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build search query
            where_conditions = []
            params = []
            
            # Text search
            if query:
                where_conditions.append("""
                    (title LIKE ? OR description LIKE ? OR 
                     tags LIKE ? OR themes LIKE ? OR subjects LIKE ?)
                """)
                query_param = f"%{query}%"
                params.extend([query_param] * 5)
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if key == "work_type" and value:
                        where_conditions.append("work_type = ?")
                        params.append(value)
                    elif key == "source" and value:
                        where_conditions.append("source = ?")
                        params.append(value)
                    elif key == "date_range" and value:
                        start_date, end_date = value
                        where_conditions.append("creation_date BETWEEN ? AND ?")
                        params.extend([start_date, end_date])
                    elif key == "tags" and value:
                        where_conditions.append("tags LIKE ?")
                        params.append(f"%{value}%")
            
            # Execute query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            cursor.execute(f"""
                SELECT id FROM works 
                WHERE {where_clause}
                ORDER BY title
            """, params)
            
            work_ids = [row[0] for row in cursor.fetchall()]
            
            # Load works
            works = []
            for work_id in work_ids:
                work = self.load_work(work_id)
                if work:
                    works.append(work)
            
            return works
    
    def save_analysis_result(self, work_id: str, analysis_type: str, 
                           results: Dict[str, Any], confidence: Optional[float] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save analysis results to the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO analysis_results (
                    work_id, analysis_type, timestamp, results, confidence, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                work_id,
                analysis_type,
                datetime.now().isoformat(),
                json.dumps(results),
                confidence,
                json.dumps(metadata) if metadata else None,
            ))
            
            conn.commit()
    
    def load_analysis_results(self, work_id: str, 
                            analysis_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load analysis results for a work."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if analysis_type:
                cursor.execute("""
                    SELECT analysis_type, timestamp, results, confidence, metadata
                    FROM analysis_results 
                    WHERE work_id = ? AND analysis_type = ?
                    ORDER BY timestamp DESC
                """, (work_id, analysis_type))
            else:
                cursor.execute("""
                    SELECT analysis_type, timestamp, results, confidence, metadata
                    FROM analysis_results 
                    WHERE work_id = ?
                    ORDER BY timestamp DESC
                """, (work_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'analysis_type': row[0],
                    'timestamp': row[1],
                    'results': json.loads(row[2]),
                    'confidence': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {},
                })
            
            return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic counts
            cursor.execute("SELECT COUNT(*) FROM works")
            total_works = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM images")
            total_images = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM analysis_results")
            total_analyses = cursor.fetchone()[0]
            
            # Work types
            cursor.execute("""
                SELECT work_type, COUNT(*) 
                FROM works 
                GROUP BY work_type 
                ORDER BY COUNT(*) DESC
            """)
            work_types = dict(cursor.fetchall())
            
            # Sources
            cursor.execute("""
                SELECT source, COUNT(*) 
                FROM works 
                GROUP BY source 
                ORDER BY COUNT(*) DESC
            """)
            sources = dict(cursor.fetchall())
            
            # Date range
            cursor.execute("""
                SELECT MIN(creation_date), MAX(creation_date) 
                FROM works 
                WHERE creation_date IS NOT NULL
            """)
            date_range = cursor.fetchone()
            
            return {
                'total_works': total_works,
                'total_images': total_images,
                'total_analyses': total_analyses,
                'work_types': work_types,
                'sources': sources,
                'date_range': {
                    'earliest': date_range[0],
                    'latest': date_range[1],
                } if date_range[0] else None,
            }
    
    def _row_to_metadata(self, row: Tuple) -> BlakeMetadata:
        """Convert database row to BlakeMetadata."""
        return BlakeMetadata(
            id=row[0],
            title=row[1],
            work_type=row[2],
            creation_date=datetime.fromisoformat(row[3]) if row[3] else None,
            publication_date=datetime.fromisoformat(row[4]) if row[4] else None,
            period=row[5],
            description=row[6],
            medium=row[7],
            dimensions=row[8],
            location=row[9],
            source=row[10],
            source_url=row[11],
            source_id=row[12],
            license_type=row[13],
            attribution=row[14],
            usage_terms=row[15],
            parent_work=row[16],
            series=row[17],
            tags=json.loads(row[18]) if row[18] else [],
            themes=json.loads(row[19]) if row[19] else [],
            subjects=json.loads(row[20]) if row[20] else [],
            file_path=Path(row[21]) if row[21] else None,
            file_size=row[22],
            mime_type=row[23],
            checksum=row[24],
            created_at=datetime.fromisoformat(row[25]),
            updated_at=datetime.fromisoformat(row[26]),
            processed=bool(row[27]),
            analysis_results=json.loads(row[28]) if row[28] else {},
        )
    
    def _row_to_image(self, row: Tuple) -> BlakeImage:
        """Convert database row to BlakeImage."""
        return BlakeImage(
            id=row[0],
            metadata_id=row[1],
            title=row[2],
            description=row[3],
            alt_text=row[4],
            file_path=Path(row[5]),
            thumbnail_path=Path(row[6]) if row[6] else None,
            original_url=row[7],
            width=row[8],
            height=row[9],
            dpi=row[10],
            format=row[11],
            color_space=row[12],
            dominant_colors=json.loads(row[13]) if row[13] else [],
            brightness=row[14],
            contrast=row[15],
            composition=json.loads(row[16]) if row[16] else None,
            extracted_text=row[17],
            text_regions=json.loads(row[18]) if row[18] else [],
            related_text_id=row[19],
            plate_number=row[20],
        )
