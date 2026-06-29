"""
Ontological Analysis Module.

This module provides functionality for constructing knowledge graphs,
extracting entities and relationships, and performing semantic analysis
on Blake's works.
"""

import logging
from typing import Dict, Any, List, Set, Tuple, Optional
import networkx as nx
from collections import Counter
import json
from pathlib import Path

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from ..models import BlakeWork, BlakeImage
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


class OntologyManager:
    """Manages ontological analysis and knowledge graph construction."""

    MAX_ENTITIES_PER_WORK = 1000
    MAX_RELATIONSHIPS_PER_WORK = 2000
    MAX_SENTENCE_ENTITIES = 24
    
    def __init__(self, data_dir: Path):
        """
        Initialize ontology manager.
        
        Args:
            data_dir: Directory to store ontology data
        """
        self.data_dir = data_dir
        self.ontology_dir = data_dir / "ontology"
        self.ontology_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize spaCy model
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model: en_core_web_sm")
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found. Some features disabled.")
        
        # Initialize global knowledge graph
        self.graph = nx.MultiDiGraph()
        
        # Blake-specific entity types
        self.entity_types = {
            'MYTH': ['Urizen', 'Los', 'Enitharmon', 'Orc', 'Tharmas', 'Luvah', 'Urthona', 'Albion', 'Jerusalem'],
            'PLACE': ['London', 'Golgonooza', 'Beulah', 'Ulro', 'Generation', 'Eden'],
            'CONCEPT': ['Innocence', 'Experience', 'Vision', 'Prophecy', 'Imagination', 'Reason'],
            'SYMBOL': ['Lamb', 'Tyger', 'Rose', 'Worm', 'Sickle', 'Hammer', 'Chain', 'Fire']
        }
        
        logger.info("Initialized OntologyManager")
    
    async def analyze_work(self, work: BlakeWork) -> Dict[str, Any]:
        """
        Perform ontological analysis on a work.
        
        Args:
            work: BlakeWork to analyze
            
        Returns:
            Dictionary of ontological analysis results
        """
        logger.info(f"Performing ontological analysis for work: {work.id}")
        
        try:
            results = {
                'entities': [],
                'relationships': [],
                'concepts': [],
                'graph_stats': {}
            }
            
            # Extract entities from text
            if work.text_content:
                text_entities = await self._extract_entities(work.text_content)
                text_entities = self._compact_entities(text_entities, self.MAX_ENTITIES_PER_WORK)
                results['entities'].extend(text_entities)
                
                # Extract relationships
                relationships = await self._extract_relationships(work.text_content, text_entities)
                results['relationships'].extend(relationships)
                
                # Update global graph
                self._update_graph(work.id, text_entities, relationships)
            
            # Extract concepts from images (via descriptions)
            if work.images:
                for image in work.images:
                    if image.description:
                        img_entities = await self._extract_entities(image.description)
                        # Tag as visual entities
                        for entity in img_entities:
                            entity['source'] = 'visual'
                            entity['image_id'] = image.id
                        results['entities'].extend(img_entities)
            
            results['graph_stats'] = self._calculate_graph_stats(
                work.id,
                results['entities'],
                results['relationships'],
            )
            
            logger.info(f"Completed ontological analysis for work: {work.id}")
            return results
            
        except Exception as e:
            logger.error(f"Error in ontological analysis for work {work.id}: {e}")
            raise AnalysisError(f"Failed to perform ontological analysis: {e}")
    
    async def build_global_graph(self) -> nx.MultiDiGraph:
        """Build and return the global knowledge graph."""
        return self.graph
    
    async def export_graph(self, format: str = 'json') -> Path:
        """Export the knowledge graph to file."""
        output_path = self.ontology_dir / f"blake_ontology.{format}"
        
        if format == 'json':
            data = nx.node_link_data(self.graph)
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format == 'gexf':
            nx.write_gexf(self.graph, output_path)
        
        logger.info(f"Exported ontology graph to {output_path}")
        return output_path

    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities and Blake-specific terms."""
        entities = []
        
        # spaCy extraction
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'GPE', 'ORG', 'LOC']:
                    entities.append({
                        'text': ent.text,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'source': 'nlp'
                    })
        
        # Rule-based extraction for Blake terms
        for category, terms in self.entity_types.items():
            for term in terms:
                if term in text: # Simple substring match, could be improved with regex
                    # Check if not already found by spaCy (or override)
                    existing = next((e for e in entities if e['text'] == term), None)
                    if not existing:
                        entities.append({
                            'text': term,
                            'label': category,
                            'source': 'rule_based'
                        })
                    elif existing['label'] not in self.entity_types.keys():
                        # Refine generic NER labels with specific Blake labels
                        existing['label'] = category
                        
        return entities

    async def _extract_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract relationships between entities."""
        relationship_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        if self.nlp:
            doc = self.nlp(text)
            entity_texts = sorted({entity.get('text', '') for entity in entities if entity.get('text')}, key=len, reverse=True)
            for sent in doc.sents:
                sent_text = sent.text
                sent_entity_texts = []
                for entity_text in entity_texts:
                    if entity_text in sent_text:
                        sent_entity_texts.append(entity_text)
                    if len(sent_entity_texts) >= self.MAX_SENTENCE_ENTITIES:
                        break

                for i in range(len(sent_entity_texts)):
                    for j in range(i + 1, len(sent_entity_texts)):
                        source = sent_entity_texts[i]
                        target = sent_entity_texts[j]
                        if source == target:
                            continue
                        key = (source, target, "CO_OCCURS")
                        row = relationship_map.setdefault(
                            key,
                            {
                                'source': source,
                                'target': target,
                                'type': "CO_OCCURS",
                                'context': sent_text[:160] + ("..." if len(sent_text) > 160 else ""),
                                'count': 0,
                            },
                        )
                        row['count'] += 1

        relationships = sorted(relationship_map.values(), key=lambda row: (-row['count'], row['source'], row['target']))
        return relationships[: self.MAX_RELATIONSHIPS_PER_WORK]

    def _compact_entities(self, entities: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        compacted: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        for entity in entities:
            text = str(entity.get('text') or '').strip()
            if not text:
                continue
            key = (text, str(entity.get('label') or ''), str(entity.get('source') or ''))
            row = compacted.setdefault(
                key,
                {
                    'text': text,
                    'label': entity.get('label'),
                    'source': entity.get('source'),
                    'mention_count': 0,
                },
            )
            row['mention_count'] += 1
            if 'first_start' not in row and entity.get('start') is not None:
                row['first_start'] = entity.get('start')
                row['first_end'] = entity.get('end')
        return sorted(compacted.values(), key=lambda row: (-row['mention_count'], row['text']))[:limit]

    def _update_graph(self, work_id: str, entities: List[Dict[str, Any]], relationships: List[Dict[str, Any]]):
        """Update the global NetworkX graph."""
        # Add nodes
        for entity in entities:
            if not self.graph.has_node(entity['text']):
                self.graph.add_node(entity['text'], type=entity['label'])
            
        # Add edges
        for rel in relationships:
            self.graph.add_edge(
                rel['source'], 
                rel['target'], 
                type=rel['type'], 
                work_id=work_id
            )

    def _calculate_graph_stats(
        self,
        work_id: str,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        unique_entities = {
            str(entity.get('text') or '')
            for entity in entities
            if isinstance(entity, dict) and entity.get('text')
        }
        node_count = len(unique_entities)
        edge_count = sum(1 for rel in relationships if isinstance(rel, dict))
        density = 0.0
        if node_count > 1:
            density = edge_count / (node_count * (node_count - 1))
        return {
            'work_id': work_id,
            'node_count': node_count,
            'edge_count': edge_count,
            'density': density,
        }
