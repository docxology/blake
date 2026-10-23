"""
Text-based visualization renderer.

Handles all text-related visualizations including word clouds,
sentiment analysis, and stylistic analysis.
"""

import logging
from typing import Dict, Any, List, Optional
import json

from ..models import TextData, VisualizationConfig

logger = logging.getLogger(__name__)


class TextRenderer:
    """Renders text-based visualizations."""
    
    def __init__(self):
        """Initialize text renderer."""
        self.supported_types = [
            'word_cloud',
            'frequency_chart', 
            'sentiment_timeline',
            'sentiment_heatmap',
            'style_evolution',
            'style_comparison'
        ]
        logger.info("Initialized TextRenderer")
    
    async def render_word_cloud(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render word cloud visualization."""
        logger.info("Rendering word cloud visualization")
        
        # Extract word frequencies
        word_freq = data.word_frequencies
        
        # Sort by frequency and take top words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
        
        # Create word cloud data structure
        word_cloud_data = {
            'words': [{'text': word, 'weight': freq} for word, freq in top_words],
            'total_words': len(word_freq),
            'unique_words': len(set(word_freq.keys())),
            'config': {
                'title': config.get('title', 'Word Cloud'),
                'width': config.get('width', 800),
                'height': config.get('height', 600),
                'max_words': config.get('max_words', 50)
            }
        }
        
        # Generate and save plot if output_path is provided
        saved_path = None
        if config.output_path and top_words:
            fig = None
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                # Create word cloud using font sizes proportional to frequency
                fig, ax = plt.subplots(figsize=(12, 8))
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 100)
                ax.axis('off')
                
                max_freq = max(freq for _, freq in top_words) if top_words else 1
                colors = plt.cm.viridis([i / len(top_words) for i in range(len(top_words))])
                
                # Position words in a spiral-like pattern
                import math
                for i, (word, freq) in enumerate(top_words[:30]):
                    # Spiral positioning
                    angle = i * 0.5
                    radius = 5 + i * 1.8
                    x = 50 + radius * math.cos(angle)
                    y = 50 + radius * math.sin(angle)
                    
                    # Font size based on frequency
                    font_size = 8 + (freq / max_freq) * 24
                    ax.text(x, y, word, fontsize=font_size, ha='center', va='center',
                           color=colors[i], fontweight='bold', alpha=0.8)
                
                ax.set_title(config.title or 'William Blake - Word Cloud', fontsize=14, fontweight='bold')
                
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                saved_path = str(config.output_path)
                logger.info(f"Saved word cloud to {saved_path}")
                
                # Save JSON data alongside PNG
                json_path = config.output_path.with_suffix('.json')
                import json
                with open(json_path, 'w') as f:
                    json.dump(word_cloud_data, f, indent=2, default=str)
                logger.info(f"Saved word cloud data to {json_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate word cloud plot: {e}")
                raise
            finally:
                if fig is not None:
                    plt.close(fig)

        word_cloud_data['saved_path'] = saved_path
        
        return {
            'type': 'word_cloud',
            'data': word_cloud_data,
            'metadata': {
                'renderer': 'TextRenderer',
                'timestamp': data.metadata[0].get('creation_date') if data.metadata else None,
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render_frequency_chart(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render frequency chart visualization."""
        logger.info("Rendering frequency chart visualization")
        
        # Extract word frequencies
        word_freq = data.word_frequencies
        
        # Sort by frequency and take top words
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Create frequency chart data
        chart_data = {
            'labels': [word for word, _ in top_words],
            'values': [freq for _, freq in top_words],
            'total_words': len(word_freq),
            'config': {
                'title': config.get('title', 'Word Frequency Chart'),
                'width': config.get('width', 800),
                'height': config.get('height', 400),
                'max_words': config.get('max_words', 20)
            }
        }
        
        # Generate and save plot if output_path is provided
        saved_path = None
        if config.output_path and top_words:
            fig = None
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                words = [word for word, _ in top_words]
                freqs = [freq for _, freq in top_words]
                
                # Create horizontal bar chart
                colors = plt.cm.plasma([i / len(words) for i in range(len(words))])
                bars = ax.barh(range(len(words)), freqs, color=colors)
                ax.set_yticks(range(len(words)))
                ax.set_yticklabels(words)
                ax.invert_yaxis()  # Highest frequency at top
                ax.set_xlabel('Frequency', fontsize=12)
                ax.set_title(config.title or 'William Blake - Word Frequency', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)
                
                # Add value labels
                for bar, freq in zip(bars, freqs):
                    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, 
                           str(freq), va='center', fontsize=9)
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                saved_path = str(config.output_path)
                logger.info(f"Saved frequency chart to {saved_path}")
                
                # Save JSON data alongside PNG
                json_path = config.output_path.with_suffix('.json')
                import json
                with open(json_path, 'w') as f:
                    json.dump(chart_data, f, indent=2, default=str)
                logger.info(f"Saved frequency chart data to {json_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate frequency chart plot: {e}")
                raise
            finally:
                if fig is not None:
                    plt.close(fig)

        chart_data['saved_path'] = saved_path
        
        return {
            'type': 'frequency_chart',
            'data': chart_data,
            'metadata': {
                'renderer': 'TextRenderer',
                'timestamp': data.metadata[0].get('creation_date') if data.metadata else None,
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render_sentiment_timeline(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render sentiment timeline visualization."""
        logger.info("Rendering sentiment timeline visualization")
        
        # Create timeline data from sentiment scores
        timeline_data = []
        for i, score in enumerate(data.sentiment_scores):
            timeline_data.append({
                'x': i,
                'y': score,
                'work_id': data.metadata[i]['work_id'] if i < len(data.metadata) else f'work_{i}',
                'title': data.metadata[i]['title'] if i < len(data.metadata) else f'Work {i+1}'
            })
        
        # Calculate sentiment statistics
        avg_sentiment = sum(data.sentiment_scores) / len(data.sentiment_scores) if data.sentiment_scores else 0
        positive_count = sum(1 for score in data.sentiment_scores if score > 0.1)
        negative_count = sum(1 for score in data.sentiment_scores if score < -0.1)
        
        # Generate and save plot if output_path is provided
        saved_path = None
        if config.output_path:
            fig = None
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')  # Non-interactive backend
                
                fig = plt.figure(figsize=(12, 6))
                plt.plot([d['x'] for d in timeline_data], [d['y'] for d in timeline_data], marker='o', linestyle='-', alpha=0.7)
                plt.axhline(y=0, color='r', linestyle='--', alpha=0.3)
                plt.title(config.title or 'Sentiment Timeline')
                plt.xlabel('Work Index')
                plt.ylabel('Sentiment Score')
                plt.grid(True, alpha=0.3)
                
                # Ensure directory exists
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path)
                plt.close(fig)
                saved_path = str(config.output_path)
                logger.info(f"Saved sentiment timeline to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate sentiment plot: {e}")
                raise
            finally:
                if fig is not None:
                    plt.close(fig)

        return {
            'type': 'sentiment_timeline',
            'data': {
                'timeline': timeline_data,
                'statistics': {
                    'average_sentiment': avg_sentiment,
                    'positive_works': positive_count,
                    'negative_works': negative_count,
                    'neutral_works': len(data.sentiment_scores) - positive_count - negative_count
                },
                'config': {
                    'title': config.title or 'Sentiment Timeline',
                    'width': config.width or 800,
                    'height': config.height or 400
                },
                'saved_path': saved_path
            },
            'metadata': {
                'renderer': 'TextRenderer',
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render_sentiment_heatmap(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render sentiment heatmap visualization."""
        logger.info("Rendering sentiment heatmap visualization")
        
        # Create heatmap data
        heatmap_data = []
        for i, score in enumerate(data.sentiment_scores):
            # Categorize sentiment
            if score > 0.1:
                category = 'positive'
            elif score < -0.1:
                category = 'negative'
            else:
                category = 'neutral'
            
            heatmap_data.append({
                'work_id': data.metadata[i]['work_id'] if i < len(data.metadata) else f'work_{i}',
                'title': data.metadata[i]['title'] if i < len(data.metadata) else f'Work {i+1}',
                'sentiment': score,
                'category': category,
                'x': i % 5,  # Simple grid layout
                'y': i // 5
            })
        
        return {
            'type': 'sentiment_heatmap',
            'data': {
                'heatmap': heatmap_data,
                'config': {
                    'title': config.get('title', 'Sentiment Heatmap'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'TextRenderer',
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render_style_evolution(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render style evolution visualization."""
        logger.info("Rendering style evolution visualization")
        
        # Create style evolution data
        evolution_data = []
        for i, metadata in enumerate(data.metadata):
            evolution_data.append({
                'work_id': metadata['work_id'],
                'title': metadata['title'],
                'date': metadata.get('creation_date'),
                'avg_word_length': data.avg_word_length,
                'avg_sentence_length': data.avg_sentence_length,
                'vocabulary_richness': data.vocabulary_richness
            })
        
        return {
            'type': 'style_evolution',
            'data': {
                'evolution': evolution_data,
                'config': {
                    'title': config.get('title', 'Style Evolution'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'TextRenderer',
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render_style_comparison(self, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render style comparison visualization."""
        logger.info("Rendering style comparison visualization")
        
        # Create style comparison data
        comparison_data = {
            'metrics': {
                'avg_word_length': data.avg_word_length,
                'avg_sentence_length': data.avg_sentence_length,
                'vocabulary_richness': data.vocabulary_richness
            },
            'works': [
                {
                    'work_id': metadata['work_id'],
                    'title': metadata['title'],
                    'work_type': metadata.get('work_type', 'unknown'),
                    'themes': metadata.get('themes', [])
                }
                for metadata in data.metadata
            ]
        }
        
        return {
            'type': 'style_comparison',
            'data': {
                'comparison': comparison_data,
                'config': {
                    'title': config.get('title', 'Style Comparison'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'TextRenderer',
                'work_count': len(data.metadata) if data.metadata else 0
            }
        }
    
    async def render(self, viz_type: str, data: TextData, config: VisualizationConfig) -> Dict[str, Any]:
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

