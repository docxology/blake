"""A small real retained-source capture for evidence interfaces."""

import pytest

from blake.recovery import recover_corpus
from tests.recovery_fixtures import COMMIT, seed_sources


@pytest.fixture
def captured_evidence(tmp_path):
    data = seed_sources(tmp_path)
    recover_corpus(data, commit=COMMIT, offline=True, images=False)
    return data
