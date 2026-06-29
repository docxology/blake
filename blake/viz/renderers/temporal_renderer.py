"""
Temporal visualization renderer.

Handles all time-based visualizations including timelines,
chronological analysis, and development phases.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models import TemporalData, VisualizationConfig

logger = logging.getLogger(__name__)


class TemporalRenderer:
    """Renders temporal visualizations."""
    
    def __init__(self):
        """Initialize temporal renderer."""
        self.supported_types = [
            'work_timeline',
            'theme_evolution',
            'creative_periods',
            'chronological_network',
            'development_phases'
        ]
        logger.info("Initialized TemporalRenderer")
    
    async def render_work_timeline(self, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render work timeline visualization."""
        logger.info("Rendering work timeline visualization")
        
        # Create timeline data
        timeline_data = []
        for point in data.timeline_points:
            timeline_data.append({
                'work_id': point['work_id'],
                'title': point['title'],
                'date': point['date'],
                'work_type': point['work_type'],
                'themes': point['themes']
            })
        
        # Sort by date
        timeline_data.sort(key=lambda x: x['date'])
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and timeline_data:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                from datetime import datetime as dt
                
                fig, ax = plt.subplots(figsize=(14, 6))
                
                # Parse dates and create scatter plot
                dates = []
                titles = []
                for item in timeline_data:
                    try:
                        date = dt.fromisoformat(item['date'].replace('Z', '+00:00'))
                        dates.append(date.year)
                        titles.append(item['title'][:30] + '...' if len(item['title']) > 30 else item['title'])
                    except:
                        continue
                
                if dates:
                    colors = plt.cm.viridis([i / len(dates) for i in range(len(dates))])
                    ax.scatter(dates, range(len(dates)), c=colors, s=100, alpha=0.7)
                    
                    # Add work titles as labels
                    for i, (year, title) in enumerate(zip(dates, titles)):
                        ax.annotate(title, (year, i), xytext=(5, 0), textcoords='offset points',
                                   fontsize=8, va='center')
                    
                    ax.set_xlabel('Year', fontsize=12)
                    ax.set_ylabel('Works', fontsize=12)
                    ax.set_title(config.title or 'William Blake - Work Timeline', fontsize=14, fontweight='bold')
                    ax.grid(axis='x', alpha=0.3)
                    ax.set_yticks([])
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved work timeline to {saved_path}")
                
                # Save JSON data alongside PNG
                json_path = config.output_path.with_suffix('.json')
                import json
                with open(json_path, 'w') as f:
                    json.dump({'timeline': timeline_data}, f, indent=2, default=str)
                logger.info(f"Saved timeline data to {json_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate work timeline plot: {e}")
        
        return {
            'type': 'work_timeline',
            'data': {
                'timeline': timeline_data,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Work Timeline'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'TemporalRenderer',
                'work_count': len(timeline_data)
            }
        }
    
    async def render_theme_evolution(self, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render theme evolution visualization."""
        logger.info("Rendering theme evolution visualization")
        
        # Create theme evolution data
        theme_evolution = []
        for theme, works in data.theme_evolution.items():
            theme_evolution.append({
                'theme': theme,
                'works': works,
                'work_count': len(works)
            })
        
        # Sort by work count
        theme_evolution.sort(key=lambda x: x['work_count'], reverse=True)
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and theme_evolution:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Create horizontal bar chart of themes
                themes = [t['theme'][:20] for t in theme_evolution[:15]]  # Top 15 themes
                counts = [t['work_count'] for t in theme_evolution[:15]]
                
                colors = plt.cm.viridis([i / len(themes) for i in range(len(themes))])
                bars = ax.barh(range(len(themes)), counts, color=colors)
                ax.set_yticks(range(len(themes)))
                ax.set_yticklabels(themes)
                ax.invert_yaxis()
                ax.set_xlabel('Number of Works', fontsize=12)
                ax.set_title(config.title or 'William Blake - Theme Evolution', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)
                
                # Add count labels
                for bar, count in zip(bars, counts):
                    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                           str(count), va='center', fontsize=9)
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved theme evolution to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate theme evolution plot: {e}")
        
        return {
            'type': 'theme_evolution',
            'data': {
                'themes': theme_evolution,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Theme Evolution'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'TemporalRenderer',
                'theme_count': len(theme_evolution)
            }
        }
    
    async def render_creative_periods(self, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render creative periods visualization."""
        logger.info("Rendering creative periods visualization")
        
        # Create periods data
        periods_data = []
        for period in data.periods:
            periods_data.append({
                'period': period['period'],
                'start_year': period['start_year'],
                'end_year': period['end_year'],
                'work_count': period['work_count'],
                'works': period['works']
            })
        
        # Generate and save plot if output_path provided
        saved_path = None
        if config.output_path and periods_data:
            try:
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Create bar chart of periods
                periods = [p['period'] for p in periods_data]
                counts = [p['work_count'] for p in periods_data]
                start_years = [p['start_year'] for p in periods_data]
                
                colors = plt.cm.plasma([i / len(periods) for i in range(len(periods))])
                bars = ax.bar(periods, counts, color=colors, edgecolor='black', linewidth=0.5)
                
                ax.set_xlabel('Creative Period', fontsize=12)
                ax.set_ylabel('Number of Works', fontsize=12)
                ax.set_title(config.title or 'William Blake - Creative Periods', fontsize=14, fontweight='bold')
                ax.grid(axis='y', alpha=0.3)
                plt.xticks(rotation=45, ha='right')
                
                # Add count labels on bars
                for bar, count in zip(bars, counts):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           str(count), ha='center', fontsize=10, fontweight='bold')
                
                plt.tight_layout()
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=100, bbox_inches='tight', facecolor='white')
                plt.close()
                saved_path = str(config.output_path)
                logger.info(f"Saved creative periods to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate creative periods plot: {e}")
        
        return {
            'type': 'creative_periods',
            'data': {
                'periods': periods_data,
                'saved_path': saved_path,
                'config': {
                    'title': config.get('title', 'Creative Periods'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'TemporalRenderer',
                'period_count': len(periods_data)
            }
        }
    
    async def render_chronological_network(self, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render chronological network visualization."""
        logger.info("Rendering chronological network visualization")
        
        # Create network nodes
        nodes = []
        for work in data.works:
            nodes.append({
                'id': work['work_id'],
                'label': work['title'],
                'work_type': work['work_type'],
                'themes': work['themes']
            })
        
        # Create network edges based on temporal proximity
        edges = []
        for i, work1 in enumerate(data.works):
            for j, work2 in enumerate(data.works[i+1:], i+1):
                # Simple temporal connection (works within same period)
                if work1.get('period') == work2.get('period'):
                    edges.append({
                        'source': work1['work_id'],
                        'target': work2['work_id'],
                        'type': 'temporal_proximity'
                    })
        
        return {
            'type': 'chronological_network',
            'data': {
                'nodes': nodes,
                'edges': edges,
                'config': {
                    'title': config.get('title', 'Chronological Network'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 600)
                }
            },
            'metadata': {
                'renderer': 'TemporalRenderer',
                'work_count': len(nodes),
                'edge_count': len(edges)
            }
        }
    
    async def render_development_phases(self, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render development phases visualization."""
        logger.info("Rendering development phases visualization")
        
        # Create phases data
        phases_data = []
        for i, work in enumerate(data.works):
            phases_data.append({
                'work_id': work['work_id'],
                'title': work['title'],
                'phase': i // 5 + 1,  # Simple phase assignment
                'work_type': work['work_type'],
                'themes': work['themes']
            })
        
        # Group by phase
        phase_groups = {}
        for work in phases_data:
            phase = work['phase']
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(work)
        
        # Convert to list format
        phases = [
            {
                'phase': phase,
                'works': works,
                'work_count': len(works)
            }
            for phase, works in phase_groups.items()
        ]
        
        return {
            'type': 'development_phases',
            'data': {
                'phases': phases,
                'config': {
                    'title': config.get('title', 'Development Phases'),
                    'width': config.get('width', 800),
                    'height': config.get('height', 400)
                }
            },
            'metadata': {
                'renderer': 'TemporalRenderer',
                'phase_count': len(phases)
            }
        }
    
    async def render(self, viz_type: str, data: TemporalData, config: VisualizationConfig) -> Dict[str, Any]:
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

