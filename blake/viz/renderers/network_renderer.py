"""
Network visualization renderer.

Handles all network-based visualizations including thematic networks,
concept maps, and influence networks.
"""

import logging
from typing import Dict, Any, List, Optional

from ..models import NetworkData, VisualizationConfig

logger = logging.getLogger(__name__)


class NetworkRenderer:
    """Renders network visualizations."""
    
    def __init__(self):
        """Initialize network renderer."""
        self.supported_types = [
            'thematic_network',
            'concept_map',
            'influence_network',
            'citation_network'
        ]
        logger.info("Initialized NetworkRenderer")
    
    async def render_thematic_network(self, data: NetworkData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render thematic network visualization."""
        logger.info("Rendering thematic network visualization")
        
        # Create network data
        network_data = {
            'nodes': data.nodes,
            'edges': data.edges,
            'statistics': {
                'node_count': len(data.nodes),
                'edge_count': len(data.edges),
                'average_degree': sum(data.node_degrees) / len(data.node_degrees) if data.node_degrees else 0,
                'clustering_coefficient': sum(data.clustering_coefficients) / len(data.clustering_coefficients) if data.clustering_coefficients else 0
            },
            'config': {
                'title': config.title or 'Thematic Network',
                'width': config.width or 800,
                'height': config.height or 600
            }
        }
        
        # Determine output path (config or default)
        saved_path = None
        if config.output_path:
            fig = None
            try:
                import networkx as nx
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                # Reconstruct graph from data
                G = nx.Graph() # Undirected for thematic similarity
                for node in data.nodes:
                    G.add_node(node['id'], **node)
                for edge in data.edges:
                    G.add_edge(edge['source'], edge['target'], weight=edge['weight'])
                
                fig = plt.figure(figsize=(12, 12))
                pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
                
                # Draw nodes
                nx.draw_networkx_nodes(G, pos, node_size=500, node_color='lightgreen', alpha=0.8)
                nx.draw_networkx_labels(G, pos, font_size=8)
                
                # Draw edges
                nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.5)
                
                plt.title(config.title or 'Thematic Network')
                plt.axis('off')
                
                # Ensure directory exists
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                saved_path = str(config.output_path)
                logger.info(f"Saved thematic network to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate thematic network plot: {e}")
                raise
            finally:
                if fig is not None:
                    plt.close(fig)

        return {
            'type': 'thematic_network',
            'data': {
                'network': network_data,
                'saved_path': saved_path
            },
            'metadata': {
                'renderer': 'NetworkRenderer',
                'node_count': len(data.nodes),
                'edge_count': len(data.edges)
            }
        }
    
    async def render_concept_map(self, data: NetworkData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render concept map visualization."""
        logger.info("Rendering concept map visualization")
        
        # Create concept map data
        concept_map_data = {
            'concepts': data.nodes,
            'relationships': data.edges,
            'centrality': data.centrality_scores,
            'config': {
                'title': config.title or 'Concept Map',
                'width': config.width or 800,
                'height': config.height or 600
            }
        }
        
        # Determine output path (config or default)
        saved_path = None
        if config.output_path:
            fig = None
            try:
                import networkx as nx
                import matplotlib.pyplot as plt
                import matplotlib
                matplotlib.use('Agg')
                
                # Reconstruct graph from data
                G = nx.MultiDiGraph()
                for node in data.nodes:
                    G.add_node(node['id'], **node)
                for edge in data.edges:
                    G.add_edge(edge['source'], edge['target'], **edge)
                
                fig = plt.figure(figsize=(12, 12))
                pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)
                
                # Draw nodes
                nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue', alpha=0.8)
                nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
                
                # Draw edges
                nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, alpha=0.5)
                
                plt.title(config.title or 'Concept Map')
                plt.axis('off')
                
                # Ensure directory exists
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                plt.savefig(config.output_path, dpi=300, bbox_inches='tight')
                plt.close(fig)
                saved_path = str(config.output_path)
                logger.info(f"Saved concept map to {saved_path}")
            except Exception as e:
                logger.error(f"Failed to generate concept map plot: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise
            finally:
                if fig is not None:
                    plt.close(fig)

        return {
            'type': 'concept_map',
            'data': {
                'map': concept_map_data,
                'saved_path': saved_path
            },
            'metadata': {
                'renderer': 'NetworkRenderer',
                'concept_count': len(data.nodes),
                'relationship_count': len(data.edges)
            }
        }
    
    async def render_influence_network(self, data: NetworkData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render influence network visualization."""
        logger.info("Rendering influence network visualization")
        
        # Create influence network data
        influence_data = {
            'nodes': data.nodes,
            'edges': data.edges,
            'influence_scores': data.centrality_scores,
            'communities': data.communities,
            'config': {
                'title': config.title or 'Influence Network',
                'width': config.width or 800,
                'height': config.height or 600
            }
        }
        
        return {
            'type': 'influence_network',
            'data': influence_data,
            'metadata': {
                'renderer': 'NetworkRenderer',
                'node_count': len(data.nodes),
                'edge_count': len(data.edges),
                'community_count': len(set(data.communities))
            }
        }
    
    async def render_citation_network(self, data: NetworkData, config: VisualizationConfig) -> Dict[str, Any]:
        """Render citation network visualization."""
        logger.info("Rendering citation network visualization")
        
        # Create citation network data
        citation_data = {
            'nodes': data.nodes,
            'edges': data.edges,
            'citation_counts': data.node_degrees,
            'config': {
                'title': config.title or 'Citation Network',
                'width': config.width or 800,
                'height': config.height or 600
            }
        }
        
        return {
            'type': 'citation_network',
            'data': citation_data,
            'metadata': {
                'renderer': 'NetworkRenderer',
                'node_count': len(data.nodes),
                'edge_count': len(data.edges)
            }
        }
    
    async def render(self, viz_type: str, data: NetworkData, config: VisualizationConfig) -> Dict[str, Any]:
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

