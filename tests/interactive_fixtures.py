"""Real corpus services and file-backed Rich prompt streams."""

import io

from rich.console import Console
import pytest_asyncio

from blake.interactive_orchestrator import InteractiveOrchestrator
from tests.gui_fixtures import seed_gui


@pytest_asyncio.fixture
async def terminal_case(tmp_path):
    handles = []

    async def create(input_text="", *, populated=True):
        data, output = tmp_path / "data", tmp_path / "output"
        if populated:
            seed_gui(data)
        prompt_file = tmp_path / ("input-" + str(len(handles)) + ".txt")
        prompt_file.write_text(input_text)
        stream = prompt_file.open()
        handles.append(stream)
        capture = io.StringIO()
        orchestrator = InteractiveOrchestrator(
            str(data),
            output_dir=output,
            console=Console(file=capture, width=140, force_terminal=False),
            input_stream=stream,
        )
        await orchestrator.initialize()
        return orchestrator, capture, stream

    yield create
    for handle in handles:
        handle.close()
