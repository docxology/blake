# Blake Analysis Module

NLP and visual analysis for William Blake's works.

## Features

- **Sentiment Analysis**: Emotional tone detection
- **Topic Modeling**: Theme extraction with LDA
- **Entity Recognition**: Named entity extraction
- **Color Analysis**: Dominant color extraction
- **Cross-Modal**: Text-image correlation

## Usage

```python
from blake.blake_analysis import BlakeAnalyzer, TextAnalyzer

analyzer = BlakeAnalyzer()
results = analyzer.analyze_work(work)

# Text-only analysis
text_analyzer = TextAnalyzer()
sentiment = text_analyzer.analyze_sentiment(text)
topics = text_analyzer.extract_topics(text)
```

## Classes

| Class | Description |
|-------|-------------|
| `BlakeAnalyzer` | Main orchestrator |
| `TextAnalyzer` | NLP analysis |
| `VisualAnalyzer` | Image analysis |
| `CrossAnalyzer` | Cross-modal analysis |

## Analysis Types

- `sentiment` - Positive/negative detection
- `topics` - LDA topic modeling
- `entities` - NER extraction
- `stylistic` - Writing style metrics
- `colors` - Image color palette
- `composition` - Visual structure
