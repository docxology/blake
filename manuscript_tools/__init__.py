"""Lightweight, stdlib-only manuscript tooling for the blake project.

This package is intentionally independent of the heavy ``blake`` analysis
package (torch/transformers/spaCy). It reads the JSON artifacts under
``analysis_output/`` and produces (a) the manuscript variable token table and
(b) the manuscript figures. Keeping it dependency-light means it imports cleanly
under the template repository's render venv during PDF hydration.
"""
