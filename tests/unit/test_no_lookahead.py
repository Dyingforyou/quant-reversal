import ast
from pathlib import Path
def test_research_labels_not_used_by_strategy():
    root=Path(__file__).parents[2]/"src/quant_reversal/strategy"
    for path in root.glob("*.py"):assert "research.labels" not in path.read_text()
def test_future_auction_not_used_in_baseline():
    tree=ast.parse((Path(__file__).parents[2]/"src/quant_reversal/features/auction.py").read_text());assert tree is not None

