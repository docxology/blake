"""Blake Concepts - Core mythological concepts in Blake's work."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

class ConceptCategory(Enum):
    FIGURE = "figure"
    PLACE = "place"
    STATE = "state"
    THEME = "theme"
    SYMBOL = "symbol"

@dataclass
class BlakeConcept:
    name: str
    category: ConceptCategory
    description: str
    aliases: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    works: List[str] = field(default_factory=list)
    
    def matches(self, text: str) -> bool:
        text_lower = text.lower()
        if self.name.lower() in text_lower:
            return True
        return any(alias.lower() in text_lower for alias in self.aliases)

class BlakeConcepts:
    def __init__(self):
        self.concepts: Dict[str, BlakeConcept] = {}
        self._load_core_concepts()
    
    def _load_core_concepts(self):
        # Four Zoas
        self._add(BlakeConcept("Urizen", ConceptCategory.FIGURE, "Zoa of Reason", ["Your Reason"], ["Los", "Luvah"], ["The Book of Urizen", "Jerusalem"]))
        self._add(BlakeConcept("Los", ConceptCategory.FIGURE, "Zoa of Imagination", ["Time"], ["Enitharmon", "Urizen"], ["The Book of Los", "Milton"]))
        self._add(BlakeConcept("Luvah", ConceptCategory.FIGURE, "Zoa of Emotion", ["Love"], ["Vala", "Orc"], ["The Four Zoas"]))
        self._add(BlakeConcept("Tharmas", ConceptCategory.FIGURE, "Zoa of Sensation", [], ["Enion"], ["The Four Zoas"]))
        # Emanations
        self._add(BlakeConcept("Enitharmon", ConceptCategory.FIGURE, "Emanation of Los", ["Space"], ["Los"], ["Europe"]))
        self._add(BlakeConcept("Ahania", ConceptCategory.FIGURE, "Emanation of Urizen", [], ["Urizen"], ["The Book of Ahania"]))
        self._add(BlakeConcept("Vala", ConceptCategory.FIGURE, "Emanation of Luvah", ["Nature"], ["Luvah"], ["The Four Zoas"]))
        # Other figures
        self._add(BlakeConcept("Orc", ConceptCategory.FIGURE, "Spirit of Revolution", [], ["Los"], ["America", "Europe"]))
        self._add(BlakeConcept("Albion", ConceptCategory.FIGURE, "Primordial Man/England", [], ["Jerusalem"], ["Jerusalem"]))
        # States
        self._add(BlakeConcept("Innocence", ConceptCategory.STATE, "State of pure joy", [], ["Experience"], ["Songs of Innocence"]))
        self._add(BlakeConcept("Experience", ConceptCategory.STATE, "State of fallen awareness", [], ["Innocence"], ["Songs of Experience"]))
        # Symbols
        self._add(BlakeConcept("Lamb", ConceptCategory.SYMBOL, "Innocence, Christ", [], ["Tyger"], ["Songs of Innocence"]))
        self._add(BlakeConcept("Tyger", ConceptCategory.SYMBOL, "Energy, wrath", ["Tiger"], ["Lamb"], ["Songs of Experience"]))
    
    def _add(self, c): self.concepts[c.name] = c
    def get(self, name): return self.concepts.get(name)
    def find_in_text(self, text): return [c for c in self.concepts.values() if c.matches(text)]
    def get_by_category(self, cat): return [c for c in self.concepts.values() if c.category == cat]
    def get_four_zoas(self): return [self.concepts[n] for n in ["Urizen", "Los", "Luvah", "Tharmas"]]
    def get_emanations(self): return [self.concepts[n] for n in ["Enitharmon", "Ahania", "Vala"]]
    def to_dict(self): return {n: {"name": c.name, "category": c.category.value, "description": c.description} for n, c in self.concepts.items()}
