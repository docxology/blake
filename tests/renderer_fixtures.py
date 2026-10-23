"""Small deterministic processed inputs for native renderer checks."""

from datetime import datetime

from blake.viz.models import (
    ImageData,
    NetworkData,
    TemporalData,
    TextData,
    VisualizationConfig,
)


def renderer_inputs():
    works = [
        {
            "work_id": str(i),
            "title": "Synthetic work " + str(i),
            "date": f"{1790 + i}-01-01",
            "work_type": "poem",
            "themes": ["time"],
            "period": "early" if i < 5 else "late",
        }
        for i in range(6)
    ]
    return {
        "text": TextData(
            texts=["state time"],
            metadata=works[:2],
            word_frequencies={"state": 4, "time": 2},
            sentiment_scores=[0.5, -0.5, 0],
            avg_word_length=4,
            avg_sentence_length=2,
            vocabulary_richness=0.75,
        ),
        "image": ImageData(
            images=[
                {
                    "image_id": str(i),
                    "work_id": str(i),
                    "title": "Synthetic plate",
                    "width": 20,
                    "height": 10 if i < 2 else 0,
                }
                for i in range(3)
            ],
            metadata=works[:3],
            dominant_colors=[["#ff0000", "#00ff00"], ["#ff0000"], []],
            brightness_scores=[10, 20],
            contrast_scores=[2, 3],
            composition_scores=[{"balance": 0.5}] * 3,
            golden_ratio_scores=[0.9, 0.3, 0.6],
            similarity_matrix=[[1, 0.7, 0.2], [0.7, 1, 0.3], [0.2, 0.3, 1]],
            clusters=[0, 0, 1],
        ),
        "temporal": TemporalData(
            works=works,
            dates=[datetime(1790 + i, 1, 1) for i in range(6)],
            timeline_points=list(reversed(works)),
            periods=[
                {
                    "period": "early",
                    "start_year": 1790,
                    "end_year": 1794,
                    "work_count": 5,
                    "works": works[:5],
                },
                {
                    "period": "late",
                    "start_year": 1795,
                    "end_year": 1795,
                    "work_count": 1,
                    "works": works[5:],
                },
            ],
            theme_evolution={"time": works[:2], "state": works[2:3]},
        ),
        "network": NetworkData(
            nodes=[
                {"id": "a", "label": "A"},
                {"id": "b", "label": "B"},
                {"id": "c", "label": "C"},
            ],
            edges=[
                {"source": "a", "target": "b", "weight": 0.7},
                {"source": "b", "target": "c", "weight": 0.5},
            ],
            node_degrees=[1, 2, 1],
            clustering_coefficients=[0, 0, 0],
            centrality_scores={"degree": [0.5, 1, 0.5]},
            communities=[0, 0, 1],
        ),
        "comparative": {
            "left": {"id": "a"},
            "right": {"id": "b"},
            "differences": ["text"],
            "similarities": ["time"],
            "dimensions": ["words"],
            "values": [[1], [2]],
            "correlations": [1],
            "sources": ["archive", "synthetic"],
            "metrics": ["count"],
            "comparisons": [2],
            "fields": ["title"],
            "statistics": {"count": 2},
        },
    }


def renderer_config(kind, output=None):
    aliases = {
        "color_distribution": "color_heatmap",
        "composition_analysis": "composition_grid",
        "image_similarity_network": "similarity_network",
        "image_clustering": "clustering_visualization",
        "thematic_network": "theme_network",
    }
    return VisualizationConfig(
        viz_type=aliases.get(kind, kind),
        title="Synthetic validation",
        output_path=output,
    )
