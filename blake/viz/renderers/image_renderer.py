"""
Image-based visualization renderer.

Handles all image-related visualizations including color analysis,
composition analysis, and image similarity networks.
"""

import logging
from typing import Dict, Any, List, Optional
import json

from ..models import ImageData, VisualizationConfig

logger = logging.getLogger(__name__)


class ImageRenderer:
    """Renders image-based visualizations."""
    
    def __init__(self):
        """Initialize image renderer."""
        self.supported_types = [
            'color_palette',
            'color_evolution',
            'color_distribution',
            'composition_analysis',
            'golden_ratio_analysis',
            'image_similarity_network',
            'image_clustering'
        ]
        logger.info("Initialized ImageRenderer")
    
    async def render_color_palette(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render color palette visualization."""
        logger.info("Rendering color palette visualization")
        
        # Extract dominant colors
        all_colors = []
        for img_colors in data.dominant_colors:
            all_colors.extend(img_colors)
            
        # Count color frequencies
        from collections import Counter
        color_counts = Counter(all_colors)
        
        # Get top colors
        top_colors = color_counts.most_common(20)
        
        # Generate plot if output_path provided
        saved_path = None
        if config.output_path:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                plt.figure(figsize=(12, 6))
                
                # Create bar chart of colors
                colors = [c[0] for c in top_colors]
                counts = [c[1] for c in top_colors]
                
                plt.bar(range(len(colors)), counts, color=colors)
                plt.title(config.title or 'Dominant Color Palette')
                plt.xlabel('Color Hex')
                plt.ylabel('Frequency')
                plt.xticks([])  # Hide x ticks as they are just colors
                
                # Ensure directory exists
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path)
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved color palette to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate color palette plot: {e}")

        # Create palette data
        palette_data = {
            'colors': [{'color': color, 'count': count} for color, count in top_colors],
            'total_colors': len(all_colors),
            'unique_colors': len(color_counts),
            'config': {
                'title': config.title or 'Color Palette',
                'width': config.width or 800,
                'height': config.height or 600
            },
            'saved_path': saved_path
        }
        
        return {
            'type': 'color_palette',
            'data': palette_data,
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images)
            }
        }
    
    async def render_color_evolution(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render color evolution timeline."""
        logger.info("Rendering color evolution visualization")
        
        # Create evolution data
        evolution_data = []
        for i, (image, colors) in enumerate(zip(data.images, data.dominant_colors)):
            evolution_data.append({
                'image_id': image['image_id'],
                'work_id': image['work_id'],
                'title': image['title'],
                'dominant_colors': colors,
                'brightness': data.brightness_scores[i] if i < len(data.brightness_scores) else 0,
                'contrast': data.contrast_scores[i] if i < len(data.contrast_scores) else 0
            })
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and evolution_data:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
                
                indices = list(range(len(evolution_data)))
                brightness = [e['brightness'] for e in evolution_data]
                contrast = [e['contrast'] for e in evolution_data]
                
                # Brightness plot
                ax1.plot(indices, brightness, 'o-', color='gold', linewidth=2, markersize=8, label='Brightness')
                ax1.fill_between(indices, brightness, alpha=0.3, color='gold')
                ax1.set_ylabel('Brightness', fontsize=12)
                ax1.set_title(config.title or 'William Blake - Color Evolution', fontsize=14, fontweight='bold')
                ax1.grid(alpha=0.3)
                ax1.legend(loc='upper right')
                
                # Contrast plot
                ax2.plot(indices, contrast, 's-', color='purple', linewidth=2, markersize=8, label='Contrast')
                ax2.fill_between(indices, contrast, alpha=0.3, color='purple')
                ax2.set_xlabel('Image Sequence', fontsize=12)
                ax2.set_ylabel('Contrast', fontsize=12)
                ax2.grid(alpha=0.3)
                ax2.legend(loc='upper right')
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved color evolution to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate color evolution plot: {e}")
        
        return {
            'type': 'color_evolution',
            'data': {
                'evolution': evolution_data,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Color Evolution Timeline'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images)
            }
        }
    
    async def render_color_distribution(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render color distribution heatmap."""
        logger.info("Rendering color distribution visualization")
        
        # Create distribution data
        distribution_data = []
        for i, (image, colors) in enumerate(zip(data.images, data.dominant_colors)):
            distribution_data.append({
                'image_id': image['image_id'],
                'work_id': image['work_id'],
                'title': image['title'],
                'colors': colors,
                'x': i % 5,  # Simple grid layout
                'y': i // 5
            })
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and distribution_data:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                from collections import Counter
                
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Collect all colors across images
                all_colors = []
                for item in distribution_data:
                    all_colors.extend(item['colors'] if item['colors'] else [])
                
                if all_colors:
                    color_counts = Counter(all_colors)
                    top_colors = color_counts.most_common(20)
                    
                    colors = [c[0] for c in top_colors]
                    counts = [c[1] for c in top_colors]
                    
                    # Create pie chart
                    wedges, texts, autotexts = ax.pie(counts, labels=None, colors=colors,
                                                       autopct='%1.0f%%', startangle=90)
                    ax.legend(wedges, colors, title='Colors', loc='center left', 
                             bbox_to_anchor=(1, 0.5), fontsize=8)
                else:
                    ax.text(0.5, 0.5, 'No color data available', ha='center', va='center',
                           fontsize=14, transform=ax.transAxes)
                
                ax.set_title(config.title or 'William Blake - Color Distribution', fontsize=14, fontweight='bold')
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved color distribution to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate color distribution plot: {e}")
        
        return {
            'type': 'color_distribution',
            'data': {
                'distribution': distribution_data,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Color Distribution Heatmap'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images)
            }
        }
    
    async def render_composition_analysis(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render composition analysis grid."""
        logger.info("Rendering composition analysis visualization")
        
        # Create composition data
        composition_data = []
        for i, (image, composition) in enumerate(zip(data.images, data.composition_scores)):
            composition_data.append({
                'image_id': image['image_id'],
                'work_id': image['work_id'],
                'title': image['title'],
                'width': image['width'],
                'height': image['height'],
                'composition': composition,
                'golden_ratio_score': data.golden_ratio_scores[i] if i < len(data.golden_ratio_scores) else 0
            })
        
        return {
            'type': 'composition_analysis',
            'data': {
                'compositions': composition_data,
                'config': {
                    'title': config.get('title', 'Composition Analysis Grid'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images)
            }
        }
    
    async def render_golden_ratio_analysis(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render golden ratio analysis."""
        logger.info("Rendering golden ratio analysis visualization")
        
        # Calculate golden ratio statistics
        avg_golden_ratio = sum(data.golden_ratio_scores) / len(data.golden_ratio_scores) if data.golden_ratio_scores else 0
        high_ratio_count = sum(1 for score in data.golden_ratio_scores if score > 0.8)
        
        # Create analysis data
        analysis_data = []
        for i, (image, score) in enumerate(zip(data.images, data.golden_ratio_scores)):
            analysis_data.append({
                'image_id': image['image_id'],
                'work_id': image['work_id'],
                'title': image['title'],
                'golden_ratio_score': score,
                'width': image['width'],
                'height': image['height'],
                'aspect_ratio': image['width'] / image['height'] if image['height'] > 0 else 1
            })
        
        return {
            'type': 'golden_ratio_analysis',
            'data': {
                'analysis': analysis_data,
                'statistics': {
                    'average_golden_ratio': avg_golden_ratio,
                    'high_ratio_count': high_ratio_count,
                    'total_images': len(data.images)
                },
                'config': {
                    'title': config.get('title', 'Golden Ratio Analysis'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images)
            }
        }
    
    async def render_image_similarity_network(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render image similarity network."""
        logger.info("Rendering image similarity network visualization")
        
        # Create network nodes
        nodes = []
        for image in data.images:
            nodes.append({
                'id': image['image_id'],
                'label': image['title'],
                'work_id': image['work_id'],
                'width': image['width'],
                'height': image['height']
            })
        
        # Create network edges based on similarity matrix
        edges = []
        for i in range(len(data.similarity_matrix)):
            for j in range(i + 1, len(data.similarity_matrix[i])):
                similarity = data.similarity_matrix[i][j]
                if similarity > 0.3:  # Threshold for connection
                    edges.append({
                        'source': data.images[i]['image_id'],
                        'target': data.images[j]['image_id'],
                        'weight': similarity
                    })
        
        return {
            'type': 'image_similarity_network',
            'data': {
                'nodes': nodes,
                'edges': edges,
                'config': {
                    'title': config.get('title', 'Image Similarity Network'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images),
                'edge_count': len(edges)
            }
        }
    
    async def render_image_clustering(self, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render image clustering visualization."""
        logger.info("Rendering image clustering visualization")
        
        # Create cluster data
        cluster_data = {}
        for i, (image, cluster) in enumerate(zip(data.images, data.clusters)):
            if cluster not in cluster_data:
                cluster_data[cluster] = []
            
            cluster_data[cluster].append({
                'image_id': image['image_id'],
                'work_id': image['work_id'],
                'title': image['title'],
                'width': image['width'],
                'height': image['height']
            })
        
        # Convert to list format
        clusters = [
            {
                'cluster_id': cluster_id,
                'images': images,
                'size': len(images)
            }
            for cluster_id, images in cluster_data.items()
        ]
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and clusters:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                import numpy as np
                
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Generate scatter plot with clusters
                cluster_colors = plt.cm.Set2(np.linspace(0, 1, len(clusters)))
                
                for i, cluster_info in enumerate(clusters):
                    cluster_id = cluster_info['cluster_id']
                    size = cluster_info['size']
                    
                    # Generate random positions within cluster boundaries
                    np.random.seed(cluster_id)  # Reproducible positions
                    x = np.random.randn(size) * 0.5 + i * 2
                    y = np.random.randn(size) * 0.5
                    
                    ax.scatter(x, y, c=[cluster_colors[i]], s=200, alpha=0.7,
                              label=f'Cluster {cluster_id} ({size} images)', edgecolors='black')
                
                ax.set_xlabel('Cluster Distribution', fontsize=12)
                ax.set_ylabel('Image Grouping', fontsize=12)
                ax.set_title(config.title or 'William Blake - Image Clustering', fontsize=14, fontweight='bold')
                ax.legend(loc='upper right', fontsize=9)
                ax.grid(alpha=0.3)
                ax.set_xticks([])
                ax.set_yticks([])
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved image clustering to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate image clustering plot: {e}")
        
        return {
            'type': 'image_clustering',
            'data': {
                'clusters': clusters,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Image Clustering'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'ImageRenderer',
                'image_count': len(data.images),
                'cluster_count': len(clusters)
            }
        }
    
    async def render(self, viz_type: str, data: ImageData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render visualization based on type."""
        if viz_type not in self.supported_types:
            raise ValueError(f"Unsupported visualization type: {viz_type}")
        
        render_method = getattr(self, f'render_{viz_type}', None)
        if not render_method:
            raise ValueError(f"Renderer method not found for type: {viz_type}")
        
        return await render_method(data, config)
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported visualization types."""
        return self.supported_types.copy()

