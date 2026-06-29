"""Blake Symbol Mapper - Maps symbols to meanings."""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Symbol:
    name: str
    meaning: str
    associations: List[str]
    state: Optional[str] = None
    keywords: List[str] = None

class SymbolMapper:
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self._load_symbols()
    
    def _load_symbols(self):
        self._add(Symbol("Lamb", "Innocence, Christ", ["shepherd", "child"], "Innocence", ["lamb", "lambs"]))
        self._add(Symbol("Tyger", "Energy, wrath", ["fire", "night"], "Experience", ["tyger", "tiger"]))
        self._add(Symbol("Rose", "Love, beauty", ["thorns", "garden"], None, ["rose", "roses"]))
        self._add(Symbol("Sunflower", "Longing for eternity", ["sun", "aspiration"], "Experience", ["sunflower"]))
        self._add(Symbol("Sun", "Divine light, imagination", ["day", "gold"], None, ["sun", "solar"]))
        self._add(Symbol("Moon", "Dreams, reflection", ["night", "silver"], None, ["moon", "lunar"]))
        self._add(Symbol("Chains", "Oppression, slavery", ["prison", "captive"], None, ["chain", "chains", "bound"]))
        self._add(Symbol("Fire", "Energy, transformation", ["passion", "forge"], None, ["fire", "flame", "burning"]))
        self._add(Symbol("Worm", "Mortality, corruption", ["death", "decay"], "Experience", ["worm", "worms"]))
    
    def _add(self, s): self.symbols[s.name] = s
    def get(self, name): return self.symbols.get(name)
    def find_symbols(self, text):
        text_lower = text.lower()
        return [s for s in self.symbols.values() if s.keywords and any(kw in text_lower for kw in s.keywords)]
    def get_by_state(self, state): return [s for s in self.symbols.values() if s.state == state]
    def to_dict(self): return {n: {"name": s.name, "meaning": s.meaning, "state": s.state} for n, s in self.symbols.items()}
