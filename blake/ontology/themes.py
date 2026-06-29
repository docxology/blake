"""Blake Theme Detection - Detects themes in Blake's works."""
from dataclasses import dataclass
from typing import Dict, List, Tuple
from collections import Counter
import re

@dataclass
class Theme:
    name: str
    description: str
    keywords: List[str]
    weight: float = 1.0

class ThemeDetector:
    def __init__(self):
        self.themes = self._load_themes()
    
    def _load_themes(self) -> Dict[str, Theme]:
        return {
            "innocence": Theme("Innocence", "Childhood, purity", ["innocent", "child", "lamb", "joy", "merry", "play", "happy"]),
            "experience": Theme("Experience", "Suffering, loss", ["experience", "woe", "sorrow", "weep", "fear", "dark", "night"]),
            "revolution": Theme("Revolution", "Uprising, freedom", ["revolution", "liberty", "freedom", "chains", "tyranny", "fire"]),
            "imagination": Theme("Imagination", "Creative vision", ["imagination", "vision", "prophet", "eternal", "infinite", "divine"]),
            "reason": Theme("Reason", "Rationalism, law", ["reason", "law", "limit", "bound", "measure", "urizen"]),
            "religion": Theme("Religion", "Spirituality", ["god", "christ", "heaven", "hell", "angel", "devil", "church"]),
            "nature": Theme("Nature", "Natural world", ["nature", "tree", "flower", "sun", "moon", "river", "garden"]),
            "love": Theme("Love", "Love and desire", ["love", "desire", "passion", "beauty", "embrace", "kiss"]),
        }
    
    def detect_themes(self, text: str) -> Dict[str, float]:
        words = re.findall(r'\b[a-z]+\b', text.lower())
        word_counts = Counter(words)
        total = len(words) or 1
        return {t.name: min(1.0, sum(word_counts.get(kw, 0) for kw in t.keywords) / total * 100) for t in self.themes.values()}
    
    def get_top_themes(self, text: str, n: int = 5) -> List[Tuple[str, float]]:
        return sorted(self.detect_themes(text).items(), key=lambda x: -x[1])[:n]
    
    def get_theme_profile(self, text: str) -> Dict:
        scores = self.detect_themes(text)
        themes = [{"name": n, "score": round(s, 3)} for n, s in sorted(scores.items(), key=lambda x: -x[1]) if s > 0.01]
        return {"themes": themes, "dominant_theme": themes[0]["name"] if themes else None, "secondary_themes": [t["name"] for t in themes[1:4]]}
