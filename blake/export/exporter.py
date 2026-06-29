"""
Main exporter class for Blake data.
"""

from pathlib import Path
from typing import List, Dict, Any
import logging
import shutil
from datetime import datetime

from .formats import EXPORTERS
from ..models import BlakeWork, ExportConfig
from ..exceptions import ExportError
from ..provenance import work_provenance

logger = logging.getLogger(__name__)


class BlakeExporter:
    """Main exporter class for Blake data."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize Blake exporter.
        
        Args:
            data_dir: Directory containing Blake data
        """
        self.data_dir = data_dir
        self.export_dir = data_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        self.exporters = {name: exporter() for name, exporter in EXPORTERS.items()}
        
        logger.info(f"Initialized BlakeExporter with data directory: {data_dir}")
    
    async def export_works(self, works: List[BlakeWork], config: ExportConfig) -> Path:
        """
        Export works according to configuration.
        
        Args:
            works: List of BlakeWork objects to export
            config: Export configuration
            
        Returns:
            Path to exported data
        """
        logger.info(f"Exporting {len(works)} works in {config.format} format")
        
        try:
            # Create output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = config.output_dir / f"blake_export_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Filter works if specified
            if config.filter_works:
                works = [w for w in works if w.id in config.filter_works]
            
            # Export based on format
            if config.format not in self.exporters:
                raise ExportError(f"Unsupported export format: {config.format}")
            
            exporter = self.exporters[config.format]
            
            # Export main data
            main_file = await exporter.export_works(works, output_dir, config)
            
            # Copy images if requested
            if config.include_images:
                await self._copy_images(works, output_dir)
            
            # Create metadata file
            await self._create_metadata_file(works, output_dir, config)
            
            # Compress if requested
            if config.compress:
                output_path = await self._compress_export(output_dir)
            else:
                output_path = output_dir
            
            logger.info(f"Export completed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting works: {e}")
            raise ExportError(f"Failed to export works: {e}")
    
    async def _copy_images(self, works: List[BlakeWork], output_dir: Path) -> None:
        """Copy images to export directory."""
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        for work in works:
            for image in work.images:
                if image.file_path and image.file_path.exists():
                    # Copy original image
                    dest_path = images_dir / f"{work.id}_{image.id}{image.file_path.suffix}"
                    shutil.copy2(image.file_path, dest_path)
                    
                    # Copy thumbnail if exists
                    if image.thumbnail_path and image.thumbnail_path.exists():
                        thumb_dir = images_dir / "thumbnails"
                        thumb_dir.mkdir(exist_ok=True)
                        thumb_dest = thumb_dir / f"{work.id}_{image.id}_thumb{image.thumbnail_path.suffix}"
                        shutil.copy2(image.thumbnail_path, thumb_dest)
    
    async def _create_metadata_file(self, works: List[BlakeWork], output_dir: Path, 
                                  config: ExportConfig) -> None:
        """Create metadata file for the export."""
        metadata = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'format': config.format,
                'total_works': len(works),
                'include_images': config.include_images,
                'include_metadata': config.include_metadata,
                'include_analysis': config.include_analysis,
            },
            'works_summary': []
        }
        
        for work in works:
            work_summary = {
                'id': work.id,
                'title': work.metadata.title,
                'work_type': work.metadata.work_type,
                'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
                'source': work.metadata.source,
                'has_text': work.text_content is not None,
                'has_images': len(work.images) > 0,
                'is_processed': work.fully_processed,
                'provenance': work_provenance(work),
            }
            metadata['works_summary'].append(work_summary)
        
        # Save metadata
        import json
        metadata_file = output_dir / "export_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    
    async def _compress_export(self, output_dir: Path) -> Path:
        """Compress export directory."""
        import zipfile
        
        zip_path = output_dir.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir.parent)
                    zipf.write(file_path, arcname)
        
        # Remove original directory
        shutil.rmtree(output_dir)
        
        return zip_path
    
    async def export_work(self, work: BlakeWork, output_path: Path, 
                         format: str = "json") -> Path:
        """
        Export a single work.
        
        Args:
            work: BlakeWork to export
            output_path: Output file path
            format: Export format
            
        Returns:
            Path to exported file
        """
        if format not in self.exporters:
            raise ExportError(f"Unsupported export format: {format}")
        
        exporter = self.exporters[format]
        return await exporter.export_work(work, output_path)
    
    async def export_analysis_results(self, works: List[BlakeWork], 
                                    output_path: Path, format: str = "json") -> Path:
        """
        Export analysis results only.
        
        Args:
            works: List of BlakeWork objects
            output_path: Output file path
            format: Export format
            
        Returns:
            Path to exported file
        """
        if format not in self.exporters:
            raise ExportError(f"Unsupported export format: {format}")
        
        exporter = self.exporters[format]
        return await exporter.export_analysis_results(works, output_path)
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return list(self.exporters.keys())
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about export capabilities."""
        return {
            'supported_formats': self.get_supported_formats(),
            'export_directory': str(self.export_dir),
            'available_exporters': list(self.exporters.keys()),
        }
