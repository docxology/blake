"""
Text analysis functionality for Blake works.
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
from collections import Counter
import numpy as np
from datetime import datetime

# NLP imports
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.stem import WordNetLemmatizer
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.chunk import ne_chunk
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from ..models import BlakeWork, AnalysisResult
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


class TextAnalyzer:
    """Text analysis functionality for Blake works."""
    
    def __init__(self):
        """Initialize text analyzer."""
        self.lemmatizer = None
        self.sentiment_analyzer = None
        self.nlp = None
        self.topic_model = None
        self.vectorizer = None
        
        # Initialize NLTK components
        if NLTK_AVAILABLE:
            self._init_nltk()
        
        # Initialize spaCy
        if SPACY_AVAILABLE:
            self._init_spacy()
    
    def _init_nltk(self):
        """Initialize NLTK components."""
        try:
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)  # Required for newer NLTK versions
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('averaged_perceptron_tagger_eng', quiet=True)  # English tagger
            nltk.download('maxent_ne_chunker', quiet=True)
            nltk.download('maxent_ne_chunker_tab', quiet=True)  # Tabular version
            nltk.download('words', quiet=True)
            
            self.lemmatizer = WordNetLemmatizer()
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            
        except Exception as e:
            logger.warning(f"Error initializing NLTK: {e}")
    
    def _init_spacy(self):
        """Initialize spaCy model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp.max_length = 3000000  # Increase limit for large texts
        except OSError:
            logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
        except Exception as e:
            logger.warning(f"Error initializing spaCy: {e}")
    
    def _analyze_readability(self, text: str) -> Dict[str, float]:
        """
        Analyze readability scores.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of readability scores
        """
        if not text:
            return {}
            
        # Basic counts
        sentences = [s for s in text.split('.') if s.strip()]
        words = [w for w in text.split() if w.isalnum()]
        num_sentences = len(sentences) or 1
        num_words = len(words) or 1
        
        # Calculate syllables (heuristic: count vowels)
        def count_syllables(word):
            word = word.lower()
            count = 0
            vowels = "aeiouy"
            if word and word[0] in vowels:
                count += 1
            for i in range(1, len(word)):
                if word[i] in vowels and word[i-1] not in vowels:
                    count += 1
            if word.endswith("e"):
                count -= 1
            return max(1, count)
            
        num_syllables = sum(count_syllables(w) for w in words)
        
        # Flesch Reading Ease
        # 206.835 - 1.015 * (total words / total sentences) - 84.6 * (total syllables / total words)
        flesch_score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
        
        # Automated Readability Index (ARI)
        # 4.71 * (characters / words) + 0.5 * (words / sentences) - 21.43
        num_chars = sum(len(w) for w in words)
        ari_score = 4.71 * (num_chars / num_words) + 0.5 * (num_words / num_sentences) - 21.43
        
        return {
            "flesch_reading_ease": round(flesch_score, 2),
            "automated_readability_index": round(ari_score, 2),
            "avg_sentence_length": round(num_words / num_sentences, 2),
            "avg_word_length": round(num_chars / num_words, 2)
        }

    def _analyze_lexical_diversity(self, text: str) -> Dict[str, float]:
        """
        Analyze lexical diversity.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of lexical diversity metrics
        """
        if not text:
            return {}
            
        words = [w.lower() for w in text.split() if w.isalnum()]
        if not words:
            return {"ttr": 0.0, "unique_words": 0}
            
        unique_words = set(words)
        
        # Type-Token Ratio (TTR)
        ttr = len(unique_words) / len(words)
        
        return {
            "ttr": round(ttr, 4),
            "unique_words": len(unique_words),
            "total_words": len(words)
        }
    
    async def analyze_work(self, work: BlakeWork) -> Dict[str, Any]:
        """
        Perform comprehensive text analysis on a work.
        
        Args:
            work: BlakeWork to analyze
            
        Returns:
            Dictionary of analysis results
        """
        if not work.text_content:
            return {}
        
        logger.info(f"Analyzing text for work: {work.id}")
        
        try:
            results = {}
            
            # Basic statistics
            results['basic_stats'] = await self._analyze_basic_stats(work.text_content)
            
            # Sentiment analysis
            results['sentiment'] = await self._analyze_sentiment(work.text_content)
            
            # Named entity recognition
            results['entities'] = await self._extract_entities(work.text_content)
            
            # Topic modeling
            results['topics'] = await self._analyze_topics(work.text_content)
            
            # Stylistic analysis
            results['style'] = await self._analyze_style(work.text_content)
            
            # Concordance and keywords
            results['concordance'] = await self._analyze_concordance(work.text_content)
            
            # Thematic analysis
            results['themes'] = await self._analyze_themes(work.text_content)
            
            logger.info(f"Completed text analysis for work: {work.id}")
            # Advanced stats
            # Advanced stats
            results["readability"] = self._analyze_readability(work.text_content)
            results["lexical_diversity"] = self._analyze_lexical_diversity(work.text_content)
        
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing text for work {work.id}: {e}")
            raise AnalysisError(f"Failed to analyze text: {e}")
    
    async def _analyze_basic_stats(self, text: str) -> Dict[str, Any]:
        """Analyze basic text statistics."""
        # Word count
        words = text.split()
        word_count = len(words)
        
        # Character count
        char_count = len(text)
        
        # Sentence count
        if NLTK_AVAILABLE:
            sentences = sent_tokenize(text)
            sentence_count = len(sentences)
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        else:
            # Simple sentence counting
            sentences = re.split(r'[.!?]+', text)
            sentence_count = len([s for s in sentences if s.strip()])
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Paragraph count
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)
        
        # Average word length
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        
        # Vocabulary richness (unique words / total words)
        unique_words = len(set(word.lower() for word in words))
        vocabulary_richness = unique_words / word_count if word_count > 0 else 0
        
        return {
            'word_count': word_count,
            'character_count': char_count,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_sentence_length': avg_sentence_length,
            'avg_word_length': avg_word_length,
            'vocabulary_richness': vocabulary_richness,
            'unique_words': unique_words,
        }
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        if not NLTK_AVAILABLE:
            return {'error': 'NLTK not available'}
        
        try:
            # VADER sentiment analysis
            scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Determine overall sentiment
            if scores['compound'] >= 0.05:
                sentiment = 'positive'
            elif scores['compound'] <= -0.05:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'sentiment': sentiment,
                'compound_score': scores['compound'],
                'positive_score': scores['pos'],
                'negative_score': scores['neg'],
                'neutral_score': scores['neu'],
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {'error': str(e)}
    
    async def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        entities = {
            'persons': [],
            'places': [],
            'organizations': [],
            'other': []
        }
        
        if SPACY_AVAILABLE and self.nlp:
            try:
                doc = self.nlp(text)
                for ent in doc.ents:
                    if ent.label_ == 'PERSON':
                        entities['persons'].append(ent.text)
                    elif ent.label_ == 'GPE' or ent.label_ == 'LOC':
                        entities['places'].append(ent.text)
                    elif ent.label_ == 'ORG':
                        entities['organizations'].append(ent.text)
                    else:
                        entities['other'].append(ent.text)
                
                # Remove duplicates
                for key in entities:
                    entities[key] = list(set(entities[key]))
                    
            except Exception as e:
                logger.error(f"Error in spaCy entity extraction: {e}")
        
        elif NLTK_AVAILABLE:
            try:
                # NLTK named entity recognition
                tokens = word_tokenize(text)
                pos_tags = pos_tag(tokens)
                chunks = ne_chunk(pos_tags)
                
                for chunk in chunks:
                    if hasattr(chunk, 'label'):
                        if chunk.label() == 'PERSON':
                            entities['persons'].append(' '.join([token for token, pos in chunk.leaves()]))
                        elif chunk.label() == 'GPE':
                            entities['places'].append(' '.join([token for token, pos in chunk.leaves()]))
                        elif chunk.label() == 'ORGANIZATION':
                            entities['organizations'].append(' '.join([token for token, pos in chunk.leaves()]))
                
                # Remove duplicates
                for key in entities:
                    entities[key] = list(set(entities[key]))
                    
            except Exception as e:
                logger.error(f"Error in NLTK entity extraction: {e}")
        
        return entities
    
    async def _analyze_topics(self, text: str) -> Dict[str, Any]:
        """Perform topic modeling on text."""
        if not SKLEARN_AVAILABLE:
            return {'error': 'scikit-learn not available'}
        
        try:
            # Prepare text for topic modeling
            # Split into sentences for better topic modeling
            if NLTK_AVAILABLE:
                sentences = sent_tokenize(text)
            else:
                sentences = re.split(r'[.!?]+', text)
            
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) < 5:  # Need enough text for topic modeling
                return {'error': 'Insufficient text for topic modeling'}
            
            # Vectorize text
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2
            )
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Perform LDA
            n_topics = min(5, len(sentences) // 2)  # Adaptive number of topics
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=100
            )
            
            lda.fit(tfidf_matrix)
            
            # Get topic words
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(lda.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                topics.append({
                    'topic_id': topic_idx,
                    'words': top_words,
                    'weights': topic[top_words_idx].tolist()
                })
            
            return {
                'n_topics': n_topics,
                'topics': topics
            }
            
        except Exception as e:
            logger.error(f"Error in topic modeling: {e}")
            return {'error': str(e)}
    
    async def _analyze_style(self, text: str) -> Dict[str, Any]:
        """Analyze stylistic features of text."""
        words = text.split()
        
        # Word length distribution
        word_lengths = [len(word) for word in words]
        
        # Sentence length distribution
        if NLTK_AVAILABLE:
            sentences = sent_tokenize(text)
        else:
            sentences = re.split(r'[.!?]+', text)
        
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        
        # Punctuation analysis
        punctuation_counts = Counter()
        for char in text:
            if char in '.,!?;:':
                punctuation_counts[char] += 1
        
        # Capitalization analysis
        capitalized_words = [word for word in words if word[0].isupper()]
        capitalization_ratio = len(capitalized_words) / len(words) if words else 0
        
        # Alliteration analysis (consecutive words starting with same letter)
        alliterations = 0
        for i in range(len(words) - 1):
            if words[i][0].lower() == words[i+1][0].lower():
                alliterations += 1
        
        return {
            'avg_word_length': np.mean(word_lengths) if word_lengths else 0,
            'std_word_length': np.std(word_lengths) if word_lengths else 0,
            'avg_sentence_length': np.mean(sentence_lengths) if sentence_lengths else 0,
            'std_sentence_length': np.std(sentence_lengths) if sentence_lengths else 0,
            'punctuation_counts': dict(punctuation_counts),
            'capitalization_ratio': capitalization_ratio,
            'alliterations': alliterations,
            'alliteration_ratio': alliterations / len(words) if words else 0,
        }
    
    async def _analyze_concordance(self, text: str) -> Dict[str, Any]:
        """Analyze concordance and keywords."""
        words = [word.lower() for word in text.split()]
        word_counts = Counter(words)
        
        # Most frequent words
        most_common = word_counts.most_common(20)
        
        # Remove stop words if NLTK is available
        if NLTK_AVAILABLE:
            stop_words = set(stopwords.words('english'))
            filtered_words = {word: count for word, count in word_counts.items() 
                            if word not in stop_words and len(word) > 2}
            filtered_common = Counter(filtered_words).most_common(20)
        else:
            filtered_common = most_common
        
        # Keyword analysis (TF-IDF-like)
        # This is a simplified version - in practice, you'd use a larger corpus
        keywords = []
        for word, count in filtered_common:
            if count > 1:  # Words that appear more than once
                keywords.append({
                    'word': word,
                    'count': count,
                    'frequency': count / len(words)
                })
        
        return {
            'most_common_words': most_common,
            'keywords': keywords,
            'total_unique_words': len(word_counts),
        }
    
    async def _analyze_themes(self, text: str) -> Dict[str, Any]:
        """Analyze thematic content."""
        # Blake-specific themes
        blake_themes = {
            'innocence': ['innocent', 'child', 'lamb', 'pure', 'simple', 'joy'],
            'experience': ['experienced', 'adult', 'tiger', 'complex', 'sorrow', 'pain'],
            'prophecy': ['prophet', 'vision', 'future', 'foretell', 'divine'],
            'revolution': ['revolution', 'rebellion', 'freedom', 'liberty', 'change'],
            'nature': ['nature', 'flower', 'tree', 'bird', 'animal', 'garden'],
            'divine': ['god', 'heaven', 'divine', 'sacred', 'holy', 'angel'],
            'imagination': ['imagination', 'creative', 'art', 'poetry', 'vision'],
            'love': ['love', 'beloved', 'heart', 'passion', 'affection'],
            'death': ['death', 'die', 'grave', 'mourn', 'end', 'eternal'],
            'transcendence': ['transcend', 'beyond', 'eternal', 'infinite', 'spirit']
        }
        
        text_lower = text.lower()
        theme_scores = {}
        
        for theme, keywords in blake_themes.items():
            score = sum(text_lower.count(keyword) for keyword in keywords)
            if score > 0:
                theme_scores[theme] = score
        
        # Sort themes by score
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'themes': sorted_themes,
            'dominant_theme': sorted_themes[0][0] if sorted_themes else None,
        }
    
    async def compare_works(self, works: List[BlakeWork]) -> Dict[str, Any]:
        """Compare multiple works for similarity and differences."""
        if len(works) < 2:
            return {'error': 'Need at least 2 works to compare'}
        
        try:
            # Extract text content
            texts = [work.text_content for work in works if work.text_content]
            work_ids = [work.id for work in works if work.text_content]
            
            if len(texts) < 2:
                return {'error': 'Need at least 2 works with text content'}
            
            # Vectorize texts
            if SKLEARN_AVAILABLE:
                vectorizer = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english',
                    ngram_range=(1, 2)
                )
                
                tfidf_matrix = vectorizer.fit_transform(texts)
                
                # Calculate similarity matrix
                similarity_matrix = cosine_similarity(tfidf_matrix)
                
                # Find most similar pairs
                similarities = []
                for i in range(len(works)):
                    for j in range(i + 1, len(works)):
                        similarities.append({
                            'work1_id': work_ids[i],
                            'work2_id': work_ids[j],
                            'similarity': float(similarity_matrix[i][j])
                        })
                
                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                
                return {
                    'similarity_matrix': similarity_matrix.tolist(),
                    'most_similar_pairs': similarities[:5],
                    'average_similarity': float(np.mean(similarity_matrix))
                }
            else:
                return {'error': 'scikit-learn not available for comparison'}
                
        except Exception as e:
            logger.error(f"Error comparing works: {e}")
            return {'error': str(e)}
