import sys
from pathlib import Path


ANALYST_DIRECTORY = Path(__file__).resolve().parents[1] / "analyst"

sys.path.insert(
    0,
    str(ANALYST_DIRECTORY),
)