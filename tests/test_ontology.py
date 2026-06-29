"""Tests for Blake Ontology Module."""
import pytest

class TestBlakeConcepts:
    def test_import(self):
        from blake.ontology.concepts import BlakeConcepts
        assert BlakeConcepts is not None
    
    def test_four_zoas_exist(self):
        from blake.ontology.concepts import BlakeConcepts
        c = BlakeConcepts()
        zoas = c.get_four_zoas()
        names = [z.name for z in zoas]
        assert all(n in names for n in ["Urizen", "Los", "Luvah", "Tharmas"])
    
    def test_find_in_text(self):
        from blake.ontology.concepts import BlakeConcepts
        c = BlakeConcepts()
        found = c.find_in_text("Urizen stood while Los labored")
        assert any(f.name == "Urizen" for f in found)

class TestThemeDetector:
    def test_import(self):
        from blake.ontology.themes import ThemeDetector
        assert ThemeDetector is not None
    
    def test_detect_themes(self):
        from blake.ontology.themes import ThemeDetector
        t = ThemeDetector()
        scores = t.detect_themes("innocent child lamb joy")
        assert "Innocence" in scores

class TestSymbolMapper:
    def test_import(self):
        from blake.ontology.symbols import SymbolMapper
        assert SymbolMapper is not None
    
    def test_find_symbols(self):
        from blake.ontology.symbols import SymbolMapper
        s = SymbolMapper()
        found = s.find_symbols("Little lamb who made thee")
        assert any(f.name == "Lamb" for f in found)

class TestOntologyExporter:
    def test_import(self):
        from blake.ontology.export import OntologyExporter
        assert OntologyExporter is not None
    
    def test_export_json(self, tmp_path):
        from blake.ontology.export import OntologyExporter
        e = OntologyExporter()
        data = e.export_json(tmp_path / "test.json")
        assert "concepts" in data
