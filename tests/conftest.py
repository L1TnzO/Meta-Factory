import sys
from pathlib import Path

# Make `metafactory` importable when pytest is invoked directly (without PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
