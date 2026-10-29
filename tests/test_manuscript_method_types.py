"""Numerical boundary controls for manuscript method typing."""
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw, ImageFont

from manuscript_tools.figures import _draw_wrapped, _pearson, _summary, _text_size
from manuscript_tools.method_types import ImageDepthRow, local_image_count


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ({"local_image_count": 0, "downloaded_image_count": 9}, 0),
        ({"local_image_count": None, "downloaded_image_count": 9}, 9),
        ({"downloaded_image_count": "12"}, 12),
        ({}, 0),
        ({"local_image_count": 3.9}, 3),
    ],
)
def test_local_count_preserves_evidence_precedence(row: ImageDepthRow, expected: int) -> None:
    # Given an image-depth evidence row.
    # When the local count is projected.
    count = local_image_count(row)
    # Then zero, fallback, and conversion semantics remain explicit.
    assert count == expected


def test_local_count_rejects_non_numeric_evidence() -> None:
    # Given an invalid source count.
    row: ImageDepthRow = {"local_image_count": "not-a-count"}
    # When conversion is attempted, then it must fail.
    with pytest.raises(ValueError):
        local_image_count(row)


def test_integer_sequences_retain_summary_statistics() -> None:
    # Given distinct integer measurements.
    values = (1, 2, 3, 6)
    # When summarized.
    summary = _summary(values)
    # Then the numerical result uses the established interpolation.
    assert summary == {
        "n": 4, "min": 1.0, "median": 2.5, "q1": 1.75,
        "q3": 3.75, "iqr": 2.0, "mean": 3.0, "max": 6.0,
    }


@pytest.mark.parametrize(
    ("xs", "ys", "expected"),
    [((1, 2, 3), (6, 4, 2), -1.0), ((1, 1), (3, 4), 0.0), ((), (), 0.0)],
)
def test_integer_sequences_retain_correlation(
    xs: tuple[int, ...], ys: tuple[int, ...], expected: float
) -> None:
    # Given the specified numerical pairs.
    # When Pearson correlation is calculated.
    correlation = _pearson(xs, ys)
    # Then the signed or degenerate result is preserved.
    assert correlation == expected


def test_bitmap_font_can_draw_wrapped_lines() -> None:
    # Given Pillow's actual bitmap font, which has no size attribute.
    font = ImageFont.load_default_imagefont()
    with Image.new("RGB", (200, 80), "white") as image:
        draw = ImageDraw.Draw(image)
        # When wrapped text is laid out.
        _draw_wrapped(draw, (0, 0), "Alpha beta gamma delta", font, "black", 50)
        # Then measurable glyphs and changed pixels are present.
        assert _text_size(draw, "Alpha", font)[0] > 0
        assert image.getextrema()[0][0] == 0
