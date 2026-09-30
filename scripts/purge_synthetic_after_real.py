"""Remove project synthetic artifacts only after real normalized data is verified."""
from pathlib import Path
import shutil

import pandas as pd


PROJECT = Path("/home/admin/quant-reversal")
REAL_DAILY = PROJECT / "data/normalized/daily_bars.parquet"

if not REAL_DAILY.exists() or pd.read_parquet(REAL_DAILY).empty:
    raise SystemExit("真实日线尚未落库，拒绝清理模拟数据")

for directory in (PROJECT / "data/fixtures", PROJECT / "data/outputs"):
    if directory.exists():
        shutil.rmtree(directory)

mock_source = PROJECT / "frontend/src/mocks/data.ts"
if mock_source.exists():
    mock_source.unlink()
mock_dir = PROJECT / "frontend/src/mocks"
if mock_dir.exists() and not any(mock_dir.iterdir()):
    mock_dir.rmdir()

(PROJECT / "data/normalized/.synthetic_purged").touch()
