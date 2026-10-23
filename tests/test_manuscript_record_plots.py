"""Real Matplotlib geometry retains duplicated source/copy titles."""

import matplotlib.pyplot as plt
import pytest

from manuscript_tools.figures import _record_bars


def test_duplicate_titles_produce_distinct_bars_and_identifiable_ranked_labels():
    figure, axis = plt.subplots()
    try:
        rows = [
            {"work_id": "copy-a", "title": "Shared title"},
            {"work_id": "copy-b", "title": "Shared title"},
        ]
        bars = _record_bars(axis, rows, [12, 8], "blue")
        assert len(bars) == 2
        assert len({bar.get_y() for bar in bars}) == 2
        assert [bar.get_width() for bar in bars] == [12, 8]
        assert [tick.get_text() for tick in axis.get_yticklabels()] == [
            "1. Shared title",
            "2. Shared title",
        ]
        figure.canvas.draw()
    finally:
        plt.close(figure)


@pytest.mark.parametrize("values", [[1], [1, -1]])
def test_record_bar_errors_are_real(values):
    figure, axis = plt.subplots()
    try:
        with pytest.raises(ValueError, match="nonnegative"):
            _record_bars(axis, [{"title": "a"}, {"title": "b"}], values, "blue")
    finally:
        plt.close(figure)
