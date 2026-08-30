# `blake/ontology/` — Blake Concept Ontology

Structured knowledge of Blake's mythological concepts, themes, and symbols,
with exporters to JSON, JSON-LD, and Markdown.

## Modules

| File | What it does |
|------|--------------|
| `concepts.py` | Core mythological concepts (Zoas, Emanations, states, etc.) |
| `themes.py` | Theme detection over Blake's works |
| `symbols.py` | Symbol-to-meaning mappings |
| `export.py` | Serializes the ontology to JSON / JSON-LD / Markdown |

## Use

```python
from blake.ontology import ...   # see __init__.py for the public surface
```
