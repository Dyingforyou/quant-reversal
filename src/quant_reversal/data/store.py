"""Incremental, de-duplicating storage for normalized market data."""
from pathlib import Path
from collections.abc import Sequence

import pandas as pd


class ParquetStore:
    """Upsert normalized rows into one local Parquet file."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def upsert(self, name: str, frame: pd.DataFrame, keys: Sequence[str]) -> int:
        if frame.empty:
            return 0
        path = self.root / f"{name}.parquet"
        incoming = frame.copy()
        if path.exists():
            incoming = pd.concat([pd.read_parquet(path), incoming], ignore_index=True)
        incoming = incoming.drop_duplicates(list(keys), keep="last").sort_values(list(keys))
        temporary = path.with_suffix(".parquet.tmp")
        incoming.to_parquet(temporary, index=False)
        temporary.replace(path)
        return len(frame)
