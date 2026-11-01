# Optional corpus analysis

Follow the [repository contract](../../AGENTS.md), [method profiles](../../docs/methods.md) and [verification guide](../../docs/verification.md).

| Owner | Public async entry points |
|---|---|
| [BlakeAnalyzer](analyzer.py) | `analyze_work(work, analysis_types=None)`, `analyze_multiple_works(works, analysis_types=None)`, `compare_works(works)`. |
| [TextAnalyzer](text_analysis.py) | `analyze_work(work)` and `compare_works(works)`. Sentiment, topics and entities are internal components of these results. |
| [VisualAnalyzer](visual_analysis.py) | `analyze_image(image)` and `compare_images(images)`. |
| [CrossAnalyzer](cross_analysis.py) | `analyze_work(work)`; private helpers implement text/image heuristics. |

Await the actual entry points. Preserve saved result shapes and explicit errors
or unavailable components; do not relabel heuristics as validated semantic,
affective or iconographic judgments. Record which text/image units and model
versions produced a new result epoch. Loading a retained analysis is distinct
from repeating inference.

This is the `full` capability: NLTK, spaCy, Transformers/Torch, scikit-learn,
OpenCV and Pillow belong to the optional Python 3.11 stack. Dependency-light
[shared methods](../../docs/shared-methods.md) must remain importable without
these engines. Do not add model initialization to generic evidence imports.
Use bounded numerical/image fixtures for changed algorithms; use the real
declared model smoke only when the change needs it. Coordinate heavyweight
inference and keep caches, temporary images and result epochs on GitVault.

New domain interpretations and manuscript claims belong in application repos.
Keep acquisition provenance, saved-result producer identity, runtime
qualification and literary interpretation as separate evidence.
