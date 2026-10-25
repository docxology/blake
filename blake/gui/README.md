# Blake GUI Module

Streamlit-based interactive exploration interface for William Blake's works.

## Features

- **Work Browser**: Browse and filter works by type, source, theme
- **Synchronized Viewer**: Text and image side-by-side viewing
- **Analysis Display**: Visualize sentiment, topics, entities
- **Search**: Full-text and metadata search
- **Export**: Download works in various formats

## Usage

```python
from blake.gui import BlakeGUI

gui = BlakeGUI(blake_works)
gui.launch(host="localhost", port=8501)
```

Or via CLI:

```bash
blake explore --port 8501
```

## Components

| Component | Description |
|-----------|-------------|
| `BlakeGUI` | Main application |
| `WorkBrowser` | Work listing component |
| `WorkViewer` | Detail view component |
| `SearchPanel` | Search interface |
