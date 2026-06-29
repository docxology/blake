# gui Module

Streamlit-based interactive exploration interface.

## Components

| File | Class | Purpose |
|------|-------|---------|
| `gui.py` | `BlakeGUI` | Main Streamlit application |
| `components.py` | UI Components | Reusable interface elements |

## Features

- Work browsing and filtering
- Text-image synchronized viewing
- Analysis visualization
- Search interface
- Export controls

## Launch

```python
gui = BlakeGUI(blake_works)
gui.launch(host="localhost", port=8501)
```
