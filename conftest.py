import sys
from pathlib import Path

# Make the archived `ucinsure` package importable during tests
sys.path.insert(0, str(Path(__file__).parent / "archive"))
