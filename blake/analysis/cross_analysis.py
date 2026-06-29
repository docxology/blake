"""
Cross-analysis functionality for text-image relationships.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
import numpy as np
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..models import BlakeWork, BlakeImage
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


class CrossAnalyzer:
    """Cross-analysis functionality for text-image relationships."""
    
    def __init__(self):
        """Initialize cross analyzer."""
        pass
    
    async def analyze_work(self, work: BlakeWork) -> Dict[str, Any]:
        """
        Perform cross-analysis between text and images in a work.
        
        Args:
            work: BlakeWork to analyze
            
        Returns:
            Dictionary of cross-analysis results
        """
        logger.info(f"Performing cross-analysis for work: {work.id}")
        
        try:
            results = {}
            
            # Text-image correlation
            if work.text_content and work.images:
                results['text_image_correlation'] = await self._analyze_text_image_correlation(work)
            
            # Plate-text mapping
            if work.images and work.text_content:
                results['plate_text_mapping'] = await self._map_plates_to_text(work)
            
            # Thematic consistency
            if work.text_content and work.images:
                results['thematic_consistency'] = await self._analyze_thematic_consistency(work)
            
            # Visual-textual harmony
            if work.text_content and work.images:
                results['visual_textual_harmony'] = await self._analyze_visual_textual_harmony(work)
            
            # Narrative flow
            if work.text_content and work.images:
                results['narrative_flow'] = await self._analyze_narrative_flow(work)
            
            logger.info(f"Completed cross-analysis for work: {work.id}")
            return results
            
        except Exception as e:
            logger.error(f"Error in cross-analysis for work {work.id}: {e}")
            raise AnalysisError(f"Failed to perform cross-analysis: {e}")
    
    async def _analyze_text_image_correlation(self, work: BlakeWork) -> Dict[str, Any]:
        """Analyze correlation between text content and images."""
        if not work.text_content or not work.images:
            return {'error': 'Need both text and images for correlation analysis'}
        
        try:
            # Extract text themes
            text_themes = await self._extract_text_themes(work.text_content)
            
            # Extract visual themes from images
            visual_themes = []
            for image in work.images:
                if image.description:
                    visual_themes.extend(await self._extract_text_themes(image.description))
            
            # Calculate theme overlap
            text_theme_set = set(text_themes)
            visual_theme_set = set(visual_themes)
            
            overlap = text_theme_set.intersection(visual_theme_set)
            union = text_theme_set.union(visual_theme_set)
            
            jaccard_similarity = len(overlap) / len(union) if union else 0
            
            # Analyze color-text relationships
            color_text_analysis = await self._analyze_color_text_relationships(work)
            
            return {
                'text_themes': list(text_theme_set),
                'visual_themes': list(visual_theme_set),
                'theme_overlap': list(overlap),
                'jaccard_similarity': jaccard_similarity,
                'color_text_analysis': color_text_analysis,
            }
            
        except Exception as e:
            logger.error(f"Error in text-image correlation analysis: {e}")
            return {'error': str(e)}
    
    async def _map_plates_to_text(self, work: BlakeWork) -> Dict[str, Any]:
        """Map plates/illustrations to specific text sections."""
        if not work.text_content or not work.images:
            return {'error': 'Need both text and images for plate mapping'}
        
        try:
            # Split text into sections (stanzas, paragraphs, etc.)
            text_sections = await self._split_text_into_sections(work.text_content)
            
            plate_mappings = []
            
            for i, image in enumerate(work.images):
                # Try to find the best matching text section
                best_match = None
                best_score = 0
                
                for j, section in enumerate(text_sections):
                    # Calculate similarity between image and text section
                    similarity = await self._calculate_text_image_similarity(section, image)
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = {
                            'section_index': j,
                            'section_text': section,
                            'similarity_score': similarity
                        }
                
                plate_mappings.append({
                    'image_id': image.id,
                    'image_title': image.title,
                    'plate_number': image.plate_number or i + 1,
                    'best_match': best_match,
                })
            
            return {
                'text_sections': text_sections,
                'plate_mappings': plate_mappings,
                'total_sections': len(text_sections),
                'total_plates': len(work.images),
            }
            
        except Exception as e:
            logger.error(f"Error in plate-text mapping: {e}")
            return {'error': str(e)}
    
    async def _analyze_thematic_consistency(self, work: BlakeWork) -> Dict[str, Any]:
        """Analyze thematic consistency between text and images."""
        if not work.text_content or not work.images:
            return {'error': 'Need both text and images for thematic analysis'}
        
        try:
            # Extract themes from text
            text_themes = await self._extract_text_themes(work.text_content)
            
            # Extract themes from image descriptions and metadata
            image_themes = []
            for image in work.images:
                if image.description:
                    image_themes.extend(await self._extract_text_themes(image.description))
                
                # Add themes from image metadata
                if hasattr(image, 'themes'):
                    image_themes.extend(image.themes)
            
            # Calculate theme consistency
            text_theme_counts = Counter(text_themes)
            image_theme_counts = Counter(image_themes)
            
            # Find common themes
            common_themes = set(text_theme_counts.keys()).intersection(set(image_theme_counts.keys()))
            
            # Calculate consistency score
            total_text_themes = len(text_themes)
            total_image_themes = len(image_themes)
            common_theme_count = sum(min(text_theme_counts[theme], image_theme_counts[theme]) 
                                   for theme in common_themes)
            
            consistency_score = common_theme_count / max(total_text_themes, total_image_themes) if max(total_text_themes, total_image_themes) > 0 else 0
            
            return {
                'text_themes': dict(text_theme_counts),
                'image_themes': dict(image_theme_counts),
                'common_themes': list(common_themes),
                'consistency_score': consistency_score,
                'thematic_alignment': 'high' if consistency_score > 0.7 else 'medium' if consistency_score > 0.4 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Error in thematic consistency analysis: {e}")
            return {'error': str(e)}
    
    async def _analyze_visual_textual_harmony(self, work: BlakeWork) -> Dict[str, Any]:
        """Analyze harmony between visual and textual elements."""
        if not work.text_content or not work.images:
            return {'error': 'Need both text and images for harmony analysis'}
        
        try:
            # Analyze emotional tone of text
            text_emotion = await self._analyze_text_emotion(work.text_content)
            
            # Analyze visual mood of images
            visual_mood = await self._analyze_visual_mood(work.images)
            
            # Calculate harmony score
            harmony_score = await self._calculate_harmony_score(text_emotion, visual_mood)
            
            # Analyze color-emotion relationships
            color_emotion_analysis = await self._analyze_color_emotion_relationships(work)
            
            return {
                'text_emotion': text_emotion,
                'visual_mood': visual_mood,
                'harmony_score': harmony_score,
                'harmony_level': 'high' if harmony_score > 0.7 else 'medium' if harmony_score > 0.4 else 'low',
                'color_emotion_analysis': color_emotion_analysis,
            }
            
        except Exception as e:
            logger.error(f"Error in visual-textual harmony analysis: {e}")
            return {'error': str(e)}
    
    async def _analyze_narrative_flow(self, work: BlakeWork) -> Dict[str, Any]:
        """Analyze narrative flow between text and images."""
        if not work.text_content or not work.images:
            return {'error': 'Need both text and images for narrative analysis'}
        
        try:
            # Analyze text progression
            text_progression = await self._analyze_text_progression(work.text_content)
            
            # Analyze visual progression
            visual_progression = await self._analyze_visual_progression(work.images)
            
            # Calculate narrative coherence
            narrative_coherence = await self._calculate_narrative_coherence(text_progression, visual_progression)
            
            return {
                'text_progression': text_progression,
                'visual_progression': visual_progression,
                'narrative_coherence': narrative_coherence,
                'flow_quality': 'excellent' if narrative_coherence > 0.8 else 'good' if narrative_coherence > 0.6 else 'fair'
            }
            
        except Exception as e:
            logger.error(f"Error in narrative flow analysis: {e}")
            return {'error': str(e)}
    
    async def _extract_text_themes(self, text: str) -> List[str]:
        """Extract themes from text."""
        # Blake-specific themes
        blake_themes = {
            'innocence': ['innocent', 'child', 'lamb', 'pure', 'simple', 'joy', 'happy'],
            'experience': ['experienced', 'adult', 'tiger', 'complex', 'sorrow', 'pain', 'sad'],
            'prophecy': ['prophet', 'vision', 'future', 'foretell', 'divine', 'revelation'],
            'revolution': ['revolution', 'rebellion', 'freedom', 'liberty', 'change', 'revolt'],
            'nature': ['nature', 'flower', 'tree', 'bird', 'animal', 'garden', 'forest'],
            'divine': ['god', 'heaven', 'divine', 'sacred', 'holy', 'angel', 'spirit'],
            'imagination': ['imagination', 'creative', 'art', 'poetry', 'vision', 'dream'],
            'love': ['love', 'beloved', 'heart', 'passion', 'affection', 'romance'],
            'death': ['death', 'die', 'grave', 'mourn', 'end', 'eternal', 'mortal'],
            'transcendence': ['transcend', 'beyond', 'eternal', 'infinite', 'spirit', 'soul']
        }
        
        text_lower = text.lower()
        found_themes = []
        
        for theme, keywords in blake_themes.items():
            if any(keyword in text_lower for keyword in keywords):
                found_themes.append(theme)
        
        return found_themes
    
    async def _split_text_into_sections(self, text: str) -> List[str]:
        """Split text into meaningful sections."""
        # Split by double newlines (paragraphs)
        sections = [s.strip() for s in text.split('\n\n') if s.strip()]
        
        # If no double newlines, split by single newlines
        if len(sections) == 1:
            sections = [s.strip() for s in text.split('\n') if s.strip()]
        
        # If still only one section, split by sentences
        if len(sections) == 1:
            import re
            sentences = re.split(r'[.!?]+', text)
            sections = [s.strip() for s in sentences if s.strip()]
        
        return sections
    
    async def _calculate_text_image_similarity(self, text_section: str, image: BlakeImage) -> float:
        """Calculate similarity between text section and image."""
        # Simple keyword-based similarity
        text_lower = text_section.lower()
        
        # Extract keywords from image description
        if image.description:
            desc_lower = image.description.lower()
            desc_words = set(desc_lower.split())
        else:
            desc_words = set()
        
        # Extract keywords from text section
        text_words = set(text_lower.split())
        
        # Calculate Jaccard similarity
        intersection = text_words.intersection(desc_words)
        union = text_words.union(desc_words)
        
        return len(intersection) / len(union) if union else 0
    
    async def _analyze_text_emotion(self, text: str) -> Dict[str, float]:
        """Analyze emotional tone of text."""
        # Simple emotion analysis based on keywords
        emotion_keywords = {
            'joy': ['happy', 'joy', 'cheerful', 'bright', 'smile', 'laugh'],
            'sadness': ['sad', 'sorrow', 'grief', 'tears', 'mourn', 'weep'],
            'anger': ['angry', 'rage', 'fury', 'wrath', 'fierce', 'storm'],
            'fear': ['fear', 'afraid', 'terror', 'dread', 'horror', 'scared'],
            'love': ['love', 'beloved', 'heart', 'passion', 'affection'],
            'peace': ['peace', 'calm', 'serene', 'tranquil', 'quiet', 'still']
        }
        
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in emotion_keywords.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            emotion_scores[emotion] = score
        
        # Normalize scores
        total_score = sum(emotion_scores.values())
        if total_score > 0:
            emotion_scores = {k: v / total_score for k, v in emotion_scores.items()}
        
        return emotion_scores
    
    async def _analyze_visual_mood(self, images: List[BlakeImage]) -> Dict[str, float]:
        """Analyze visual mood of images."""
        # Analyze based on color properties
        mood_scores = {
            'bright': 0,
            'dark': 0,
            'warm': 0,
            'cool': 0,
            'vibrant': 0,
            'muted': 0
        }
        
        for image in images:
            if image.brightness is not None:
                if image.brightness > 128:
                    mood_scores['bright'] += 1
                else:
                    mood_scores['dark'] += 1
            
            if image.dominant_colors:
                # Analyze color temperature
                for color in image.dominant_colors:
                    if isinstance(color, str) and color.startswith('#'):
                        # Convert hex to RGB
                        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                        r, g, b = rgb
                        
                        if r > g and r > b:  # Red dominant
                            mood_scores['warm'] += 1
                        elif b > r and b > g:  # Blue dominant
                            mood_scores['cool'] += 1
        
        # Normalize scores
        total_images = len(images)
        if total_images > 0:
            mood_scores = {k: v / total_images for k, v in mood_scores.items()}
        
        return mood_scores
    
    async def _calculate_harmony_score(self, text_emotion: Dict[str, float], 
                                     visual_mood: Dict[str, float]) -> float:
        """Calculate harmony score between text emotion and visual mood."""
        # Simple harmony calculation
        # This could be made more sophisticated with proper emotion-mood mapping
        
        # Map emotions to visual moods
        emotion_mood_mapping = {
            'joy': ['bright', 'warm', 'vibrant'],
            'sadness': ['dark', 'cool', 'muted'],
            'anger': ['warm', 'vibrant'],
            'fear': ['dark', 'cool'],
            'love': ['warm', 'bright'],
            'peace': ['cool', 'muted']
        }
        
        harmony_score = 0.0
        total_weight = 0.0
        
        for emotion, score in text_emotion.items():
            if emotion in emotion_mood_mapping:
                for mood in emotion_mood_mapping[emotion]:
                    if mood in visual_mood:
                        harmony_score += score * visual_mood[mood]
                        total_weight += score
        
        return harmony_score / total_weight if total_weight > 0 else 0.0

    async def _analyze_color_text_relationships(self, work: BlakeWork) -> Dict[str, Any]:
        text_themes = await self._extract_text_themes(work.text_content or "")
        colors = []
        for image in work.images:
            colors.extend(image.dominant_colors or [])

        color_categories = Counter()
        for color in colors:
            category = self._categorize_color(color)
            if category:
                color_categories[category] += 1

        theme_color_map = {
            "innocence": {"yellow", "light", "green"},
            "experience": {"red", "dark", "blue"},
            "revolution": {"red", "dark"},
            "nature": {"green", "blue"},
            "divine": {"yellow", "light"},
            "imagination": {"purple", "blue", "yellow"},
            "love": {"red", "yellow"},
            "death": {"dark", "blue"},
            "transcendence": {"light", "blue", "purple"},
        }
        possible = 0
        observed = 0
        for theme in text_themes:
            expected = theme_color_map.get(theme, set())
            if not expected:
                continue
            possible += 1
            if any(color_categories.get(category, 0) for category in expected):
                observed += 1

        return {
            "text_themes": text_themes,
            "dominant_colors": list(colors),
            "color_categories": dict(color_categories),
            "relationship_score": observed / possible if possible else 0.0,
            "matched_theme_count": observed,
            "theme_count": possible,
        }

    def _categorize_color(self, color: Any) -> Optional[str]:
        if not isinstance(color, str) or not color.startswith("#") or len(color) < 7:
            return None
        try:
            r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            return None
        brightness = (r + g + b) / 3
        if brightness < 64:
            return "dark"
        if brightness > 210:
            return "light"
        if r > g and r > b:
            return "red"
        if g > r and g > b:
            return "green"
        if b > r and b > g:
            return "blue"
        if r > 120 and b > 120 and g < 120:
            return "purple"
        if r > 160 and g > 130 and b < 120:
            return "yellow"
        return "mixed"
    
    async def _analyze_color_emotion_relationships(self, work: BlakeWork) -> Dict[str, Any]:
        """Analyze relationships between colors and emotions in the work."""
        # This is a simplified analysis
        # In practice, you'd use more sophisticated color psychology
        
        color_emotion_map = {
            'red': ['anger', 'love', 'passion'],
            'blue': ['sadness', 'peace', 'calm'],
            'yellow': ['joy', 'happiness', 'energy'],
            'green': ['nature', 'peace', 'growth'],
            'purple': ['mystery', 'spirituality', 'royalty'],
            'orange': ['warmth', 'energy', 'creativity']
        }
        
        # Extract colors from images
        all_colors = []
        for image in work.images:
            if image.dominant_colors:
                all_colors.extend(image.dominant_colors)
        
        # Count color occurrences
        color_counts = Counter(all_colors)
        
        # Map to emotions
        emotion_color_analysis = {}
        for color, count in color_counts.items():
            if isinstance(color, str) and color.startswith('#'):
                # Determine color category
                rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
                r, g, b = rgb
                
                if r > g and r > b:
                    color_category = 'red'
                elif g > r and g > b:
                    color_category = 'green'
                elif b > r and b > g:
                    color_category = 'blue'
                elif r > b and g > b:
                    color_category = 'yellow'
                else:
                    color_category = 'other'
                
                if color_category in color_emotion_map:
                    for emotion in color_emotion_map[color_category]:
                        if emotion not in emotion_color_analysis:
                            emotion_color_analysis[emotion] = 0
                        emotion_color_analysis[emotion] += count
        
        return emotion_color_analysis
    
    async def _analyze_text_progression(self, text: str) -> Dict[str, Any]:
        """Analyze progression and flow of text."""
        sections = await self._split_text_into_sections(text)
        
        # Analyze section lengths
        section_lengths = [len(section.split()) for section in sections]
        
        # Analyze emotional progression
        emotional_progression = []
        for section in sections:
            emotion = await self._analyze_text_emotion(section)
            dominant_emotion = max(emotion.items(), key=lambda x: x[1])[0] if emotion else 'neutral'
            emotional_progression.append(dominant_emotion)
        
        return {
            'num_sections': len(sections),
            'section_lengths': section_lengths,
            'emotional_progression': emotional_progression,
            'avg_section_length': np.mean(section_lengths) if section_lengths else 0,
        }
    
    async def _analyze_visual_progression(self, images: List[BlakeImage]) -> Dict[str, Any]:
        """Analyze progression and flow of images."""
        # Analyze brightness progression
        brightness_progression = []
        for image in images:
            if image.brightness is not None:
                brightness_progression.append(image.brightness)
        
        # Analyze color progression
        color_progression = []
        for image in images:
            if image.dominant_colors:
                # Use first dominant color
                color_progression.append(image.dominant_colors[0])
        
        return {
            'num_images': len(images),
            'brightness_progression': brightness_progression,
            'color_progression': color_progression,
        }
    
    async def _calculate_narrative_coherence(self, text_progression: Dict[str, Any], 
                                           visual_progression: Dict[str, Any]) -> float:
        """Calculate narrative coherence between text and visual progression."""
        # Simple coherence calculation
        # In practice, this would be more sophisticated
        
        text_sections = text_progression.get('num_sections', 0)
        visual_sections = visual_progression.get('num_images', 0)
        
        # Check if number of sections is similar
        section_ratio = min(text_sections, visual_sections) / max(text_sections, visual_sections) if max(text_sections, visual_sections) > 0 else 0
        
        # Check emotional-visual consistency
        emotional_progression = text_progression.get('emotional_progression', [])
        brightness_progression = visual_progression.get('brightness_progression', [])
        
        consistency_score = 0.0
        if len(emotional_progression) > 1 and len(brightness_progression) > 1:
            # Simple consistency check
            # Bright emotions should correlate with bright images
            bright_emotions = ['joy', 'love', 'peace']
            dark_emotions = ['sadness', 'fear', 'anger']
            
            for i in range(min(len(emotional_progression), len(brightness_progression))):
                emotion = emotional_progression[i]
                brightness = brightness_progression[i]
                
                if emotion in bright_emotions and brightness > 128:
                    consistency_score += 1
                elif emotion in dark_emotions and brightness <= 128:
                    consistency_score += 1
            
            consistency_score /= min(len(emotional_progression), len(brightness_progression))
        
        # Combine scores
        coherence = (section_ratio + consistency_score) / 2
        
        return coherence
