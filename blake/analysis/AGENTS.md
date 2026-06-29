# analysis Module

Text and visual analysis for Blake's works using NLP and computer vision.

## Components

| File | Class | Purpose |
|------|-------|---------|
| `analyzer.py` | `BlakeAnalyzer` | Main analysis orchestrator |
| `text_analysis.py` | `TextAnalyzer` | NLP analysis (sentiment, topics, entities) |
| `visual_analysis.py` | `VisualAnalyzer` | Image analysis (colors, composition) |
| `cross_analysis.py` | `CrossAnalyzer` | Text-image correlation |

## Key Methods

- `BlakeAnalyzer.analyze_work()` - Full analysis of single work
- `TextAnalyzer.analyze_sentiment()` - Sentiment detection
- `TextAnalyzer.extract_topics()` - Topic modeling
- `VisualAnalyzer.analyze_colors()` - Color palette extraction
- `CrossAnalyzer.correlate_text_image()` - Cross-modal analysis

## Dependencies

- NLTK, spaCy - NLP processing
- transformers - Deep learning models
- scikit-learn - ML algorithms
- OpenCV, Pillow - Image processing
