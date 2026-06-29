"""Blake Ontology Export - Exports ontology in JSON, JSON-LD, Markdown."""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from .concepts import BlakeConcepts
from .themes import ThemeDetector
from .symbols import SymbolMapper

class OntologyExporter:
    def __init__(self):
        self.concepts = BlakeConcepts()
        self.themes = ThemeDetector()
        self.symbols = SymbolMapper()
    
    def export_json(self, output_path: Optional[Path] = None) -> Dict:
        data = {"metadata": {"title": "William Blake Ontology", "created": datetime.now().isoformat()},
                "concepts": self.concepts.to_dict(), "symbols": self.symbols.to_dict(),
                "themes": {n: {"name": t.name, "description": t.description} for n, t in self.themes.themes.items()}}
        if output_path:
            with open(output_path, 'w') as f: json.dump(data, f, indent=2)
        return data
    
    def export_jsonld(self, output_path: Optional[Path] = None) -> Dict:
        data = {"@context": {"@vocab": "https://blakearchive.org/ontology/"}, "@type": "skos:ConceptScheme",
                "dc:title": "William Blake Ontology", "hasTopConcept": [{"@id": f"blake:{z.name}", "label": z.name} for z in self.concepts.get_four_zoas()]}
        if output_path:
            with open(output_path, 'w') as f: json.dump(data, f, indent=2)
        return data
    
    def export_markdown(self, output_path: Optional[Path] = None) -> str:
        lines = ["# William Blake Ontology", "", "## Four Zoas"]
        for z in self.concepts.get_four_zoas():
            lines.extend([f"### {z.name}", f"*{z.description}*", ""])
        lines.extend(["## Key Symbols", ""] + [f"- **{s.name}**: {s.meaning}" for s in list(self.symbols.symbols.values())[:8]])
        content = '\n'.join(lines)
        if output_path:
            with open(output_path, 'w') as f: f.write(content)
        return content
