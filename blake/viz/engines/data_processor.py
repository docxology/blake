"""
Data Processing Engine

High-performance data processing pipeline for visualization preparation.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter
import json

from ..models import TextData, ImageData, TemporalData, NetworkData

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes raw data for visualization."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize data processor.
        
        Args:
            data_dir: Directory containing Blake data
        """
        self.data_dir = data_dir
        self.cache_dir = data_dir / "visualization_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized DataProcessor with data directory: {data_dir}")
    
    async def prepare_text_data(self, works: List[Any]) -> TextData:
        """
        Prepare text data for visualization.
        
        Args:
            works: List of BlakeWork objects
            
        Returns:
            Processed text data
        """
        logger.info(f"Preparing text data for {len(works)} works")
        
        texts = []
        metadata = []
        word_frequencies = {}
        sentiment_scores = []
        topics = []
        entities = []
        
        # Collect all text data
        all_words_for_freq = []  # Collect words for frequency computation
        for work in works:
            if work.text_content:
                texts.append(work.text_content)
                metadata.append({
                    'work_id': work.id,
                    'title': work.metadata.title,
                    'work_type': work.metadata.work_type,
                    'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
                    'themes': work.metadata.themes
                })
                
                # Extract analysis results if available
                if work.text_analysis and 'word_frequencies' in work.text_analysis:
                    # Use pre-computed word frequencies
                    for word, freq in work.text_analysis['word_frequencies'].items():
                        word_frequencies[word] = word_frequencies.get(word, 0) + freq
                else:
                    # Compute from raw text
                    import re
                    words = re.findall(r'\b[a-zA-Z]{3,}\b', work.text_content.lower())
                    all_words_for_freq.extend(words)
                
                if work.text_analysis:
                    # Sentiment scores
                    if 'sentiment' in work.text_analysis:
                        sentiment_scores.append(work.text_analysis['sentiment'].get('compound', 0.0))
                    else:
                        # Compute simple sentiment estimate
                        sentiment_scores.append(0.0)  # Neutral default
                    
                    # Topics
                    if 'topics' in work.text_analysis:
                        topics.extend(work.text_analysis['topics'])
                    
                    # Entities
                    if 'entities' in work.text_analysis:
                        entities.extend(work.text_analysis['entities'])
                else:
                    sentiment_scores.append(0.0)  # Neutral default
        
        # If word_frequencies is empty, compute from collected words
        if not word_frequencies and all_words_for_freq:
            # Basic stopwords
            stopwords = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
                        'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
                        'how', 'its', 'may', 'new', 'now', 'old', 'see', 'way', 'who', 'boy',
                        'did', 'she', 'too', 'use', 'that', 'with', 'have', 'this', 'will',
                        'your', 'from', 'they', 'been', 'call', 'each', 'into', 'time',
                        'very', 'when', 'come', 'made', 'find', 'more', 'long', 'what',
                        'other', 'about', 'their', 'would', 'there', 'could', 'which', 'these'}
            filtered_words = [w for w in all_words_for_freq if w not in stopwords]
            word_freq_counter = Counter(filtered_words)
            word_frequencies = dict(word_freq_counter.most_common(200))
        
        # Calculate stylistic features
        avg_word_length = 0.0
        avg_sentence_length = 0.0
        vocabulary_richness = 0.0
        
        if texts:
            total_words = 0
            total_chars = 0
            total_sentences = 0
            unique_words = set()
            
            for text in texts:
                words = text.split()
                sentences = text.split('.')
                
                total_words += len(words)
                total_chars += sum(len(word) for word in words)
                total_sentences += len(sentences)
                unique_words.update(words)
            
            avg_word_length = total_chars / total_words if total_words > 0 else 0.0
            avg_sentence_length = total_words / total_sentences if total_sentences > 0 else 0.0
            vocabulary_richness = len(unique_words) / total_words if total_words > 0 else 0.0
        
        return TextData(
            texts=texts,
            metadata=metadata,
            word_frequencies=word_frequencies,
            sentiment_scores=sentiment_scores,
            topics=topics,
            entities=entities,
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            vocabulary_richness=vocabulary_richness
        )
    
    async def prepare_image_data(self, works: List[Any]) -> ImageData:
        """
        Prepare image data for visualization.
        
        Args:
            works: List of BlakeWork objects
            
        Returns:
            Processed image data
        """
        logger.info(f"Preparing image data for {len(works)} works")
        
        images = []
        metadata = []
        dominant_colors = []
        color_histograms = []
        brightness_scores = []
        contrast_scores = []
        composition_scores = []
        golden_ratio_scores = []
        
        # Collect all image data
        for work in works:
            for image in work.images:
                image_data = {
                    'image_id': image.id,
                    'work_id': work.id,
                    'title': image.title,
                    'file_path': str(image.file_path),
                    'width': image.width,
                    'height': image.height
                }
                images.append(image_data)
                
                metadata.append({
                    'image_id': image.id,
                    'work_id': work.id,
                    'title': work.metadata.title,
                    'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else None,
                    'themes': work.metadata.themes
                })
                
                # Extract visual analysis results if available
                if work.visual_analysis and image.id in work.visual_analysis:
                    analysis = work.visual_analysis[image.id]
                    
                    # Color data
                    if 'dominant_colors' in analysis:
                        dominant_colors.append(analysis['dominant_colors'])
                    else:
                        dominant_colors.append([])
                    
                    if 'color_histogram' in analysis:
                        color_histograms.append(analysis['color_histogram'])
                    else:
                        color_histograms.append({})
                    
                    # Brightness and contrast
                    brightness_scores.append(analysis.get('brightness', 0.0))
                    contrast_scores.append(analysis.get('contrast', 0.0))
                    
                    # Composition data
                    composition_scores.append(analysis.get('composition', {}))
                    golden_ratio_scores.append(analysis.get('golden_ratio_score', 0.0))
        
        # Calculate similarity matrix (simplified)
        similarity_matrix = []
        for i in range(len(images)):
            row = []
            for j in range(len(images)):
                if i == j:
                    row.append(1.0)
                else:
                    # Simple similarity based on color overlap
                    colors_i = set(dominant_colors[i]) if i < len(dominant_colors) else set()
                    colors_j = set(dominant_colors[j]) if j < len(dominant_colors) else set()
                    
                    if colors_i and colors_j:
                        similarity = len(colors_i.intersection(colors_j)) / len(colors_i.union(colors_j))
                    else:
                        similarity = 0.0
                    
                    row.append(similarity)
            similarity_matrix.append(row)
        
        # Simple clustering (assign to clusters based on similarity)
        clusters = [0] * len(images)  # Simplified clustering
        cluster_id = 0
        for i in range(len(images)):
            if clusters[i] == 0:  # Not yet assigned
                clusters[i] = cluster_id
                for j in range(i + 1, len(images)):
                    if similarity_matrix[i][j] > 0.5:  # Similarity threshold
                        clusters[j] = cluster_id
                cluster_id += 1
        
        return ImageData(
            images=images,
            metadata=metadata,
            dominant_colors=dominant_colors,
            color_histograms=color_histograms,
            brightness_scores=brightness_scores,
            contrast_scores=contrast_scores,
            composition_scores=composition_scores,
            golden_ratio_scores=golden_ratio_scores,
            similarity_matrix=similarity_matrix,
            clusters=clusters
        )
    
    async def prepare_temporal_data(self, works: List[Any]) -> TemporalData:
        """
        Prepare temporal data for visualization.
        
        Args:
            works: List of BlakeWork objects
            
        Returns:
            Processed temporal data
        """
        logger.info(f"Preparing temporal data for {len(works)} works")
        
        work_data = []
        dates = []
        timeline_points = []
        periods = []
        theme_evolution = {}
        style_evolution = []
        
        # Sort works by creation date (include works without dates)
        dated_works = []
        for work in works:
            if work.metadata.creation_date:
                dated_works.append((work, work.metadata.creation_date))
            else:
                # Use a default date for works without creation dates
                from datetime import datetime
                default_date = datetime(1800, 1, 1)  # Default to 1800
                dated_works.append((work, default_date))
        
        dated_works.sort(key=lambda x: x[1])
        
        for work, date in dated_works:
            work_data.append({
                'work_id': work.id,
                'title': work.metadata.title,
                'work_type': work.metadata.work_type,
                'themes': work.metadata.themes,
                'period': work.metadata.period
            })
            dates.append(date)
            
            # Timeline points
            timeline_points.append({
                'work_id': work.id,
                'title': work.metadata.title,
                'date': date.isoformat(),
                'work_type': work.metadata.work_type,
                'themes': work.metadata.themes
            })
            
            # Theme evolution
            for theme in work.metadata.themes:
                if theme not in theme_evolution:
                    theme_evolution[theme] = []
                theme_evolution[theme].append({
                    'work_id': work.id,
                    'title': work.metadata.title,
                    'date': date.isoformat()
                })
            
            # Style evolution
            if work.text_analysis:
                style_data = work.text_analysis.get('style', {})
                style_evolution.append({
                    'work_id': work.id,
                    'title': work.metadata.title,
                    'date': date.isoformat(),
                    'avg_word_length': style_data.get('avg_word_length', 0),
                    'avg_sentence_length': style_data.get('avg_sentence_length', 0),
                    'vocabulary_richness': work.text_analysis.get('basic_stats', {}).get('vocabulary_richness', 0)
                })
        
        # Identify creative periods (simplified)
        if len(dates) > 1:
            # Group works by decade
            decade_groups = {}
            for work, date in dated_works:
                decade = (date.year // 10) * 10
                if decade not in decade_groups:
                    decade_groups[decade] = []
                decade_groups[decade].append(work)
            
            for decade, decade_works in decade_groups.items():
                periods.append({
                    'period': f"{decade}s",
                    'start_year': decade,
                    'end_year': decade + 9,
                    'work_count': len(decade_works),
                    'works': [w.id for w in decade_works]
                })
        
        return TemporalData(
            works=work_data,
            dates=dates,
            timeline_points=timeline_points,
            periods=periods,
            theme_evolution=theme_evolution,
            style_evolution=style_evolution
        )
    
    async def prepare_network_data(self, works: List[Any]) -> NetworkData:
        """
        Prepare network data for visualization.
        
        Args:
            works: List of BlakeWork objects
            
        Returns:
            Processed network data
        """
        logger.info(f"Preparing network data for {len(works)} works")
        
        nodes = []
        edges = []
        
        # Create nodes for works
        for work in works:
            nodes.append({
                'id': work.id,
                'label': work.metadata.title,
                'type': 'work',
                'work_type': work.metadata.work_type,
                'themes': work.metadata.themes,
                'creation_date': work.metadata.creation_date.isoformat() if work.metadata.creation_date else None
            })
        
        # Create edges based on theme similarity
        for i, work1 in enumerate(works):
            for j, work2 in enumerate(works[i+1:], i+1):
                # Calculate theme similarity
                themes1 = set(work1.metadata.themes)
                themes2 = set(work2.metadata.themes)
                
                if themes1 and themes2:
                    similarity = len(themes1.intersection(themes2)) / len(themes1.union(themes2))
                    
                    if similarity > 0.1:  # Threshold for connection
                        edges.append({
                            'source': work1.id,
                            'target': work2.id,
                            'weight': similarity,
                            'type': 'thematic_similarity'
                        })
        
        # Calculate network properties
        node_degrees = [0] * len(nodes)
        for edge in edges:
            try:
                source_idx = next(i for i, node in enumerate(nodes) if node['id'] == edge['source'])
                target_idx = next(i for i, node in enumerate(nodes) if node['id'] == edge['target'])
                node_degrees[source_idx] += 1
                node_degrees[target_idx] += 1
            except StopIteration:
                # Skip edges with missing nodes
                continue
        
        # Simple clustering coefficient calculation
        clustering_coefficients = []
        # Create a mapping from node ID to index for O(1) lookups
        node_id_to_idx = {n['id']: i for i, n in enumerate(nodes)}
        
        # Build adjacency list (using indices)
        adj = {i: set() for i in range(len(nodes))}
        for edge in edges:
            if edge['source'] in node_id_to_idx and edge['target'] in node_id_to_idx:
                u, v = node_id_to_idx[edge['source']], node_id_to_idx[edge['target']]
                adj[u].add(v)
                adj[v].add(u) # Treat as undirected for clustering coeff
        
        for i in range(len(nodes)):
            neighbors = list(adj[i])
            
            if len(neighbors) < 2:
                clustering_coefficients.append(0.0)
            else:
                # Count triangles
                triangles = 0
                for idx_j, j in enumerate(neighbors):
                    for k in neighbors[idx_j+1:]:
                        if k in adj[j]:
                            triangles += 1
                
                possible_triangles = len(neighbors) * (len(neighbors) - 1) / 2
                clustering_coefficients.append(triangles / possible_triangles if possible_triangles > 0 else 0.0)
        
        # Simple centrality scores (degree centrality)
        max_degree = max(node_degrees) if node_degrees and max(node_degrees) > 0 else 1
        degree_centrality = [d / max_degree for d in node_degrees]
        
        # Simple community detection (connected components)
        communities = [0] * len(nodes)
        community_id = 0
        visited = [False] * len(nodes)
        
        def dfs(node_idx):
            visited[node_idx] = True
            communities[node_idx] = community_id
            
            for edge in edges:
                if edge['source'] == nodes[node_idx]['id']:
                    target_idx = next(i for i, n in enumerate(nodes) if n['id'] == edge['target'])
                    if not visited[target_idx]:
                        dfs(target_idx)
                elif edge['target'] == nodes[node_idx]['id']:
                    source_idx = next(i for i, n in enumerate(nodes) if n['id'] == edge['source'])
                    if not visited[source_idx]:
                        dfs(source_idx)
        
        for i in range(len(nodes)):
            if not visited[i]:
                dfs(i)
                community_id += 1
        
        return NetworkData(
            nodes=nodes,
            edges=edges,
            node_degrees=node_degrees,
            clustering_coefficients=clustering_coefficients,
            centrality_scores={'degree': degree_centrality},
            positions={},  # Will be calculated by layout algorithm
            communities=communities
        )
