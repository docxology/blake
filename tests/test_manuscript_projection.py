"""Numerical oracles include rank-deficient and constant text spaces."""

import numpy as np
import pytest

from manuscript_tools.nlp_diagnostics import _build_tfidf_embedding


def documents(*tokens):
    return [
        {
            "work_id": str(i),
            "title": str(i),
            "tokens": row.split(),
            "word_count": len(row.split()),
        }
        for i, row in enumerate(tokens)
    ]


def test_rank_one_projection_cannot_report_the_same_variance_twice():
    result = _build_tfidf_embedding(documents("fire fire", "vision vision"))
    assert result["variance_pc1"] == pytest.approx(1.0)
    assert result["variance_pc2"] == pytest.approx(0.0, abs=1e-12)
    assert all(abs(row["pc2"]) < 1e-12 for row in result["points"])


def test_projection_variance_matches_an_independent_singular_value_oracle():
    result = _build_tfidf_embedding(
        documents("fire fire city", "city vision", "vision fire")
    )
    # Every term occurs in two documents, so IDF cancels under row normalization.
    matrix = np.array([[2.0, 1.0, 0.0], [0.0, 1.0, 1.0], [1.0, 0.0, 1.0]])
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix -= matrix.mean(axis=0)
    singular = np.linalg.svd(matrix, compute_uv=False)
    expected = singular[:2] ** 2 / np.sum(singular**2)
    actual = [result["variance_pc1"], result["variance_pc2"]]
    np.testing.assert_allclose(actual, expected, atol=1e-12)
    # A wrong second variance must be rejected by this same oracle.
    with pytest.raises(AssertionError):
        np.testing.assert_allclose([actual[0], actual[0]], expected, atol=1e-12)


def test_constant_text_space_has_no_explained_variance_or_displacement():
    result = _build_tfidf_embedding(
        documents("fire city vision", "fire city vision", "fire city vision")
    )
    assert result["variance_pc1"] == 0.0
    assert result["variance_pc2"] == 0.0
    assert all(row["pc1"] == 0.0 and row["pc2"] == 0.0 for row in result["points"])


@pytest.mark.parametrize("rows", [(), ("fire city",), ("fire", "fire"), ("", "")])
def test_insufficient_projection_dimensions_do_not_invent_axes(rows):
    result = _build_tfidf_embedding(documents(*rows))
    assert result["points"] == []
    assert result["variance_pc1"] == result["variance_pc2"] == 0.0
