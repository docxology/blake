from pathlib import Path
from typing import Optional

from .corpus import BlakeCorpus, CorpusConfig


class BlakeWorks(BlakeCorpus):
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        output_dir: Optional[Path] = None,
        config: Optional[CorpusConfig] = None,
    ):
        super().__init__(data_dir=data_dir, output_dir=output_dir, config=config)
