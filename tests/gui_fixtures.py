"""A synthetic SQLite collection for native Streamlit application tests."""

from pathlib import Path

from blake.metadata.database import MetadataDatabase
from blake.models import WorkType
from tests.export_fixtures import export_work


def seed_gui(root: Path, *, empty_only: bool = False):
    root.mkdir(parents=True, exist_ok=True)
    database = MetadataDatabase(root / "metadata/metadata.db")
    rich = export_work(root / "input")
    empty = export_work(root / "empty", rich=False)
    empty.metadata.work_type = WorkType.LETTER
    if not empty_only:
        text_path = root / "texts/rich.txt"
        text_path.parent.mkdir()
        text_path.write_text(rich.text_content)
        rich.metadata.file_path = text_path
        rich.text_analysis["topics"] = {"topics": [{"words": ["states", "time"]}]}
        rich.images = [
            rich.images[0].model_copy(update={"id": "plate-" + str(i)})
            for i in range(4)
        ]
        rich.visual_analysis = {
            image.id: {"brightness": 0.25} for image in rich.images[:2]
        }
        database.save_work(rich)
        for kind in ("text", "visual", "cross"):
            database.save_analysis_result(
                rich.id, kind, getattr(rich, kind + "_analysis")
            )
    database.save_work(empty)
    return rich, empty


def app_source(data: Path, output: Path) -> str:
    return (
        "from pathlib import Path\n"
        "from blake.gui.gui import BlakeGUI\n"
        f"app = BlakeGUI(Path({str(data)!r}), Path({str(output)!r}))\n"
        "app.run()\n"
    )
