"""
Main analyzer class that coordinates all analysis operations.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .text_analysis import TextAnalyzer
from .visual_analysis import VisualAnalyzer
from .cross_analysis import CrossAnalyzer
from .ontology import OntologyManager
from ..models import BlakeWork, AnalysisResult
from ..exceptions import AnalysisError
from ..utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)


class BlakeAnalyzer:
    """Main analyzer class that coordinates all analysis operations."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize Blake analyzer.
        
        Args:
            data_dir: Directory to store analysis results
        """
        self.data_dir = data_dir
        self.analysis_dir = data_dir / "analysis"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize analysis components
        self.text_analyzer = TextAnalyzer()
        self.visual_analyzer = VisualAnalyzer()
        self.cross_analyzer = CrossAnalyzer()
        self.ontology_manager = OntologyManager(data_dir)
        
        # Mock metadata manager for testing compatibility
        self.metadata_manager = None
        
        logger.info(f"Initialized BlakeAnalyzer with data directory: {data_dir}")
    
    async def analyze_work(self, work: BlakeWork, 
                          analysis_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on a work.
        
        Args:
            work: BlakeWork to analyze
            analysis_types: Types of analysis to perform. If None, performs all analyses
            
        Returns:
            Dictionary of analysis results
        """
        logger.info(f"Starting analysis for work: {work.id}")
        
        if analysis_types is None:
            analysis_types = ['text', 'visual', 'cross', 'ontology']
        
        results = {}
        
        try:
            # Text analysis
            if 'text' in analysis_types and work.text_content:
                logger.info(f"Performing text analysis for work: {work.id}")
                text_results = await self.text_analyzer.analyze_work(work)
                results['text_analysis'] = text_results
                
                # Save text analysis results
                await self._save_analysis_result(work.id, 'text_analysis', text_results, work.metadata.title)
            
            # Visual analysis
            if 'visual' in analysis_types and work.images:
                logger.info(f"Performing visual analysis for work: {work.id}")
                visual_results = {}
                
                for image in work.images:
                    image_results = await self.visual_analyzer.analyze_image(image)
                    visual_results[image.id] = image_results
                
                results['visual_analysis'] = visual_results
                
                # Save visual analysis results
                await self._save_analysis_result(work.id, 'visual_analysis', visual_results, work.metadata.title)
            
            # Cross analysis
            if 'cross' in analysis_types and work.text_content and work.images:
                logger.info(f"Performing cross-analysis for work: {work.id}")
                cross_results = await self.cross_analyzer.analyze_work(work)
                results['cross_analysis'] = cross_results
                
                # Save cross analysis results
                await self._save_analysis_result(work.id, 'cross_analysis', cross_results, work.metadata.title)
            
            # Use 'ontology' in analysis_types to trigger it
            if 'ontology' in analysis_types:
                logger.info(f"Performing ontological analysis for work: {work.id}")
                ontology_results = await self.ontology_manager.analyze_work(work)
                results['ontological_analysis'] = ontology_results
                await self._save_analysis_result(work.id, 'ontological_analysis', ontology_results, work.metadata.title)
            
            # Update work with analysis results
            work.text_analysis.update(results.get('text_analysis', {}))
            work.visual_analysis.update(results.get('visual_analysis', {}))
            work.cross_analysis.update(results.get('cross_analysis', {}))
            work.ontological_analysis.update(results.get('ontological_analysis', {}))
            
            # Mark as fully processed
            work.fully_processed = True
            
            logger.info(f"Completed analysis for work: {work.id}")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing work {work.id}: {e}")
            work.processing_errors.append(str(e))
            raise AnalysisError(f"Failed to analyze work {work.id}: {e}")
    
    async def analyze_multiple_works(self, works: List[BlakeWork], 
                                   analysis_types: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple works.
        
        Args:
            works: List of BlakeWork objects to analyze
            analysis_types: Types of analysis to perform
            
        Returns:
            Dictionary mapping work IDs to analysis results
        """
        logger.info(f"Starting analysis for {len(works)} works")
        
        results = {}
        
        # Process works in parallel (with some concurrency limit)
        semaphore = asyncio.Semaphore(3)  # Limit concurrent analyses
        
        async def analyze_single_work(work):
            async with semaphore:
                try:
                    work_results = await self.analyze_work(work, analysis_types)
                    return work.id, work_results
                except Exception as e:
                    logger.error(f"Error analyzing work {work.id}: {e}")
                    return work.id, {'error': str(e)}
        
        # Run analyses concurrently
        tasks = [analyze_single_work(work) for work in works]
        work_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in work_results:
            if isinstance(result, tuple):
                work_id, work_result = result
                results[work_id] = work_result
            else:
                logger.error(f"Unexpected result type: {type(result)}")
        
        logger.info(f"Completed analysis for {len(results)} works")
        return results
    
    async def compare_works(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """
        Compare multiple works for similarities and differences.
        
        Args:
            works: List of BlakeWork objects to compare
            
        Returns:
            Dictionary of comparison results
        """
        logger.info(f"Comparing {len(works)} works")
        
        try:
            results = {}
            
            # Text comparison
            text_works = [w for w in works if w.text_content]
            if len(text_works) >= 2:
                text_comparison = await self.text_analyzer.compare_works(text_works)
                results['text_comparison'] = text_comparison
            
            # Visual comparison
            visual_works = [w for w in works if w.images]
            if len(visual_works) >= 2:
                all_images = []
                for work in visual_works:
                    all_images.extend(work.images)
                
                if len(all_images) >= 2:
                    visual_comparison = await self.visual_analyzer.compare_images(all_images)
                    results['visual_comparison'] = visual_comparison
            
            # Thematic comparison
            thematic_comparison = await self._compare_themes(works)
            results['thematic_comparison'] = thematic_comparison
            
            # Chronological analysis
            chronological_analysis = await self._analyze_chronological_development(works)
            results['chronological_analysis'] = chronological_analysis
            
            logger.info(f"Completed comparison of {len(works)} works")
            return results
            
        except Exception as e:
            logger.error(f"Error comparing works: {e}")
            raise AnalysisError(f"Failed to compare works: {e}")
    
    async def _compare_themes(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """Compare themes across works."""
        all_themes = []
        work_themes = {}
        
        for work in works:
            themes = work.metadata.themes
            all_themes.extend(themes)
            work_themes[work.id] = themes
        
        # Count theme frequencies
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        # Find common themes
        common_themes = [theme for theme, count in theme_counts.items() if count > 1]
        
        # Find unique themes per work
        unique_themes = {}
        for work_id, themes in work_themes.items():
            unique_themes[work_id] = [theme for theme in themes if theme_counts[theme] == 1]
        
        return {
            'all_themes': list(set(all_themes)),
            'theme_frequencies': theme_counts,
            'common_themes': common_themes,
            'unique_themes_per_work': unique_themes,
        }
    
    async def _analyze_chronological_development(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """Analyze chronological development across works."""
        # Sort works by creation date
        dated_works = [(work, work.metadata.creation_date) for work in works 
                      if work.metadata.creation_date]
        dated_works.sort(key=lambda x: x[1])
        
        if len(dated_works) < 2:
            return {'error': 'Need at least 2 dated works for chronological analysis'}
        
        # Analyze theme evolution
        theme_evolution = {}
        for work, date in dated_works:
            for theme in work.metadata.themes:
                if theme not in theme_evolution:
                    theme_evolution[theme] = []
                theme_evolution[theme].append({
                    'work_id': work.id,
                    'date': date.isoformat(),
                    'title': work.metadata.title
                })
        
        # Analyze stylistic evolution
        stylistic_evolution = []
        for work, date in dated_works:
            if work.text_analysis:
                style_data = work.text_analysis.get('style', {})
                stylistic_evolution.append({
                    'work_id': work.id,
                    'date': date.isoformat(),
                    'title': work.metadata.title,
                    'avg_word_length': style_data.get('avg_word_length', 0),
                    'avg_sentence_length': style_data.get('avg_sentence_length', 0),
                    'vocabulary_richness': work.text_analysis.get('basic_stats', {}).get('vocabulary_richness', 0)
                })
        
        return {
            'dated_works': len(dated_works),
            'date_range': {
                'earliest': dated_works[0][1].isoformat(),
                'latest': dated_works[-1][1].isoformat()
            },
            'theme_evolution': theme_evolution,
            'stylistic_evolution': stylistic_evolution,
        }
    
    async def _save_analysis_result(self, work_id: str, analysis_type: str, 
                                  results: Dict[str, Any], work_title: str = "") -> None:
        """Save analysis results to file."""
        try:
            safe_title = sanitize_filename(work_title)
            filename = f"{work_id}_{safe_title}_{analysis_type}.json" if safe_title else f"{work_id}_{analysis_type}.json"
            result_file = self.analysis_dir / filename
            
            import json
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug(f"Saved {analysis_type} results for work {work_id}")
            
        except Exception as e:
            logger.error(f"Error saving analysis results for work {work_id}: {e}")
    
    async def load_analysis_result(self, work_id: str, analysis_type: str) -> Optional[Dict[str, Any]]:
        """Load analysis results from file."""
        try:
            result_file = self.analysis_dir / f"{work_id}_{analysis_type}.json"
            
            if not result_file.exists():
                return None
            
            import json
            with open(result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            return results
            
        except Exception as e:
            logger.error(f"Error loading analysis results for work {work_id}: {e}")
            return None
    
    def get_analysis_summary(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """Get summary of analysis results across works."""
        summary = {
            'total_works': len(works),
            'analyzed_works': 0,
            'analysis_types': {
                'text': 0,
                'visual': 0,
                'cross': 0
            },
            'common_themes': {},
            'stylistic_patterns': {},
            'visual_patterns': {}
        }
        
        all_themes = []
        all_style_data = []
        all_visual_data = []
        
        for work in works:
            if work.fully_processed:
                summary['analyzed_works'] += 1
            
            # Count analysis types
            if work.text_analysis:
                summary['analysis_types']['text'] += 1
                all_themes.extend(work.metadata.themes)
                
                # Collect style data
                style_data = work.text_analysis.get('style', {})
                if style_data:
                    all_style_data.append(style_data)
            
            if work.visual_analysis:
                summary['analysis_types']['visual'] += 1
                
                # Collect visual data
                for image_id, image_analysis in work.visual_analysis.items():
                    if isinstance(image_analysis, dict):
                        all_visual_data.append(image_analysis)
            
            if work.cross_analysis:
                summary['analysis_types']['cross'] += 1
        
        # Analyze common themes
        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        summary['common_themes'] = dict(sorted(theme_counts.items(), 
                                             key=lambda x: x[1], reverse=True)[:10])
        
        # Analyze stylistic patterns
        if all_style_data:
            avg_word_lengths = [data.get('avg_word_length', 0) for data in all_style_data]
            avg_sentence_lengths = [data.get('avg_sentence_length', 0) for data in all_style_data]
            
            summary['stylistic_patterns'] = {
                'avg_word_length': sum(avg_word_lengths) / len(avg_word_lengths) if avg_word_lengths else 0,
                'avg_sentence_length': sum(avg_sentence_lengths) / len(avg_sentence_lengths) if avg_sentence_lengths else 0,
            }
        
        # Analyze visual patterns
        if all_visual_data:
            # This would be more sophisticated in practice
            summary['visual_patterns'] = {
                'total_images_analyzed': len(all_visual_data),
            }
        
        return summary

